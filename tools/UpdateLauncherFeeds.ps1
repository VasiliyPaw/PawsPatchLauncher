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

    if ($channel -eq 'stable') {
        $feed.newsTitle = [ordered]@{ ru = "Лаунчер $LauncherVersion · удобные проверки"; en = "Launcher $LauncherVersion · convenient checks" }
        $feed.newsBody = [ordered]@{
            ru = 'Кнопка проверки обновлений теперь всегда доступна в нижней панели. Проверка целостности установленных файлов перенесена в настройки.'
            en = 'The update check is now always available in the bottom bar. Installed-file verification was moved to Settings.'
        }
    } else {
        $feed.newsTitle = [ordered]@{ ru = "Бета · цвета r10 и лаунчер $LauncherVersion"; en = "Beta · colors r10 and launcher $LauncherVersion" }
        $feed.newsBody = [ordered]@{
            ru = 'Палитра упорядочена по обычной, светлой и тёмной радуге; исправлена начальная подпись «Случайно». Проверка обновлений перенесена в нижнюю панель, а проверка файлов — в настройки.'
            en = 'The palette is ordered as regular, light and dark rainbows, and the initial Random label is fixed. Update checking moved to the bottom bar and file verification to Settings.'
        }
    }

    $feed | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $path -Encoding utf8NoBOM
    Write-Output "Updated launcher metadata in $path"
}
