param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$out = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $out) { throw 'Choose a fresh output directory.' }
New-Item -ItemType Directory -Path $out | Out-Null
$gameSource = Join-Path $PSScriptRoot '../game/beta7'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
$variants = Get-Content -LiteralPath (Join-Path $gameSource 'variants.json') -Raw | ConvertFrom-Json
Copy-Item -LiteralPath (Join-Path $gameSource 'paws_player_colors.ini') -Destination $out
foreach ($variant in $variants.PSObject.Properties) {
    $sourceName = if ($variant.Name.StartsWith('k2_paws_lobby_colors_mp_nohostility')) { 'k2_paws_lobby_colors_mp_1372_experimental.cs' } else { [IO.Path]::GetFileNameWithoutExtension($variant.Name) + '.cs' }
    $source = [IO.File]::ReadAllText((Join-Path $gameSource $sourceName))
    # Independently selected runtime features must not install the core terrain,
    # random-map or formatter hooks, nor demand their data files. The menu label
    # remains independent of the core and reads launcher-generated metadata.
    foreach ($anchor in @('ReleaseStartup.GuardData(root);', 'ReleaseStartup.GuardData(gameDirectory);', 'ReleaseStartup.InstallTerrainAndMap(game, imageBase, delegate(string m) { AppendLog(logPath, m); });', 'PawGamePresentation.Install(process, imageBase, logPath);')) {
        if (($source.Split([string[]]@($anchor),[StringSplitOptions]::None).Length-1) -ne 1) { throw "Changed source anchor: $anchor" }
        $replacement = if ($anchor -eq 'PawGamePresentation.Install(process, imageBase, logPath);') {
            'PawGamePresentation.InstallMenuOnly(process, imageBase, logPath, AppDomain.CurrentDomain.BaseDirectory);'
        } else { '/* Paw core is disabled for this standalone Arcane Wars build. */' }
        $source = $source.Replace($anchor, $replacement)
    }
    $start = $source.IndexOf('        VerifyHash(' + "`r`n" + '            Path.Combine(gameDirectory, "Data", "Templates"')
    if ($start -lt 0) { $start = $source.IndexOf('        VerifyHash(' + "`n" + '            Path.Combine(gameDirectory, "Data", "Templates"') }
    $end = $source.IndexOf('    private static void VerifyHash(', $start)
    if ($start -lt 0 -or $end -lt 0) { throw 'Changed game verification anchors.' }
    # The installer's signed module manifest validates standalone game data.
    # Retain verification of the original Steam executable and all native hook guards.
    $source = $source.Substring(0,$start) + "    }`n`n" + $source.Substring($end)
    $generated = Join-Path $out ($variant.Name + '.cs')
    [IO.File]::WriteAllText($generated,$source,[Text.UTF8Encoding]::new($false))
    $exe = Join-Path $out ($variant.Name.Replace('k2_paws_', 'k2_aw_'))
    $compilerArgs = @('/nologo','/target:winexe','/platform:x86','/optimize+', '/r:System.Core.dll','/r:System.Windows.Forms.dll','/r:System.Drawing.dll',
        ('/define:'+$variant.Value+';PAW_CORELESS'),('/out:'+$exe),$generated)
    foreach ($name in 'TerrainRuntime','RandomMapPatch','ReleaseStartup','LobbyColorsNative','GamePresentation1372','RandomMapBundle','BuildFeatures','GameText') { $compilerArgs += Join-Path $gameSource ($name+'.cs') }
    foreach ($name in 'PawLobbyColorsPayload','PawLobbyColorsFixups','PawCommonUiPayload','PawCommonUiFixups','RandomMapPayload','RandomMapFixups') { $compilerArgs += '/resource:'+(Join-Path $gameSource ($name+'.bin'))+','+$name }
    & $compiler @compilerArgs
    if ($LASTEXITCODE -ne 0) { throw 'Standalone Arcane Wars helper compilation failed.' }
    foreach ($mode in '--quiet-startup-self-test','--lobby-payload-test','--features') {
        $test = Start-Process -FilePath $exe -ArgumentList $mode -WindowStyle Hidden -Wait -PassThru
        if ($test.ExitCode -ne 0) { throw "Helper test failed: $exe $mode" }
    }
}
Write-Output 'Built and offline-tested 8 standalone Arcane Wars helpers. No game started.'
