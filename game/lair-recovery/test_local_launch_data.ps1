param(
    [Parameter(Mandatory=$true)][string]$Executable,
    [Parameter(Mandatory=$true)][string]$GameRoot,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
$exe=[IO.Path]::GetFullPath($Executable)
$root=[IO.Path]::GetFullPath($GameRoot)
$out=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $out){throw 'Choose an unused fixture directory.'}
New-Item -ItemType Directory -Path $out | Out-Null
# Reproduce the actual failure: the user-facing EXE has no adjacent INI/data.
foreach($file in 'paws_patch_versions.ini','paws_player_colors.ini','paws_game_text.ini','data\UI\Menus\main.tgi') {
    if(Test-Path -LiteralPath (Join-Path (Split-Path -Parent $exe) $file)){throw "Not an isolated test EXE: $file"}
}
$files=@('paws_patch_versions.ini','paws_player_colors.ini','paws_game_text.ini','data\UI\Menus\main.tgi','data\UI\Menus\pcolors.tgi')
$results=@()
function Check-Data([string]$name,[string]$folder,[int]$expected,[string]$language) {
    $stdout=Join-Path $out ($name+'.stdout.txt')
    $stderr=Join-Path $out ($name+'.stderr.txt')
    $run=Start-Process -FilePath $exe -ArgumentList ('--local-data-check "'+$folder+'"') -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $text=[IO.File]::ReadAllText($stdout)
    if($run.ExitCode -ne $expected){throw "$name returned $($run.ExitCode), expected $expected. $([IO.File]::ReadAllText($stderr))"}
    if($expected -eq 0 -and $text.Trim() -ne ('LOCAL_DATA_PASS language='+$language)){throw "Wrong selected catalog for $name : $text"}
    $script:results += [ordered]@{case=$name;exitCode=$run.ExitCode;result='PASS'}
}
$installedLanguage=([IO.File]::ReadLines((Join-Path $root 'paws_game_text.ini')) | Select-Object -First 1).Substring(9)
Check-Data 'installed-root' $root 0 $installedLanguage
foreach($case in 'external-valid','missing-versions','missing-main','missing-palette','missing-color-menu','invalid-catalog') {
    $fixture=Join-Path $out $case
    New-Item -ItemType Directory -Path (Join-Path $fixture 'data\UI\Menus') -Force | Out-Null
    foreach($file in $files) {
        if(($case -eq 'missing-versions' -and $file -eq 'paws_patch_versions.ini') -or
           ($case -eq 'missing-main' -and $file -eq 'data\UI\Menus\main.tgi') -or
           ($case -eq 'missing-palette' -and $file -eq 'paws_player_colors.ini') -or
           ($case -eq 'missing-color-menu' -and $file -eq 'data\UI\Menus\pcolors.tgi')) {continue}
        Copy-Item -LiteralPath (Join-Path $root $file) -Destination (Join-Path $fixture $file)
    }
    if($case -eq 'external-valid') {
        [IO.File]::WriteAllText((Join-Path $fixture 'paws_game_text.ini'),"language=uk`n",[Text.UTF8Encoding]::new($false))
        Check-Data $case $fixture 0 'uk'
    } else {
        if($case -eq 'invalid-catalog') {
            [IO.File]::WriteAllText((Join-Path $fixture 'paws_game_text.ini'),"language=invalid`n",[Text.UTF8Encoding]::new($false))
        }
        Check-Data $case $fixture 2 ''
    }
}
$preflight=Start-Process -FilePath $exe -ArgumentList ('--preflight "'+$root+'"') -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $out 'preflight.stdout.txt') -RedirectStandardError (Join-Path $out 'preflight.stderr.txt')
if($preflight.ExitCode -ne 0){throw 'Full installed-game preflight failed.'}
$results += [ordered]@{case='full-preflight';exitCode=$preflight.ExitCode;result='PASS'}
[ordered]@{checks=$results.Count;gameLaunched=$false;executable=$exe;results=$results} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'results.json') -Encoding UTF8
Write-Output "LOCAL_LAUNCH_DATA_PASS $($results.Count) checks; external EXE, selected installation/catalog, four missing dependencies and invalid catalog; no game launched."
