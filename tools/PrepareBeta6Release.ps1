param([string]$OutputDirectory=(Join-Path $PSScriptRoot '..\release_workspace_colors_beta6'))
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$out=[IO.Path]::GetFullPath($OutputDirectory)
$dotnet='C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe'
$publisher=Join-Path $repo 'tools\PawsPatchPublisher\bin\Release\net8.0-windows\PawsPatchPublisher.dll'
$publicKey=Join-Path $repo '.local\signing\pawpatch-signing-public.pem'
$privateKey=Join-Path $repo '.local\signing\pawpatch-signing-private.pem'
$source=Join-Path $repo 'feed\beta.json'
$snapshot=Join-Path $repo 'feed\history\beta-colors-beta5.json'
if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $snapshot).Hash) {
    throw 'Beta input must exactly match the preserved beta.5 signed snapshot.'
}
& $dotnet $publisher verify $source $publicKey
if ($LASTEXITCODE -ne 0) { throw 'Invalid input signature' }
$envelope=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
$feed=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($envelope.payload)) | ConvertFrom-Json
$launcherBefore=$feed.launcher | ConvertTo-Json -Depth 20 -Compress
$othersBefore=@($feed.packages | Where-Object id -ne 'player-colors') | ConvertTo-Json -Depth 30 -Compress
$colors=@($feed.packages | Where-Object id -eq 'player-colors')
if ($colors.Count -ne 1 -or $colors[0].version -ne '0.1.0-beta.5') { throw 'Unexpected color version' }
$colors=$colors[0]
$archive=Get-Item -LiteralPath (Join-Path $repo 'packages\player-colors-0.1.0-beta.6.zip')
$digest=(Get-FileHash -LiteralPath $archive.FullName).Hash
if ($archive.Length -ne 69009 -or $digest -ne 'C45EF0EE397DEC4242CCCA7884E4579049997DBF3E835FD095F8FB0C8251ECEE') {
    throw 'Archive is not the audited r16 candidate'
}
$colors.version='0.1.0-beta.6'; $colors.size=$archive.Length; $colors.sha256=$digest
$colors.urls=@('https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/colors-beta.6/'+$archive.Name)
$colors.description.ru='49 цветов игроков; исправление рассинхрона при выборе цвета в лобби. Все участники должны обновить Beta.'
$colors.description.en='49 player colors; lobby color-change desync fix. All peers must update Beta.'
$oldUrl='https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/history/beta-colors-beta5.json'
$feed.previousReleases=@([pscustomobject]@{label='Beta: colors beta.5';url=$oldUrl})+@($feed.previousReleases | Where-Object url -ne $oldUrl)
$history=Get-Content -LiteralPath (Join-Path $repo 'feed\changelog.history.json') -Raw | ConvertFrom-Json
if ($history.beta[0].version -ne '0.1.0-beta.6') { throw 'Missing beta.6 changelog' }
$feed.changelog=@($history.beta); $feed.newsTitle=$history.beta[0].title; $feed.newsBody=$history.beta[0].body
$feed.publishedAt=[DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
if (($feed.launcher | ConvertTo-Json -Depth 20 -Compress) -ne $launcherBefore) { throw 'Launcher changed' }
if ((@($feed.packages | Where-Object id -ne 'player-colors') | ConvertTo-Json -Depth 30 -Compress) -ne $othersBefore) { throw 'Other packages changed' }
New-Item -ItemType Directory -Path $out -Force | Out-Null
$payload=Join-Path $out 'beta.production.payload.json'
$signed=Join-Path $out 'beta.signed.json'
$feed | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $payload -Encoding utf8NoBOM
& $dotnet $publisher sign $payload $privateKey pawpatch-prod-2026 $signed
if ($LASTEXITCODE -ne 0) { throw 'Signing failed' }
& $dotnet $publisher verify $signed $publicKey
if ($LASTEXITCODE -ne 0) { throw 'Candidate signature verification failed' }
Write-Output 'Beta candidate signed. Download and verify every asset before advertising it. Stable is untouched.'
