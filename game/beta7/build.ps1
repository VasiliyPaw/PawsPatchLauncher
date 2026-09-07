param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$out = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $out) { throw 'Choose an unused output directory.' }
New-Item -ItemType Directory -Path $out | Out-Null
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
$variants = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'variants.json') -Raw | ConvertFrom-Json
$shared = 'TerrainRuntime.cs','RandomMapPatch.cs','ReleaseStartup.cs','LobbyColorsNative.cs','GamePresentation1372.cs','RandomMapBundle.cs','BuildFeatures.cs'
$resources = 'PawLobbyColorsPayload','PawLobbyColorsFixups','PawCommonUiPayload','PawCommonUiFixups','RandomMapPayload','RandomMapFixups'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'paws_player_colors.ini') -Destination $out
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'paws_patch_versions.ini') -Destination $out
foreach ($variant in $variants.PSObject.Properties) {
    $exe = Join-Path $out $variant.Name
    $arguments = @('/nologo','/target:winexe','/platform:x86','/optimize+',
        '/r:System.Core.dll','/r:System.Windows.Forms.dll','/r:System.Drawing.dll',
        ("/define:" + $variant.Value), ("/out:" + $exe))
    foreach ($resource in $resources) { $arguments += '/resource:' + (Join-Path $PSScriptRoot "$resource.bin") + ',' + $resource }
    $source = if ($variant.Name.StartsWith('k2_paws_lobby_colors_mp_nohostility')) { 'k2_paws_lobby_colors_mp_1372_experimental.cs' } else { [IO.Path]::GetFileNameWithoutExtension($variant.Name) + '.cs' }
    $arguments += Join-Path $PSScriptRoot $source
    foreach ($file in $shared) { $arguments += Join-Path $PSScriptRoot $file }
    & $compiler @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Helper compilation failed.' }
    foreach ($mode in '--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test') {
        $test = Start-Process -FilePath $exe -ArgumentList $mode -WindowStyle Hidden -PassThru -Wait
        if ($test.ExitCode -ne 0) { throw "Offline test failed: $($variant.Name) $mode" }
    }
}
Write-Output 'Built eight quiet helpers. No game launched. Install only with the matching signed release data packages.'
