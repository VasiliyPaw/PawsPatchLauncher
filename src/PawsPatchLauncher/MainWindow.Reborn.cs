using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Threading;
using Microsoft.Win32;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private IReadOnlyList<RebornBuild> _rebornBuilds = [];
    private bool _rebornLoading, _rebornBusy, _rebornDenied;
    private string _rebornOwner = "", _rebornError = "";
    private int _rebornGeneration;
    private CancellationTokenSource? _rebornOperation;
    private readonly DispatcherTimer _rebornTimer = new() { Interval = TimeSpan.FromSeconds(45) };
    private Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>? _rebornCatalogOverride = null;
    private bool RebornAccess => (_account.PawsTeam || _account.AdminLevel > 0) && !_rebornDenied;
    private string RebornChannel => RebornBuild.IsChannel(_settings.RebornChannel) ? _settings.RebornChannel : "stable";

    private void InitializeReborn()
    {
        LauncherIcon.SetKind(RebornNav,IconKind.Reborn);
        _rebornTimer.Tick += async (_, _) => { if (_activePage == "reborn") await LoadRebornCatalogAsync(); if (_historyWindow?.IsVisible == true) await LoadRebornHistoryAsync(force:true); };
        if (!ActivityStore.IsSmokeTest) _rebornTimer.Start();
        Closed += (_, _) => { _rebornTimer.Stop(); _rebornOperation?.Cancel(); _rebornGeneration++; };
        RefreshRebornAccess();
    }
    private void RefreshRebornAccess()
    {
        if (RebornNav is null) return;
        if (_rebornOwner != _account.UserId)
        { _rebornOwner = _account.UserId; _rebornDenied = false; _rebornBuilds = []; _rebornGeneration++; _rebornOperation?.Cancel(); }
        if (!_account.PawsTeam && _account.AdminLevel < 1) { _rebornDenied = false; _rebornBuilds = []; _rebornGeneration++; _rebornOperation?.Cancel(); }
        RebornNav.Visibility = RebornAccess ? Visibility.Visible : Visibility.Collapsed;
        RebornNav.Content = "Kohan Reborn";
        RefreshActionLayout();
        if (!RebornAccess && _activePage == "reborn") SetActivePage("home");
        RefreshRebornHistoryAccess();
        if (RebornAccess && _activePage == "reborn" && !_rebornBusy) RenderReborn();
    }
    private void RebornNav_Click(object sender, RoutedEventArgs e) { if (RebornAccess) SetActivePage("reborn"); }
    private async Task LoadRebornCatalogAsync()
    {
        if (!RebornAccess || _rebornLoading || _rebornBusy) return;
        var owner = _account.UserId; var generation = _rebornGeneration;
        _rebornLoading = true; _rebornError = ""; RenderReborn();
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token); timeout.CancelAfter(TimeSpan.FromSeconds(12));
            var builds = await (ActivityStore.IsSmokeTest && _rebornCatalogOverride is not null ? _rebornCatalogOverride(timeout.Token) : _account.GetRebornBuildsAsync(timeout.Token));
            if (owner != _account.UserId || generation != _rebornGeneration || !RebornAccess) return;
            foreach (var build in builds) RebornBuild.Validate(build);
            if (builds.Count > 2 || builds.Select(b => b.Channel).Distinct().Count() != builds.Count) throw new InvalidDataException("Invalid Reborn catalog.");
            _rebornBuilds = builds;
        }
        catch (AccountException error) when (error.Code == "reborn_access_denied")
        { if (owner == _account.UserId) { _rebornDenied = true; _rebornBuilds = []; RefreshRebornAccess(); } }
        catch (Exception error) when (error is AccountException or IOException or InvalidDataException or OperationCanceledException or System.Net.Http.HttpRequestException)
        { if (owner == _account.UserId && generation == _rebornGeneration) _rebornError = "catalog"; }
        finally { _rebornLoading = false; RefreshRebornAccess(); if (_activePage == "reborn") RenderReborn(); }
    }
    private void RenderReborn()
    {
        if (RebornBody is null || _activePage != "reborn" || !RebornAccess) return;
        RebornBody.Children.Clear(); var selected = RebornChannel;
        var available = _rebornBuilds.FirstOrDefault(b => b.Channel == selected);
        var installed = RebornInstall.Installed(_settings.RebornPath,selected);
        TextBlock Text(string value, double size = 14, string color = "#B5C7DC") => new() { Text = value, FontSize = size, Foreground = SocialBrush(color), TextWrapping = TextWrapping.Wrap };
        Border Card(UIElement child) => new() { Style = (Style)FindResource("Card"), Margin = new Thickness(0,0,0,14), Child = child };
        Button Button(string text, IconKind icon, bool gold, Action action) {
            var button = new Button { Content = text, Style = (Style)FindResource(gold ? "GoldButton" : "GhostButton"), Margin = new Thickness(0,0,8,5), IsEnabled = !_rebornBusy };
            LauncherIcon.SetKind(button,icon); button.Click += (_,_) => action(); return button;
        }
        var hero = new StackPanel();
        var badge = Text("PAW’S TEAM  ·  "+T("ЗАКРЫТОЕ ТЕСТИРОВАНИЕ","CLOSED TESTING"),11,"#D7B45D"); badge.FontWeight = FontWeights.Bold; badge.Margin = new Thickness(0,0,0,12); hero.Children.Add(badge);
        var title = Text("Kohan Reborn",36,"#F2DEAA"); title.FontWeight = FontWeights.Bold; hero.Children.Add(title);
        var intro = Text(T("Знакомый Kohan на новом движке. Закрытые сборки для команды и администраторов.","Familiar Kohan on a new engine. Private builds for the team and administrators.")); intro.Margin = new Thickness(0,10,0,0); hero.Children.Add(intro);
        var heroCard = Card(hero); heroCard.Background = new LinearGradientBrush(SocialBrush("#20394F").Color,SocialBrush("#132236").Color,25); heroCard.BorderBrush = SocialBrush("#8B7444"); RebornBody.Children.Add(heroCard);

        var channels = new UniformGrid { Columns = 2, Margin = new Thickness(0,0,-8,14) };
        foreach (var channel in new[] { "stable", "beta" })
        {
            var name = channel == "stable" ? T("Релиз","Release") : T("Бета","Beta");
            var words = new StackPanel(); var label = Text(name,19,channel == selected ? "#F2D58D" : "#E5ECF5"); label.FontWeight = FontWeights.Bold; words.Children.Add(label);
            var caption = Text(channel == "stable" ? T("Основной канал","Main channel") : T("Тестовые сборки","Test builds"),12); caption.Margin = new Thickness(0,5,0,0); words.Children.Add(caption);
            var button = new Button { Name = channel == "stable" ? "RebornReleaseChoice" : "RebornBetaChoice", Content = words, Style = (Style)FindResource("GhostButton"),
                HorizontalContentAlignment = HorizontalAlignment.Left, Padding = new Thickness(18,14,18,14), Margin = new Thickness(0,0,8,0), IsEnabled = !_rebornBusy,
                Background = SocialBrush(channel == selected ? "#30465D" : "#14283E"), BorderBrush = SocialBrush(channel == selected ? "#D0AD5B" : "#344B63") };
            button.Click += (_,_) => { if (_rebornBusy) return; _settings.RebornChannel = channel; _settingsStore.Save(_settings); RenderReborn(); if (_historyWindow is not null) RefreshNews(); };
            channels.Children.Add(button);
        }
        RebornBody.Children.Add(channels);
        if (_rebornError.Length > 0)
        {
            var error = new StackPanel(); error.Children.Add(Text(_rebornError == "catalog" ? T("Каталог сборок пока недоступен. Проверьте подключение и повторите попытку.","The build catalog is unavailable. Check your connection and try again.")
                : T("Не удалось завершить операцию. Установленные сборки сохранены.","Could not complete the operation. Installed builds were kept."),13,"#E9BE96"));
            var retry = Button(T("Повторить","Retry"),IconKind.Sync,false,() => _ = LoadRebornCatalogAsync()); retry.Margin = new Thickness(0,10,0,0); error.Children.Add(retry); RebornBody.Children.Add(Card(error));
        }
        var buildPanel = new StackPanel();
        if (_rebornLoading && available is null) buildPanel.Children.Add(Text(T("Проверяем сборки…","Checking builds…"),20,"#F1D78F"));
        else if (available is null)
        {
            var icon = new LauncherIcon { Kind = IconKind.Download, Width = 34, Height = 34, Foreground = SocialBrush("#BDA064"), Margin = new Thickness(0,2,0,14), HorizontalAlignment = HorizontalAlignment.Left }; buildPanel.Children.Add(icon);
            var empty = Text(T("Сборка ещё не опубликована","No build published yet"),23,"#E9EEF7"); empty.FontWeight = FontWeights.SemiBold; buildPanel.Children.Add(empty);
            var hint = Text(selected == "stable" ? T("Здесь появится релизная сборка Kohan Reborn, когда она будет готова.","The Kohan Reborn release build will appear here when it is ready.")
                : T("Здесь появятся новые тестовые сборки Kohan Reborn.","New Kohan Reborn test builds will appear here.")); hint.Margin = new Thickness(0,9,0,18); buildPanel.Children.Add(hint);
        }
        else
        {
            var version = Text(available.Version,27,"#F0D18A"); version.FontWeight = FontWeights.Bold; buildPanel.Children.Add(version);
            var info = Text($"{available.PublishedAt.ToLocalTime():d}  ·  {available.Size / 1048576d:0.0} MB",12); info.Margin = new Thickness(0,7,0,16); buildPanel.Children.Add(info);
            var notes = Text(available.Note(_text.Language)); notes.Margin = new Thickness(0,0,0,18); buildPanel.Children.Add(notes);
        }
        var installedText = Text(T("Установлено: ","Installed: ")+(installed?.Version ?? "—"),12); installedText.Margin = new Thickness(0,0,0,14); buildPanel.Children.Add(installedText);
        RebornBody.Children.Add(Card(buildPanel));
        RenderRebornActions(available,installed);
    }
    private void RenderRebornActions(RebornBuild? available, RebornBuild? installed)
    {
        var update = installed is not null && available is not null && installed.Id != available.Id;
        RebornInstallButton.Content = installed is null ? T("Установить","Install") : update ? T("Обновить","Update") : T("Установлено","Installed");
        LauncherIcon.SetKind(RebornInstallButton,installed is not null && !update ? IconKind.Check : IconKind.Download);
        RebornInstallButton.IsEnabled = !_rebornBusy && !_rebornLoading && available is not null && (installed is null || update) && _rebornError != "catalog";
        RebornInstallButton.ToolTip = available is null && installed is null ? T("Скачивание станет доступно после публикации сборки.","Downloading will become available after a build is published.") : null;
        RebornCheckUpdatesButton.Content = T("Проверить обновления","Check for updates");
        LauncherIcon.SetKind(RebornCheckUpdatesButton,IconKind.Sync);
        RebornCheckUpdatesButton.IsEnabled = !_rebornBusy && !_rebornLoading;
        RebornLaunchButton.Content = T("Играть","Play");
        LauncherIcon.SetKind(RebornLaunchButton,IconKind.Play);
        RebornLaunchButton.IsEnabled = !_rebornBusy && !_rebornLoading && installed is not null && _rebornError != "catalog";
        RebornOperationPanel.Visibility = _rebornBusy ? Visibility.Visible : Visibility.Collapsed;
        RebornCancelButton.Content = T("Отменить","Cancel");
        LauncherIcon.SetKind(RebornCancelButton,IconKind.Close);
        if (_rebornBusy) { RebornProgressText.Text = T("Подготавливаем Reborn…","Preparing Reborn…"); RebornProgressBar.IsIndeterminate = true; }
        RefreshActionLayout();
    }
    private async void RebornInstall_Click(object sender, RoutedEventArgs e) => await RebornActionAsync();
    private async void RebornLaunch_Click(object sender, RoutedEventArgs e) => await RebornActionAsync(playInstalled:true);
    private async void RebornCheckUpdates_Click(object sender, RoutedEventArgs e) => await LoadRebornCatalogAsync();
    private void RebornCancel_Click(object sender, RoutedEventArgs e) => _rebornOperation?.Cancel();
    private bool ChooseRebornInstallFolder()
    {
        if (!RebornAccess || _rebornBusy) return false;
        var dialog = new OpenFolderDialog { Title = T("Папка Kohan Reborn","Kohan Reborn folder") };
        if (dialog.ShowDialog(this) != true || !RebornAccess) return false;
        _settings.RebornPath = dialog.FolderName;
        _settingsStore.Save(_settings);
        return true;
    }
    private async Task RebornActionAsync(bool playInstalled = false)
    {
        if (!RebornAccess || _rebornBusy || _rebornLoading) return;
        var channel = RebornChannel;
        var installed = RebornInstall.Installed(_settings.RebornPath,channel);
        var build = _rebornBuilds.FirstOrDefault(b => b.Channel == channel);
        if (playInstalled ? installed is null : build is null || installed?.Id == build.Id) return;
        // Pick one shared root only when the first actual installation begins.
        if (string.IsNullOrWhiteSpace(_settings.RebornPath) && !ChooseRebornInstallFolder()) return;
        if (!RebornAccess) return;
        var root = _settings.RebornPath!; var owner = _account.UserId;
        _rebornBusy = true; _rebornError = ""; _rebornOperation = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token); var ct = _rebornOperation.Token;
        string? archive = null; RenderReborn();
        void Guard() { ct.ThrowIfCancellationRequested(); if (!RebornAccess || owner != _account.UserId) throw new OperationCanceledException(); }
        try
        {
            if (installed is not null && (playInstalled || build is null || build.Id == installed.Id))
            {
                await _account.GetRebornBuildsAsync(ct); Guard();
                var executable = RebornInstall.Executable(root,installed);
                Process.Start(new ProcessStartInfo(executable) { WorkingDirectory = Path.GetDirectoryName(executable)!, UseShellExecute = false });
            }
            else
            {
                var ticket = await _account.GetRebornTicketAsync(build!,ct); Guard();
                archive = Path.Combine(ActivityStore.Root,"reborn-downloads",Guid.NewGuid().ToString("N")+".zip");
                var progress = new CoalescingProgress<(long Received,long Total)>(p =>
                {
                    if (!RebornAccess || owner != _account.UserId || ct.IsCancellationRequested) return;
                    RebornProgressBar.IsIndeterminate = false; RebornProgressBar.Value = 100d*p.Received/p.Total;
                    RebornProgressText.Text = $"{p.Received/1048576d:0.0} / {p.Total/1048576d:0.0} MB";
                });
                await RebornInstall.DownloadAsync(ticket,archive,progress,ct);
                progress.Complete(); Guard();
                RebornProgressText.Text = T("Устанавливаем Reborn…","Installing Reborn…");
                await RebornInstall.InstallAsync(root,build!,archive,async () => { await _account.GetRebornTicketAsync(build!,ct); Guard(); },ct);
            }
        }
        catch (OperationCanceledException) { }
        catch (AccountException error) when (error.Code == "reborn_access_denied") { _rebornDenied = true; RefreshRebornAccess(); }
        catch (Exception error) when (error is IOException or InvalidDataException or UnauthorizedAccessException or AccountException or System.Net.Http.HttpRequestException or System.ComponentModel.Win32Exception) { _rebornError = "operation"; }
        finally
        {
            try { if (archive is not null && File.Exists(archive)) { RemovalSafety.CheckNoLinks(archive); File.Delete(archive); } }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException) { }
            _rebornOperation.Dispose(); _rebornOperation = null; _rebornBusy = false; RefreshRebornAccess(); if (_activePage == "reborn") RenderReborn();
        }
    }
}
