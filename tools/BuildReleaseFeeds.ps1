param(
    [Parameter(Mandatory = $true)]
    [string]$LauncherPath,
    [string]$LauncherVersion = '0.4.0',
    [long]$PublishedLauncherSize = 0,
    [string]$PublishedLauncherSha256 = '',
    [string]$ModuleVersion = '1.3.72-options.1',
    [string]$ReleaseWorkspace = (Join-Path $PSScriptRoot '..\release_workspace_20260905')
)

$ErrorActionPreference = 'Stop'
$releaseRoot = [IO.Path]::GetFullPath($ReleaseWorkspace)
$packagesRoot = Join-Path $releaseRoot 'packages'
$feedRoot = Join-Path $releaseRoot 'feed'
$launcher = Get-Item -LiteralPath ([IO.Path]::GetFullPath($LauncherPath))
$launcherSize = if ($PublishedLauncherSize -gt 0) { $PublishedLauncherSize } else { $launcher.Length }
$launcherHash = if ([string]::IsNullOrWhiteSpace($PublishedLauncherSha256)) {
    (Get-FileHash -LiteralPath $launcher.FullName -Algorithm SHA256).Hash
} else {
    $PublishedLauncherSha256.ToUpperInvariant()
}
$publishedAt = [DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')

$definitions = @(
    [pscustomobject]@{
        Id = 'startup-base'; Version = '1.3.72-startup.1'; Priority = 50; Required = $true
        DependsOn = @('arcane-wars')
        RuName = 'Базовая конфигурация запуска'; EnName = 'Base startup configuration'
        RuDescription = 'Сохраняет рабочий depot игры при отключённой русской локализации'
        EnDescription = 'Keeps the game work depot configured when Russian localization is disabled'
    },
    [pscustomobject]@{
        Id = 'roaming-profile-standard-with-new'; Version = $ModuleVersion; Priority = 500; Required = $false
        DependsOn = @('arcane-wars', 'pawpatch-core')
        RuName = 'Стандартная частота с новыми ротами'; EnName = 'Standard frequency with additional companies'
        RuDescription = 'Обычные интервалы и шансы; дополнительные блуждающие роты включены'
        EnDescription = 'Original intervals and chances; additional roaming companies enabled'
    },
    [pscustomobject]@{
        Id = 'roaming-profile-x4-no-new'; Version = $ModuleVersion; Priority = 510; Required = $false
        DependsOn = @('arcane-wars', 'pawpatch-core')
        RuName = 'Частота ×4 без новых рот'; EnName = '×4 frequency without additional companies'
        RuDescription = 'Ускоряет штатные блуждающие роты, не добавляя новые источники'
        EnDescription = 'Speeds up original roaming companies without adding new sources'
    },
    [pscustomobject]@{
        Id = 'roaming-profile-standard-no-new'; Version = $ModuleVersion; Priority = 520; Required = $false
        DependsOn = @('arcane-wars', 'pawpatch-core')
        RuName = 'Стандартные блуждающие роты'; EnName = 'Original roaming-company profile'
        RuDescription = 'Обычные интервалы, шансы и исходный набор источников'
        EnDescription = 'Original intervals, chances and source set'
    },
    [pscustomobject]@{
        Id = 'siege-balance-standard'; Version = $ModuleVersion; Priority = 600; Required = $false
        DependsOn = @('arcane-wars', 'pawpatch-core')
        RuName = 'Стандартный баланс осадных машин'; EnName = 'Original siege-engine balance'
        RuDescription = 'Возвращает исходную стоимость четырёх особых осадных машин'
        EnDescription = 'Restores the original cost of four special siege engines'
    },
    [pscustomobject]@{
        Id = 'large-map-sizes-standard'; Version = $ModuleVersion; Priority = 700; Required = $false
        DependsOn = @('arcane-wars', 'pawpatch-core')
        RuName = 'Стандартные размеры карт'; EnName = 'Original map sizes'
        RuDescription = 'Убирает только дополнительные размеры 1024 и 1152'
        EnDescription = 'Removes only the additional 1024 and 1152 sizes'
    }
)

function New-PackageRelease($definition) {
    $archiveName = "$($definition.Id)-$($definition.Version).zip"
    $archivePath = Join-Path $packagesRoot $archiveName
    $archive = Get-Item -LiteralPath $archivePath
    $packageUrl = if ($definition.Id -eq 'startup-base') {
        "https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/packages/$archiveName"
    } else {
        "https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v$LauncherVersion/$archiveName"
    }
    return [ordered]@{
        id = $definition.Id
        version = $definition.Version
        priority = $definition.Priority
        required = $definition.Required
        experimental = $false
        size = $archive.Length
        sha256 = (Get-FileHash -LiteralPath $archive.FullName -Algorithm SHA256).Hash
        urls = @($packageUrl)
        dependsOn = @($definition.DependsOn)
        name = [ordered]@{ ru = $definition.RuName; en = $definition.EnName }
        description = [ordered]@{ ru = $definition.RuDescription; en = $definition.EnDescription }
    }
}

$newIds = $definitions.Id
foreach ($channel in @('stable', 'beta')) {
    $path = Join-Path $feedRoot "$channel.production.payload.json"
    $feed = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    $feed.publishedAt = $publishedAt
    $feed.launcher.version = $LauncherVersion
    $feed.launcher.size = $launcherSize
    $feed.launcher.sha256 = $launcherHash
    $feed.launcher.urls = @("https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v$LauncherVersion/PawsPatchLauncher.exe")
    $kept = @($feed.packages | Where-Object { $_.id -notin $newIds })
    $feed.packages = @($kept) + @($definitions | ForEach-Object { New-PackageRelease $_ })
    if ($channel -eq 'stable') {
        $feed.newsTitle = [ordered]@{ ru = 'Лаунчер 0.4.0 · игровые переключатели'; en = 'Launcher 0.4.0 · gameplay switches' }
        $feed.newsBody = [ordered]@{
            ru = 'Добавлены переключатели вражды независимых, частоты и состава блуждающих рот, баланса осадных машин и больших карт. У каждого пункта есть справка, а код конфигурации и архив диагностики упрощают сетевую игру и разбор ошибок.'
            en = 'Added switches for independent hostility, roaming-company frequency and sources, siege balance and large maps. Every item has help, while configuration codes and diagnostic archives simplify multiplayer setup and troubleshooting.'
        }
    } else {
        $feed.newsTitle = [ordered]@{ ru = 'Бета · игровые переключатели и цвета'; en = 'Beta · gameplay switches and colors' }
        $feed.newsBody = [ordered]@{
            ru = 'Все игровые переключатели версии 0.4.0 доступны вместе с экспериментальными расширенными цветами. Перед сетевой игрой сравните код конфигурации у всех участников.'
            en = 'All 0.4.0 gameplay switches are available alongside the experimental extended colors. Compare configuration codes for every participant before a multiplayer match.'
        }
    }
    $feed | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $path -Encoding utf8NoBOM
    Write-Output "Updated $path"
}

Write-Output "Launcher $LauncherVersion $launcherSize bytes $launcherHash"
