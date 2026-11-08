using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private Window? _onlineWindow;
    private CommunityOnlinePage? _onlinePage;
    private StackPanel? _onlineRows;
    private TextBlock? _onlineSummary, _onlineStatus, _onlinePageLabel;
    private Button? _onlinePrevious, _onlineNext, _onlineRefresh;
    private CancellationTokenSource? _onlineRequest;
    private Func<int, CancellationToken, Task<CommunityOnlinePage>>? _communityPlayersOverride = null;

    private async void CommunityOnline_Click(object sender, RoutedEventArgs e)
    {
        if (ConfirmationActive) return;
        if (_onlineWindow is { } existing) { existing.Activate(); return; }
        var (window, body) = CreateCommunityDialog(T("Игроки в сети", "Online players"), IconKind.Person, 460, 780);
        _onlineWindow = window; _onlinePage = null;
        var layout = new Grid();
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition());
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        _onlineSummary = new TextBlock { Foreground = SocialBrush("#A8BBD2"), Margin = new Thickness(0, 0, 0, 12), TextWrapping = TextWrapping.Wrap };
        layout.Children.Add(_onlineSummary);
        _onlineRows = new StackPanel();
        var scroll = new ScrollViewer { Content = _onlineRows, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled };
        Grid.SetRow(scroll, 1); layout.Children.Add(scroll);
        _onlineStatus = new TextBlock { TextWrapping = TextWrapping.Wrap, Foreground = SocialBrush("#A8BBD2"), Margin = new Thickness(0, 12, 0, 12), VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
        Grid.SetRow(_onlineStatus, 1); layout.Children.Add(_onlineStatus);
        var footer = new Grid();
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        footer.ColumnDefinitions.Add(new ColumnDefinition { MinWidth = 16 });
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var pager = new Grid();
        pager.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        pager.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        pager.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Button PageButton(string name, string hint, double angle)
        {
            var arrow = new LauncherIcon { Kind = IconKind.ChevronUp, Width = 16, Height = 16,
                LayoutTransform = new RotateTransform(angle) };
            var button = new Button { Name = name, Content = arrow, ToolTip = hint,
                Style = (Style)FindResource("GhostButton"), Width = 32, Height = 32, Padding = new Thickness(0),
                Background = Brushes.Transparent, BorderBrush = Brushes.Transparent };
            LauncherIcon.SetUseAccent(button, false);
            AutomationProperties.SetName(button, hint);
            return button;
        }
        _onlinePrevious = PageButton("OnlinePrevious", T("Предыдущая страница", "Previous page") + " (←)", -90);
        _onlineNext = PageButton("OnlineNext", T("Следующая страница", "Next page") + " (→)", 90);
        pager.Children.Add(_onlinePrevious); Grid.SetColumn(_onlineNext, 2); pager.Children.Add(_onlineNext);
        _onlinePageLabel = new TextBlock { Margin = new Thickness(2, 0, 2, 0), FontSize = 12,
            FontWeight = FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center, TextAlignment = TextAlignment.Center };
        Grid.SetColumn(_onlinePageLabel, 1); pager.Children.Add(_onlinePageLabel);
        footer.Children.Add(new Border { Child = pager, Background = SocialBrush("#11233A"), BorderBrush = SocialBrush("#354C69"),
            BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(8), Padding = new Thickness(4) });
        _onlineRefresh = new Button { Name = "OnlineRefresh", Content = T("Обновить", "Refresh"),
            Style = (Style)FindResource("GhostButton"), FontSize = 12, Height = 42, Padding = new Thickness(12, 8, 12, 8) };
        LauncherIcon.SetKind(_onlineRefresh, IconKind.Sync);
        Grid.SetColumn(_onlineRefresh, 2); footer.Children.Add(_onlineRefresh);
        var footerBorder = new Border { Child = footer, BorderBrush = SocialBrush("#263B54"), BorderThickness = new Thickness(0, 1, 0, 0),
            Margin = new Thickness(0, 12, 0, 0), Padding = new Thickness(0, 12, 0, 0) };
        Grid.SetRow(footerBorder, 2); layout.Children.Add(footerBorder); body.Content = layout;
        _onlinePrevious.Click += async (_, _) => { scroll.ScrollToTop(); await LoadCommunityPlayersAsync(Math.Max(0, (_onlinePage?.Page ?? 0) - 1)); };
        _onlineNext.Click += async (_, _) => { scroll.ScrollToTop(); await LoadCommunityPlayersAsync((_onlinePage?.Page ?? 0) + 1); };
        _onlineRefresh.Click += async (_, _) => await LoadCommunityPlayersAsync(_onlinePage?.Page ?? 0);
        window.PreviewKeyDown += (_, key) =>
        {
            if (Keyboard.Modifiers != ModifierKeys.None || key.Key is not (Key.Left or Key.Right)) return;
            key.Handled = true;
            if (key.IsRepeat || _onlineRequest is not null) return;
            var button = key.Key == Key.Left ? _onlinePrevious : _onlineNext;
            if (button is { IsEnabled: true }) button.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        };
        var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(15) };
        timer.Tick += async (_, _) => { if (_onlineRequest is null && window.IsVisible && window.WindowState != WindowState.Minimized) await LoadCommunityPlayersAsync(_onlinePage?.Page ?? 0); };
        window.Closed += (_, _) =>
        {
            timer.Stop(); _onlineRequest?.Cancel(); _onlineRequest = null;
            _onlineWindow = null; _onlinePage = null; _onlineRows = null;
        };
        Closed += CloseOnlineWithOwner;
        void CloseOnlineWithOwner(object? _, EventArgs __) { window.Close(); }
        window.Closed += (_, _) => Closed -= CloseOnlineWithOwner;
        window.Show(); timer.Start();
        await LoadCommunityPlayersAsync(0);
    }

    private async Task LoadCommunityPlayersAsync(int page)
    {
        if (_onlineWindow is not { } window) return;
        _onlineRequest?.Cancel();
        using var request = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);
        request.CancelAfter(TimeSpan.FromSeconds(15)); _onlineRequest = request;
        _onlinePrevious!.IsEnabled = _onlineNext!.IsEnabled = _onlineRefresh!.IsEnabled = false;
        _onlineStatus!.Text = T("Загрузка…", "Loading…");
        _onlineStatus.Visibility = _onlinePage is null ? Visibility.Visible : Visibility.Collapsed;
        try
        {
            var result = await (_communityPlayersOverride?.Invoke(page, request.Token) ?? _account.ReadCommunityPlayersAsync(page, request.Token));
            if (request.IsCancellationRequested || _onlineWindow != window) return;
            var changed = _onlinePage?.Page != result.Page || _onlinePage?.Total != result.Total || !_onlinePage.Players.SequenceEqual(result.Players);
            _onlinePage = result;
            _communityOnline = result.Total; _communityOnlineReceived = DateTimeOffset.UtcNow; RefreshCommunityOnline();
            _onlineSummary!.Text = UiLanguages.Format(_text.Language, $"В сети: {result.Total} · Гости не учитываются", $"Online: {result.Total} · Guests are not counted");
            _onlinePageLabel!.Text = UiLanguages.Format(_text.Language, $"{result.Page + 1} из {result.PageCount}", $"{result.Page + 1} of {result.PageCount}");
            if (changed)
            {
                _onlineRows!.Children.Clear();
                foreach (var player in result.Players)
                {
                    var content = new Grid();
                    content.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto }); content.ColumnDefinitions.Add(new ColumnDefinition()); content.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
                    var avatar = PublicPlayerAvatar(player.Id, player.AvatarRevision, 34); avatar.Margin = new Thickness(0, 0, 10, 0); content.Children.Add(avatar);
                    var names = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
                    names.Children.Add(new TextBlock { Text = player.DisplayName, FontWeight = FontWeights.SemiBold, TextTrimming = TextTrimming.CharacterEllipsis });
                    names.Children.Add(new TextBlock { Text = "@" + player.Nickname, FontSize = 11, Foreground = SocialBrush("#A8BBD2"), TextTrimming = TextTrimming.CharacterEllipsis });
                    Grid.SetColumn(names, 1); content.Children.Add(names);
                    var arrow = new TextBlock { Text = "›", Foreground = SocialBrush("#79C9A0"), FontSize = 22, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(8, 0, 0, 0) }; Grid.SetColumn(arrow, 2); content.Children.Add(arrow);
                    var card = new Button { Name = "OnlinePlayerCard", Tag = player.Id, Content = content, Style = (Style)FindResource("GhostButton"), HorizontalContentAlignment = HorizontalAlignment.Stretch, Padding = new Thickness(10, 7, 10, 7), Margin = new Thickness(0, 0, 0, 6), ToolTip = T("Открыть профиль", "Open profile") };
                    AutomationProperties.SetName(card, player.DisplayName + " @" + player.Nickname);
                    card.Click += async (_, _) => { window.Close(); await OpenPublicPlayerProfileAsync(player.Id, player.Nickname, player.DisplayName, player.AvatarRevision); };
                    _onlineRows.Children.Add(card);
                }
            }
            _onlineStatus.Text = result.Total == 0 ? T("Сейчас никого нет в сети.", "No players are online right now.") : "";
            _onlineStatus.Visibility = result.Total == 0 ? Visibility.Visible : Visibility.Collapsed;
            // Avatar reads update their existing views and must not delay paging.
            _ = Task.WhenAll(result.Players.Select(p => RefreshPublicAvatarAsync(p.Id, p.AvatarRevision)));
        }
        catch (Exception)
        {
            if (_onlineWindow != window || !ReferenceEquals(_onlineRequest, request)) return;
            _onlineRows!.Children.Clear(); _onlinePage = null; _onlinePageLabel!.Text = "";
            _onlineSummary!.Text = T("Игроки с активной сессией лаунчера", "Players with an active launcher session");
            _onlineStatus.Text = T("Не удалось загрузить список. Нажмите «Обновить».", "Could not load players. Click Refresh to try again.");
            _onlineStatus.Visibility = Visibility.Visible;
        }
        finally
        {
            if (_onlineWindow == window && ReferenceEquals(_onlineRequest, request))
            {
                _onlineRequest = null; _onlineRefresh!.IsEnabled = true;
                _onlinePrevious!.IsEnabled = _onlinePage?.Page > 0;
                _onlineNext!.IsEnabled = _onlinePage is { } current && current.Page + 1 < current.PageCount;
            }
        }
    }
}
