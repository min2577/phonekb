# PhoneKB - USB mode (adb reverse)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$adb = $null
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Try direct exec of known-good paths. Use System.IO.File.Exists (no wildcard issues, handles unicode).
$candidates = @(
  (Join-Path $env:LOCALAPPDATA 'HBuilderX\plugins\launcher-tools\tools\adbs\adb.exe'),
  (Join-Path $env:PROGRAMFILES 'HBuilderX\plugins\launcher-tools\tools\adbs\adb.exe'),
  (Join-Path $scriptDir 'adb.exe')
)

foreach ($p in $candidates) {
  if ([string]::IsNullOrEmpty($p)) { continue }
  if ([System.IO.File]::Exists($p)) {
    $adb = $p
    break
  }
}

if (-not $adb) {
  $cmd = Get-Command adb -ErrorAction SilentlyContinue
  if ($cmd) { $adb = $cmd.Source }
}

if (-not $adb) {
  Write-Host ''
  Write-Host '[ERROR] adb.exe not found.' -ForegroundColor Red
  Write-Host 'Tried:'
  foreach ($p in $candidates) { Write-Host "  - $p" }
  Write-Host '  - PATH'
  Read-Host 'Press Enter to exit'
  exit 1
}

Write-Host "[INFO] adb = $adb" -ForegroundColor Cyan

$devicesOutput = & $adb devices 2>&1 | Out-String
Write-Host "[INFO] devices:" -ForegroundColor Cyan
Write-Host $devicesOutput

if ($devicesOutput -notmatch '\bdevice\b') {
  Write-Host '[WARN] no device detected. Check USB cable + USB debugging on phone.' -ForegroundColor Yellow
  Start-Sleep -Seconds 2
}
Write-Host ''

Write-Host '[1/2] adb reverse tcp:9877 tcp:9877' -ForegroundColor Yellow
& $adb reverse tcp:9877 tcp:9877
if ($LASTEXITCODE -ne 0) {
  Write-Host '[ERROR] adb reverse failed.' -ForegroundColor Red
  Read-Host 'Press Enter to exit'
  exit 1
}
Write-Host 'OK' -ForegroundColor Green
Write-Host ''

Write-Host '[2/2] current tunnels:' -ForegroundColor Yellow
& $adb reverse --list
Write-Host ''

Write-Host '========================================================' -ForegroundColor Green
Write-Host '  USB mode ready. Open the App, choose USB, connect.' -ForegroundColor Green
Write-Host '========================================================' -ForegroundColor Green
Read-Host 'Press Enter to exit'
exit 0
