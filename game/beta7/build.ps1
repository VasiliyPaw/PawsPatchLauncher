param([Parameter(Mandatory=$true)][string]$OutputDirectory, [switch]$CityAssistant, [string]$LegacyWorkDirectory, [switch]$LobbyCompatibility, [string]$NativeCompiler, [switch]$LairWoundedTest, [switch]$LairRecovery, [switch]$CameraZoom, [switch]$CompanyPositionRecovery)
$ErrorActionPreference = 'Stop'
if($LairWoundedTest){$LairRecovery=$true}
$out = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $out) { throw 'Choose an unused output directory.' }
New-Item -ItemType Directory -Path $out | Out-Null
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
$variants = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'variants.json') -Raw | ConvertFrom-Json
$shared = 'TerrainRuntime.cs','RandomMapPatch.cs','ReleaseStartup.cs','LobbyColorsNative.cs','GamePresentation1372.cs','RandomMapBundle.cs','BuildFeatures.cs','GameText.cs'
$resources = 'PawLobbyColorsPayload','PawLobbyColorsFixups','PawCommonUiPayload','PawCommonUiFixups','RandomMapPayload','RandomMapFixups'
$assistant = Join-Path $PSScriptRoot '../city-assistant'
$transfer = Join-Path $PSScriptRoot '../fast-transfer'
$work = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$python = 'C:\Users\Paw\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if($LobbyCompatibility) {
    if(!$CityAssistant -or !$NativeCompiler){throw 'Lobby compatibility is part of the full beta helper build; specify -CityAssistant and -NativeCompiler.'}
    $lobby=Join-Path $PSScriptRoot '../lobby-compatibility'
    $packageVersion=[regex]::Match([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'paws_patch_versions.ini')),'(?m)^PawPatch=([^\r\n]+)').Groups[1].Value
    $helperVersion=[regex]::Match([IO.File]::ReadAllText((Join-Path $lobby 'PawLobbyCompatibility.cs')),'internal const string Version = "([^"]+)";').Groups[1].Value
    if(!$packageVersion -or $packageVersion -ne $helperVersion){throw 'Lobby compatibility version differs from package version.'}
    & $NativeCompiler -shared -Wall -Werror (Join-Path $lobby 'lobby_compatibility.c') -o (Join-Path $out 'paws_lobby_compatibility.dll') -lkernel32 -luser32
    if($LASTEXITCODE -ne 0){throw 'Lobby compatibility DLL build failed.'}
    & $NativeCompiler -Wall -Werror -DPAW_TEST (Join-Path $lobby 'lobby_compatibility.c') -o (Join-Path $out 'LobbyProtocolTests.exe') -lkernel32 -luser32
    if($LASTEXITCODE -ne 0){throw 'Lobby protocol test build failed.'}
    & (Join-Path $out 'LobbyProtocolTests.exe')
    if($LASTEXITCODE -ne 0){throw 'Lobby protocol test failed.'}
}
if ($CityAssistant) {
    if ($LegacyWorkDirectory) {
        $work = [IO.Path]::GetFullPath($LegacyWorkDirectory)
    } elseif (-not (Test-Path -LiteralPath (Join-Path $work 'city_assistant_1372'))) {
        # Accepted local audit source after the workspace migration. Rebuilders
        # elsewhere should supply their verified source root explicitly.
        $work = 'G:\CodexData\projects\Codex\2026-08-11\kohan-ii-d-steamlibrary-steamapps-common\work'
    }
    foreach ($required in 'city_assistant_1372','city_policy_v2','fast_transfer_1372') {
        if (-not (Test-Path -LiteralPath (Join-Path $work $required))) { throw "Missing accepted legacy source $required. Set -LegacyWorkDirectory to its work directory." }
    }
    Write-Output "Verified legacy sources: $work"
    & $python (Join-Path $assistant 'build_policy_native.py') --legacy (Join-Path $work 'city_assistant_1372') --out (Join-Path $out 'native')
    if ($LASTEXITCODE -ne 0) { throw 'Native city policy generation failed.' }
    foreach ($resource in 'AssistantPayload','AssistantFixups') {
        if ((Get-FileHash (Join-Path $out "native/$resource.bin")).Hash -ne (Get-FileHash (Join-Path $assistant "$resource.bin")).Hash) { throw "Checked-in native resource differs: $resource" }
    }
    & $python (Join-Path $transfer 'prepare_guards.py') --work $work --out $out
    if ($LASTEXITCODE -ne 0) { throw 'Transfer guards generation failed.' }
}
function Replace-StartupAnchor([string]$text, [string]$before, [string]$after) {
    if (($text.Split([string[]]@($before),[StringSplitOptions]::None).Length-1) -ne 1) { throw "Startup source anchor changed: $before" }
    return $text.Replace($before,$after)
}
if($LairRecovery) {
    if(!$CityAssistant -or !$LobbyCompatibility){throw 'Lair recovery requires the full beta helper and lobby compatibility.'}
    $lair=Join-Path $PSScriptRoot '../lair-recovery'
    $lairNative=Join-Path $out 'lair-native'
    & $python (Join-Path $lair 'build_native.py') --legacy $work --out $lairNative
    if($LASTEXITCODE -ne 0){throw 'Lair native build failed.'}
    & $python (Join-Path $lair 'test_native.py') --legacy $work --native $lairNative
    if($LASTEXITCODE -ne 0){throw 'Lair native regression failed.'}
    $lairTests=Join-Path $out 'LairRecoveryTests.exe'
    & $compiler /nologo /target:exe /platform:x86 /r:System.Core.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll /main:LairRecoveryTests "/out:$lairTests" (Join-Path $PSScriptRoot 'TerrainRuntime.cs') (Join-Path $PSScriptRoot 'ReleaseStartup.cs') (Join-Path $PSScriptRoot 'RandomMapPatch.cs') (Join-Path $PSScriptRoot 'RandomMapBundle.cs') (Join-Path $lair 'LairRecoveryPatch.cs') (Join-Path $lairNative 'LairRecoveryPayload.cs') (Join-Path $lair 'LairRecoveryTests.cs')
    if($LASTEXITCODE -ne 0){throw 'Lair transaction tests compilation failed.'}
    & $lairTests
    if($LASTEXITCODE -ne 0){throw 'Lair transaction regression failed.'}
}
if($CameraZoom) {
    if(!$CityAssistant -or !$LobbyCompatibility -or !$LairRecovery){throw 'Camera zoom requires the complete Arcane beta helper.'}
    $camera=Join-Path $PSScriptRoot '../camera-zoom'
    $cameraNative=Join-Path $out 'camera-native'
    & $python (Join-Path $camera 'build_native.py') --legacy $work --out $cameraNative
    if($LASTEXITCODE -ne 0){throw 'Camera native build failed.'}
    $cameraTests=Join-Path $out 'CameraZoomTests.exe'
    & $compiler /nologo /target:exe /platform:x86 /r:System.Core.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll /main:CameraZoomTests "/out:$cameraTests" (Join-Path $PSScriptRoot 'TerrainRuntime.cs') (Join-Path $PSScriptRoot 'ReleaseStartup.cs') (Join-Path $PSScriptRoot 'RandomMapPatch.cs') (Join-Path $PSScriptRoot 'RandomMapBundle.cs') (Join-Path $camera 'CameraZoomPatch.cs') (Join-Path $cameraNative 'CameraZoomPayload.cs') (Join-Path $camera 'CameraZoomTests.cs')
    if($LASTEXITCODE -ne 0){throw 'Camera transaction tests compilation failed.'}
    & $cameraTests $cameraNative
    if($LASTEXITCODE -ne 0){throw 'Camera transaction regression failed.'}
    & $python (Join-Path $camera 'test_native.py') --legacy $work --native $cameraNative
    if($LASTEXITCODE -ne 0){throw 'Camera native regression failed.'}
}
if($CompanyPositionRecovery) {
    if(!$CityAssistant -or !$LobbyCompatibility -or !$CameraZoom -or !$LairRecovery){throw 'Company recovery requires the complete current Arcane helper.'}
    $company=Join-Path $PSScriptRoot '../company-position'
    $companyNative=Join-Path $out 'company-native'
    & $python (Join-Path $company 'build_native.py') --legacy $work --out $companyNative
    if($LASTEXITCODE -ne 0){throw 'Company native build failed.'}
    $companyTests=Join-Path $out 'CompanyPositionTests.exe'
    & $compiler /nologo /target:exe /platform:x86 /r:System.Core.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll /main:CompanyPositionTests "/out:$companyTests" (Join-Path $PSScriptRoot 'TerrainRuntime.cs') (Join-Path $PSScriptRoot 'ReleaseStartup.cs') (Join-Path $PSScriptRoot 'RandomMapPatch.cs') (Join-Path $PSScriptRoot 'RandomMapBundle.cs') (Join-Path $company 'CompanyPositionPatch.cs') (Join-Path $companyNative 'CompanyPositionPayload.cs') (Join-Path $company 'CompanyPositionTests.cs')
    if($LASTEXITCODE -ne 0){throw 'Company transaction tests compilation failed.'}
    & $companyTests $companyNative
    if($LASTEXITCODE -ne 0){throw 'Company transaction regression failed.'}
    & $python (Join-Path $company 'test_native.py') --legacy $work --native $companyNative
    if($LASTEXITCODE -ne 0){throw 'Company native regression failed.'}
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'paws_player_colors.ini') -Destination $out
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'paws_patch_versions.ini') -Destination $out
foreach ($variant in $variants.PSObject.Properties) {
    $exe = Join-Path $out $variant.Name
    $arguments = @('/nologo','/target:winexe','/platform:x86','/optimize+',
        '/r:System.Core.dll','/r:System.Windows.Forms.dll','/r:System.Drawing.dll',
        ("/define:" + $variant.Value + $(if($CityAssistant){';CITY_ASSISTANT;FAST_SAVE_TRANSFER'}else{''}) + $(if($LobbyCompatibility){';LOBBY_COMPATIBILITY'}else{''}) + $(if($LairWoundedTest){';LAIR_RECOVERY_TEST'}else{''}) + $(if($LairRecovery){';LAIR_RECOVERY'}else{''})), ("/out:" + $exe))
    if($CompanyPositionRecovery){$arguments += '/define:COMPANY_POSITION_RECOVERY';$arguments += (Join-Path $company 'CompanyPositionPatch.cs'),(Join-Path $companyNative 'CompanyPositionPayload.cs')}
    if($CameraZoom){$arguments += '/define:CAMERA_ZOOM_2';$arguments += (Join-Path $camera 'CameraZoomPatch.cs'),(Join-Path $cameraNative 'CameraZoomPayload.cs')}
    if($LairRecovery){$arguments += (Join-Path $lair 'LairRecoveryPatch.cs'),(Join-Path $lairNative 'LairRecoveryPayload.cs')}
    foreach ($resource in $resources) { $arguments += '/resource:' + (Join-Path $PSScriptRoot "$resource.bin") + ',' + $resource }
    $source = if ($variant.Name.StartsWith('k2_paws_lobby_colors_mp_nohostility')) { 'k2_paws_lobby_colors_mp_1372_experimental.cs' } else { [IO.Path]::GetFileNameWithoutExtension($variant.Name) + '.cs' }
    $sourcePath = Join-Path $PSScriptRoot $source
    if ($CityAssistant) {
        $text = [IO.File]::ReadAllText($sourcePath)
        $text = Replace-StartupAnchor $text 'if (args.Length == 1 && args[0] == "--features") return BuildFeatures.Write();' @'
if (args.Length == 1 && args[0] == "--assistant-self-test") return PawAssistantRuntime.SelfTest();
        if (args.Length == 1 && args[0] == "--fast-transfer-self-test") return FastTransferTests.Run(null);
        if (args.Length == 1 && args[0] == "--features") return BuildFeatures.Write();
'@
        $text = Replace-StartupAnchor $text 'ReleaseStartup.GuardData(root);' 'ReleaseStartup.GuardData(root); PawAssistantRuntime.GuardData(root);'
        $text = Replace-StartupAnchor $text 'startupComplete = true;' @'
PawAssistantRuntime.Install(game, imageBase, syncSignal, gameDirectory, delegate(string m) { AppendLog(logPath, m); });
            PawFastTransfer.Install(game, imageBase, delegate(string m) { AppendLog(logPath, m); });
            startupComplete = true;
'@
        $text = Replace-StartupAnchor $text 'current = ReadCounters(process, counters);' @'
PawAssistantRuntime.Tick();
                PawFastTransfer.Tick();
                current = ReadCounters(process, counters);
'@
        if($LobbyCompatibility) {
            $text=Replace-StartupAnchor $text 'PawAssistantRuntime.GuardData(root);' 'PawAssistantRuntime.GuardData(root); PawLobbyCompatibility.ValidateInstallation(root);'
            $text=Replace-StartupAnchor $text 'ReleaseStartup.GuardData(gameDirectory);' 'ReleaseStartup.GuardData(gameDirectory); PawLobbyCompatibility.Prepare(gameDirectory);'
            $text=Replace-StartupAnchor $text 'ReleaseStartup.InstallTerrainAndMap(game, imageBase, delegate(string m) { AppendLog(logPath, m); });' 'PawLobbyCompatibility.Install(game, imageBase, delegate(string m) { AppendLog(logPath, m); }); ReleaseStartup.InstallTerrainAndMap(game, imageBase, delegate(string m) { AppendLog(logPath, m); });'
            $arguments += '/r:System.Web.Extensions.dll'
            $arguments += Join-Path $lobby 'PawLobbyCompatibility.cs'
            $arguments += '/resource:'+(Join-Path $out 'paws_lobby_compatibility.dll')+',PawLobbyCompatibilityNative'
        }
        if($LairWoundedTest) {
            $text=Replace-StartupAnchor $text 'if (args.Length == 1 && args[0] == "--features") return BuildFeatures.Write();' @'
if (args.Length == 2 && args[0] == "--local-data-check") {
            try { ReleaseStartup.VerifyLocalLaunchData(args[1]); Console.WriteLine("LOCAL_DATA_PASS language="+PawGameText.Language); return 0; }
            catch(Exception error) { Console.Error.WriteLine(error.Message); return 2; }
        }
        if (args.Length == 1 && args[0] == "--features") return BuildFeatures.Write();
'@
            $text=Replace-StartupAnchor $text 'ReleaseStartup.GuardData(root);' 'ReleaseStartup.GuardData(root); ReleaseStartup.VerifyLocalLaunchData(root);'
            $text=Replace-StartupAnchor $text 'ReleaseStartup.GuardData(gameDirectory);' 'ReleaseStartup.GuardData(gameDirectory); ReleaseStartup.VerifyLocalLaunchData(gameDirectory);'
        }
        $sourcePath = Join-Path $out ($variant.Name + '.generated.cs')
        [IO.File]::WriteAllText($sourcePath,$text,[Text.UTF8Encoding]::new($false))
        $arguments += Join-Path $assistant 'PawAssistantRuntime.cs'
        $arguments += Join-Path $assistant 'PawAssistantParties.cs'
        $arguments += Join-Path $assistant 'CityPartyStore.cs'
        $arguments += Join-Path $assistant 'CityDevelopmentText.cs'
        $arguments += Join-Path $assistant 'CityPlanner.cs'
        $arguments += Join-Path $assistant 'CityMilitiaPlanner.cs'
        $arguments += Join-Path $assistant 'CityPolicy.cs'
        $arguments += Join-Path $assistant 'CityResourceOrder.cs'
        $arguments += Join-Path $assistant 'CitySettingsForm.cs'
        $arguments += Join-Path $transfer 'FastTransfer.cs'
        $arguments += Join-Path $transfer 'FastTransferTests.cs'
        $arguments += '/resource:' + (Join-Path $out 'FastTransferGuards.bin') + ',FastTransferGuards'
        foreach ($resource in 'AssistantPayload','AssistantFixups') { $arguments += '/resource:' + (Join-Path $assistant "$resource.bin") + ',' + $resource }
    }
    $arguments += $sourcePath
    foreach ($file in $shared) { $arguments += Join-Path $PSScriptRoot $file }
    & $compiler @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Helper compilation failed.' }
    $modes = @('--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test')
    if ($CityAssistant) { $modes += '--assistant-self-test','--fast-transfer-self-test' }
    foreach ($mode in $modes) {
        $test = Start-Process -FilePath $exe -ArgumentList $mode -WindowStyle Hidden -PassThru -Wait
        if ($test.ExitCode -ne 0) { throw "Offline test failed: $($variant.Name) $mode" }
    }
}
if ($CityAssistant) {
    & $python (Join-Path $PSScriptRoot 'test_saved_owners.py') --helpers $out --legacy $work
    if ($LASTEXITCODE -ne 0) { throw 'Saved owner regression failed.' }
    $layoutOut = Join-Path $out 'data/UI/Game'
    New-Item -ItemType Directory -Path $layoutOut -Force | Out-Null
    foreach($language in 'en','ru') {
        $file = "paw_city_$language.tgi"
        [IO.File]::WriteAllText((Join-Path $layoutOut $file),[IO.File]::ReadAllText((Join-Path $assistant $file)),[Text.Encoding]::Unicode)
        $localeDir = Join-Path $out $(if ($language -eq 'en') {'data/Localization'} else {'Local_ru/Localization'})
        New-Item -ItemType Directory -Path $localeDir -Force | Out-Null
        [IO.File]::WriteAllText((Join-Path $localeDir 'paw_city_policy.tgi'),[IO.File]::ReadAllText((Join-Path $assistant "localization_$language.tgi")),[Text.Encoding]::Unicode)
    }
    $queueTest = Join-Path $out 'CityPlannerTests.exe'
    & $compiler /nologo /target:exe /r:System.Core.dll "/out:$queueTest" (Join-Path $assistant 'CityPlanner.cs') (Join-Path $assistant 'CityPolicy.cs') (Join-Path $assistant 'CityResourceOrder.cs') (Join-Path $assistant 'CityPlannerTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'City planner test compilation failed.' }
    & $queueTest
    if ($LASTEXITCODE -ne 0) { throw 'City planner regression failed.' }
    $partyTest = Join-Path $out 'CityPartyStoreTests.exe'
    & $compiler /nologo /target:exe /r:System.Core.dll "/out:$partyTest" (Join-Path $assistant 'CityPartyStore.cs') (Join-Path $assistant 'CityPartyStoreTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'City party test compilation failed.' }
    & $partyTest
    if ($LASTEXITCODE -ne 0) { throw 'City party persistence regression failed.' }
    $militiaTest = Join-Path $out 'CityMilitiaPlannerTests.exe'
    & $compiler /nologo /target:exe /r:System.Core.dll "/out:$militiaTest" (Join-Path $assistant 'CityMilitiaPlanner.cs') (Join-Path $assistant 'CityMilitiaPlannerTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'City militia test compilation failed.' }
    & $militiaTest
    if ($LASTEXITCODE -ne 0) { throw 'City militia regression failed.' }
    $formTest = Join-Path $out 'CitySettingsFormTests.exe'
    & $compiler /nologo /target:exe /r:System.Core.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll "/out:$formTest" (Join-Path $PSScriptRoot 'GameText.cs') (Join-Path $assistant 'CityPlanner.cs') (Join-Path $assistant 'CityPolicy.cs') (Join-Path $assistant 'CitySettingsForm.cs') (Join-Path $assistant 'CitySettingsFormTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'City settings test compilation failed.' }
    & $formTest
    if ($LASTEXITCODE -ne 0) { throw 'City settings regression failed.' }
    foreach ($test in 'test_policy_native.py','test_construction_native.py','test_resource_inputs_native.py','test_automation_native.py','test_transport_native.py','test_preferences_native.py','test_markets_native.py') {
        & $python (Join-Path $assistant $test) --legacy (Join-Path $work 'city_assistant_1372') --native (Join-Path $out 'native')
        if ($LASTEXITCODE -ne 0) { throw "Native regression failed: $test" }
    }
    $transferTest = Join-Path $out 'FastTransferTests.exe'
    & $compiler /nologo /target:exe /platform:x86 /r:System.Core.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll "/out:$transferTest" ("/resource:" + (Join-Path $out 'FastTransferGuards.bin') + ',FastTransferGuards') (Join-Path $PSScriptRoot 'TerrainRuntime.cs') (Join-Path $transfer 'FastTransfer.cs') (Join-Path $transfer 'FastTransferTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Transfer test compilation failed.' }
    & $transferTest $out
    if ($LASTEXITCODE -ne 0) { throw 'Transfer regression failed.' }
    & $python (Join-Path $transfer 'test_native.py') --work $work --out $out
    if ($LASTEXITCODE -ne 0) { throw 'Native transfer regression failed.' }
}
Write-Output 'Built eight quiet helpers. No game launched. Install only with the matching signed release data packages.'
