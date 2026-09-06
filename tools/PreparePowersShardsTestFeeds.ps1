param([Parameter(Mandatory=$true)][string]$OutputDirectory,
      [Parameter(Mandatory=$true)][string]$LauncherPath)
$ErrorActionPreference = 'Stop'
$releaseRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$releaseOutput = [IO.Path]::GetFullPath($OutputDirectory)
if (-not $releaseOutput.StartsWith($releaseRepo + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be inside this workspace.' }
$releaseFeed = Join-Path $releaseOutput 'feed'
if ((Test-Path -LiteralPath $releaseFeed) -and @(Get-ChildItem -LiteralPath $releaseFeed -Force).Count -gt 0) { throw 'Use a fresh feed output; existing candidates are retained.' }
$releaseDotnet = 'C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe'
$releasePublisher = Join-Path $releaseRepo 'tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll'
$releasePublic = Join-Path $releaseRepo '.local/signing/pawpatch-signing-public.pem'
$releasePrivate = Join-Path $releaseRepo '.local/signing/pawpatch-signing-private.pem'
$releaseArchive = Join-Path $releaseOutput 'packages/powers-shards-original-1.3.72-powers.1.zip'
$releaseSource = Join-Path $releaseOutput 'sources/powers-shards-original'
& $releaseDotnet $releasePublisher pack powers-shards-original 1.3.72-powers.1 $releaseSource $releaseArchive
if ($LASTEXITCODE -ne 0) { throw 'Package build failed.' }
$releaseLauncher = Get-Item -LiteralPath $LauncherPath
$releaseLauncherHash = (Get-FileHash -LiteralPath $releaseLauncher.FullName).Hash
$releaseVersion = [Version]::Parse($releaseLauncher.VersionInfo.FileVersion).ToString(3)
$releasePackage = [ordered]@{
    id='powers-shards-original'; version='1.3.72-powers.1'; priority=450; required=$false; experimental=$false
    size=(Get-Item -LiteralPath $releaseArchive).Length; sha256=(Get-FileHash -LiteralPath $releaseArchive).Hash
    urls=@($releaseArchive); dependsOn=@('arcane-wars','pawpatch-core')
    name=@{ru='Powers и Shards Arcane Wars';en='Arcane Wars Powers and Shards'}
    description=@{ru='Возвращает обе механики при выключенном пункте «Отключение Powers и Shards»';en='Restores both mechanics when Disable Powers and Shards is off'}
}
New-Item -ItemType Directory -Path $releaseFeed -Force | Out-Null
foreach ($releaseChannel in @('stable','beta')) {
    $releaseInput = Join-Path $releaseRepo "feed/$releaseChannel.json"
    & $releaseDotnet $releasePublisher verify $releaseInput $releasePublic
    if ($LASTEXITCODE -ne 0) { throw 'Original feed signature check failed.' }
    $releaseEnvelope = Get-Content -LiteralPath $releaseInput -Raw | ConvertFrom-Json
    $releasePayload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($releaseEnvelope.payload)) | ConvertFrom-Json
    foreach ($releaseItem in $releasePayload.packages) {
        $releaseName = [IO.Path]::GetFileName(([Uri]$releaseItem.urls[0]).AbsolutePath)
        $releaseCandidates = @((Join-Path $releaseRepo "packages/$releaseName"), (Join-Path $releaseRepo "release_workspace_20260905/packages/$releaseName"))
        $releaseLocal = $releaseCandidates | Where-Object { (Test-Path -LiteralPath $_ -PathType Leaf) -and (Get-FileHash -LiteralPath $_).Hash -eq $releaseItem.sha256 } | Select-Object -First 1
        if (-not $releaseLocal) { throw "Verified local package missing: $releaseName" }
        $releaseItem.urls = @($releaseLocal)
    }
    $releasePayload.packages = @($releasePayload.packages) + @($releasePackage)
    $releasePayload.publishedAt = [DateTimeOffset]::UtcNow.ToString('o')
    $releasePayload.launcher.version = $releaseVersion
    $releasePayload.launcher.size = $releaseLauncher.Length
    $releasePayload.launcher.sha256 = $releaseLauncherHash
    $releasePayload.launcher.urls = @($releaseLauncher.FullName)
    # Keep the test fully local, including the historical-release picker.
    $releasePayload | Add-Member -NotePropertyName previousReleases -NotePropertyValue @() -Force
    $releasePayloadPath = Join-Path $releaseFeed "$releaseChannel.local.payload.json"
    $releaseSignedPath = Join-Path $releaseFeed "$releaseChannel.signed.json"
    $releasePayload | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $releasePayloadPath -Encoding utf8NoBOM
    & $releaseDotnet $releasePublisher sign $releasePayloadPath $releasePrivate pawpatch-prod-2026 $releaseSignedPath
    if ($LASTEXITCODE -ne 0) { throw 'Local signing failed.' }
    & $releaseDotnet $releasePublisher verify $releaseSignedPath $releasePublic
    if ($LASTEXITCODE -ne 0) { throw 'Local signature verification failed.' }
}
$releaseConfig = Get-Content -LiteralPath (Join-Path $releaseRepo 'src/PawsPatchLauncher/launcher.config.json') -Raw | ConvertFrom-Json
$releaseConfig.feedUrls = @((Join-Path $releaseFeed 'stable.signed.json'))
$releaseConfig.betaFeedUrls = @((Join-Path $releaseFeed 'beta.signed.json'))
$releaseConfig.cacheRoot = Join-Path $releaseOutput 'local-cache'
$releaseConfig | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $releaseLauncher.DirectoryName 'launcher.config.json') -Encoding utf8NoBOM
Write-Output 'LOCAL TEST FEEDS READY. No remote uploads or live-game changes.'
