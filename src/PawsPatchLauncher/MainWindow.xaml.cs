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
    private bool _backgroundFeedCheck;
    private bool FeedBlocksActions => _checkingFeed && !_backgroundFeedCheck;
    private long _feedCheckVersion;
    private CancellationTokenSource? _feedCancellation;
    private bool _patchUpdateAvailable;
    private bool _patchInstalled;
    private string _activePage = "home";
    private string _changelogCategory = "patch";
    private LauncherRelease? _pendingLauncherUpdate;
    private readonly LauncherUpdateState _launcherUpdates = new();
    private bool _launcherCheckFailed;
    private DateTimeOffset? _lastChecked;
    private readonly DispatcherTimer _updateTimer = new();

    public MainWindow() : this(null, null) { }

    public MainWindow(LauncherConfiguration? configuration, FeedClient? feedClient, WindowPlacementStore? windowPlacementStore = null)
    {
        InitializeComponent();
        // Keep the larger default usable on small screens and at increased Windows scaling.
        var workArea = SystemParameters.WorkArea;
        Width = Math.Min(Width, Math.Max(1, workArea.Width - 32));
        Height = Math.Min(Height, Math.Max(1, workArea.Height - 32));
        MinWidth = Math.Min(MinWidth, Width);
        MinHeight = Math.Min(MinHeight, Height);
        _configuration = configuration ?? SettingsStore.LoadConfiguration();
        _feedClient = feedClient ?? new FeedClient(_configuration);
        _settings = _settingsStore.Load();
        if (!_settings.LargeMapSizes)
        {
            _settings.LargeMapSizes = true;
            _settings.PreparedFeedFingerprint = null;
            _settingsStore.Save(_settings);
        }
        _text = new Localization(_settings.Language);
        InitializeAccountUi();
        InitializeGameLaunchState();
        InitializeNotificationSound();
        InitializeFeedback();
        InitializeNotifications();
        InitializeReliabilityUi();
        InitializeEnhancementsUi();
        InitializeDiagnosticsUi();
        InitializeConfirmation();
        InitializeAppearance();
        SyncPatchChannelControls();
        RussianToggle.IsChecked = _settings.RussianLocalization;
        ColorsToggle.IsChecked = _settings.CustomPlayerColors;
        IndependentHostilityToggle.IsChecked = _settings.IndependentHostility;
        AdditionalRoamingToggle.IsChecked = _settings.AdditionalRoamingCompanies;
        SiegeBalanceToggle.IsChecked = _settings.SiegeBalance;
        PowersShardsToggle.IsChecked = _settings.DisablePowersAndShards;
        SelectOosMode(_settings.DesyncMode);
        SelectSpawnMode(_settings.RoamingSpawnMode);
        ApplyLanguage();
        SetActivePage("home");
        _updateTimer.Interval = TimeSpan.FromMinutes(1);
        _updateTimer.Tick += async (_, _) => await CheckFeedAsync(background: true);
        Closed += (_, _) => { _updateTimer.Stop(); CancelBackgroundFeed(); };
        Closed += (_, _) => CancelChangelogTransition();
        Closed += (_, _) => CancelAboutTransition();
        Closed += (_, _) => ResetChatMedia(dispose:true);
        Closing += (_, e) =>
        {
            if (ConfirmationActive) { e.Cancel = true; _ = CompleteConfirmationAsync(false); }
            else if (_busy) { e.Cancel = true; ShowToast(() => T("Дождитесь окончания операции или приостановите загрузку.", "Wait for the operation or pause the download.")); }
        };
        _initializing = false;
        Loaded += async (_, _) => await InitializeAsync();
        ContentRendered += (_, _) => MarkVisibleChangelogRead();
        Activated += (_, _) => MarkVisibleChangelogRead();
        StateChanged += (_, _) => MarkVisibleChangelogRead();
        // Off-screen preview/smoke fixtures never read or overwrite the user's desktop placement.
        if (!ActivityStore.IsSmokeTest || windowPlacementStore is not null)
            _windowPlacement = new WindowPlacementPersistence(this, windowPlacementStore ?? new WindowPlacementStore(ActivityStore.Root));
    }

    private async Task InitializeAsync()
    {
        if (ActivityStore.IsSmokeTest)
        {
            await Dispatcher.InvokeAsync(() => { }, DispatcherPriority.ApplicationIdle);
            SelfUpdater.AcknowledgeStartup();
            File.WriteAllText(Path.Combine(ActivityStore.Root, "window-ready.txt"), SelfUpdater.CurrentVersion.ToString(3));
            return;
        }
        try
        {
            await Dispatcher.InvokeAsync(() => { }, DispatcherPriority.ApplicationIdle);
            SelfUpdater.AcknowledgeStartup();
            LocateGame();
            await RecoverAndCheckRunsAsync();
        }
        catch (Exception ex) { ShowError(ex); return; }
        await CheckFeedAsync();
        if (await InstallPendingLauncherUpdateAsync(showErrors: false)) return;
        _updateTimer.Start();
        RefreshStatus();
        await LoadVersionChoicesAsync();
    }

    private void ApplyLanguage()
    {
        ApplyReliabilityLanguage();
        TitleText.Text = _text["app.title"];
        SubtitleText.Text = _text["app.subtitle"];
        HomeNav.Content = _text["nav.home"];
        ModulesNav.Content = _text["nav.modules"];
        SettingsNav.Content = _text["nav.settings"];
        AboutNav.Content = _text["nav.about"];
        RefreshAboutPage();
        MinimizeWindowButton.ToolTip = T("Свернуть", "Minimize");
        CloseWindowButton.ToolTip = T("Закрыть", "Close");
        System.Windows.Automation.AutomationProperties.SetName(MinimizeWindowButton, (string)MinimizeWindowButton.ToolTip);
        System.Windows.Automation.AutomationProperties.SetName(CloseWindowButton, (string)CloseWindowButton.ToolTip);
        ApplyPatchChannelLanguage();
        HomeWelcomeTitleText.Text = _text["home.welcome.title"];
        HomeWelcomeBodyText.Text = _text["home.welcome.body"];
        SettingsTitleText.Text = _text["settings.title"];
        SettingsLanguageTitleText.Text = _text["settings.language"];
        SettingsLanguageDescriptionText.Text = _text["settings.language.desc"];
        SettingsLanguageButton.Content = _text.Language == "ru" ? "English" : "Русский";
        SettingsRepairTitleText.Text = _text["settings.repair"];
        SettingsRepairDescriptionText.Text = _text["settings.repair.desc"];
        SettingsRepairButton.Content = _text["button.repair"];
        SettingsUpdatesDescriptionText.Text = _text["settings.updates.desc"];
        ApplyRemovalLanguage();
        CheckUpdatesButton.Content = _text["button.checknow"];
        var version = Assembly.GetExecutingAssembly().GetName().Version ?? new Version(0, 0, 0);
        LauncherVersionLabel.Text = T("ЛАУНЧЕР", "LAUNCHER");
        InstalledPatchLabel.Text = T("УСТАНОВЛЕННЫЙ ПАТЧ", "INSTALLED PATCH");
        LauncherVersionText.Text = $"{version.Major}.{version.Minor}.{version.Build}";
        GamePathLabel.Text = _text["game.path"];
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
        OosDescriptionText.Text = T("Продолжает матч при обнаружении рассинхрона, не устраняя его причину", "Continues the match on desync without fixing its cause");
        ApplySettingsButton.Content = T("Применить настройки", "Apply settings");
        IndependentTitleText.Text = _text["modules.independent"];
        IndependentDescriptionText.Text = _text["modules.independent.desc"];
        RoamingSpawnTitleText.Text = _text["modules.spawn"];
        StandardSpawnRadio.Content = _text["modules.spawn.standard"];
        X2SpawnRadio.Content = "×2";
        X4SpawnRadio.Content = _text["modules.spawn.x4"];
        AdditionalRoamingTitleText.Text = _text["modules.roaming"];
        AdditionalRoamingDescriptionText.Text = _text["modules.roaming.desc"];
        SiegeBalanceTitleText.Text = _text["modules.siege"];
        SiegeBalanceDescriptionText.Text = _text["modules.siege.desc"];
        PowersShardsTitleText.Text = _text["modules.powers"];
        System.Windows.Automation.AutomationProperties.SetName(PowersShardsToggle, _text["modules.powers"]);
        RefreshPowersShardsOption();
        MultiplayerNoteText.Text = _text["modules.multiplayer.note"];
        ConfigurationTitleText.Text = _text["configuration.title"];
        ConfigurationDescriptionText.Text = _text["configuration.desc"];
        CopyConfigurationButton.Content = _text["button.copyconfig"];
        DiagnosticsTitleText.Text = _text["diagnostics.title"];
        DiagnosticsDescriptionText.Text = _text["diagnostics.desc"];
        DiagnosticsButton.Content = _text["button.diagnostics"];
        RenderDiagnosticsArchive();
        HelpCloseButton.Content = _text["help.close"];
        PatchChangelogButton.Content = _text["news.tab.patch"];
        LauncherChangelogButton.Content = _text["news.tab.launcher"];
        RefreshNews();
        UpdateButton.Content = _text["button.install"];
        LaunchButton.Content = _text["button.launch"];
        BrowseButton.Content = _text["button.browse"];
        LanguageButton.Content = _text.Language == "ru" ? "EN" : "RU";
        // Friend profiles reuse the component labels; refresh only after those labels are localized.
        ApplyAccountLanguage();
        ApplyHelpTooltips(this);
        RefreshConfigurationCode();
        RefreshModuleAvailability();
        RefreshStatus();
        RefreshToast();
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

    private async Task<bool> CheckFeedAsync(bool background = false)
    {
        if (!background) CancelBackgroundFeed();
        if (_checkingFeed || _busy || ConfirmationActive) return false;
        var requestedChannel = _settings.Channel;
        var requestedRelease = _settings.PinnedRelease;
        _checkingFeed = true;
        _backgroundFeedCheck = background;
        var version = ++_feedCheckVersion;
        if (!background) SetBusy(true, _text["progress.checking"]);
        var revision = _operationRevision;
        bool IsCurrent() => requestedChannel == _settings.Channel && requestedRelease == _settings.PinnedRelease
            && version == _feedCheckVersion && revision == _operationRevision && (!background || !_busy && !ConfirmationActive);
        using var cancellation = new CancellationTokenSource(_feedTimeout);
        _feedCancellation = cancellation;
        var launcherCheck = CheckLauncherUpdateAsync(cancellation.Token, IsCurrent);
        try
        {
            var latest = await _feedClient.GetChannelAsync(requestedChannel, cancellation.Token);
            if (!IsCurrent()) return false;
            if (latest is null) throw new InvalidOperationException(_text["status.feedmissing"]);
            var selected = requestedRelease is null ? latest : _feedClient.LoadArchived(requestedRelease, requestedChannel);
            _latestChannel = latest;
            _channel = selected;
            _feedFailure = null;
            if (_errorFromFeed) ClearFriendlyError();
            _lastChecked = DateTimeOffset.Now;
            RefreshNews();
            RefreshModuleAvailability();
            RefreshStatus();
            if (!background && _game is not null && _channel is not null && !IsGameRunning())
            {
                var installer = new ModuleInstaller(_game.Directory);
                var state = installer.LoadState();
                if (state.AppliedSettings is null && state.Modules.ContainsKey("pawpatch-core") && !UpdateDetector.HasModuleChanges(state, ResolveSelectedPackages(_channel)))
                        await installer.RememberLegacyConfigurationAsync(GetEffectiveSettings(), ChannelFingerprint.Create(_channel));
            }
            if (!IsCurrent()) return false;
            if (!background)
                ShowResult(() => _pendingLauncherUpdate is not null || _patchUpdateAvailable || !_patchInstalled || _game is null || _settingsPending || _installationFailure is not null || _fileCheckFailed || _launcherCheckFailed
                    ? IdleStatus()
                    : T("Проверка завершена. Обновлений нет.", "Check complete. No updates available."));
            return true;
        }
        catch (OperationCanceledException) when (!IsCurrent()) { return false; }
        catch (Exception ex)
        {
            ActivityStore.Log(ex);
            if (!IsCurrent()) return false;
            _silentFeedFailure = background;
            SetFriendlyError(ex, fromFeed: true);
            var friendly = _presentedError!;
            _feedFailure = () => friendly.Title(_text.Language);
            if (!background) _feedback.Clear();
            return false;
        }
        finally
        {
            // Also complete the independent check when the patch feed is broken
            // or a pinned patch cannot be loaded. Startup self-update still runs.
            await launcherCheck;
            if (version == _feedCheckVersion)
            {
                _feedCancellation = null;
                _checkingFeed = false;
                _backgroundFeedCheck = false;
                if (!background)
                {
                    SetBusy(false);
                    ApplyLanguage();
                }
                else RefreshStatus();
            }
        }
    }

    private void CancelBackgroundFeed()
    {
        if (!_checkingFeed || !_backgroundFeedCheck) return;
        ++_feedCheckVersion;
        _checkingFeed = false;
        _backgroundFeedCheck = false;
        var cancellation = _feedCancellation;
        _feedCancellation = null;
        cancellation?.Cancel();
    }

    private async Task CheckLauncherUpdateAsync(CancellationToken cancellationToken, Func<bool> isCurrent)
    {
        try
        {
            var release = await _feedClient.GetLauncherUpdateAsync(cancellationToken);
            if (!isCurrent()) return;
            _launcherUpdates.Observe(release);
            _launcherCheckFailed = false;
        }
        catch (Exception error)
        {
            if (!isCurrent()) return;
            _launcherCheckFailed = true;
            ActivityStore.Log(error);
        }
        RefreshStatus();
    }

    private void RefreshStatus()
    {
        InstallState? state = null;
        _installationFailure = null;
        _settingsPending = false;
        try { state = _game is null ? null : new ModuleInstaller(_game.Directory).LoadState(); }
        catch (Exception ex) { _installationFailure = ex.Message; _incident = T("Не удалось прочитать состояние установки: ", "Cannot read the installation state: ") + ex.Message; }
        RefreshAvailableUpdates(state);
        if (_patchInstalled && _channel is not null && state is not null && _installationFailure is null)
            try { _settingsPending = UpdateDetector.HasSettingsChanges(state, ResolveSelectedPackages(_channel), GetEffectiveSettings()); }
            catch (FrequencyUnavailableException) { _settingsPending = true; }
            catch (Exception ex) { _installationFailure = ex.Message; }
        GamePathText.Text = _game?.Directory ?? "-";
        GameVersionText.Text = _game is null ? "-" : $"{(_game.Branch == "beta" ? "Beta" : "Steam")} · build {_game.SteamBuild ?? "?"}";
        var core = state?.Modules.GetValueOrDefault("pawpatch-core");
        PatchVersionText.Text = core?.Enabled == true ? core.Version : "-";
        InstalledPatchText.Text = core?.Enabled == true ? core.Version + " · " +
            (state?.AppliedSettings?.Channel == "beta" ? T("Бета", "Beta") : T("Релиз", "Release")) : T("Не установлен", "Not installed");
        PatchDownloadedText.Text = core?.Enabled == true ? core.DownloadedAt is DateTimeOffset downloaded
            ? T("Скачана: ", "Downloaded: ") + downloaded.ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
            : T("Дата загрузки неизвестна", "Download date unavailable") : "";
        ReadyStatusText.Text = FrequencyUnavailable ? T("Режим ×2 недоступен", "×2 unavailable in this release")
            : _installationFailure is not null || _fileCheckFailed
            ? T("Нужна проверка файлов", "File check required")
            : _feedFailure is not null
            ? T("Обновления не проверены", "Updates not checked")
            : _game is null
            ? _text["status.notfound"]
            : !_patchInstalled
                ? _text["status.notinstalled"]
            : _patchUpdateAvailable
                ? string.Format(_text["update.patch.title"], CurrentChannelName())
                : _settingsPending ? T("Настройки не применены", "Settings not applied")
                : _channel is null || _lastChecked is null ? T("Обновления не проверены", "Updates not checked")
                : string.Format(_text["patch.ready"], CurrentChannelName());
        var statusKind = _game is null || _installationFailure is not null || _fileCheckFailed ? "danger" : !_patchInstalled || _patchUpdateAvailable || _settingsPending || _feedFailure is not null || _channel is null || _lastChecked is null ? "update" : "ready";
        ReadyStatusText.Foreground = (Brush)FindResource(statusKind == "danger" ? "DangerBrush" : statusKind == "update" ? "GoldBrightBrush" : "SuccessBrush");
        ReadyStatusBadge.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(statusKind == "danger" ? "#3B2226" : statusKind == "update" ? "#40351E" : "#193926"));
        ReadyStatusBadge.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(statusKind == "danger" ? "#844B50" : statusKind == "update" ? "#A9873E" : "#3F8D64"));
        UpdateButton.IsEnabled = !_busy && !FeedBlocksActions && _game is not null && _channel is not null && _patchUpdateAvailable;
        SettingsRepairButton.IsEnabled = !_busy && _game is not null && state?.Modules.Count > 0;
        RemovePatchButton.IsEnabled = !_busy && !FeedBlocksActions && _game is not null && state?.Modules.Count > 0;
        RemoveLauncherButton.IsEnabled = !_busy && !FeedBlocksActions;
        RefreshGameFolderButton();
        RefreshGameLaunchState();
        ApplySettingsButton.IsEnabled = !_busy && !FeedBlocksActions && !FrequencyUnavailable && _game is not null && _channel is not null && (_settingsPending || !_patchInstalled);
        ApplySettingsButton.ToolTip = FrequencyUnavailable ? FrequencyUnavailableText : _settingsPending || !_patchInstalled
            ? T("Применить выбранные компоненты без запуска игры.", "Apply selected components without starting the game.")
            : T("Выбранные настройки уже применены.", "Selected settings are already applied.");
        RefreshApplySettingsVisibility();
        ColorsToggle.IsEnabled = !_busy && _colorsAvailable;
        IndependentHostilityToggle.IsEnabled = !_busy && CanChangeHostilityWithSelectedColors;
        StandardSpawnRadio.IsEnabled = !_busy;
        X2SpawnRadio.IsEnabled = !_busy && SupportsX2(_channel);
        X2SpawnRadio.ToolTip = SupportsX2(_channel) ? null : T("Для ×2 нужен выпуск патча с пакетами этой частоты.", "×2 requires a patch release containing this frequency.");
        X4SpawnRadio.IsEnabled = !_busy;
        AdditionalRoamingToggle.IsEnabled = !_busy;
        SiegeBalanceToggle.IsEnabled = !_busy;
        RefreshPowersShardsOption();
        CopyConfigurationButton.IsEnabled = !_busy;
        DiagnosticsButton.IsEnabled = !_busy;
        RenderDiagnosticsArchive();
        SyncPatchChannelControls();
        CheckUpdatesButton.IsEnabled = !_busy && !FeedBlocksActions;
        LastCheckedText.Text = _lastChecked is null ? "" : string.Format(_text["updates.checked"], _lastChecked.Value.ToString("HH:mm:ss"));
        RefreshConfigurationCode();
        RefreshReliabilityStatus();
        RefreshOperationStatus();
    }

    private void RefreshAvailableUpdates(InstallState? state)
    {
        var launcher = _launcherUpdates.Latest;
        _pendingLauncherUpdate = launcher is not null && SelfUpdater.IsNewer(launcher.Version) && launcher.Urls.Count > 0 && !SelfUpdater.IsBlocked(launcher.Sha256)
            ? launcher
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
            try { _patchUpdateAvailable = !_patchInstalled || UpdateDetector.HasRemoteUpdate(state, ResolveSelectedPackages(_channel), _feedClient.IsPackageCached); }
            catch (FrequencyUnavailableException) { }
            catch (Exception ex) { _installationFailure = ex.Message; }
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
        return UpdateDetector.NeedsDownload(state, ResolveSelectedPackages(channel), _feedClient.IsPackageCached);
    }

    private string CurrentChannelName()
        => ChannelPresentation.Name(_settings.Channel, _text.Language);

    private void RefreshNews()
    {
        if (NewsEntriesPanel is null) return;
        NewsTitleText.Text = _text["news.title"];

        RefreshChangelogTabState();
        var entries = ((_latestChannel ?? _channel)?.Changelog ?? [])
            .Where(entry => string.Equals(entry.Category, _changelogCategory, StringComparison.OrdinalIgnoreCase))
            .ToList();
        if (entries.Count == 0 && _channel is not null
            && _changelogCategory == "patch"
            && (!string.IsNullOrWhiteSpace(_channel.NewsTitle.Get(_text.Language))
                || !string.IsNullOrWhiteSpace(_channel.NewsBody.Get(_text.Language))))
        {
            entries =
            [
                new ChangelogEntry
                {
                    PublishedAt = _channel.PublishedAt,
                    Title = _channel.NewsTitle,
                    Body = _channel.NewsBody
                }
            ];
        }

        var identity = System.Text.Json.JsonSerializer.Serialize(new { _text.Language, Category = _changelogCategory, Entries = entries });
        if (identity == _renderedNewsIdentity) { MarkVisibleChangelogRead(); return; }
        _renderedNewsIdentity = identity;
        CancelChangelogTransition();
        NewsEntriesPanel.Children.Clear();
        if (entries.Count == 0)
        {
            NewsEntriesPanel.Children.Add(new TextBlock
            {
                Text = _text["news.empty"],
                Style = (Style)FindResource("CardDescription")
            });
            return;
        }

        for (var index = 0; index < entries.Count; index++)
        {
            var entry = entries[index];
            var item = new StackPanel();
            var title = ChannelPresentation.ChangelogText(entry.Title.Get(_text.Language), _text.Language);
            if (!string.IsNullOrWhiteSpace(title))
            {
                item.Children.Add(new TextBlock
                {
                    Text = title,
                    FontFamily = new FontFamily("Arial"),
                    Style = (Style)FindResource("CardSubtitle"),
                    Margin = new Thickness(0)
                });
            }

            var metadata = FormatChangelogMetadata(entry);
            if (!string.IsNullOrWhiteSpace(metadata))
            {
                item.Children.Add(new TextBlock
                {
                    Text = metadata,
                    Style = (Style)FindResource("SmallMetadataText"),
                    Margin = new Thickness(0, 4, 0, 0)
                });
            }

            item.Children.Add(new TextBlock
            {
                Text = ChannelPresentation.ChangelogText(entry.Body.Get(_text.Language), _text.Language),
                Style = (Style)FindResource("CardDescription"),
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#CDD5E1")),
                Margin = new Thickness(0, 7, 0, 0)
            });
            NewsEntriesPanel.Children.Add(item);

            if (index < entries.Count - 1)
            {
                NewsEntriesPanel.Children.Add(new Separator
                {
                    Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#40536E")),
                    Margin = new Thickness(0, 14, 0, 14)
                });
            }
        }
        MarkVisibleChangelogRead();
    }

    private string FormatChangelogMetadata(ChangelogEntry entry)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(entry.Version)) parts.Add(entry.Version);
        if (DateTimeOffset.TryParse(entry.PublishedAt, out var published))
            parts.Add(_text.Language == "ru" ? published.ToString("dd.MM.yyyy") : published.ToString("yyyy-MM-dd"));
        return string.Join(" · ", parts);
    }

    private async void ChangelogTab_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string category }) return;
        await SwitchChangelogAsync(category);
    }

    private void RefreshChangelogTabState()
    {
        SetChangelogTabState(PatchChangelogButton, _changelogCategory == "patch");
        SetChangelogTabState(LauncherChangelogButton, _changelogCategory == "launcher");
        RefreshUnreadBadges();
    }

    private static void SetChangelogTabState(Button button, bool active)
    {
        button.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(active ? "#5B451D" : "#1B304D"));
        button.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(active ? "#D6AA45" : "#526984"));
        button.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString(active ? "#FFF4CF" : "#E8EDF5"));
    }

    private async void UpdateButton_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _channel is null || _busy) return;
        try
        {
            SetBusy(true, _text["progress.downloading"]);
            await ApplySelectedConfigurationAsync(_channel, prepareWholeChannel: true);
            ShowResult(() => T("Установка завершена.", "Installation complete."));
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); RefreshStatus(); }
    }

    private async Task ApplySelectedConfigurationAsync(ChannelManifest channel, bool prepareWholeChannel = false)
        => await ApplyConfigurationSnapshotAsync(channel, prepareWholeChannel, _settings);

    private async Task ApplyConfigurationSnapshotAsync(ChannelManifest channel, bool prepareWholeChannel, UserSettings selection, Func<Task>? beforeCommit = null)
    {
        if (_game is null) throw new InvalidOperationException(_text["status.notfound"]);
        EnsureGameClosed();
        if (selection.RoamingSpawnMode == "x2" && !SupportsX2(channel))
            throw new FrequencyUnavailableException(FrequencyUnavailableText);
        await EnsureSupportedGameAsync(channel);

        var activeSettings = EffectiveSettings.ForFeed(selection, channel);
        var selected = GamePackageSelector.Select(channel, activeSettings, activeSettings.RussianLocalization, activeSettings.CustomPlayerColors);
        Dictionary<string, string>? downloaded = null;
        if (prepareWholeChannel)
        {
            TransferText.Text = T("Всего к загрузке: ", "Total download: ") + FormatBytes(channel.Packages.Where(p => !_feedClient.IsPackageCached(p)).Sum(p => p.Size));
            TransferText.Visibility = Visibility.Visible;
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
        ShowWorking(() => _text["progress.installing"]);
        if (beforeCommit is not null) await beforeCommit();
        EnsureGameClosed();
        await installer.ReconcileAsync(modules, settings: activeSettings, releaseId: ChannelFingerprint.Create(channel));
        InvalidateReadiness();
        _fileCheckFailed = false;
        if (prepareWholeChannel)
        {
            selection.PreparedChannel = channel.Channel;
            selection.PreparedFeedFingerprint = ChannelFingerprint.Create(channel);
            if (ReferenceEquals(selection, _settings)) _settingsStore.Save(_settings);
        }
        OperationProgress.IsIndeterminate = false;
        OperationProgress.Value = 100;
    }

    private async Task<string> DownloadPackageAsync(PackageRelease package)
    {
        using var cancellation = new CancellationTokenSource();
        _downloadCancellation = cancellation;
        CancelDownloadButton.Visibility = Visibility.Visible;
        var progress = TransferProgress(ChannelPresentation.PlainPunctuation(package.Name.Get(_text.Language)));
        try { return await _feedClient.DownloadVerifiedAsync(package, progress, cancellation.Token); }
        finally
        {
            FinishTransfer();
            _downloadCancellation = null;
            CancelDownloadButton.Visibility = Visibility.Collapsed;
        }
    }

    private UserSettings GetEffectiveSettings() => EffectiveSettings.ForFeed(_settings, _channel);
    private string EffectiveConfigurationCode => ConfigurationCode.Create(GetEffectiveSettings());

    private List<PackageRelease> ResolveSelectedPackages(ChannelManifest channel)
    {
        EnsureFrequencyAvailable(channel);
        var active = EffectiveSettings.ForFeed(_settings, channel);
        return GamePackageSelector.Select(channel, active, active.RussianLocalization, active.CustomPlayerColors);
    }

    private async void RepairButton_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _busy) return;
        try
        {
            SetBusy(true, _text["button.repair"] + "…");
            var errors = await new ModuleInstaller(_game.Directory).VerifyAsync();
            _fileCheckFailed = errors.Count > 0;
            ShowResult(() => errors.Count == 0 ? T("Проверка файлов завершена. Ошибок нет.", "File check complete. No errors found.") : string.Join(Environment.NewLine, errors.Take(5)), failure: errors.Count > 0);
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); }
    }

    private async void LaunchButton_Click(object sender, RoutedEventArgs e) => await LaunchGameAsync();

    private async Task LaunchGameAsync()
    {
        if (_game is null || _busy || _launchStarting) return;
        _launchStarting=true;
        try
        {
            EnsureGameClosed();
            if (_channel is null && !await CheckFeedAsync()) return;
            var channel = _channel ?? throw new InvalidOperationException(_text["status.feedmissing"]);
            if(!await CheckGameCompatibilityAsync(true))return;
            var installer = new ModuleInstaller(_game.Directory);
            var state = installer.LoadState();
            var executable = ResolveLaunchExecutable(_game.Directory);
            var prepareWholeChannel = NeedsChannelPreparation(channel, state);
            var needsApply = UpdateDetector.HasSettingsChanges(state, ResolveSelectedPackages(channel), GetEffectiveSettings()) || !File.Exists(executable);
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

            SetBusy(true, T("Проверяю критические файлы…", "Checking critical files…"));
            var critical = await MultiplayerCheck.CriticalAsync(_game.Directory, installer.LoadState(), executable, channel.Game);
            _fileCheckFailed = critical.Count > 0;
            if (_fileCheckFailed) throw new IOException(T("Запуск остановлен: ", "Launch stopped: ") + string.Join("; ", critical.Take(5)));
            EnsureGameClosed();
            var process = Process.Start(new ProcessStartInfo(executable) { WorkingDirectory = _game.Directory, UseShellExecute = true })
                ?? throw new IOException("Cannot start Kohan II.");
            BeginGameObservation(process, installer.LoadState());
            ShowResult(() => T("Игра запущена.", "Game launched."));
        }
        catch (Exception ex) { ShowError(ex); }
        finally { _launchStarting=false; SetBusy(false); RefreshStatus(); }
    }

    private Func<bool> _gameRunningProbe = DetectGameRunning;
    private bool IsGameRunning() => _gameRunningProbe();

    private static bool DetectGameRunning()
    {
        var processNames = new[]
        {
            "k2",
            "k2_paws_family_herd_relations_1372",
            "k2_paws_sync_family_herd_relations_1372",
            "k2_paws_sync_continue_1372",
            "k2_paws_ui_1372",
            "k2_paws_lobby_colors_mp_1372_experimental",
            "k2_paws_lobby_colors_mp_sync_1372",
            "k2_paws_lobby_colors_mp_nohostility_1372",
            "k2_paws_lobby_colors_mp_nohostility_sync_1372"
        };
        foreach (var name in processNames)
        {
            var processes = Process.GetProcessesByName(name);
            try { if (processes.Length > 0) return true; }
            finally { foreach (var process in processes) process.Dispose(); }
        }
        return false;
    }

    private string ResolveLaunchExecutable(string root)
    {
        var name = GameExecutableSelector.Select(
            _configuration,
            GetEffectiveSettings().CustomPlayerColors,
            _settings.DesyncMode.Equals("continue", StringComparison.OrdinalIgnoreCase),
            _settings.IndependentHostility,
            GameExecutableSelector.HasCommonUi(_channel),
            GameExecutableSelector.SupportsIndependentColors(_channel));
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
        await InstallPendingLauncherUpdateAsync(showErrors: true);
    }

    private async Task<bool> InstallPendingLauncherUpdateAsync(bool showErrors)
    {
        var release = _pendingLauncherUpdate;
        if (release is null || _busy || ConfirmationActive) return false;
        try
        {
            SetBusy(true, _text.Language == "ru" ? $"Обновляю лаунчер до {release.Version}…" : $"Updating launcher to {release.Version}…");
            var progress = TransferProgress("Paw's Patch Launcher " + release.Version);
            var executable = await _feedClient.DownloadLauncherAsync(release, progress);
            FinishTransfer();
            SelfUpdater.ScheduleReplacement(executable, release.Sha256);
            _busy = false;
            Application.Current.Shutdown();
            return true;
        }
        catch (Exception ex)
        {
            if (showErrors) ShowError(ex);
            else
            {
                ActivityStore.Log(ex); SetFriendlyError(ex);
                var friendly = _presentedError!;
                ShowResult(() => friendly.Title(_text.Language), failure: true);
            }
            SetBusy(false);
            return false;
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
        ResetFeedbackContext();
        _settingsStore.Save(_settings);
        RefreshStatus();
    }

    private void OptionChanged(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        var appearance = CaptureAppearance();
        _settings.RussianLocalization = RussianToggle.IsChecked == true;
        if (ReferenceEquals(sender, ColorsToggle) && _colorsAvailable)
            _settings.CustomPlayerColors = ColorsToggle.IsChecked == true;
        if (ColorsToggle.IsChecked == true && _settings.DesyncMode == "continue"
            && !GameExecutableSelector.SupportsColorDesyncContinue(_channel))
        {
            _settings.DesyncMode = "official";
            SelectOosMode("official");
            ShowResult(() => _text.Language == "ru"
                ? "Для цветов вместе с пропуском рассинхрона выберите последний выпуск. В этом старом выпуске сочетание недоступно."
                : "Select the latest release to combine colors with desync bypass. This older release does not support the combination.");
        }
        if (ColorsToggle.IsChecked == true && !GameExecutableSelector.SupportsIndependentColors(_channel))
        {
            _settings.IndependentHostility = true;
            IndependentHostilityToggle.IsChecked = true;
        }
        IgnoreDesyncToggle.IsEnabled = !_busy && CanContinueWithSelectedColors;
        _settingsStore.Save(_settings);
        RefreshConfigurationCode();
        RefreshStatus();
        HighlightAppearanceChanges(appearance);
    }

    private void GameplayOptionChanged(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        var appearance = CaptureAppearance();
        _settings.IndependentHostility = IndependentHostilityToggle.IsChecked == true;
        _settings.AdditionalRoamingCompanies = AdditionalRoamingToggle.IsChecked == true;
        _settings.SiegeBalance = SiegeBalanceToggle.IsChecked == true;
        _settings.DisablePowersAndShards = PowersShardsToggle.IsChecked == true;
        _settingsStore.Save(_settings);
        InvalidateReadiness();
        RefreshConfigurationCode();
        RefreshStatus();
        HighlightAppearanceChanges(appearance);
    }

    private void RefreshModuleAvailability()
    {
        RefreshAboutFeed();
        var wasInitializing = _initializing;
        _initializing = true;
        try
        {
        _colorsAvailable = _channel?.Packages.Any(x => x.Id.Equals("player-colors", StringComparison.OrdinalIgnoreCase)) == true;
        ColorsToggle.IsChecked = _colorsAvailable && _settings.CustomPlayerColors;
        if (ColorsToggle.IsChecked == true && _settings.DesyncMode == "continue"
            && !GameExecutableSelector.SupportsColorDesyncContinue(_channel))
        {
            _settings.DesyncMode = "official";
            SelectOosMode("official");
            _settingsStore.Save(_settings);
        }
        if (ColorsToggle.IsChecked == true && !GameExecutableSelector.SupportsIndependentColors(_channel))
        {
            _settings.IndependentHostility = true;
            IndependentHostilityToggle.IsChecked = true;
            _settingsStore.Save(_settings);
        }
        ColorsToggle.IsEnabled = !_busy && _colorsAvailable;
        PowersShardsToggle.IsChecked = _settings.DisablePowersAndShards;
        RefreshPowersShardsOption();
        IgnoreDesyncToggle.IsEnabled = !_busy && CanContinueWithSelectedColors;
        IndependentHostilityToggle.IsChecked = _settings.IndependentHostility;
        AdditionalRoamingToggle.IsChecked = _settings.AdditionalRoamingCompanies;
        SiegeBalanceToggle.IsChecked = _settings.SiegeBalance;
        IndependentHostilityToggle.IsEnabled = !_busy && CanChangeHostilityWithSelectedColors;
        ColorsDescriptionText.Text = _colorsAvailable ? _text["modules.colors.desc"] : _text.Language == "ru"
                ? "Недоступно в выбранном старом выпуске. Выберите последнюю версию патча."
                : "Unavailable in this older release. Select the latest patch version.";
        }
        finally { _initializing = wasInitializing; }
    }

    private bool PowersShardsAvailable => _channel?.Packages.Any(p => p.Id.Equals("powers-shards-original", StringComparison.OrdinalIgnoreCase)) == true;

    private void PowersShardsChanged(object sender, RoutedEventArgs e)
    {
        if (_initializing || _busy) return;
        if (!PowersShardsAvailable && PowersShardsToggle.IsChecked != true)
        {
            PowersShardsToggle.IsChecked = _settings.DisablePowersAndShards;
            ShowToast(() => _text["modules.powers.unavailable"], true);
            return;
        }
        GameplayOptionChanged(sender, e);
    }

    private void RefreshPowersShardsOption()
    {
        var available = PowersShardsAvailable;
        // Never silently change imported/restored settings when using an older feed.
        PowersShardsToggle.IsEnabled = !_busy && (available || !_settings.DisablePowersAndShards);
        PowersShardsDescriptionText.Text = _text[available ? "modules.powers.desc" : "modules.powers.unavailable"];
    }

    private async Task ChangeChannelAsync(bool beta)
    {
        if (_busy || FeedBlocksActions || ConfirmationActive || _initializing) { SyncPatchChannelControls(); return; }
        if (_settings.Channel.Equals(beta ? "beta" : "stable", StringComparison.OrdinalIgnoreCase)) { SyncPatchChannelControls(); return; }
        var appearance = CaptureAppearance();
        _settings.PinnedRelease = null;
        _latestChannel = null;
        _settings.Channel = beta ? "beta" : "stable";
        ResetFeedbackContext();
        SyncPatchChannelControls();
        _settingsStore.Save(_settings);
        _channel = null;
        RefreshModuleAvailability();
        ApplyLanguage();
        HighlightAppearanceChanges(appearance);
        await CheckFeedAsync();
        await LoadVersionChoicesAsync();
        RefreshStatus();
    }

    private async void CheckUpdatesButton_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || FeedBlocksActions) return;
        await CheckFeedAsync();
        await LoadVersionChoicesAsync();
        RefreshStatus();
    }

    private void OosToggle_Click(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        if (sender is CheckBox item)
        {
            var mode = item.IsChecked == true ? "continue" : "official";
            if (mode == "continue" && !CanContinueWithSelectedColors)
            {
                SelectOosMode("official");
                return;
            }
            var appearance = CaptureAppearance();
            _settings.DesyncMode = mode;
            _settingsStore.Save(_settings);
            RefreshConfigurationCode();
            RefreshStatus();
            HighlightAppearanceChanges(appearance);
        }
    }

    private void SelectOosMode(string mode)
    {
        IgnoreDesyncToggle.IsChecked = mode.Equals("continue", StringComparison.OrdinalIgnoreCase);
    }

    private bool CanContinueWithSelectedColors => ColorsToggle.IsChecked != true
        || GameExecutableSelector.SupportsColorDesyncContinue(_channel);

    private bool CanChangeHostilityWithSelectedColors => ColorsToggle.IsChecked != true
        || GameExecutableSelector.SupportsIndependentColors(_channel);

    private void SpawnMode_Checked(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        if (sender is RadioButton item && item.Tag is string mode)
        {
            var appearance = CaptureAppearance();
            if (mode == "x2" && !SupportsX2(_channel)) { SelectSpawnMode(_settings.RoamingSpawnMode); return; }
            _settings.RoamingSpawnMode = mode.ToLowerInvariant() is "x2" or "x4" ? mode.ToLowerInvariant() : "standard";
            _settingsStore.Save(_settings);
            RefreshConfigurationCode();
            RefreshStatus();
            HighlightAppearanceChanges(appearance);
        }
    }

    private void SelectSpawnMode(string mode)
    {
        StandardSpawnRadio.IsChecked = mode.Equals("standard", StringComparison.OrdinalIgnoreCase);
        X2SpawnRadio.IsChecked = mode.Equals("x2", StringComparison.OrdinalIgnoreCase);
        X4SpawnRadio.IsChecked = mode.Equals("x4", StringComparison.OrdinalIgnoreCase);
    }

    private void LanguageButton_Click(object sender, RoutedEventArgs e)
    {
        var appearance = CaptureAppearance();
        _settings.Language = _text.Language == "ru" ? "en" : "ru";
        _text.SetLanguage(_settings.Language);
        _settingsStore.Save(_settings);
        ApplyLanguage();
        HighlightAppearanceChanges(appearance);
    }

    private void RefreshConfigurationCode()
    {
        InvalidateReadinessIfChanged();
        var context = EffectiveConfigurationCode + "|" + _settings.GamePath + "|" + _settings.PinnedRelease;
        if (_feedbackContext is not null && context != _feedbackContext && !_feedback.Working)
            _feedback.Clear();
        _feedbackContext = context;
        if (ConfigurationCodeText is not null)
            ConfigurationCodeText.Text = EffectiveConfigurationCode;
    }

    private async void CopyConfigurationButton_Click(object sender, RoutedEventArgs e)
    {
        var code = EffectiveConfigurationCode;
        await CopyConfigurationButton.CopyAsync(()=>CopyTextAsync(code, () => _text["configuration.copied"]));
    }

    private async void DiagnosticsButton_Click(object sender, RoutedEventArgs e)
    {
        if (_busy) return;
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
            var archive = _game is null
                ? await DiagnosticsCollector.CreateLauncherOnlyAsync(dialog.FileName)
                : await CreateGameDiagnosticsAsync(dialog.FileName);
            var remembered = await RememberCreatedDiagnosticsAsync(archive);
            ShowResult(() => string.Format(_text["diagnostics.ready"], archive), duration: TimeSpan.FromSeconds(30));
            if (remembered) ShowToast(() => T("Архив диагностики готов.", "Diagnostic archive is ready."));
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); RefreshStatus(); }
    }

    private void HelpButton_Click(object sender, RoutedEventArgs e)
    {
        _socialDetailsPeer=null;
        if (sender is not Button { Tag: string key }) return;
        HelpTitleText.Text = _text[$"{key}.title"] == $"{key}.title" ? _text[key] : _text[$"{key}.title"];
        HelpBodyText.Text = _text[$"{key}.help"];
        RenderArcaneWarsCredit(key);
        HelpOverlay.Visibility = Visibility.Visible;
        HelpOverlay.UpdateLayout();
        Motion.Reveal(HelpOverlay);
    }

    private void HelpCloseButton_Click(object sender, RoutedEventArgs e) => Motion.Hide(HelpOverlay);

    private void ApplyHelpTooltips(DependencyObject parent)
    {
        for (var index = 0; index < VisualTreeHelper.GetChildrenCount(parent); index++)
        {
            var child = VisualTreeHelper.GetChild(parent, index);
            if (child is Button { Tag: string key } button
                && (key.StartsWith("modules.", StringComparison.Ordinal) || key is "configuration" or "diagnostics"))
                button.ToolTip = _text[$"{key}.help"] + (key == "modules.core"
                    ? "\n\n" + ArcaneWarsAuthorText + "\n" + ArcaneWarsDiscordInvite : "");
            ApplyHelpTooltips(child);
        }
    }

    private void SetBusy(bool busy, string? message = null)
    {
        if (busy) CancelBackgroundFeed();
        if (busy && !_busy) _operationRevision++;
        _busy = busy;
        RefreshOfferActions();
        if (!busy)
        {
            FinishTransfer();
            _feedback.Finish();
        }
        else
        {
            // Capture a localization key when possible, so switching RU/EN cannot leave old text.
            var key = Localization.KeyFor(message);
            ShowWorking(() => key is not null ? _text[key] : message ?? T("Выполняю операцию…", "Operation in progress…"));
            OperationProgress.Value = 0;
        }
        OperationProgress.IsIndeterminate = busy;
        RefreshStatus();
    }

    private void ShowError(Exception exception)
    {
        if (exception is GameAlreadyRunningException)
        {
            ShowResult(() => T("Kohan II уже запущен. Закройте игру перед применением настроек, обновлением или новым запуском.",
                "Kohan II is already running. Close the game before applying settings, updating or launching again."));
            ShowToast(() => T("Игра уже запущена. Сначала закройте Kohan II.", "The game is running. Close Kohan II first."));
            return;
        }
        if (exception is FrequencyUnavailableException)
        {
            ShowResult(() => exception.Message);
            ShowToast(() => exception.Message);
            return;
        }
        ActivityStore.Log(exception);
        if (exception is OperationCanceledException)
        {
            ShowResult(() => T("Загрузка приостановлена. При повторной установке она продолжится.", "Download paused. Install again to resume."), failure: true);
            return;
        }
        SetFriendlyError(exception);
        var friendly = _presentedError!;
        ShowResult(() => friendly.Title(_text.Language), failure: true);
        // Details remain available through the error action; ordinary failures use a toast.
    }

    private void MinimizeButton_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;
    private void CloseButton_Click(object sender, RoutedEventArgs e) => Close();
    private void HomeNav_Click(object sender, RoutedEventArgs e) => SetActivePage("home");
    private void ModulesNav_Click(object sender, RoutedEventArgs e) => SetActivePage("modules");
    private async void SettingsNav_Click(object sender, RoutedEventArgs e) { SetActivePage("settings"); await LoadVersionChoicesAsync(); }

    private void SetActivePage(string page)
    {
        if(page=="admin"&&_account.AdminLevel<1)page="home";
        AdminPanel.Visibility=page=="admin"?Visibility.Visible:Visibility.Collapsed;
        MainOptionsScroll.Visibility=page=="admin"?Visibility.Collapsed:Visibility.Visible;
        SetNavState(AdminNav,page=="admin");
        if (page == "multiplayer") page = "friends";
        CloseSocialMenu();
        var changed = _activePage != page;
        _activePage = page;
        var home = page == "home";
        var modules = page == "modules";
        RefreshActionLayout();
        var settings = page == "settings";
        AboutPatchPanel.Visibility = page == "about" ? Visibility.Visible : Visibility.Collapsed;
        FriendsPanel.Visibility = page == "friends" ? Visibility.Visible : Visibility.Collapsed;
        FriendsConversationScroll.Visibility = page == "friends" ? Visibility.Visible : Visibility.Collapsed;
        ChangelogCard.Visibility = home ? Visibility.Visible : Visibility.Collapsed;
        if (!home) CancelChangelogTransition();
        var split = home || page == "friends";
        Grid.SetColumnSpan(MainOptionsScroll, split ? 1 : 3);
        OptionsGapColumn.Width = new GridLength(split ? 20 : 0);
        OptionsColumn.Width = new GridLength(page == "friends" ? .8 : 1.6, GridUnitType.Star);
        NewsColumn.Width = split ? new GridLength(page == "friends" ? 1.5 : 1, GridUnitType.Star) : new GridLength(0);
        RefreshOperationPlacement();
        AccountPanel.Visibility = page == "account" ? Visibility.Visible : Visibility.Collapsed;
        if (page != "account") ClearAccountPasswords();
        if (page != "about") CancelAboutTransition();
        else if (changed) RefreshAboutPage();

        HomeWelcomeCard.Visibility = home ? Visibility.Visible : Visibility.Collapsed;
        UpdateNoticeBorder.Visibility = home && _patchUpdateAvailable ? Visibility.Visible : Visibility.Collapsed;
        GameInfoCard.Visibility = home || settings ? Visibility.Visible : Visibility.Collapsed;
        SettingsPanel.Visibility = settings ? Visibility.Visible : Visibility.Collapsed;
        PatchUpdatesCard.Visibility = RecoveryHost.Visibility = RemovalCard.Visibility = settings ? Visibility.Visible : Visibility.Collapsed;
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
        PowersShardsCard.Visibility = modules ? Visibility.Visible : Visibility.Collapsed;
        ConfigurationCodeCard.Visibility = ConfigurationImportHost.Visibility = settings ? Visibility.Visible : Visibility.Collapsed;
        DiagnosticsCard.Visibility = settings ? Visibility.Visible : Visibility.Collapsed;
        if (settings) _ = RefreshDiagnosticsArchiveAsync();
        RefreshReliabilityVisibility();

        SetNavState(HomeNav, home);
        SetNavState(ModulesNav, modules);
        SetNavState(SettingsNav, settings);
        SetNavState(AboutNav, page == "about");
        SetNavState(FriendsNav, page == "friends");
        AccountHeaderButton.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(page == "account" ? "#314969" : "#00000000"));
        AccountHeaderButton.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(page == "account" ? "#B68D37" : "#00000000"));
        MainOptionsScroll.ScrollToTop();
        if (page == "admin" && changed) AdminContentScroll.ScrollToTop();
        RenderSocialNotifications();
        if (changed && !_initializing)
        {
            Motion.Reveal(page == "admin" ? (FrameworkElement)AdminPanel : MainOptionsScroll);
            // Both Friends columns enter together after their first layout.
            Dispatcher.BeginInvoke(System.Windows.Threading.DispatcherPriority.Loaded, new Action(() =>
            {
                if (_activePage != page) return;
                if (page == "friends") Motion.Reveal(FriendsConversationScroll);
                else if (home) Motion.Reveal(ChangelogCard);
            }));
        }
    }

    private static void SetNavState(Button button, bool active)
    {
        var background = (Color)ColorConverter.ConvertFromString(active ? "#314969" : "#1B304D");
        var border = (Color)ColorConverter.ConvertFromString(active ? "#B68D37" : "#526984");
        if (button.Background is not SolidColorBrush current || current.Color != background) button.Background = new SolidColorBrush(background);
        if (button.BorderBrush is not SolidColorBrush edge || edge.Color != border) button.BorderBrush = new SolidColorBrush(border);
    }
}
