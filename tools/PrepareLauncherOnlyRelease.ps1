param(
    [Parameter(Mandatory=$true)][string]$PublishedLauncherPath,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$out=[IO.Path]::GetFullPath($OutputDirectory)
$dotnet='C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe'
$publisher=Join-Path $repo 'tools\PawsPatchPublisher\bin\Release\net8.0-windows\PawsPatchPublisher.dll'
$publicKey=Join-Path $repo '.local\signing\pawpatch-signing-public.pem'
$privateKey=Join-Path $repo '.local\signing\pawpatch-signing-private.pem'
$history=Get-Content -LiteralPath (Join-Path $repo 'feed\changelog.history.json') -Raw | ConvertFrom-Json
$launcher=Get-Item -LiteralPath $PublishedLauncherPath
$version=[Version]::Parse($launcher.VersionInfo.FileVersion).ToString(3)
if ($version -ne '0.5.5') { throw 'Expected launcher 0.5.5.' }
$launcherHash=(Get-FileHash -LiteralPath $launcher.FullName).Hash
New-Item -ItemType Directory -Path $out -Force | Out-Null
foreach ($channel in 'stable','beta') {
    $source=Join-Path $repo "feed\$channel.json"
    & $dotnet $publisher verify $source $publicKey
    if ($LASTEXITCODE -ne 0) { throw 'Input feed signature invalid' }
    $envelope=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
    $feed=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($envelope.payload)) | ConvertFrom-Json
    $originalGame=$feed | Select-Object * -ExcludeProperty launcher,publishedAt,changelog,newsTitle,newsBody | ConvertTo-Json -Depth 40 -Compress
    $feed.publishedAt=[DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    $feed.launcher.version=$version; $feed.launcher.size=$launcher.Length
    $feed.launcher.sha256=$launcherHash
    $feed.launcher.urls=@("https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v$version/PawsPatchLauncher.exe")
    $feed.changelog=@($history.$channel)
    $feed.newsTitle=$history.$channel[0].title; $feed.newsBody=$history.$channel[0].body
    $currentGame=$feed | Select-Object * -ExcludeProperty launcher,publishedAt,changelog,newsTitle,newsBody | ConvertTo-Json -Depth 40 -Compress
    if ($currentGame -ne $originalGame) { throw "Launcher-only update changed game data in $channel" }
    $payload=Join-Path $out "$channel.production.payload.json"
    $signed=Join-Path $out "$channel.signed.json"
    $feed | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $payload -Encoding utf8NoBOM
    & $dotnet $publisher sign $payload $privateKey pawpatch-prod-2026 $signed
    if ($LASTEXITCODE -ne 0) { throw 'Signing failed' }
    & $dotnet $publisher verify $signed $publicKey
    if ($LASTEXITCODE -ne 0) { throw 'Signed feed verification failed' }
    Write-Output "UNCHANGED game data: $channel"
}
