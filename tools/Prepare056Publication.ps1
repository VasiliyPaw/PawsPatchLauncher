param([Parameter(Mandatory=$true)][string]$PreviousCommit)
$ErrorActionPreference='Stop'
if ($PreviousCommit -notmatch '^[a-f0-9]{40}$') { throw 'Expected an immutable previous commit.' }
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$out=Join-Path $repo 'release_workspace_056/publication'
$feedOut=Join-Path $out 'feed'
if(Test-Path -LiteralPath $feedOut){throw 'Publication feed output already exists; preserve the previous preparation.'}
$dotnet='C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe'
$publisher=Join-Path $repo 'tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll'
$publicKey=Join-Path $repo '.local/signing/pawpatch-signing-public.pem'
$privateKey=Join-Path $repo '.local/signing/pawpatch-signing-private.pem'
$launcher=Get-Item -LiteralPath (Join-Path $out 'win-x64/PawsPatchLauncher.exe')
if($launcher.VersionInfo.FileVersion -ne '0.5.6.0'){throw 'Expected 0.5.6 launcher.'}
$launcherHash=(Get-FileHash -LiteralPath $launcher.FullName).Hash
$history=Get-Content -LiteralPath (Join-Path $repo 'feed/changelog.history.json') -Raw|ConvertFrom-Json
$ids=@('roaming-profile-x4-no-new','roaming-profile-standard-no-new','siege-balance-standard','powers-shards-original')
New-Item -ItemType Directory -Path $feedOut,(Join-Path $out 'assets')|Out-Null
function Read-VerifiedFeed([string]$path){
    & $dotnet $publisher verify $path $publicKey | Out-Host
    if($LASTEXITCODE -ne 0){throw "Feed signature invalid: $path"}
    $envelope=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($envelope.payload))|ConvertFrom-Json
}
function Comparable($package){return $package|Select-Object * -ExcludeProperty urls|ConvertTo-Json -Depth 40 -Compress}
foreach($channel in @('stable','beta')){
    $feed=Read-VerifiedFeed (Join-Path $repo "feed/$channel.json")
    $candidate=Read-VerifiedFeed (Join-Path $repo "release_workspace_056/combination-fix/feed/$channel.signed.json")
    if(($feed.game|ConvertTo-Json -Compress) -ne ($candidate.game|ConvertTo-Json -Compress)){throw 'Game compatibility changed.'}
    $originalPrevious=@($feed.previousReleases)
    foreach($package in $feed.packages){
        if($package.id -in $ids){continue}
        $same=$candidate.packages|Where-Object id -EQ $package.id
        if(-not $same -or (Comparable $package) -ne (Comparable $same)){throw "Unrelated candidate package changed: $($package.id)"}
    }
    foreach($id in $ids){
        $package=$candidate.packages|Where-Object id -EQ $id
        if(@($package).Count -ne 1){throw "Missing/duplicate fixed package: $id"}
        $archive=Get-Item -LiteralPath $package.urls[0]
        if($archive.Length -ne $package.size -or (Get-FileHash -LiteralPath $archive.FullName).Hash -ne $package.sha256){throw "Candidate archive mismatch: $id"}
        $destination=Join-Path $out "assets/$($archive.Name)"
        if(Test-Path -LiteralPath $destination){
            if((Get-FileHash -LiteralPath $destination).Hash -ne $package.sha256){throw 'Conflicting prepared asset.'}
        }else{Copy-Item -LiteralPath $archive.FullName -Destination $destination}
        $package.urls=@("https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v0.5.6/$($archive.Name)")
        $index=-1
        for($i=0;$i -lt $feed.packages.Count;$i++){if($feed.packages[$i].id -eq $id){$index=$i;break}}
        if($index -ge 0){$feed.packages[$index]=$package}else{$feed.packages=@($feed.packages)+@($package)}
    }
    if($feed.packages.Count -ne $candidate.packages.Count){throw 'Unexpected final package count.'}
    foreach($package in $feed.packages){
        $expected=$candidate.packages|Where-Object id -EQ $package.id
        if((Comparable $package) -ne (Comparable $expected)){throw 'Final packages differ from tested composition.'}
        foreach($url in $package.urls){if(-not $url.StartsWith('https://')){throw 'Local/non-HTTPS URL in public feed.'}}
    }
    if($channel -eq 'beta'){
        $prior=[pscustomobject]@{label='Beta before launcher 0.5.6 components';url="https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/$PreviousCommit/feed/beta.json"}
        $feed.previousReleases=@($prior)+@($originalPrevious|Where-Object {$_})
    }
    $feed.publishedAt=[DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    $feed.launcher.version='0.5.6';$feed.launcher.size=$launcher.Length;$feed.launcher.sha256=$launcherHash
    $feed.launcher.urls=@('https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v0.5.6/PawsPatchLauncher.exe')
    $feed.changelog=@($history.$channel)
    if($feed.changelog[0].version -ne '0.5.6'){throw 'New changelog entry is missing.'}
    $feed.newsTitle=$feed.changelog[0].title;$feed.newsBody=$feed.changelog[0].body
    $json=Join-Path $feedOut "$channel.production.payload.json"
    $signed=Join-Path $feedOut "$channel.signed.json"
    $feed|ConvertTo-Json -Depth 45|Set-Content -LiteralPath $json -Encoding utf8NoBOM
    & $dotnet $publisher sign $json $privateKey pawpatch-prod-2026 $signed
    if($LASTEXITCODE -ne 0){throw 'Signing failed.'}
    & $dotnet $publisher verify $signed $publicKey
    if($LASTEXITCODE -ne 0){throw 'Output signature invalid.'}
    "PUBLIC FEED READY $channel`: tested package composition preserved; game EXEs unchanged"
}
$config=Get-Content -LiteralPath (Join-Path $out 'win-x64/launcher.config.json') -Raw|ConvertFrom-Json
if($config.cacheRoot -or -not $config.requireSignedRemoteFeed -or ($config.feedUrls+$config.betaFeedUrls|Where-Object {$_ -notlike 'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/*'})){throw 'Portable config is not public-safe.'}
$zip=Join-Path $out 'assets/PawsPatchLauncher-v0.5.6-win-x64.zip'
Compress-Archive -LiteralPath $launcher.FullName,(Join-Path $launcher.DirectoryName 'launcher.config.json') -DestinationPath $zip
'READY: local publication artifacts only; no online feed changed.'
