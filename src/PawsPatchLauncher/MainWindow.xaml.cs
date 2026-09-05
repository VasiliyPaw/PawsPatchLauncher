using Microsoft.Win32;
using System.Diagnostics;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow : Window
{
    private readonly SettingsStore _settingsStore = new();
    private readonly LauncherConfiguration _configuration;
    private readonly FeedClient _feedClient;
    private readonly UserSettings _settings;
    private readonly Localization _text;
    private GameInstallation? _game;
    private ChannelManifest? _channel;
    private bool _busy;
    private bool _initializing = true;
    private bool _colorsAvailable;
    private bool _checkingFeed;
    private bool _patchUpdateAvailable;
    private bool _patchInstalled;
    private string _activePage = "home";
    private LauncherRelease? _pendingLauncherUpdate;
    private DateTimeOffset? _lastChecked;
    private readonly DispatcherTimer _updateTimer = new();

    public MainWindow()
    {
        InitializeComponent();
        _configuration = SettingsStore.LoadConfiguration();
        _feedClient = new FeedClient(_configuration);
        _settings = _settingsStore.Load();
        if (!_settings.LargeMapSizes)
        {
            _settings.LargeMapSizes = true;
            _settings.PreparedFeedFingerprint = null;
            _settingsStore.Save(_settings);
        }
        _text = new Localization(_settings.Language);
        BetaChannelToggle.IsChecked = _settings.Channel.Equals("beta", StringComparison.OrdinalIgnoreCase);
        SettingsBetaToggle.IsChecked = BetaChannelToggle.IsChecked;
        RussianToggle.IsChecked = _settings.RussianLocalization;
        ColorsToggle.IsChecked = _settings.CustomPlayerColors;
        IndependentHostilityToggle.IsChecked = _settings.IndependentHostility;
        AdditionalRoamingToggle.IsChecked = _settings.AdditionalRoamingCompanies;
        SiegeBalanceToggle.IsChecked = _settings.SiegeBalance;
        SelectOosMode(_settings.DesyncMode);
        SelectSpawnMode(_settings.RoamingSpawnMode);
        ApplyLanguage();
        SetActivePage("home");
        _updateTimer.Interval = TimeSpan.FromMinutes(1);
        _updateTimer.Tick += async (_, _) => await CheckFeedAsync(background: true);
        Closed += (_, _) => _updateTimer.Stop();
        _initializing = false;
        Loaded += async (_, _) => await InitializeAsync();
    }

    private async Task InitializeAsync()
    {
        LocateGame();
        await CheckFeedAsync();
        _updateTimer.Start();
        RefreshStatus();
    }

    private void ApplyLanguage()
    {
        TitleText.Text = _text["app.title"];
        SubtitleText.Text = _text["app.subtitle"];
        HomeNav.Content = "⌂   " + _text["nav.home"];
        ModulesNav.Content = "◇   " + _text["nav.modules"];
        SettingsNav.Content = "⚙   " + _text["nav.settings"];
        BetaChannelText.Text = _text["channel.beta"];
        BetaChannelToggle.ToolTip = _text["channel.beta.tip"];
        HomeWelcomeTitleText.Text = _text["home.welcome.title"];
        HomeWelcomeBodyText.Text = _text["home.welcome.body"];
        SettingsTitleText.Text = _text["settings.title"];
        SettingsLanguageTitleText.Text = _text["settings.language"];
        SettingsLanguageDescriptionText.Text = _text["settings.language.desc"];
        SettingsLanguageButton.Content = _text.Language == "ru" ? "English" : "Русский";
        SettingsBetaTitleText.Text = _text["settings.beta"];
        SettingsBetaDescriptionText.Text = _text["settings.beta.desc"];
        SettingsRepairTitleText.Text = _text["settings.repair"];
        SettingsRepairDescriptionText.Text = _text["settings.repair.desc"];
        SettingsRepairButton.Content = _text["button.repair"];
        SettingsUpdatesDescriptionText.Text = _text["settings.updates.desc"];
        CheckUpdatesButton.Content = _text["button.checknow"];
        var version = Assembly.GetExecutingAssembly().GetName().Version ?? new Version(0, 0, 0);
        LauncherVersionText.Text = $"{version.Major}.{version.Minor}.{version.Build} · {_settings.Channel.ToLowerInvariant()}";
        GamePathLabel.Text = _text["game.path"].ToUpperInvariant();
        GameVersionLabel.Text = _text["game.version"].ToUpperInvariant();
        PatchVersionLabel.Text = _text["patch.version"].ToUpperInvariant();
        ModulesTitleText.Text = _text["modules.title"];
        CoreTitleText.Text = _text["modules.core"];
        CoreDescriptionText.Text = _text["modules.core.desc"];
        RussianTitleText.Text = _text["modules.ru"];
        RussianDescriptionText.Text = _text["modules.ru.desc"];
        ColorsTitleText.Text = _text["modules.colors"];
        ColorsDescriptionText.Text = _text["modules.colors.desc"];
        OosTitleText.Text = _text["modules.oos"];
        OfficialOosRadio.Content = _text["modules.oos.official"];
        ContinueOosRadio.Content = _text["modules.oos.continue"];
        IndependentTitleText.Text = _text["modules.independent"];
        IndependentDescriptionText.Text = _text["modules.independent.desc"];
        RoamingSpawnTitleText.Text = _text["modules.spawn"];
        StandardSpawnRadio.Content = _text["modules.spawn.standard"];
        X4SpawnRadio.Content = _text["modules.spawn.x4"];
        AdditionalRoamingTitleText.Text = _text["modules.roaming"];
        AdditionalRoamingDescriptionText.Text = _text["modules.roaming.desc"];
        SiegeBalanceTitleText.Text = _text["modules.siege"];
        SiegeBalanceDescriptionText.Text = _text["modules.siege.desc"];
        MultiplayerNoteText.Text = _text["modules.multiplayer.note"];
        ConfigurationTitleText.Text = _text["configuration.title"];
        ConfigurationDescriptionText.Text = _text["configuration.desc"];
        CopyConfigurationButton.Content = _text["button.copyconfig"];
        DiagnosticsTitleText.Text = _text["diagnostics.title"];
        DiagnosticsDescriptionText.Text = _text["diagnostics.desc"];
        DiagnosticsButton.Content = _text["button.diagnostics"];
        HelpCloseButton.Content = _text["help.close"];
        NewsTitleText.Text = _channel?.NewsTitle.Get(_text.Language) is { Length: > 0 } title ? title : _text["news.title"];
        NewsBodyText.Text = _channel?.NewsBody.Get(_text.Language) is { Length: > 0 } body ? body : _text["news.empty"];
        UpdateButton.Content = _text["button.install"];
        LaunchButton.Content = _text["button.launch"];
        BrowseButton.Content = _text["button.browse"];
        LanguageButton.Content = _text.Language == "ru" ? "EN" : "RU";
        ApplyHelpTooltips(this);
        RefreshConfigurationCode();
        RefreshModuleAvailability();
        RefreshStatus();
    }

    private void LocateGame()
    {
        _game = GameLocator.Locate(_configuration.SteamAppId, _settings.GamePath);
        if (_game is not null && !string.Equals(_settings.GamePath, _game.Directory, StringComparison.OrdinalIgnoreCase))
        {
            _settings.GamePath = _game.Directory;
            _settingsStore.Save(_settings);
        }
    }

    private async Task CheckFeedAsync(bool background = false)
    {
        if (_checkingFeed || _busy && background) return;
        var sources = _settings.Channel.Equals("beta", StringComparison.OrdinalIgnoreCase)
            ? _configuration.BetaFeedUrls
            : _configuration.FeedUrls;
        if (sources.Count == 0)
        {
            OperationText.Text = _text["status.feedmissing"];
            return;
        }

        _checkingFeed = true;
        try
        {
            if (!background)
            {
                SetBusy(true, _text["progress.checking"]);
                _channel = null;
                RefreshModuleAvailability();
            }
            _channel = await _feedClient.GetChannelAsync(_settings.Channel);
            _lastChecked = DateTimeOffset.Now;
            RefreshModuleAvailability();
            RefreshStatus();
            if (background && _pendingLauncherUpdate is not null)
                OperationText.Text = string.Format(_text["update.launcher.ready"], _pendingLauncherUpdate.Version);
            else if (background && _patchUpdateAvailable)
                OperationText.Text = _patchInstalled
                    ? string.Format(_text["update.patch.title"], CurrentChannelName())
                    : _text["install.patch.title"];
        }
        catch (Exception ex)
        {
            if (!background) OperationText.Text = ex.GetBaseException().Message;
        }
        finally
        {
            _checkingFeed = false;
            if (!background)
            {
                SetBusy(false);
                ApplyLanguage();
            }
            else RefreshStatus();
        }
    }

    private void RefreshStatus()
    {
        var state = _game is null ? null : new ModuleInstaller(_game.Directory).LoadState();
        RefreshAvailableUpdates(state);
        GamePathText.Text = _game?.Directory ?? "—";
        GameVersionText.Text = _game is null ? "—" : $"{(_game.Branch == "beta" ? "Beta" : "Steam")} · build {_game.SteamBuild ?? "?"}";
        PatchVersionText.Text = state?.Modules.TryGetValue("pawpatch-core", out var core) == true ? core.Version : "—";
        ReadyStatusText.Text = _game is null
            ? _text["status.notfound"]
            : !_patchInstalled
                ? _text["status.notinstalled"]
            : _patchUpdateAvailable
                ? string.Format(_text["update.patch.title"], CurrentChannelName())
                : $"{_text["status.ready"]} · {CurrentChannelName()}";
        var statusKind = _game is null ? "danger" : !_patchInstalled || _patchUpdateAvailable ? "update" : "ready";
        ReadyStatusText.Foreground = (Brush)FindResource(statusKind == "danger" ? "DangerBrush" : statusKind == "update" ? "GoldBrightBrush" : "SuccessBrush");
        ReadyStatusBadge.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(statusKind == "danger" ? "#3B2226" : statusKind == "update" ? "#40351E" : "#193926"));
        ReadyStatusBadge.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(statusKind == "danger" ? "#844B50" : statusKind == "update" ? "#A9873E" : "#3F8D64"));
        UpdateButton.IsEnabled = !_busy && _game is not null && _channel is not null && _patchUpdateAvailable;
        SettingsRepairButton.IsEnabled = !_busy && _game is not null && state?.Modules.Count > 0;
        LaunchButton.IsEnabled = !_busy && _game is not null;
        ColorsToggle.IsEnabled = !_busy && _colorsAvailable;
        IndependentHostilityToggle.IsEnabled = !_busy && ColorsToggle.IsChecked != true;
        StandardSpawnRadio.IsEnabled = !_busy;
        X4SpawnRadio.IsEnabled = !_busy;
        AdditionalRoamingToggle.IsEnabled = !_busy;
        SiegeBalanceToggle.IsEnabled = !_busy;
        CopyConfigurationButton.IsEnabled = !_busy;
        DiagnosticsButton.IsEnabled = !_busy && _game is not null;
        BetaChannelToggle.IsEnabled = !_busy;
        SettingsBetaToggle.IsEnabled = !_busy;
        CheckUpdatesButton.IsEnabled = !_busy && !_checkingFeed;
        LastCheckedText.Text = _lastChecked is null ? "" : string.Format(_text["updates.checked"], _lastChecked.Value.ToString("HH:mm:ss"));
        RefreshConfigurationCode();
    }

    private void RefreshAvailableUpdates(InstallState? state)
    {
        _pendingLauncherUpdate = _channel is not null && SelfUpdater.IsNewer(_channel.Launcher.Version) && _channel.Launcher.Urls.Count > 0
            ? _channel.Launcher
            : null;
        LauncherUpdateButton.Visibility = _pendingLauncherUpdate is null ? Visibility.Collapsed : Visibility.Visible;
        if (_pendingLauncherUpdate is not null)
            LauncherUpdateButton.Content = string.Format(_text["button.launcherupdate"], _pendingLauncherUpdate.Version);

        _patchInstalled = state is not null
            && state.Modules.ContainsKey("arcane-wars")
            && state.Modules.ContainsKey("pawpatch-core");
        _patchUpdateAvailable = false;
        if (_game is not null && _channel is not null && state is not null)
        {
            try { _patchUpdateAvailable = NeedsChannelPreparation(_channel, state); }
            catch { _patchUpdateAvailable = false; }
        }

        UpdateNoticeTitleText.Text = _patchInstalled
            ? string.Format(_text["update.patch.title"], CurrentChannelName())
            : _text["install.patch.title"];
        UpdateNoticeBodyText.Text = _patchInstalled ? _text["update.patch.body"] : _text["install.patch.body"];
        UpdateNoticeBorder.Visibility = _activePage == "home" && _patchUpdateAvailable ? Visibility.Visible : Visibility.Collapsed;
        UpdateButton.Content = !_patchInstalled
            ? _text["button.install"]
            : _patchUpdateAvailable
                ? string.Format(_text["button.patchupdate"], CurrentChannelName())
                : _text["button.installed"];
    }

    private bool NeedsChannelPreparation(ChannelManifest channel, InstallState state)
    {
        if (!state.Modules.ContainsKey("arcane-wars") || !state.Modules.ContainsKey("pawpatch-core")) return true;
        foreach (var package in channel.Packages.Where(package => package.Required))
        {
            if (!state.Modules.TryGetValue(package.Id, out var installed)
                || !installed.Enabled
                || !installed.Version.Equals(package.Version, StringComparison.OrdinalIgnoreCase)
                || !installed.ArchiveSha256.Equals(package.Sha256, StringComparison.OrdinalIgnoreCase)
                || installed.Priority != package.Priority)
                return true;
        }

        var fingerprint = ChannelFingerprint.Create(channel);
        if (!string.Equals(_settings.PreparedChannel, channel.Channel, StringComparison.OrdinalIgnoreCase)
            || !string.Equals(_settings.PreparedFeedFingerprint, fingerprint, StringComparison.OrdinalIgnoreCase))
            return true;
        return channel.Packages.Any(package => !_feedClient.IsPackageCached(package));
    }

    private string CurrentChannelName()
        => _settings.Channel.Equals("beta", StringComparison.OrdinalIgnoreCase) ? _text["channel.beta"] : "Stable";

    private async void UpdateButton_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _channel is null || _busy) return;
        try
        {
            SetBusy(true, _text["progress.downloading"]);
            await ApplySelectedConfigurationAsync(_channel, prepareWholeChannel: true);
            OperationText.Text = _text["status.ready"];
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); RefreshStatus(); }
    }

    private async Task ApplySelectedConfigurationAsync(ChannelManifest channel, bool prepareWholeChannel = false)
    {
        if (_game is null) throw new InvalidOperationException(_text["status.notfound"]);
        await EnsureSupportedGameAsync(channel);
        if (IsGameRunning())
            throw new InvalidOperationException(_text.Language == "ru" ? "Перед изменением файлов полностью закройте Kohan II." : "Close Kohan II before changing its files.");

        var selected = ResolveSelectedPackages(channel);
        Dictionary<string, string>? downloaded = null;
        if (prepareWholeChannel)
        {
            downloaded = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var package in channel.Packages.OrderBy(package => package.Priority))
                downloaded[package.Id] = await DownloadPackageAsync(package);
        }
        var modules = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase);
        var installer = new ModuleInstaller(_game.Directory);
        foreach (var package in selected.OrderBy(x => x.Priority))
        {
            var archive = downloaded is not null && downloaded.TryGetValue(package.Id, out var cached)
                ? cached
                : await DownloadPackageAsync(package);
            modules[package.Id] = await installer.PrepareAsync(package, archive);
        }
        OperationProgress.IsIndeterminate = true;
        OperationText.Text = _text["progress.installing"];
        await installer.ReconcileAsync(modules);
        var errors = await installer.VerifyAsync();
        if (errors.Count > 0)
            throw new InvalidDataException("Installed file verification failed: " + string.Join("; ", errors.Take(5)));
        if (prepareWholeChannel)
        {
            _settings.PreparedChannel = channel.Channel;
            _settings.PreparedFeedFingerprint = ChannelFingerprint.Create(channel);
            _settingsStore.Save(_settings);
        }
        OperationProgress.IsIndeterminate = false;
        OperationProgress.Value = 100;
    }

    private Task<string> DownloadPackageAsync(PackageRelease package)
    {
        var progress = new Progress<(long Received, long? Total)>(value =>
        {
            OperationText.Text = $"{_text["progress.downloading"]}: {package.Name.Get(_text.Language)}";
            OperationProgress.IsIndeterminate = value.Total is null;
            if (value.Total is > 0) OperationProgress.Value = value.Received * 100d / value.Total.Value;
        });
        return _feedClient.DownloadVerifiedAsync(package, progress);
    }

    private List<PackageRelease> ResolveSelectedPackages(ChannelManifest channel)
    {
        var ids = new HashSet<string>(channel.Packages.Where(x => x.Required).Select(x => x.Id), StringComparer.OrdinalIgnoreCase);
        if (RussianToggle.IsChecked == true) ids.Add("localization-ru");
        if (_colorsAvailable && ColorsToggle.IsChecked == true) ids.Add("player-colors");
        if (_settings.DesyncMode == "continue") ids.Add("desync-continue");

        var fastSpawn = _settings.RoamingSpawnMode.Equals("x4", StringComparison.OrdinalIgnoreCase);
        if (!fastSpawn && _settings.AdditionalRoamingCompanies) ids.Add("roaming-profile-standard-with-new");
        if (fastSpawn && !_settings.AdditionalRoamingCompanies) ids.Add("roaming-profile-x4-no-new");
        if (!fastSpawn && !_settings.AdditionalRoamingCompanies) ids.Add("roaming-profile-standard-no-new");
        if (!_settings.SiegeBalance) ids.Add("siege-balance-standard");

        bool changed;
        do
        {
            changed = false;
            foreach (var package in channel.Packages.Where(x => ids.Contains(x.Id)))
                foreach (var dependency in package.DependsOn)
                    if (ids.Add(dependency)) changed = true;
        } while (changed);

        var missing = ids.Where(id => channel.Packages.All(x => !x.Id.Equals(id, StringComparison.OrdinalIgnoreCase))).ToList();
        if (missing.Count > 0) throw new InvalidDataException("Missing update packages: " + string.Join(", ", missing));
        return channel.Packages.Where(x => ids.Contains(x.Id)).ToList();
    }

    private async void RepairButton_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _busy) return;
        try
        {
            SetBusy(true, _text["button.repair"] + "…");
            var errors = await new ModuleInstaller(_game.Directory).VerifyAsync();
            OperationText.Text = errors.Count == 0 ? _text["status.ready"] : string.Join(Environment.NewLine, errors.Take(5));
            OperationProgress.Value = errors.Count == 0 ? 100 : 0;
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); }
    }

    private async void LaunchButton_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _busy) return;
        try
        {
            if (_channel is null) await CheckFeedAsync();
            var channel = _channel ?? throw new InvalidOperationException(_text["status.feedmissing"]);
            var installer = new ModuleInstaller(_game.Directory);
            var state = installer.LoadState();
            var executable = ResolveLaunchExecutable(_game.Directory);
            var prepareWholeChannel = NeedsChannelPreparation(channel, state);
            var needsApply = prepareWholeChannel || UpdateDetector.HasModuleChanges(state, ResolveSelectedPackages(channel)) || !File.Exists(executable);
            if (needsApply)
            {
                SetBusy(true, _text["progress.beforelaunch"]);
                await ApplySelectedConfigurationAsync(channel, prepareWholeChannel);
                executable = ResolveLaunchExecutable(_game.Directory);
            }
            if (!File.Exists(executable))
                throw new FileNotFoundException(_text.Language == "ru"
                    ? "Не найден EXE для выбранного набора функций."
                    : "The executable for the selected feature set was not found.", executable);

            OperationText.Text = _text["status.ready"];
            Process.Start(new ProcessStartInfo(executable) { WorkingDirectory = _game.Directory, UseShellExecute = true });
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); RefreshStatus(); }
    }

    private static bool IsGameRunning()
    {
        var processNames = new[]
        {
            "k2",
            "k2_paws_family_herd_relations_1372",
            "k2_paws_sync_family_herd_relations_1372",
            "k2_paws_sync_continue_1372",
            "k2_paws_lobby_colors_mp_1372_experimental"
        };
        return processNames.Any(name => Process.GetProcessesByName(name).Length > 0);
    }

    private string ResolveLaunchExecutable(string root)
    {
        var name = GameExecutableSelector.Select(
            _configuration,
            _colorsAvailable && ColorsToggle.IsChecked == true,
            _settings.DesyncMode.Equals("continue", StringComparison.OrdinalIgnoreCase),
            _settings.IndependentHostility);
        return Path.Combine(root, name);
    }

    private async Task EnsureSupportedGameAsync(ChannelManifest channel)
    {
        if (_game is null) throw new InvalidOperationException(_text["status.notfound"]);
        var hash = await CryptoAndIO.Sha256Async(_game.ExecutablePath);
        if (channel.Game.K2ExeSha256.Count > 0 && !channel.Game.K2ExeSha256.Contains(hash, StringComparer.OrdinalIgnoreCase))
            throw new InvalidOperationException(_text.Language == "ru"
                ? $"Версия k2.exe не поддерживается. Нужна Steam Beta {channel.Game.Version}, build {channel.Game.SteamBuild}."
                : $"This k2.exe version is unsupported. Steam Beta {channel.Game.Version}, build {channel.Game.SteamBuild} is required.");
    }

    private async void LauncherUpdateButton_Click(object sender, RoutedEventArgs e)
    {
        var release = _pendingLauncherUpdate;
        if (release is null || _busy) return;
        try
        {
            SetBusy(true, _text.Language == "ru" ? $"Обновляю лаунчер до {release.Version}…" : $"Updating launcher to {release.Version}…");
            var progress = new Progress<(long Received, long? Total)>(value =>
            {
                OperationProgress.IsIndeterminate = value.Total is null;
                if (value.Total is > 0) OperationProgress.Value = value.Received * 100d / value.Total.Value;
            });
            var executable = await _feedClient.DownloadLauncherAsync(release, progress);
            SelfUpdater.ScheduleReplacement(executable);
            Application.Current.Shutdown();
        }
        catch (Exception ex)
        {
            ShowError(ex);
            SetBusy(false);
        }
    }

    private void BrowseButton_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog { Title = _text["dialog.selectgame"], InitialDirectory = _game?.Directory };
        if (dialog.ShowDialog(this) != true) return;
        var found = GameLocator.Validate(dialog.FolderName, _configuration.SteamAppId);
        if (found is null)
        {
            MessageBox.Show(_text["status.notfound"], _text["error.title"], MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        _game = found;
        _settings.GamePath = found.Directory;
        _settingsStore.Save(_settings);
        RefreshStatus();
    }

    private void OptionChanged(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        _settings.RussianLocalization = RussianToggle.IsChecked == true;
        _settings.CustomPlayerColors = ColorsToggle.IsChecked == true;
        if (ColorsToggle.IsChecked == true && _settings.DesyncMode == "continue")
        {
            _settings.DesyncMode = "official";
            SelectOosMode("official");
            OperationText.Text = _text.Language == "ru"
                ? "Цвета пока тестируются только со штатной проверкой рассинхрона."
                : "Player colors are currently tested only with the official out-of-sync handling.";
        }
        if (ColorsToggle.IsChecked == true)
        {
            _settings.IndependentHostility = true;
            IndependentHostilityToggle.IsChecked = true;
        }
        ContinueOosRadio.IsEnabled = ColorsToggle.IsChecked != true;
        _settingsStore.Save(_settings);
        RefreshConfigurationCode();
        RefreshStatus();
    }

    private void GameplayOptionChanged(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        _settings.IndependentHostility = IndependentHostilityToggle.IsChecked == true;
        _settings.AdditionalRoamingCompanies = AdditionalRoamingToggle.IsChecked == true;
        _settings.SiegeBalance = SiegeBalanceToggle.IsChecked == true;
        _settingsStore.Save(_settings);
        RefreshConfigurationCode();
        RefreshStatus();
    }

    private void RefreshModuleAvailability()
    {
        _colorsAvailable = _channel?.Packages.Any(x => x.Id.Equals("player-colors", StringComparison.OrdinalIgnoreCase)) == true;
        ColorsToggle.IsChecked = _colorsAvailable && _settings.CustomPlayerColors;
        if (ColorsToggle.IsChecked == true && _settings.DesyncMode == "continue")
        {
            _settings.DesyncMode = "official";
            SelectOosMode("official");
            _settingsStore.Save(_settings);
        }
        if (ColorsToggle.IsChecked == true)
        {
            _settings.IndependentHostility = true;
            IndependentHostilityToggle.IsChecked = true;
            _settingsStore.Save(_settings);
        }
        ColorsToggle.IsEnabled = !_busy && _colorsAvailable;
        ContinueOosRadio.IsEnabled = ColorsToggle.IsChecked != true;
        IndependentHostilityToggle.IsChecked = _settings.IndependentHostility;
        AdditionalRoamingToggle.IsChecked = _settings.AdditionalRoamingCompanies;
        SiegeBalanceToggle.IsChecked = _settings.SiegeBalance;
        IndependentHostilityToggle.IsEnabled = !_busy && ColorsToggle.IsChecked != true;
        if (!_colorsAvailable)
        {
            ColorsDescriptionText.Text = _text.Language == "ru"
                ? "Доступно в канале «Бета»"
                : "Available in the Beta channel";
        }
    }

    private async void BetaChannelToggle_Click(object sender, RoutedEventArgs e)
    {
        if (_initializing || _busy) return;
        await ChangeChannelAsync(BetaChannelToggle.IsChecked == true);
    }

    private async void SettingsBetaToggle_Click(object sender, RoutedEventArgs e)
    {
        if (_initializing || _busy) return;
        await ChangeChannelAsync(SettingsBetaToggle.IsChecked == true);
    }

    private async Task ChangeChannelAsync(bool beta)
    {
        _settings.Channel = beta ? "beta" : "stable";
        BetaChannelToggle.IsChecked = beta;
        SettingsBetaToggle.IsChecked = beta;
        _settingsStore.Save(_settings);
        _channel = null;
        RefreshModuleAvailability();
        ApplyLanguage();
        await CheckFeedAsync();
        RefreshStatus();
    }

    private async void CheckUpdatesButton_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || _checkingFeed) return;
        await CheckFeedAsync();
        RefreshStatus();
        if (!_patchUpdateAvailable && _pendingLauncherUpdate is null)
            OperationText.Text = string.Format(_text["updates.current"], CurrentChannelName());
    }

    private void OosMode_Checked(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        if (sender is RadioButton item && item.Tag is string mode)
        {
            _settings.DesyncMode = mode;
            _settingsStore.Save(_settings);
            RefreshConfigurationCode();
            RefreshStatus();
        }
    }

    private void SelectOosMode(string mode)
    {
        OfficialOosRadio.IsChecked = !mode.Equals("continue", StringComparison.OrdinalIgnoreCase);
        ContinueOosRadio.IsChecked = mode.Equals("continue", StringComparison.OrdinalIgnoreCase);
    }

    private void SpawnMode_Checked(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        if (sender is RadioButton item && item.Tag is string mode)
        {
            _settings.RoamingSpawnMode = mode.Equals("x4", StringComparison.OrdinalIgnoreCase) ? "x4" : "standard";
            _settingsStore.Save(_settings);
            RefreshConfigurationCode();
            RefreshStatus();
        }
    }

    private void SelectSpawnMode(string mode)
    {
        var fast = mode.Equals("x4", StringComparison.OrdinalIgnoreCase);
        StandardSpawnRadio.IsChecked = !fast;
        X4SpawnRadio.IsChecked = fast;
    }

    private void LanguageButton_Click(object sender, RoutedEventArgs e)
    {
        _settings.Language = _text.Language == "ru" ? "en" : "ru";
        _text.SetLanguage(_settings.Language);
        _settingsStore.Save(_settings);
        ApplyLanguage();
    }

    private void RefreshConfigurationCode()
    {
        if (ConfigurationCodeText is not null)
            ConfigurationCodeText.Text = ConfigurationCode.Create(_settings);
    }

    private void CopyConfigurationButton_Click(object sender, RoutedEventArgs e)
    {
        var code = ConfigurationCode.Create(_settings);
        Clipboard.SetText(code);
        OperationText.Text = _text["configuration.copied"];
    }

    private async void DiagnosticsButton_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _busy) return;
        var downloads = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
        var dialog = new SaveFileDialog
        {
            Title = _text["diagnostics.dialog"],
            Filter = "ZIP archive (*.zip)|*.zip",
            FileName = $"PawsPatch_Diagnostics_{DateTime.Now:yyyy-MM-dd_HHmmss}.zip",
            InitialDirectory = Directory.Exists(downloads) ? downloads : Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
            AddExtension = true,
            DefaultExt = ".zip"
        };
        if (dialog.ShowDialog(this) != true) return;

        try
        {
            SetBusy(true, _text["diagnostics.progress"]);
            var installer = new ModuleInstaller(_game.Directory);
            var state = installer.LoadState();
            var errors = await installer.VerifyAsync();
            var archive = await DiagnosticsCollector.CreateAsync(dialog.FileName, _game, _settings, state, errors);
            OperationProgress.IsIndeterminate = false;
            OperationProgress.Value = 100;
            OperationText.Text = string.Format(_text["diagnostics.ready"], archive);
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); RefreshStatus(); }
    }

    private void HelpButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string key }) return;
        HelpTitleText.Text = _text[$"{key}.title"] == $"{key}.title" ? _text[key] : _text[$"{key}.title"];
        HelpBodyText.Text = _text[$"{key}.help"];
        HelpOverlay.Visibility = Visibility.Visible;
    }

    private void HelpCloseButton_Click(object sender, RoutedEventArgs e) => HelpOverlay.Visibility = Visibility.Collapsed;

    private void ApplyHelpTooltips(DependencyObject parent)
    {
        for (var index = 0; index < VisualTreeHelper.GetChildrenCount(parent); index++)
        {
            var child = VisualTreeHelper.GetChild(parent, index);
            if (child is Button { Tag: string key } button
                && (key.StartsWith("modules.", StringComparison.Ordinal) || key is "configuration" or "diagnostics"))
                button.ToolTip = _text[$"{key}.help"];
            ApplyHelpTooltips(child);
        }
    }

    private void SetBusy(bool busy, string? message = null)
    {
        _busy = busy;
        if (message is not null) OperationText.Text = message;
        OperationProgress.IsIndeterminate = busy;
        RefreshStatus();
    }

    private void ShowError(Exception exception)
    {
        OperationProgress.IsIndeterminate = false;
        OperationProgress.Value = 0;
        OperationText.Text = exception.GetBaseException().Message;
        MessageBox.Show(exception.GetBaseException().Message, _text["error.title"], MessageBoxButton.OK, MessageBoxImage.Error);
    }

    private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e) { if (e.ButtonState == MouseButtonState.Pressed) DragMove(); }
    private void MinimizeButton_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;
    private void CloseButton_Click(object sender, RoutedEventArgs e) => Close();
    private void HomeNav_Click(object sender, RoutedEventArgs e) => SetActivePage("home");
    private void ModulesNav_Click(object sender, RoutedEventArgs e) => SetActivePage("modules");
    private void SettingsNav_Click(object sender, RoutedEventArgs e) => SetActivePage("settings");

    private void SetActivePage(string page)
    {
        _activePage = page;
        var home = page == "home";
        var modules = page == "modules";
        var settings = page == "settings";

        HomeWelcomeCard.Visibility = home ? Visibility.Visible : Visibility.Collapsed;
        UpdateNoticeBorder.Visibility = home && _patchUpdateAvailable ? Visibility.Visible : Visibility.Collapsed;
        GameInfoCard.Visibility = home || settings ? Visibility.Visible : Visibility.Collapsed;
        SettingsPanel.Visibility = settings ? Visibility.Visible : Visibility.Collapsed;
        ModulesTitleText.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        MultiplayerNoteCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        CoreModuleCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        RussianModuleCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        ColorsModuleCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        OosModuleCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        IndependentHostilityCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        RoamingSpawnCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        AdditionalRoamingCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        SiegeBalanceCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        ConfigurationCodeCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        DiagnosticsCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;

        SetNavState(HomeNav, home);
        SetNavState(ModulesNav, modules);
        SetNavState(SettingsNav, settings);
        MainOptionsScroll.ScrollToTop();
    }

    private static void SetNavState(Button button, bool active)
    {
        button.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(active ? "#314969" : "#1B304D"));
        button.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(active ? "#B68D37" : "#526984"));
    }
}
