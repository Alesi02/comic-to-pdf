$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$localPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $localPython) {
    $appPython = $localPython
} elseif (Test-Path -LiteralPath $bundledPython) {
    $appPython = $bundledPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host 'Setting up the local Python environment...'
    & py -3 -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $appPython = $localPython
} else {
    Write-Host 'Install Python 3.12 or newer with the Python launcher, then run Start.cmd again.'
    exit 1
}
& $appPython -c "import sys, importlib.util; sys.path.insert(0, '.vendor'); sys.exit(0 if all(importlib.util.find_spec(m) for m in ('img2pdf', 'rarfile')) else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing conversion libraries (internet needed for initial setup)...'
    & $appPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $appPython (Join-Path $PSScriptRoot 'app.py')
exit $LASTEXITCODE

