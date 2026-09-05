using Microsoft.Win32;
using System.Diagnostics;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

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

    public MainWindow()
    {
        InitializeComponent();
        _configuration = SettingsStore.LoadConfiguration();
        _feedClient = new FeedClient(_configuration);
        _settings = _settingsStore.Load();
        _text = new Localization(_settings.Language);
        RussianToggle.IsChecked = _settings.RussianLocalization;
        ColorsToggle.IsChecked = _settings.CustomPlayerColors;
        SelectOosMode(_settings.DesyncMode);
        ApplyLanguage();
        _initializing = false;
        Loaded += async (_, _) => await InitializeAsync();
    }

    private async Task InitializeAsync()
    {
        LocateGame();
        await CheckFeedAsync();
        RefreshStatus();
    }

    private void ApplyLanguage()
    {
        TitleText.Text = _text["app.title"];
        SubtitleText.Text = _text["app.subtitle"];
        HomeNav.Content = "⌂   " + _text["nav.home"];
        ModulesNav.Content = "◇   " + _text["nav.modules"];
        SettingsNav.Content = "⚙   " + _text["nav.settings"];
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
        NewsTitleText.Text = _channel?.NewsTitle.Get(_text.Language) is { Length: > 0 } title ? title : _text["news.title"];
        NewsBodyText.Text = _channel?.NewsBody.Get(_text.Language) is { Length: > 0 } body ? body : _text["news.empty"];
        UpdateButton.Content = _text["button.update"];
        RepairButton.Content = _text["button.repair"];
        LaunchButton.Content = _text["button.launch"];
        BrowseButton.Content = _text["button.browse"];
        LanguageButton.Content = _text.Language == "ru" ? "EN" : "RU";
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

    private async Task CheckFeedAsync()
    {
        if (_configuration.FeedUrls.Count == 0)
        {
            OperationText.Text = _text["status.feedmissing"];
            return;
        }

        try
        {
            SetBusy(true, _text["progress.checking"]);
            _channel = await _feedClient.GetChannelAsync();
            RefreshModuleAvailability();
            if (_channel is not null && await TrySelfUpdateAsync(_channel.Launcher)) return;
        }
        catch (Exception ex) { OperationText.Text = ex.GetBaseException().Message; }
        finally { SetBusy(false); ApplyLanguage(); }
    }

    private void RefreshStatus()
    {
        var state = _game is null ? null : new ModuleInstaller(_game.Directory).LoadState();
        GamePathText.Text = _game?.Directory ?? "—";
        GameVersionText.Text = _game is null ? "—" : $"{(_game.Branch == "beta" ? "Beta" : "Steam")} · build {_game.SteamBuild ?? "?"}";
        PatchVersionText.Text = state?.Modules.TryGetValue("pawpatch-core", out var core) == true ? core.Version : "—";
        ReadyStatusText.Text = _game is null ? _text["status.notfound"] : _text["status.ready"];
        ReadyStatusText.Foreground = _game is null ? (System.Windows.Media.Brush)FindResource("DangerBrush") : (System.Windows.Media.Brush)FindResource("SuccessBrush");
        ReadyStatusBadge.Background = new System.Windows.Media.SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString(_game is null ? "#3B2226" : "#193926"));
        ReadyStatusBadge.BorderBrush = new System.Windows.Media.SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString(_game is null ? "#844B50" : "#3F8D64"));
        UpdateButton.IsEnabled = !_busy && _game is not null && _channel is not null;
        RepairButton.IsEnabled = !_busy && _game is not null && state?.Modules.Count > 0;
        LaunchButton.IsEnabled = !_busy && _game is not null;
        ColorsToggle.IsEnabled = !_busy && _colorsAvailable;
    }

    private async void UpdateButton_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _channel is null || _busy) return;
        try
        {
            SetBusy(true, _text["progress.downloading"]);
            await EnsureSupportedGameAsync(_channel);
            if (Process.GetProcessesByName("k2").Any())
                throw new InvalidOperationException(_text.Language == "ru" ? "Перед обновлением полностью закройте Kohan II." : "Close Kohan II before updating.");
            var selected = ResolveSelectedPackages(_channel);
            var modules = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase);
            var installer = new ModuleInstaller(_game.Directory);
            foreach (var package in selected.OrderBy(x => x.Priority))
            {
                var progress = new Progress<(long Received, long? Total)>(value =>
                {
                    OperationText.Text = $"{_text["progress.downloading"]}: {package.Name.Get(_text.Language)}";
                    OperationProgress.IsIndeterminate = value.Total is null;
                    if (value.Total is > 0) OperationProgress.Value = value.Received * 100d / value.Total.Value;
                });
                var archive = await _feedClient.DownloadVerifiedAsync(package, progress);
                modules[package.Id] = await installer.PrepareAsync(package, archive);
            }
            OperationProgress.IsIndeterminate = true;
            OperationText.Text = _text["progress.installing"];
            await installer.ReconcileAsync(modules);
            OperationProgress.IsIndeterminate = false;
            OperationProgress.Value = 100;
            OperationText.Text = _text["status.ready"];
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); RefreshStatus(); }
    }

    private List<PackageRelease> ResolveSelectedPackages(ChannelManifest channel)
    {
        var ids = new HashSet<string>(channel.Packages.Where(x => x.Required).Select(x => x.Id), StringComparer.OrdinalIgnoreCase);
        if (RussianToggle.IsChecked == true) ids.Add("localization-ru");
        if (_colorsAvailable && ColorsToggle.IsChecked == true) ids.Add("player-colors");
        if (_settings.DesyncMode == "continue") ids.Add("desync-continue");

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

    private void LaunchButton_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null) return;
        var executable = ResolveLaunchExecutable(_game.Directory);
        if (!File.Exists(executable))
        {
            MessageBox.Show(_text.Language == "ru"
                    ? "Для выбранного набора функций пока нет установленного EXE. Нажмите «Установить / обновить»."
                    : "The executable for the selected feature set is not installed. Choose Install / update first.",
                _text["error.title"], MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        Process.Start(new ProcessStartInfo(executable) { WorkingDirectory = _game.Directory, UseShellExecute = true });
    }

    private string ResolveLaunchExecutable(string root)
    {
        var colors = _colorsAvailable && ColorsToggle.IsChecked == true;
        var bypass = _settings.DesyncMode == "continue";
        var name = (colors, bypass) switch
        {
            (true, true) => "k2_paws_sync_family_herd_relations_lobby_colors_mp_1372_experimental.exe",
            (true, false) => "k2_paws_family_herd_relations_lobby_colors_mp_1372_experimental.exe",
            (false, true) => "k2_paws_sync_family_herd_relations_1372.exe",
            _ => _configuration.PreferredGameExecutable
        };
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

    private async Task<bool> TrySelfUpdateAsync(LauncherRelease release)
    {
        if (!SelfUpdater.IsNewer(release.Version) || release.Urls.Count == 0 || string.IsNullOrWhiteSpace(release.Sha256)) return false;
        OperationText.Text = _text.Language == "ru" ? $"Обновляю лаунчер до {release.Version}…" : $"Updating launcher to {release.Version}…";
        var progress = new Progress<(long Received, long? Total)>(value =>
        {
            OperationProgress.IsIndeterminate = value.Total is null;
            if (value.Total is > 0) OperationProgress.Value = value.Received * 100d / value.Total.Value;
        });
        var executable = await _feedClient.DownloadLauncherAsync(release, progress);
        SelfUpdater.ScheduleReplacement(executable);
        Application.Current.Shutdown();
        return true;
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
        _settingsStore.Save(_settings);
    }

    private void RefreshModuleAvailability()
    {
        _colorsAvailable = _channel?.Packages.Any(x => x.Id.Equals("player-colors", StringComparison.OrdinalIgnoreCase)) == true;
        ColorsToggle.IsChecked = _colorsAvailable && _settings.CustomPlayerColors;
        ColorsToggle.IsEnabled = !_busy && _colorsAvailable;
        if (!_colorsAvailable)
        {
            ColorsDescriptionText.Text = _text.Language == "ru"
                ? "Готовится совместимая версия для сетевой игры"
                : "A multiplayer-compatible build is in preparation";
        }
    }

    private void OosMode_Checked(object sender, RoutedEventArgs e)
    {
        if (_initializing) return;
        if (sender is RadioButton item && item.Tag is string mode)
        {
            _settings.DesyncMode = mode;
            _settingsStore.Save(_settings);
        }
    }

    private void SelectOosMode(string mode)
    {
        OfficialOosRadio.IsChecked = !mode.Equals("continue", StringComparison.OrdinalIgnoreCase);
        ContinueOosRadio.IsChecked = mode.Equals("continue", StringComparison.OrdinalIgnoreCase);
    }

    private void LanguageButton_Click(object sender, RoutedEventArgs e)
    {
        _settings.Language = _text.Language == "ru" ? "en" : "ru";
        _text.SetLanguage(_settings.Language);
        _settingsStore.Save(_settings);
        ApplyLanguage();
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
    private void HomeNav_Click(object sender, RoutedEventArgs e) { }
    private void ModulesNav_Click(object sender, RoutedEventArgs e) { }
    private void SettingsNav_Click(object sender, RoutedEventArgs e) { }
}
