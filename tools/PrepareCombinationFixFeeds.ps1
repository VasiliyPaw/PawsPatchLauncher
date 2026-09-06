param([Parameter(Mandatory=$true)][string]$LauncherPath)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$output = Join-Path $repo 'release_workspace_056/combination-fix'
$feedOutput = Join-Path $output 'feed'
if (Test-Path -LiteralPath $feedOutput) { throw 'Keep previous candidates; use an unprepared combination-fix directory.' }
$dotnet = 'C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe'
$publisher = Join-Path $repo 'tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll'
$public = Join-Path $repo '.local/signing/pawpatch-signing-public.pem'
$private = Join-Path $repo '.local/signing/pawpatch-signing-private.pem'
$launcher = Get-Item -LiteralPath $LauncherPath
$version = [Version]::Parse($launcher.VersionInfo.FileVersion).ToString(3)
$repairs = @('roaming-profile-x4-no-new','roaming-profile-standard-no-new','siege-balance-standard')
foreach ($id in $repairs) {
    & $dotnet $publisher pack $id '1.3.72-options.2' (Join-Path $output "sources/$id") (Join-Path $output "packages/$id-1.3.72-options.2.zip")
    if ($LASTEXITCODE -ne 0) { throw "Cannot pack $id" }
}
New-Item -ItemType Directory -Path $feedOutput | Out-Null
foreach ($channel in @('stable','beta')) {
    $inputFeed = Join-Path $repo "release_workspace_056/powers-shards/feed/$channel.signed.json"
    & $dotnet $publisher verify $inputFeed $public
    if ($LASTEXITCODE -ne 0) { throw 'Previous candidate signature is invalid' }
    $envelope = Get-Content -LiteralPath $inputFeed -Raw | ConvertFrom-Json
    $payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($envelope.payload)) | ConvertFrom-Json
    foreach ($package in $payload.packages) {
        if ($package.id -in $repairs) {
            $archive = Get-Item -LiteralPath (Join-Path $output "packages/$($package.id)-1.3.72-options.2.zip")
            $package.version = '1.3.72-options.2'
            $package.size = $archive.Length
            $package.sha256 = (Get-FileHash -LiteralPath $archive.FullName).Hash
            $package.urls = @($archive.FullName)
        }
        # No network fallback in this candidate; verify all reused package bytes as well.
        foreach ($url in $package.urls) {
            if (-not [IO.Path]::IsPathFullyQualified($url) -or $url -match '^https?:') { throw 'Candidate package URL is not local' }
            if ((Get-FileHash -LiteralPath $url).Hash -ne $package.sha256) { throw "Package hash differs: $($package.id)" }
        }
        if ($package.id -eq 'siege-balance-standard') {
            $package.description.ru = 'Возвращает исходный осадный баланс Arcane Wars, включая стоимость и атаки, с сохранением перевода'
            $package.description.en = 'Restores original Arcane Wars siege balance, including cost and attacks, while preserving localization'
        }
    }
    $payload.launcher.version = $version
    $payload.launcher.sha256 = (Get-FileHash -LiteralPath $launcher.FullName).Hash
    $payload.launcher.size = $launcher.Length
    $payload.launcher.urls = @($launcher.FullName)
    $payload.publishedAt = [DateTimeOffset]::UtcNow.ToString('o')
    $json = Join-Path $feedOutput "$channel.payload.json"
    $signed = Join-Path $feedOutput "$channel.signed.json"
    $payload | ConvertTo-Json -Depth 45 | Set-Content -LiteralPath $json -Encoding utf8NoBOM
    & $dotnet $publisher sign $json $private pawpatch-prod-2026 $signed
    if ($LASTEXITCODE -ne 0) { throw 'Local signing failed' }
    & $dotnet $publisher verify $signed $public
    if ($LASTEXITCODE -ne 0) { throw 'Local signature verification failed' }
}
$config = Get-Content -LiteralPath (Join-Path $repo 'src/PawsPatchLauncher/launcher.config.json') -Raw | ConvertFrom-Json
$config.feedUrls = @((Join-Path $feedOutput 'stable.signed.json'))
$config.betaFeedUrls = @((Join-Path $feedOutput 'beta.signed.json'))
$config.cacheRoot = Join-Path $output 'local-cache'
$config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $launcher.DirectoryName 'launcher.config.json') -Encoding utf8NoBOM
'READY: local candidate only; no uploads or installed-game changes'
