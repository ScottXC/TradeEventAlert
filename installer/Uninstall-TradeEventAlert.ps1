$ErrorActionPreference = "SilentlyContinue"

$appName = "TradeEventAlert"
$installDir = Join-Path (Join-Path $env:LOCALAPPDATA "Programs") $appName
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$appName"
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$appName"

Get-Process -Name $appName -ErrorAction SilentlyContinue | Stop-Process -Force

Remove-Item -LiteralPath $desktopShortcut -Force
Remove-Item -LiteralPath $startMenuDir -Recurse -Force
Remove-Item -LiteralPath $uninstallKey -Recurse -Force

$cleanup = Join-Path $env:TEMP "$appName-cleanup.cmd"
$installDirForCmd = $installDir.Replace('"', '""')
Set-Content -LiteralPath $cleanup -Encoding ASCII -Value @"
@echo off
timeout /t 2 /nobreak >nul
rmdir /s /q "$installDirForCmd"
del "%~f0" >nul 2>nul
"@

Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$cleanup`"" -WindowStyle Hidden

Write-Host "Trade Event Alert has been uninstalled."
Write-Host "User configuration, API keys, and local alert database are intentionally kept under %APPDATA%\TradeEventAlert."
