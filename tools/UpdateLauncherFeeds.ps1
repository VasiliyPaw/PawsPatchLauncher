param(
    [Parameter(Mandatory = $true)]
    [string]$LauncherVersion,
    [Parameter(Mandatory = $true)]
    [long]$PublishedLauncherSize,
    [Parameter(Mandatory = $true)]
    [string]$PublishedLauncherSha256,
    [string]$ReleaseWorkspace = (Join-Path $PSScriptRoot '..\release_workspace_20260905')
)

$ErrorActionPreference = 'Stop'
if ($PublishedLauncherSize -le 0) { throw 'PublishedLauncherSize must be positive.' }
if ($PublishedLauncherSha256 -notmatch '^[0-9A-Fa-f]{64}$') { throw 'PublishedLauncherSha256 must be a SHA-256 hash.' }

$releaseRoot = [IO.Path]::GetFullPath($ReleaseWorkspace)
$feedRoot = Join-Path $releaseRoot 'feed'
$history = Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\feed\changelog.history.json') -Raw | ConvertFrom-Json
$publishedAt = [DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
$launcherUrl = "https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v$LauncherVersion/PawsPatchLauncher.exe"

foreach ($channel in @('stable', 'beta')) {
    $path = Join-Path $feedRoot "$channel.production.payload.json"
    $feed = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    $feed.publishedAt = $publishedAt
    $feed.launcher.version = $LauncherVersion
    $feed.launcher.size = $PublishedLauncherSize
    $feed.launcher.sha256 = $PublishedLauncherSha256.ToUpperInvariant()
    $feed.launcher.urls = @($launcherUrl)

    $entries = @($history.$channel)
    if ($entries.Count -eq 0) { throw "No changelog entries are defined for $channel." }
    $feed | Add-Member -NotePropertyName changelog -NotePropertyValue $entries -Force
    $feed.newsTitle = $entries[0].title
    $feed.newsBody = $entries[0].body

    $feed | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $path -Encoding utf8NoBOM
    Write-Output "Updated launcher metadata in $path"
}
