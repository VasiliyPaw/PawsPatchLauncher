param(
    [string]$ReleaseWorkspace = (Join-Path $PSScriptRoot '..\release_workspace_20260905')
)

$ErrorActionPreference = 'Stop'

$releaseRoot = [IO.Path]::GetFullPath($ReleaseWorkspace)
$sourcesRoot = [IO.Path]::GetFullPath((Join-Path $releaseRoot 'sources'))
$coreData = [IO.Path]::GetFullPath((Join-Path $sourcesRoot 'pawpatch-core\data'))
$arcaneData = [IO.Path]::GetFullPath((Join-Path $releaseRoot 'original_extract\Arcane Wars 0.82beta\data'))
$standardRoaming = [IO.Path]::GetFullPath((Join-Path $releaseRoot '..\..\roaming_spawn_backup_pre_x4_20260826'))
$baseRwd = [IO.Path]::GetFullPath((Join-Path $releaseRoot 'baseline_rwd'))
$localizedAutoexec = [IO.Path]::GetFullPath((Join-Path $sourcesRoot 'localization-ru\startup\autoexec.txt'))

foreach ($required in @($releaseRoot, $sourcesRoot, $coreData, $arcaneData, $standardRoaming, $baseRwd, $localizedAutoexec)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required source is missing: $required"
    }
}

function Reset-SourceDirectory([string]$name) {
    $target = [IO.Path]::GetFullPath((Join-Path $sourcesRoot $name))
    $allowedPrefix = $sourcesRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $target.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to reset a directory outside the release sources root: $target"
    }
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
    New-Item -ItemType Directory -Path $target | Out-Null
    return $target
}

function Copy-RelativeFile([string]$fromRoot, [string]$relative, [string]$toRoot) {
    $source = Join-Path $fromRoot $relative
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Required file is missing: $source"
    }
    $destination = Join-Path $toRoot $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Write-NoNewRoamingFiles([string]$targetRoot) {
    $arcaneLairs = @(
        'Buildings\LairsMonster\AW_scorpion_nest_grim.tgi',
        'Buildings\LairsMonster\AW_spider_lair_grim.tgi',
        'Buildings\LairsMonster\dark_rift.tgi',
        'Buildings\LairsMonster\haunted_ruin_lich.tgi',
        'Buildings\LairsMonster\haunted_ruin_skeleton.tgi'
    )
    foreach ($relative in $arcaneLairs) {
        Copy-RelativeFile $arcaneData $relative $targetRoot
    }

    $baseLairs = @(
        'scorpion_nest.tgi',
        'scorpion_nest_arctic.tgi',
        'scorpion_nest_temperate.tgi',
        'spider_lair.tgi',
        'spider_lair_arctic.tgi',
        'spider_lair_desert.tgi'
    )
    foreach ($fileName in $baseLairs) {
        Copy-RelativeFile $baseRwd "Buildings\LairsMonster\$fileName" $targetRoot
    }

    $foundationCamps = @(
        'Buildings\Camps\bandit_foundationcamp.tgi',
        'Buildings\Camps\barbarian_foundationcamp.tgi',
        'Buildings\Camps\rhaksha_foundationcamp.tgi',
        'Buildings\Camps\slaan_foundationcamp.tgi'
    )
    foreach ($relative in $foundationCamps) {
        Copy-RelativeFile $arcaneData $relative $targetRoot
    }

    $settlementOrganizations = [ordered]@{
        'bandit_settlementcamp.tgi' = 'militia_bandit'
        'barbarian_settlementcamp.tgi' = 'militia_tough_barbarian'
        'rhaksha_settlementcamp.tgi' = 'militia_rhaksha'
        'slaan_settlementcamp.tgi' = 'militia_tough_warrior'
    }
    foreach ($item in $settlementOrganizations.GetEnumerator()) {
        $relative = "Buildings\Camps\$($item.Key)"
        $source = Join-Path $coreData $relative
        $destination = Join-Path $targetRoot $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        $text = Get-Content -LiteralPath $source -Raw
        $text = [regex]::Replace($text, '(?m)^\s*organization_ids\s*=\s*\S+\s*$', "`torganization_ids = $($item.Value)")
        $text = [regex]::Replace($text, '(?m)^\s*event_time\s*=\s*\S+\s*$', "`tevent_time = 0")
        $text = [regex]::Replace($text, '(?m)^\s*event_chance\s*=\s*\S+\s*$', "`tevent_chance = 0.0")
        $text = [regex]::Replace($text, '(?m)^\s*marauder_chance\s*=\s*\S+\s*$', "`tmarauder_chance = 0")
        Set-Content -LiteralPath $destination -Value $text -Encoding utf8NoBOM -NoNewline
    }

    $units = @(
        'Units\Undead\skeleton.tgi',
        'Units\Undead\ghoul.tgi',
        'Units\Monster\AW_scorpion_grim.tgi',
        'Units\Monster\AW_spider_giant_grim.tgi',
        'Units\Monster\bandit.tgi',
        'Units\Monster\barbarian.tgi',
        'Units\Monster\scorpion.tgi',
        'Units\Monster\rhaksha.tgi',
        'Units\Monster\scorpion_arctic.tgi',
        'Units\Tech\warrior.tgi',
        'Units\Monster\shadow_lord.tgi',
        'Units\Monster\scorpion_temperate.tgi',
        'Units\Monster\spider_giant_arctic.tgi',
        'Units\Monster\spider_giant.tgi',
        'Units\Monster\spider_giant_desert.tgi'
    )
    foreach ($relative in $units) {
        Copy-RelativeFile $arcaneData $relative $targetRoot
    }
}

# startup\autoexec.txt is required even when Russian localization is disabled:
# it registers the game's writable work depot.  The localization package may
# override this file at a higher priority to add the Russian localized depot.
$startupBase = Reset-SourceDirectory 'startup-base'
$startupDestination = Join-Path $startupBase 'startup\autoexec.txt'
New-Item -ItemType Directory -Path (Split-Path -Parent $startupDestination) -Force | Out-Null
$startupText = Get-Content -LiteralPath $localizedAutoexec -Raw
$startupText = [regex]::Replace(
    $startupText,
    '(?m)^[ \t]*addlocaledepot[ \t]+localized/RU/Local_ru\.rwd[ \t]*$',
    '# addlocaledepot localized/RU/Local_ru.rwd')
if ($startupText -match '(?m)^[ \t]*addlocaledepot[ \t]+localized/RU/') {
    throw 'Failed to remove the active Russian depot from startup-base.'
}
if (-not $startupText.Contains('adddepot %USERDATA%/data/ 1', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'startup-base does not define the required writable work depot.'
}
Set-Content -LiteralPath $startupDestination -Value $startupText -Encoding utf8NoBOM -NoNewline

$standardWithNew = Reset-SourceDirectory 'roaming-profile-standard-with-new'
New-Item -ItemType Directory -Path (Join-Path $standardWithNew 'data') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $standardRoaming 'Buildings') -Destination (Join-Path $standardWithNew 'data\Buildings') -Recurse -Force

$x4NoNew = Reset-SourceDirectory 'roaming-profile-x4-no-new'
Write-NoNewRoamingFiles (Join-Path $x4NoNew 'data')

$standardNoNew = Reset-SourceDirectory 'roaming-profile-standard-no-new'
New-Item -ItemType Directory -Path (Join-Path $standardNoNew 'data') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $standardRoaming 'Buildings') -Destination (Join-Path $standardNoNew 'data\Buildings') -Recurse -Force
Write-NoNewRoamingFiles (Join-Path $standardNoNew 'data')

$siegeStandard = Reset-SourceDirectory 'siege-balance-standard'
foreach ($relative in @(
    'Units\CeyahAW\AW_plague_catapult.tgi',
    'Units\NationalistAW\AW_crimson_catapult.tgi',
    'Units\NationalistAW\AW_vorpal_engine.tgi',
    'Units\RoyalistAW\AW_dragonfire_balistae.tgi'
)) {
    Copy-RelativeFile $arcaneData $relative (Join-Path $siegeStandard 'data')
}

$largeMapsStandard = Reset-SourceDirectory 'large-map-sizes-standard'
$mapRelative = 'Templates\template_rmc_k2.tgi'
$mapSource = Join-Path $coreData $mapRelative
$mapDestination = Join-Path (Join-Path $largeMapsStandard 'data') $mapRelative
New-Item -ItemType Directory -Path (Split-Path -Parent $mapDestination) -Force | Out-Null
$mapText = Get-Content -LiteralPath $mapSource -Raw
foreach ($size in @(1024, 1152)) {
    $pattern = "(?m)\r?\n[ \t]*\[MapSize\][ \t]*\r?\n[ \t]*width[ \t]*=[ \t]*$size[ \t]*\r?\n[ \t]*height[ \t]*=[ \t]*$size[ \t]*\r?\n[ \t]*recommended_kingdoms_min[ \t]*=[ \t]*2[ \t]*\r?\n[ \t]*recommended_kingdoms_max[ \t]*=[ \t]*16[ \t]*\r?\n"
    $mapText = [regex]::Replace($mapText, $pattern, "`r`n")
}
if ($mapText -match '(?m)^\s*width\s*=\s*(1024|1152)\s*$') {
    throw 'Failed to remove the two Paw map sizes from the standard-map profile.'
}
if ($mapText -notmatch '(?m)^\s*width\s*=\s*960\s*$') {
    throw 'The standard-map profile unexpectedly lost the 960 map size.'
}
Set-Content -LiteralPath $mapDestination -Value $mapText -Encoding utf8NoBOM -NoNewline

# Original balance/roaming data must retain the current localization references.
# This changes quoted display strings only and verifies that all gameplay bytes are preserved.
$optionPython = 'C:\Users\Paw\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$optionRuStrings = Join-Path (Split-Path (Split-Path $localizedAutoexec)) 'Local_ru\Localization\strings_data_K2.tgi'
& $optionPython (Join-Path $PSScriptRoot 'RepairComponentLocalization.py') --repair-generated $sourcesRoot --core-source $coreData --ru-source $optionRuStrings
if ($LASTEXITCODE -ne 0) { throw 'Gameplay profiles failed localization preservation checks.' }
Write-Output "Prepared gameplay option sources in $sourcesRoot"
