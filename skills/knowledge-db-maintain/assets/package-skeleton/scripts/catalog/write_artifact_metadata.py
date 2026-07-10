from __future__ import annotations

import argparse
from pathlib import Path

from .metadata import write_artifact_metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--public-base-url", required=True)
    parser.add_argument("--object-prefix", required=True)
    parser.add_argument("--latest-object-key", required=True)
    parser.add_argument("--builder-metadata", type=Path, required=True)
    parser.add_argument("--timings", type=Path, required=True)
    args = parser.parse_args()

    write_artifact_metadata(
        out_dir=args.out_dir,
        source_repo=args.source_repo,
        source_ref=args.source_ref,
        source_revision=args.source_revision,
        version=args.version,
        package_name=args.package_name,
        public_base_url=args.public_base_url,
        object_prefix=args.object_prefix,
        latest_object_key=args.latest_object_key,
        builder_metadata_path=args.builder_metadata,
        timings_path=args.timings,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
