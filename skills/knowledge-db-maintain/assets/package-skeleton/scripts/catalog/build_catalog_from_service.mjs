#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) {
      throw new Error(`invalid argument near ${key ?? "<end>"}`);
    }
    args[key.slice(2)] = value;
  }
  return args;
}

function requireArg(args, name) {
  const value = args[name];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`missing required argument: --${name}`);
  }
  return value;
}

function moduleUrl(serviceRoot, relativePath) {
  return pathToFileURL(join(serviceRoot, relativePath)).href;
}

function serviceRevision(serviceRoot, fallback) {
  try {
    return execFileSync("git", ["-C", serviceRoot, "rev-parse", "HEAD"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return fallback;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const serviceRoot = resolve(requireArg(args, "service-root"));
  const kbRoot = resolve(requireArg(args, "kb"));
  const packageName = requireArg(args, "package-name");
  const revision = requireArg(args, "revision");
  const outDir = resolve(requireArg(args, "out"));
  const catalogPath = join(outDir, "catalog.sqlite");
  const metadataPath = join(outDir, "builder-metadata.json");

  await mkdir(dirname(catalogPath), { recursive: true });

  const { createKnowledgeDatabase } = await import(
    moduleUrl(serviceRoot, "src/kb/database.ts")
  );
  const { createKnowledgeCatalog } = await import(
    moduleUrl(serviceRoot, "src/kb/catalog.ts")
  );
  const { validateKnowledgePackage } = await import(
    moduleUrl(serviceRoot, "src/kb/validation.ts")
  );

  const generator = {
    name: "knowledge-service-catalog-builder",
    version: serviceRevision(serviceRoot, revision),
  };
  const timingsMs = {
    validate: 0,
    buildCatalog: 0,
  };
  const database = createKnowledgeDatabase(catalogPath);

  try {
    const validateStart = Date.now();
    const report = await validateKnowledgePackage({
      packageName,
      rootPath: kbRoot,
      revision,
    });
    timingsMs.validate = Date.now() - validateStart;

    const validation = {
      ok: report.ok,
      errorCount: report.errors.length,
      warningCount: report.warnings.length,
      entryCount: report.entries.length,
    };

    if (!report.ok) {
      await writeFile(
        metadataPath,
        `${JSON.stringify({ generator, validation, timingsMs }, null, 2)}\n`,
        "utf8"
      );
      await writeFile(
        join(outDir, "validation-report.json"),
        `${JSON.stringify(report, null, 2)}\n`,
        "utf8"
      );
      process.exitCode = 2;
      return;
    }

    const buildStart = Date.now();
    const catalog = createKnowledgeCatalog(database);
    catalog.loadValidatedPackageSnapshot(
      {
        packageName,
        rootPath: kbRoot,
        revision,
      },
      report
    );
    timingsMs.buildCatalog = Date.now() - buildStart;

    await writeFile(
      metadataPath,
      `${JSON.stringify({ generator, validation, timingsMs }, null, 2)}\n`,
      "utf8"
    );
  } finally {
    database.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
