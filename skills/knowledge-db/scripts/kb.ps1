[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "kb.py"

if (-not (Test-Path -LiteralPath $pythonScript)) {
    Write-Error "Cannot find kb.py beside kb.ps1: $pythonScript"
    exit 127
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
    Invoke-KbPython -Command $env:KB_PYTHON
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    Invoke-KbPython -Command $python.Source
}

$python3 = Get-Command python3 -ErrorAction SilentlyContinue
if ($python3) {
    Invoke-KbPython -Command $python3.Source
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    Invoke-KbPython -Command $py.Source -PrefixArgs @("-3")
}

Write-Error "No Python interpreter found. Set KB_PYTHON to the Python executable path."
exit 127
