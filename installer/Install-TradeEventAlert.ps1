$ErrorActionPreference = "Stop"

$appName = "TradeEventAlert"
$installRoot = Join-Path $env:LOCALAPPDATA "Programs"
$installDir = Join-Path $installRoot $appName
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$appName"
$desktopDir = [Environment]::GetFolderPath("Desktop")
$desktopShortcut = Join-Path $desktopDir "$appName.lnk"
$startShortcut = Join-Path $startMenuDir "$appName.lnk"
$exePath = Join-Path $installDir "$appName.exe"
$uninstallPath = Join-Path $installDir "Uninstall-$appName.ps1"

New-Item -ItemType Directory -Force -Path $installDir | Out-Null
New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null

Copy-Item -LiteralPath ".\$appName.exe" -Destination $exePath -Force
Copy-Item -LiteralPath ".\Uninstall-$appName.ps1" -Destination $uninstallPath -Force

$shell = New-Object -ComObject WScript.Shell

$startLink = $shell.CreateShortcut($startShortcut)
$startLink.TargetPath = $exePath
$startLink.WorkingDirectory = $installDir
$startLink.IconLocation = $exePath
$startLink.Description = "Trade Event Alert"
$startLink.Save()

$desktopLink = $shell.CreateShortcut($desktopShortcut)
$desktopLink.TargetPath = $exePath
$desktopLink.WorkingDirectory = $installDir
$desktopLink.IconLocation = $exePath
$desktopLink.Description = "Trade Event Alert"
$desktopLink.Save()

$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$appName"
New-Item -Force -Path $uninstallKey | Out-Null
New-ItemProperty -Force -Path $uninstallKey -Name "DisplayName" -Value "Trade Event Alert" -PropertyType String | Out-Null
New-ItemProperty -Force -Path $uninstallKey -Name "DisplayVersion" -Value "1.0.0" -PropertyType String | Out-Null
New-ItemProperty -Force -Path $uninstallKey -Name "Publisher" -Value "Local Codex Build" -PropertyType String | Out-Null
New-ItemProperty -Force -Path $uninstallKey -Name "InstallLocation" -Value $installDir -PropertyType String | Out-Null
New-ItemProperty -Force -Path $uninstallKey -Name "DisplayIcon" -Value $exePath -PropertyType String | Out-Null
New-ItemProperty -Force -Path $uninstallKey -Name "UninstallString" -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$uninstallPath`"" -PropertyType String | Out-Null
New-ItemProperty -Force -Path $uninstallKey -Name "NoModify" -Value 1 -PropertyType DWord | Out-Null
New-ItemProperty -Force -Path $uninstallKey -Name "NoRepair" -Value 1 -PropertyType DWord | Out-Null

Write-Host "Trade Event Alert has been installed to: $installDir"
Write-Host "User configuration and API keys are stored separately under %APPDATA%\TradeEventAlert and are not packaged by this installer."
