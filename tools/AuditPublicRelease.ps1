param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$auditRepo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$auditOutput=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $auditOutput){throw 'Use a new audit directory.'}
New-Item -ItemType Directory -Path $auditOutput | Out-Null
$auditConfig=Get-Content -LiteralPath (Join-Path $auditRepo 'src/PawsPatchLauncher/launcher.config.json') -Raw | ConvertFrom-Json
if(!$auditConfig.requireSignedRemoteFeed){throw 'Remote signatures not required.'}
$null=[Reflection.Assembly]::LoadFrom((Join-Path $auditRepo 'src/PawsPatchLauncher/bin/Release/net8.0-windows/PawsPatchLauncher.dll'))
$auditManifests=@()
foreach($auditChannel in @('stable','beta')){
    $auditUrl=if($auditChannel -eq 'stable'){$auditConfig.feedUrls[0]}else{$auditConfig.betaFeedUrls[0]}
    if(([uri]$auditUrl).Scheme -ne 'https'){throw 'Expected public HTTPS feed.'}
    $auditFile=Join-Path $auditOutput ($auditChannel+'.json')
    Invoke-WebRequest -Uri $auditUrl -Headers @{'Cache-Control'='no-cache'} -OutFile $auditFile
    $auditEnvelope=Get-Content -LiteralPath $auditFile -Raw | ConvertFrom-Json
    $auditPayload=[Convert]::FromBase64String($auditEnvelope.payload)
    if(![PawsPatchLauncher.CryptoAndIO]::VerifySignature($auditPayload,$auditEnvelope.signature,$auditConfig.publicKeyPem)){throw 'Public feed signature invalid.'}
    $auditManifest=[Text.Encoding]::UTF8.GetString($auditPayload) | ConvertFrom-Json
    if($auditManifest.channel -ne $auditChannel){throw 'Feed channel mismatch.'}
    $auditManifests+=,$auditManifest
    [pscustomobject]@{Channel=$auditChannel;Signature='Valid';Launcher=$auditManifest.launcher.version;Packages=$auditManifest.packages.Count;LauncherHash=$auditManifest.launcher.sha256} | ConvertTo-Json -Compress
}
$auditRelease=$auditManifests[0].launcher
$auditDownload=$auditRelease.urls[0]
if(([uri]$auditDownload).Scheme -ne 'https' -or ([uri]$auditDownload).Host -ne 'github.com'){throw 'Unexpected public launcher host.'}
$auditExe=Join-Path $auditOutput 'PawsPatchLauncher-public.exe'
Invoke-WebRequest -Uri $auditDownload -OutFile $auditExe
$auditHash=(Get-FileHash -LiteralPath $auditExe).Hash
$auditInfo=Get-Item -LiteralPath $auditExe
if($auditHash -ne $auditRelease.sha256 -or $auditInfo.Length -ne $auditRelease.size){throw 'Public launcher hash/size mismatch.'}
[pscustomobject]@{PublicExecutable=$auditExe;Version=$auditInfo.VersionInfo.FileVersion;Bytes=$auditInfo.Length;Hash=$auditHash;BothFeedsSameLauncher=($auditManifests[1].launcher.sha256 -eq $auditHash)} | ConvertTo-Json -Compress
