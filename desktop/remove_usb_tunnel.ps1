# remove_usb_tunnel.ps1 — 拆掉 PhoneKB 的 USB 反向隧道
$ErrorActionPreference = 'SilentlyContinue'

$adb = $null
$candidates = @(
  (Join-Path $env:LOCALAPPDATA 'HBuilderX\plugins\launcher-tools\tools\adbs\adb.exe'),
  (Join-Path $env:PROGRAMFILES 'HBuilderX\plugins\launcher-tools\tools\adbs\adb.exe'),
  (Join-Path $PSScriptRoot 'adb.exe')
)
foreach ($p in $candidates) {
  if ($p -and (Test-Path $p)) { $adb = $p; break }
}
if (-not $adb) {
  $cmd = Get-Command adb -ErrorAction SilentlyContinue
  if ($cmd) { $adb = $cmd.Source }
}

if (-not $adb) {
  Write-Host '[WARN] adb not found, USB tunnel not removed.' -ForegroundColor Yellow
  exit 0
}

Write-Host "[INFO] adb = $adb"
& $adb reverse --remove tcp:9877 | Out-Null
Write-Host ''
Write-Host '[INFO] remaining tunnels:'
& $adb reverse --list
