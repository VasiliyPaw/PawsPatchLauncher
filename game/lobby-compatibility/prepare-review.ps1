param([Parameter(Mandatory=$true)][string]$GameRoot,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $GameRoot).ProviderPath.TrimEnd('\')
$statePath=Join-Path $root '.pawpatch\state.json'
$state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$settings=$state.appliedSettings
if (!$settings -or $settings.dataOnly) {throw 'This local review requires an applied 1.3.72 patch profile.'}
$mod=[string]$settings.mod
if($mod -notin @('arcane-wars','vanilla','immortals')){throw 'Unknown installed mod.'}
if(!$settings.pawPatchEnabled){throw 'This local review is for the two existing patch-enabled games.'}
$helper=if($mod -ne 'arcane-wars'){'k2_paws_pure_fixes_1372.exe'}
elseif($settings.customPlayerColors){
    if($settings.independentHostility){if($settings.desyncMode -eq 'continue'){'k2_paws_lobby_colors_mp_sync_1372.exe'}else{'k2_paws_lobby_colors_mp_1372_experimental.exe'}}
    else {if($settings.desyncMode -eq 'continue'){'k2_paws_lobby_colors_mp_nohostility_sync_1372.exe'}else{'k2_paws_lobby_colors_mp_nohostility_1372.exe'}}
}elseif($settings.desyncMode -eq 'continue'){
    if($settings.independentHostility){'k2_paws_sync_family_herd_relations_1372.exe'}else{'k2_paws_sync_continue_1372.exe'}
}elseif($settings.independentHostility){throw 'Resolve the configured preferred helper for this profile first.'}
else {'k2_paws_ui_1372.exe'}
$versions=@{}
foreach($line in (Get-Content -LiteralPath (Join-Path $root 'paws_launch_versions.ini'))){
    if($line -match '^([A-Za-z]+)=(.*)$'){$versions[$matches[1]]=$matches[2].Trim()}
}
if($versions.Mod -ne $mod){throw 'Launch metadata does not match applied mod.'}
$modVersion=($versions.ModVersion -replace ' beta$','')
$patchVersion=$versions.PawPatch
foreach($v in @($modVersion,$patchVersion)){if(!$v -or $v -notmatch '^[A-Za-z0-9.+_-]{1,48}$'){throw 'Invalid installed version.'}}
$exeHash=(Get-FileHash -LiteralPath (Join-Path $root 'k2.exe')).Hash
if($exeHash -ne '1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45'){throw 'This review supports only the verified Steam 1.3.72 executable.'}
$helperHash=(Get-FileHash -LiteralPath (Join-Path $root $helper)).Hash
$lines=New-Object 'System.Collections.Generic.List[string]'
$lines.Add('protocol=1');$lines.Add('exe='+$exeHash);$lines.Add('helper='+$helper.ToLowerInvariant()+':'+$helperHash)
# Canonical installed manifest payload, plus actual EXE/helper bytes. The game's
# original file checksum remains responsible for validating the loaded game data.
# Text/speech packages and UI preferences never participate in this identity.
foreach($p in ($state.modules.PSObject.Properties | Sort-Object Name)){
    $m=$p.Value
    if(!$m.enabled -or $p.Name -match '^(localization|game-voice|game-text)(-|$)'){continue}
    $lines.Add('module='+$p.Name+':'+$m.version)
    foreach($file in ($m.files | Sort-Object path)){$lines.Add('file='+$file.path.ToLowerInvariant().Replace('\','/')+':'+$file.sha256.ToUpperInvariant())}
    foreach($file in ($m.remove | Sort-Object)){$lines.Add('remove='+([string]$file).ToLowerInvariant().Replace('\','/'))}
}
foreach($name in @('customPlayerColors','desyncMode','independentHostility','roamingSpawnMode','additionalRoamingCompanies','siegeBalance','disablePowersAndShards','largeMapSizes')){
    if($mod -eq 'arcane-wars'){$lines.Add('setting='+$name+':'+([string]$settings.$name).ToLowerInvariant())}
}
$hash=[Security.Cryptography.SHA256]::Create()
try{$digest=[BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes(($lines -join "`n")))).Replace('-','')}finally{$hash.Dispose()}
$token='PWLC1|1.3.72|'+$mod+'|'+$modVersion+'|'+$patchVersion+'|'+$digest
if($token.Length -gt 255){throw 'Identity too long.'}
[IO.Directory]::CreateDirectory($OutputDirectory)|Out-Null
$out=(Resolve-Path -LiteralPath $OutputDirectory).ProviderPath
$config=New-Object byte[] 264
[BitConverter]::GetBytes([uint32]0x31434C50).CopyTo($config,0)
[BitConverter]::GetBytes([int]1).CopyTo($config,4)
[Text.Encoding]::ASCII.GetBytes($token).CopyTo($config,8)
[IO.File]::WriteAllBytes((Join-Path $out 'identity.bin'),$config)
$summary=[ordered]@{gameRoot=$root;gameVersion='1.3.72';mod=$mod;modVersion=$modVersion;patchVersion=$patchVersion;helper=$helper;exeSha256=$exeHash;helperSha256=$helperHash;token=$token;stateSha256=(Get-FileHash -LiteralPath $statePath).Hash}
$summary|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $out 'identity.json') -Encoding UTF8
$lines|Set-Content -LiteralPath (Join-Path $out 'fingerprint-input.txt') -Encoding UTF8
$summary|ConvertTo-Json
