param(
    [Parameter(Mandatory=$true)][string]$GameRoot,
    [Parameter(Mandatory=$true)][string]$ArtifactRoot
)
$ErrorActionPreference = 'Stop'
$gameDir = (Resolve-Path -LiteralPath $GameRoot).Path
$artifactDir = (Resolve-Path -LiteralPath $ArtifactRoot).Path
if (Get-Process k2,PawsPatchLauncher,PawsLairSurvivorTest -ErrorAction SilentlyContinue) {
    throw 'Close the game and launcher before installing the temporary HUD.'
}
if (-not (Test-Path -LiteralPath (Join-Path $gameDir 'k2.exe'))) { throw 'Not a Kohan II game directory.' }
$races = @('Human','Gauri','Drauga','Haroun','Undead','Shadow')
$variants = @('UI/Game/ControlPanel','UI/800/Game/ControlPanel','UI/1280/Game/ControlPanel')
$expected = @($races | ForEach-Object { $race = $_; $variants | ForEach-Object { "skins/$race/$_/Background.tga" } })
$rows = @(Import-Csv -LiteralPath (Join-Path $artifactDir 'assets.tsv') -Delimiter "`t")
if ($rows.Count -ne 18 -or @(Compare-Object ($expected | Sort-Object) ($rows.path | Sort-Object)).Count -ne 0) { throw 'Unexpected asset list.' }
function CheckedTarget([string]$relative) {
    if ($relative -notin $expected) { throw "Unexpected path: $relative" }
    $full = [IO.Path]::GetFullPath((Join-Path $gameDir $relative))
    if (-not $full.StartsWith((Join-Path $gameDir 'skins') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escaped skins.' }
    return $full
}
function Hash([string]$path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
foreach ($row in $rows) {
    $path = Join-Path $artifactDir ('payload/' + $row.path)
    if ((Hash $path) -ne $row.sha256) { throw "Payload mismatch: $($row.path)" }
    $null = CheckedTarget $row.path
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = Join-Path $artifactDir ('backups/' + $stamp)
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$protected = @('k2.exe','.pawpatch/state.json','paws_patch_versions.ini','paws_launch_versions.ini','paws_player_colors.ini','paws_game_text.ini')
$protected += @(Get-ChildItem -LiteralPath $gameDir -Filter 'k2_paws*.exe' -File | ForEach-Object { $_.Name })
$protected += @($races | ForEach-Object { 'skins/' + $_ + '.rwd' })
$beforeProtected = @($protected | Where-Object { Test-Path -LiteralPath (Join-Path $gameDir $_) } | ForEach-Object { [ordered]@{path=$_;sha256=(Hash (Join-Path $gameDir $_))} })
$entries = @()
foreach ($row in $rows) {
    $target = CheckedTarget $row.path
    $existed = Test-Path -LiteralPath $target
    $oldHash = $null
    if ($existed) {
        $oldHash = Hash $target
        if ($oldHash -ne $row.sourceSha256) { throw "An existing custom frame needs review before replacement: $($row.path)" }
        $backup = Join-Path $backupDir $row.path
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
        Copy-Item -LiteralPath $target -Destination $backup
        if ((Hash $backup) -ne $oldHash) { throw 'Backup verification failed.' }
    }
    $entries += [ordered]@{path=$row.path;existedBefore=$existed;beforeSha256=$oldHash;installedSha256=$row.sha256;archiveAssetSha256=$row.sourceSha256}
}
$receipt = [ordered]@{schemaVersion=1;id='minimap-frame-local-16x9-r1';gameRoot=$gameDir;artifactRoot=$artifactDir;backupRoot=$backupDir;installedAt=(Get-Date).ToString('o');screenAspect='16:9';referenceResolution='2560x1440';published=$false;files=$entries;protectedFiles=$beforeProtected;status='prepared'}
$receiptPath = Join-Path $backupDir 'installation.json'
$receipt | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
$written = @()
try {
    foreach ($entry in $entries) {
        $target = CheckedTarget $entry.path
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath (Join-Path $artifactDir ('payload/' + $entry.path)) -Destination $target
        $written += $entry
        if ((Hash $target) -ne $entry.installedSha256) { throw 'Installed frame verification failed.' }
    }
    foreach ($item in $beforeProtected) {
        if ((Hash (Join-Path $gameDir $item.path)) -ne $item.sha256) { throw "Protected file changed: $($item.path)" }
    }
    $receipt.status = 'installed'
    $receipt | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    Copy-Item -LiteralPath $receiptPath -Destination (Join-Path $artifactDir 'installed.json')
    Write-Output "Installed and verified 18 racial HUD textures. Receipt: $receiptPath"
} catch {
    foreach ($entry in $written) {
        $target = CheckedTarget $entry.path
        if ($entry.existedBefore) { Copy-Item -LiteralPath (Join-Path $backupDir $entry.path) -Destination $target }
        elseif (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target }
    }
    $receipt.status = 'rolled-back-after-error'
    $receipt | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    throw
}
