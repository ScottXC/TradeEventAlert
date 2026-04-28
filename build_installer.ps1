$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$appName = "TradeEventAlert"
$distExe = Join-Path $root "dist\$appName.exe"
$installerSource = Join-Path $root "installer"
$payloadDir = Join-Path $root ".installer_payload"
$outputDir = Join-Path $root "installer_dist"
$sedPath = Join-Path $payloadDir "$appName.sed"
$installerExe = Join-Path $outputDir "$appName-Setup.exe"
$iexpress = Join-Path $env:WINDIR "System32\iexpress.exe"

if (!(Test-Path -LiteralPath $distExe)) {
    throw "Missing $distExe. Run .\build_exe.ps1 first."
}
if (!(Test-Path -LiteralPath $iexpress)) {
    throw "iexpress.exe was not found on this Windows installation."
}

Remove-Item -LiteralPath $payloadDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $payloadDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Copy-Item -LiteralPath $distExe -Destination (Join-Path $payloadDir "$appName.exe") -Force
Copy-Item -LiteralPath (Join-Path $installerSource "Install-$appName.ps1") -Destination $payloadDir -Force
Copy-Item -LiteralPath (Join-Path $installerSource "Uninstall-$appName.ps1") -Destination $payloadDir -Force

$payloadFiles = Get-ChildItem -LiteralPath $payloadDir -File | Select-Object -ExpandProperty Name
$forbidden = $payloadFiles | Where-Object {
    $_ -match "config|sqlite|token|key|secret|\.db|\.json"
}
if ($forbidden) {
    throw "Installer payload contains forbidden/sensitive-looking files: $($forbidden -join ', ')"
}

$escapedPayloadDir = $payloadDir.TrimEnd("\")
$escapedInstallerExe = $installerExe

$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3

[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AdminQuietInstCmd%
UserQuietInstCmd=%UserQuietInstCmd%
SourceFiles=SourceFiles

[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=Trade Event Alert installation completed.
TargetName=$escapedInstallerExe
FriendlyName=Trade Event Alert Installer
AppLaunched=powershell.exe -NoProfile -ExecutionPolicy Bypass -File Install-$appName.ps1
PostInstallCmd=<None>
AdminQuietInstCmd=powershell.exe -NoProfile -ExecutionPolicy Bypass -File Install-$appName.ps1
UserQuietInstCmd=powershell.exe -NoProfile -ExecutionPolicy Bypass -File Install-$appName.ps1
FILE0="$appName.exe"
FILE1="Install-$appName.ps1"
FILE2="Uninstall-$appName.ps1"

[SourceFiles]
SourceFiles0=$escapedPayloadDir

[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"@

Set-Content -LiteralPath $sedPath -Encoding ASCII -Value $sed

Start-Process -FilePath $iexpress -ArgumentList "/N", $sedPath -Wait | Out-Null

if (!(Test-Path -LiteralPath $installerExe)) {
    throw "Installer was not created: $installerExe"
}

Write-Host "Installer created: $installerExe"
Write-Host "Payload checked: only app exe and install/uninstall scripts were packaged. User API keys and %APPDATA%\TradeEventAlert are not included."
