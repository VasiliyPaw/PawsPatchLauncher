param(
    [string]$Version = '0.1.0-beta.2',
    [string]$ReleaseWorkspace = ''
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ReleaseWorkspace)) {
    $ReleaseWorkspace = Join-Path $PSScriptRoot '..\release_workspace_20260905'
}

$releaseRoot = [IO.Path]::GetFullPath($ReleaseWorkspace)
$archiveName = "player-colors-$Version.zip"
$archivePath = Join-Path (Join-Path $releaseRoot 'packages') $archiveName
$archive = Get-Item -LiteralPath $archivePath
$payloadPath = Join-Path (Join-Path $releaseRoot 'feed') 'beta.production.payload.json'
$feed = Get-Content -LiteralPath $payloadPath -Raw | ConvertFrom-Json
$package = $feed.packages | Where-Object { $_.id -eq 'player-colors' } | Select-Object -First 1
if ($null -eq $package) { throw 'The Beta feed has no player-colors package.' }

$package.version = $Version
$package.size = $archive.Length
$package.sha256 = (Get-FileHash -LiteralPath $archive.FullName -Algorithm SHA256).Hash
$package.urls = @("https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/packages/$archiveName")
$package.description.ru = '50 цветов: обычная, светлая и тёмная радуга, чёрный и графитовый; исправлена начальная подпись «Случайно»'
$package.description.en = '50 colors: regular, light and dark rainbows, black and graphite; fixes the initial Random label'
$feed.publishedAt = [DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
$feed.newsTitle = [ordered]@{
    ru = 'Бета · обновление цветов r10'
    en = 'Beta · player colors r10'
}
$feed.newsBody = [ordered]@{
    ru = 'Белый удалён, «Почти чёрный» переименован в «Чёрный». Цвета упорядочены: обычная, светлая и тёмная радуга. Исправлено пустое поле вместо «Случайно» при первом входе в лобби.'
    en = 'White was removed and Near Black was renamed to Black. Colors are ordered as regular, light and dark rainbows. Fixed the blank field instead of Random on the first lobby entry.'
}

$feed | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $payloadPath -Encoding utf8NoBOM
Write-Output "Updated Beta player-colors $Version $($archive.Length) bytes $($package.sha256)"
