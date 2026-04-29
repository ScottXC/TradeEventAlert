$ErrorActionPreference = "Stop"

$BundledPython = "C:\Users\scott\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if ($env:TRADE_ALERT_PYTHON) {
    $Python = $env:TRADE_ALERT_PYTHON
} elseif (Test-Path $BundledPython) {
    $Python = $BundledPython
} else {
    $Python = "python"
}

$DepsDir = Join-Path $PSScriptRoot ".build_deps"
New-Item -ItemType Directory -Force -Path $DepsDir | Out-Null

$TmpDir = Join-Path $PSScriptRoot ".tmp"
New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null
$env:TEMP = $TmpDir
$env:TMP = $TmpDir
$env:PIP_CACHE_DIR = Join-Path $PSScriptRoot ".pip_cache"

& $Python -m pip install --upgrade --target $DepsDir -r (Join-Path $PSScriptRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed with exit code $LASTEXITCODE"
}

$OldPythonPath = $env:PYTHONPATH
if ($OldPythonPath) {
    $env:PYTHONPATH = "$DepsDir;$OldPythonPath"
} else {
    $env:PYTHONPATH = $DepsDir
}

$IconPath = Join-Path $PSScriptRoot "assets\app.ico"
$IconArgs = @()
if (Test-Path $IconPath) {
    $IconArgs = @("--icon", $IconPath, "--add-data", "$IconPath;assets")
}

& $Python -m PyInstaller --clean --noconfirm --onefile --windowed --name TradeEventAlert @IconArgs --distpath .\dist --workpath .\build --specpath .\build .\src\trade_alert_app.py
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Build complete: .\dist\TradeEventAlert.exe"
