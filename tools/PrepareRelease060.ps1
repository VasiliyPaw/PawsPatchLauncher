param(
    [Parameter(Mandatory=$true)][string]$PublishedLauncherPath,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$DotnetPath='dotnet'
)
$ErrorActionPreference='Stop'
$releaseRepo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$releaseOut=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $releaseOut){throw 'Use a new feed staging directory.'}
$releaseExe=Get-Item -LiteralPath ([IO.Path]::GetFullPath($PublishedLauncherPath))
if($releaseExe.VersionInfo.FileVersion -ne '0.6.0.0'){throw 'Expected launcher 0.6.0.'}
$releaseHash=(Get-FileHash -LiteralPath $releaseExe.FullName).Hash
$releasePublic=Join-Path $releaseRepo '.local/signing/pawpatch-signing-public.pem'
$releasePrivate=Join-Path $releaseRepo '.local/signing/pawpatch-signing-private.pem'
$releasePublisher=Join-Path $releaseRepo 'tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll'
$releaseTests=Join-Path $releaseRepo 'tests/PawsPatchLauncher.Tests/bin/Release/net8.0-windows/PawsPatchLauncher.Tests.dll'
$releaseHistory=Get-Content -LiteralPath (Join-Path $releaseRepo 'feed/changelog.history.json') -Raw | ConvertFrom-Json -DateKind String
New-Item -ItemType Directory -Path $releaseOut | Out-Null
function Read-VerifiedFeed([string]$path){
    & $DotnetPath $releasePublisher verify $path $releasePublic
    if($LASTEXITCODE -ne 0){throw 'Feed signature verification failed.'}
    $envelope=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($envelope.payload)) | ConvertFrom-Json -DateKind String
}
# Suppress verifier's informational output from the returned object.
function Load-Feed([string]$path){
    $items=@(Read-VerifiedFeed $path)
    return $items[-1]
}
$guideFile=Join-Path $releaseOut 'guide.json'
& $DotnetPath $releaseTests --export-guide $guideFile
if($LASTEXITCODE -ne 0){throw 'Guide export failed.'}
$guide=Get-Content -LiteralPath $guideFile -Raw | ConvertFrom-Json -DateKind String
$guide.version='0.2.1'
foreach($channel in @('stable','beta')){
    $feed=Load-Feed (Join-Path $releaseRepo "feed/$channel.json")
    $candidate=Load-Feed (Join-Path $releaseRepo "release_workspace_059/components-v2/feed/$channel.local.signed.json")
    if($feed.channel -ne $channel -or $candidate.channel -ne $channel -or $feed.packages.Count -ne 13){throw 'Unexpected source channel/packages.'}
    $originalPackages=$feed.packages | ConvertTo-Json -Depth 50 -Compress
    $originalRest=$feed | Select-Object * -ExcludeProperty packages,launcher,publishedAt,changelog,newsTitle,newsBody,patchGuide | ConvertTo-Json -Depth 50 -Compress
    foreach($package in $feed.packages){
        $local=@($candidate.packages | Where-Object id -EQ $package.id)
        if($local.Count -ne 1 -or $local[0].sha256 -ne $package.sha256 -or $local[0].size -ne $package.size -or $local[0].version -ne $package.version){throw 'Candidate base differs from public packages.'}
    }
    $additions=@()
    foreach($id in @('roaming-profile-x2-with-new','roaming-profile-x2-no-new')){
        $profile=@($candidate.packages | Where-Object id -EQ $id)
        if($profile.Count -ne 1 -or $profile[0].version -ne '1.3.72-options.3'){throw 'Unexpected x2 package.'}
        $profile=$profile[0]
        $archive=Get-Item -LiteralPath (Join-Path $releaseRepo "release_workspace_059/components-v2/packages/$id-1.3.72-options.3.zip")
        if($archive.Length -ne $profile.size -or (Get-FileHash -LiteralPath $archive.FullName).Hash -ne $profile.sha256){throw 'x2 package hash or size mismatch.'}
        $profile.urls=@("https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v0.6.0/$($archive.Name)")
        $additions+=,$profile
    }
    $feed.packages=@($feed.packages)+$additions
    $feed.launcher.version='0.6.0'; $feed.launcher.size=$releaseExe.Length; $feed.launcher.sha256=$releaseHash
    $feed.launcher.urls=@('https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v0.6.0/PawsPatchLauncher.exe')
    $feed.publishedAt=[DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    if($releaseHistory.$channel[0].version -ne '0.6.0'){throw 'Missing 0.6.0 changelog.'}
    $feed.changelog=@($releaseHistory.$channel)
    $feed.newsTitle=$feed.changelog[0].title; $feed.newsBody=$feed.changelog[0].body
    $feed.patchGuide=$guide
    $kept=@($feed.packages | Where-Object { $_.id -notin $additions.id }) | ConvertTo-Json -Depth 50 -Compress
    $rest=$feed | Select-Object * -ExcludeProperty packages,launcher,publishedAt,changelog,newsTitle,newsBody,patchGuide | ConvertTo-Json -Depth 50 -Compress
    if($kept -ne $originalPackages -or $rest -ne $originalRest){throw 'Existing gameplay/compatibility/history data changed.'}
    if(@($feed.packages | ForEach-Object {$_.urls} | Where-Object {$_ -notmatch '^https://'}).Count){throw 'Local package path escaped into production feed.'}
    $payload=Join-Path $releaseOut "$channel.production.payload.json"
    $signed=Join-Path $releaseOut "$channel.signed.json"
    $feed | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $payload -Encoding utf8NoBOM
    & $DotnetPath $releasePublisher sign $payload $releasePrivate pawpatch-prod-2026 $signed
    if($LASTEXITCODE -ne 0){throw 'Feed signing failed.'}
    & $DotnetPath $releasePublisher verify $signed $releasePublic
    if($LASTEXITCODE -ne 0){throw 'Signed feed verification failed.'}
    Write-Output "READY $channel`: launcher 0.6.0; 13 existing packages unchanged; 2 verified x2 additions."
}
