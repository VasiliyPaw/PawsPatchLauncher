using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shell;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private string CommunityNotificationLabel(string mode) => mode == "mute" ? T("Без звука", "Muted")
        : mode == "all" ? T("Все сообщения", "All messages") : T("Только упоминания", "Mentions only");

    private void RefreshCommunityNotificationMode()
    {
        if (_settings.CommunityNotifications is not ("mute" or "mentions" or "all")) _settings.CommunityNotifications = "mentions";
        CommunityNotificationIcon.Kind = _settings.CommunityNotifications == "mute" ? IconKind.BellMuted : IconKind.Bell;
        CommunityNotificationIcon.Foreground = SocialBrush(_settings.CommunityNotifications == "all" ? "#E8C36E" : "#A8BBD2");
        CommunityNotificationButton.ToolTip = T("Уведомления: ", "Notifications: ") + CommunityNotificationLabel(_settings.CommunityNotifications);
        AutomationProperties.SetName(CommunityNotificationButton, CommunityNotificationButton.ToolTip.ToString());
    }

    private void CommunityNotifications_Click(object sender, RoutedEventArgs e)
    {
        if (ConfirmationActive) return;
        CloseSocialMenu();
        var menu = new ContextMenu { Style = (Style)FindResource("SocialContextMenu"), PlacementTarget = CommunityNotificationButton,
            Placement = PlacementMode.Bottom, HorizontalOffset = -160, VerticalOffset = 5 };
        foreach (var mode in new[] { "mute", "mentions", "all" })
        {
            var item = new MenuItem { Header = CommunityNotificationLabel(mode), Tag = mode,
                Style = (Style)FindResource("SocialMenuItem"), IsCheckable = true, IsChecked = _settings.CommunityNotifications == mode };
            item.Icon = new LauncherIcon { Kind = item.IsChecked ? IconKind.Check : IconKind.None,
                Width = 17, Height = 17, Foreground = SocialBrush("#D3AF59") };
            item.Click += (_, _) => { _settings.CommunityNotifications = mode; RefreshCommunityNotificationMode(); SaveCommunitySoon(); CloseSocialMenu(); };
            menu.Items.Add(item);
        }
        RevealSocialMenu(menu);
    }

    // Native resizing/window management with launcher-colored content and caption.
    private (Window Window, ContentControl Body) CreateCommunityDialog(string title, IconKind icon, double width, double height)
    {
        var window = new Window { Owner = this, Title = title, Width = Math.Min(width, ActualWidth - 48), Height = Math.Min(height, ActualHeight - 48),
            MinWidth = 360, MinHeight = 300, WindowStartupLocation = WindowStartupLocation.CenterOwner,
            WindowStyle = WindowStyle.None, ResizeMode = ResizeMode.CanResize, Background = SocialBrush("#0A1729"),
            Foreground = SocialBrush("#E8EDF5"), FontFamily = FontFamily, Resources = Resources, ShowInTaskbar = false };
        WindowChrome.SetWindowChrome(window, new WindowChrome { CaptionHeight = 60, ResizeBorderThickness = new Thickness(6),
            GlassFrameThickness = new Thickness(0), CornerRadius = new CornerRadius(8), UseAeroCaptionButtons = false });
        var layout = new Grid(); layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto }); layout.RowDefinitions.Add(new RowDefinition());
        var header = new Grid { Margin = new Thickness(20,12,12,12) };
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto }); header.ColumnDefinitions.Add(new ColumnDefinition()); header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        header.Children.Add(new LauncherIcon { Kind = icon, Width = 23, Height = 23, Foreground = SocialBrush("#D3AF59"), Margin = new Thickness(0,0,12,0) });
        var heading = new TextBlock { Text = title, FontSize = 20, FontWeight = FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center };
        Grid.SetColumn(heading,1); header.Children.Add(heading);
        var close = new Button { Content = new LauncherIcon { Kind = IconKind.Close, Width = 18, Height = 18 }, Width = 34, Height = 34,
            Padding = new Thickness(0), Style = (Style)FindResource("GhostButton"), ToolTip = T("Закрыть", "Close") };
        AutomationProperties.SetName(close,close.ToolTip.ToString()); WindowChrome.SetIsHitTestVisibleInChrome(close,true);
        close.Click += (_,_) => window.Close(); Grid.SetColumn(close,2); header.Children.Add(close); layout.Children.Add(header);
        var body = new ContentControl { Margin = new Thickness(20,0,20,20), HorizontalContentAlignment = HorizontalAlignment.Stretch, VerticalContentAlignment = VerticalAlignment.Stretch };
        Grid.SetRow(body,1);layout.Children.Add(body);
        window.Content = new Border { Background = SocialBrush("#0A1729"), BorderBrush = SocialBrush("#3B526F"), BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(8), Child = layout };
        window.PreviewKeyDown += (_,key) => { if (key.Key == Key.Escape) { key.Handled = true; window.Close(); } };
        return (window,body);
    }

    private async Task OpenCommunityProfileAsync(CommunityMessage message)
    {
        if (ConfirmationActive) return;
        if (message.SenderId.ToString() == _account.UserId) { await ShowOwnPlayerCardAsync(); return; }
        var friend = _socialPlayers.FirstOrDefault(p => p.Id == message.SenderId && p.Relation == "friend");
        if (friend is not null) { ShowSocialDetails(friend); return; }
        // Chat identities are public; a public card must not request or reveal a
        // stranger's private presence, configuration, match or account details.
        var (window, body) = CreateCommunityDialog(T("Профиль игрока", "Player profile"), IconKind.Profile, 440, 350);
        var content = new StackPanel { Margin = new Thickness(20), VerticalAlignment = VerticalAlignment.Center };
        var avatar = CommunityAvatar(message,64); avatar.HorizontalAlignment = HorizontalAlignment.Center; avatar.Margin = new Thickness(0,0,0,16); content.Children.Add(avatar);
        content.Children.Add(new TextBlock { Text = message.DisplayName, FontSize = 22, FontWeight = FontWeights.SemiBold, TextAlignment = TextAlignment.Center, TextWrapping = TextWrapping.Wrap });
        content.Children.Add(new TextBlock { Text = "@" + message.Nickname, Foreground = SocialBrush("#A8BBD2"), TextAlignment = TextAlignment.Center, Margin = new Thickness(0,6,0,20) });
        var add = new Button { Content = _account.State == AccountState.Guest ? T("Войти в аккаунт", "Sign in") : T("Добавить в друзья", "Add friend"), Name = "CommunityProfileAction", Style = (Style)FindResource("GoldButton"), HorizontalAlignment = HorizontalAlignment.Center };
        add.Click += (_,_) => { window.Close(); if (_account.State == AccountState.Guest) ShowAccountForm(false);
            else { SetActivePage("friends"); FriendsShowAdd_Click(FriendsShowAddButton,new RoutedEventArgs()); FriendsNicknameInput.Text = message.Nickname; } };
        content.Children.Add(add);body.Content = content;
        window.Loaded += async (_,_) => await RefreshCommunityAvatarAsync(message);
        window.ShowDialog();
    }
}
