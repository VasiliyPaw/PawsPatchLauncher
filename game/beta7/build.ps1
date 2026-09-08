param([Parameter(Mandatory=$true)][string]$OutputDirectory, [switch]$CityAssistant)
$ErrorActionPreference = 'Stop'
$out = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $out) { throw 'Choose an unused output directory.' }
New-Item -ItemType Directory -Path $out | Out-Null
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
$variants = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'variants.json') -Raw | ConvertFrom-Json
$shared = 'TerrainRuntime.cs','RandomMapPatch.cs','ReleaseStartup.cs','LobbyColorsNative.cs','GamePresentation1372.cs','RandomMapBundle.cs','BuildFeatures.cs'
$resources = 'PawLobbyColorsPayload','PawLobbyColorsFixups','PawCommonUiPayload','PawCommonUiFixups','RandomMapPayload','RandomMapFixups'
$assistant = Join-Path $PSScriptRoot '../city-assistant'
function Replace-StartupAnchor([string]$text, [string]$before, [string]$after) {
    if (($text.Split([string[]]@($before),[StringSplitOptions]::None).Length-1) -ne 1) { throw "Startup source anchor changed: $before" }
    return $text.Replace($before,$after)
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'paws_player_colors.ini') -Destination $out
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'paws_patch_versions.ini') -Destination $out
foreach ($variant in $variants.PSObject.Properties) {
    $exe = Join-Path $out $variant.Name
    $arguments = @('/nologo','/target:winexe','/platform:x86','/optimize+',
        '/r:System.Core.dll','/r:System.Windows.Forms.dll','/r:System.Drawing.dll',
        ("/define:" + $variant.Value + $(if($CityAssistant){';CITY_ASSISTANT'}else{''})), ("/out:" + $exe))
    foreach ($resource in $resources) { $arguments += '/resource:' + (Join-Path $PSScriptRoot "$resource.bin") + ',' + $resource }
    $source = if ($variant.Name.StartsWith('k2_paws_lobby_colors_mp_nohostility')) { 'k2_paws_lobby_colors_mp_1372_experimental.cs' } else { [IO.Path]::GetFileNameWithoutExtension($variant.Name) + '.cs' }
    $sourcePath = Join-Path $PSScriptRoot $source
    if ($CityAssistant) {
        $text = [IO.File]::ReadAllText($sourcePath)
        $text = Replace-StartupAnchor $text 'if (args.Length == 1 && args[0] == "--features") return BuildFeatures.Write();' @'
if (args.Length == 1 && args[0] == "--assistant-self-test") return PawAssistantRuntime.SelfTest();
        if (args.Length == 1 && args[0] == "--features") return BuildFeatures.Write();
'@
        $text = Replace-StartupAnchor $text 'ReleaseStartup.GuardData(root);' 'ReleaseStartup.GuardData(root); PawAssistantRuntime.GuardData(root);'
        $text = Replace-StartupAnchor $text 'startupComplete = true;' @'
PawAssistantRuntime.Install(game, imageBase, syncSignal, gameDirectory, delegate(string m) { AppendLog(logPath, m); });
            startupComplete = true;
'@
        $text = Replace-StartupAnchor $text 'current = ReadCounters(process, counters);' @'
PawAssistantRuntime.Tick();
                current = ReadCounters(process, counters);
'@
        $sourcePath = Join-Path $out ($variant.Name + '.generated.cs')
        [IO.File]::WriteAllText($sourcePath,$text,[Text.UTF8Encoding]::new($false))
        $arguments += Join-Path $assistant 'PawAssistantRuntime.cs'
        $arguments += Join-Path $assistant 'CityPlanner.cs'
        foreach ($resource in 'AssistantPayload','AssistantFixups') { $arguments += '/resource:' + (Join-Path $assistant "$resource.bin") + ',' + $resource }
    }
    $arguments += $sourcePath
    foreach ($file in $shared) { $arguments += Join-Path $PSScriptRoot $file }
    & $compiler @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Helper compilation failed.' }
    $modes = @('--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test')
    if ($CityAssistant) { $modes += '--assistant-self-test' }
    foreach ($mode in $modes) {
        $test = Start-Process -FilePath $exe -ArgumentList $mode -WindowStyle Hidden -PassThru -Wait
        if ($test.ExitCode -ne 0) { throw "Offline test failed: $($variant.Name) $mode" }
    }
}
if ($CityAssistant) {
    $layoutOut = Join-Path $out 'data/UI/Game'
    New-Item -ItemType Directory -Path $layoutOut -Force | Out-Null
    foreach($language in 'en','ru') {
        $file = "paw_city_$language.tgi"
        [IO.File]::WriteAllText((Join-Path $layoutOut $file),[IO.File]::ReadAllText((Join-Path $assistant $file)),[Text.Encoding]::Unicode)
    }
    $queueTest = Join-Path $out 'CityPlannerTests.exe'
    & $compiler /nologo /target:exe /r:System.Core.dll "/out:$queueTest" (Join-Path $assistant 'CityPlanner.cs') (Join-Path $assistant 'CityPlannerTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'City planner test compilation failed.' }
    & $queueTest
    if ($LASTEXITCODE -ne 0) { throw 'City planner regression failed.' }
}
Write-Output 'Built eight quiet helpers. No game launched. Install only with the matching signed release data packages.'
