[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
try {
    [Console]::InputEncoding = $utf8NoBom
    [Console]::OutputEncoding = $utf8NoBom
} catch {
    # Some non-interactive hosts do not expose a mutable console.
}
$OutputEncoding = $utf8NoBom
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "kb.py"

if (-not (Test-Path -LiteralPath $pythonScript)) {
    Write-Error "Cannot find kb.py beside kb.ps1: $pythonScript"
    exit 127
}

function Test-KbPython {
    param(
        [string]$Command,
        [string[]]$PrefixArgs = @()
    )

    try {
        & $Command @PrefixArgs -c "import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Invoke-KbPython {
    param(
        [string]$Command,
        [string[]]$PrefixArgs = @()
    )

    & $Command @PrefixArgs $pythonScript @RemainingArgs
    exit $LASTEXITCODE
}

if ($env:KB_PYTHON) {
    if (Test-KbPython -Command $env:KB_PYTHON) {
        Invoke-KbPython -Command $env:KB_PYTHON
    }
    Write-Error "KB_PYTHON is not a usable Python 3 interpreter: $env:KB_PYTHON"
    exit 127
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python -and (Test-KbPython -Command $python.Source)) {
    Invoke-KbPython -Command $python.Source
}

$python3 = Get-Command python3 -ErrorAction SilentlyContinue
if ($python3 -and (Test-KbPython -Command $python3.Source)) {
    Invoke-KbPython -Command $python3.Source
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py -and (Test-KbPython -Command $py.Source -PrefixArgs @("-3"))) {
    Invoke-KbPython -Command $py.Source -PrefixArgs @("-3")
}

Write-Error "No Python interpreter found. Set KB_PYTHON to the Python executable path."
exit 127
