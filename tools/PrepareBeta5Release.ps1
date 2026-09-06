param(
    [Parameter(Mandatory=$true)][string]$PublishedLauncherPath,
    [string]$OutputDirectory=(Join-Path $PSScriptRoot '..\release_workspace_20260906')
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
if ($launcher.VersionInfo.FileVersion -ne '0.5.4.0') { throw 'Expected the published launcher 0.5.4.' }
$launcherHash=(Get-FileHash -LiteralPath $launcher.FullName).Hash
$assetRoot='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v0.5.4/'
New-Item -ItemType Directory -Path $out -Force | Out-Null
foreach ($channel in 'stable','beta') {
    $source=Join-Path $repo "feed\$channel.json"
    & $dotnet $publisher verify $source $publicKey
    if ($LASTEXITCODE -ne 0) { throw 'Input feed signature invalid' }
    $envelope=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
    $feed=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($envelope.payload)) | ConvertFrom-Json
    $originalPackages=$feed.packages | ConvertTo-Json -Depth 30 -Compress
    $feed.publishedAt=[DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    $feed.launcher.version='0.5.4'; $feed.launcher.size=$launcher.Length
    $feed.launcher.sha256=$launcherHash; $feed.launcher.urls=@($assetRoot+'PawsPatchLauncher.exe')
    if ($channel -eq 'beta') {
        $colors=$feed.packages | Where-Object id -eq 'player-colors'
        if (@($colors).Count -ne 1 -or $colors.version -ne '0.1.0-beta.4') { throw 'Unexpected source color package' }
        $archive=Get-Item -LiteralPath (Join-Path $repo 'packages\player-colors-0.1.0-beta.5.zip')
        $colors.version='0.1.0-beta.5'; $colors.size=$archive.Length
        $colors.sha256=(Get-FileHash -LiteralPath $archive.FullName).Hash
        $colors.urls=@($assetRoot+$archive.Name)
        $colors.dependsOn=@($colors.dependsOn)+@('common-ui')
        if (@($feed.packages | Where-Object id -eq 'common-ui').Count -ne 0) { throw 'Common UI is already advertised' }
        $archive=Get-Item -LiteralPath (Join-Path $repo 'packages\common-ui-1.3.72-ui.1.zip')
        $feed.packages=@($feed.packages)+@([pscustomobject]@{
            id='common-ui';version='1.3.72-ui.1';priority=900;required=$true;experimental=$false
            size=$archive.Length;sha256=(Get-FileHash -LiteralPath $archive.FullName).Hash
            urls=@($assetRoot+$archive.Name);dependsOn=@('pawpatch-core')
            name=@{ru='Общие исправления интерфейса';en='Common interface fixes'}
            description=@{ru='Версии модов в меню и исправление отрицательного нуля. Всегда включено.';en='Mod versions in the menu and negative-zero display fix. Always enabled.'}
        })
        $oldUrl='https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/history/beta-colors-beta4.json'
        $feed.previousReleases=@([pscustomobject]@{label='Beta: colors beta.4';url=$oldUrl})+@($feed.previousReleases | Where-Object url -ne $oldUrl)
    }
    if ($channel -eq 'stable' -and ($feed.packages | ConvertTo-Json -Depth 30 -Compress) -ne $originalPackages) {
        throw 'Stable game packages changed; this release authorizes Beta only'
    }
    $feed.changelog=@($history.$channel); $feed.newsTitle=$history.$channel[0].title; $feed.newsBody=$history.$channel[0].body
    $payload=Join-Path $out "$channel.production.payload.json"
    $signed=Join-Path $out "$channel.signed.json"
    $feed | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $payload -Encoding utf8NoBOM
    & $dotnet $publisher sign $payload $privateKey pawpatch-prod-2026 $signed
    if ($LASTEXITCODE -ne 0) { throw 'Signing failed' }
    & $dotnet $publisher verify $signed $publicKey
    if ($LASTEXITCODE -ne 0) { throw 'Signed feed verification failed' }
}
Write-Output 'Signed candidates ready. Verify all published assets before copying to feed/ and pushing.'
