param([Parameter(Mandatory=$true)][string]$ReceiptPath)
$ErrorActionPreference = 'Stop'
if (Get-Process k2,PawsPatchLauncher,PawsLairSurvivorTest -ErrorAction SilentlyContinue) { throw 'Close the game and launcher before restoring the HUD.' }
$receipt = Get-Content -Raw -LiteralPath $ReceiptPath | ConvertFrom-Json
if ($receipt.schemaVersion -ne 1 -or $receipt.id -ne 'minimap-frame-local-16x9-r1' -or $receipt.status -ne 'installed') { throw 'Invalid or already restored receipt.' }
$gameDir = (Resolve-Path -LiteralPath $receipt.gameRoot).Path
$backupDir = (Resolve-Path -LiteralPath $receipt.backupRoot).Path
$races = @('Human','Gauri','Drauga','Haroun','Undead','Shadow')
$variants = @('UI/Game/ControlPanel','UI/800/Game/ControlPanel','UI/1280/Game/ControlPanel')
$expected = @($races | ForEach-Object { $race=$_; $variants | ForEach-Object { "skins/$race/$_/Background.tga" } })
if ($receipt.files.Count -ne 18 -or @(Compare-Object ($expected | Sort-Object) ($receipt.files.path | Sort-Object)).Count -ne 0) { throw 'Unexpected restore targets.' }
function CheckedPath([string]$root,[string]$relative) {
    if ($relative -notin $expected) { throw 'Unexpected file path.' }
    $full=[IO.Path]::GetFullPath((Join-Path $root $relative))
    if (-not $full.StartsWith($root + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Restore path escaped the expected directory.' }
    return $full
}
function Hash([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash }
# Validate every path and backup before changing any file. Never remove a later edit.
foreach ($entry in $receipt.files) {
    $target=CheckedPath $gameDir $entry.path
    if (-not (Test-Path -LiteralPath $target) -or (Hash $target) -ne $entry.installedSha256) { throw "Frame changed since installation; review required: $($entry.path)" }
    if ($entry.existedBefore -and (Hash (CheckedPath $backupDir $entry.path)) -ne $entry.beforeSha256) { throw 'Backup mismatch.' }
}
foreach ($entry in $receipt.files) {
    $target=CheckedPath $gameDir $entry.path
    if ($entry.existedBefore) {
        Copy-Item -LiteralPath (CheckedPath $backupDir $entry.path) -Destination $target
        if ((Hash $target) -ne $entry.beforeSha256) { throw 'Restored file mismatch.' }
    } else {
        # Exactly this trial-created file; never a recursive directory deletion.
        Remove-Item -LiteralPath $target
        if (Test-Path -LiteralPath $target) { throw 'Trial texture was not removed.' }
    }
}
$receipt.status='restored'
$receipt | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8
Write-Output 'All 18 original frame states restored.'
