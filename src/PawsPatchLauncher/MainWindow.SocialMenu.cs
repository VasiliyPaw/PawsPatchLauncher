using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private ContextMenu? _socialMenu;
    private Action<ContextMenu>? _socialMenuOpenOverride = null;
    private void RevealSocialMenu(ContextMenu menu)
    {
        _socialMenu=menu;
        if(ActivityStore.IsSmokeTest&&_socialMenuOpenOverride is not null)_socialMenuOpenOverride(menu);
        else menu.IsOpen=true;
    }
    private void CloseSocialMenu()
    {
        if (_socialMenu is not null) _socialMenu.IsOpen = false;
        _socialMenu = null;
    }

    private Button SocialMoreButton(SocialPlayer player)
    {
        var button = new Button { Content = new LauncherIcon { Kind = IconKind.More, Width = 20, Height = 20 }, Padding = new Thickness(0), Style = (Style)FindResource("GhostButton") };
        button.Click += (_, _) => OpenSocialMenu(button, player);
        button.Unloaded += (_, _) => { if (_socialMenu?.PlacementTarget == button) CloseSocialMenu(); };
        return button;
    }

    private void OpenSocialMenu(Button anchor, SocialPlayer player)
    {
        if (_socialBusy || _accountBusy || ConfirmationActive || _account.State == AccountState.Guest) return;
        CloseSocialMenu();
        var menu = CreateSocialMenu(anchor, player);
        _socialMenu = menu;
        SetNavState(anchor, true);
        RevealSocialMenu(menu);
    }

    private ContextMenu CreateSocialMenu(Button anchor, SocialPlayer player)
    {
        var owner = _account.UserId;
        var menu = new ContextMenu { Style = (Style)FindResource("SocialContextMenu"), PlacementTarget = anchor,
            Placement = PlacementMode.Bottom, HorizontalOffset = Math.Min(0, anchor.ActualWidth - 195), VerticalOffset = 5, StaysOpen = false };
        menu.Opened += (_, _) => { if (menu.Template.FindName("MenuSurface", menu) is FrameworkElement surface) Motion.Reveal(surface); };
        AutomationProperties.SetName(menu, T("Действия: ", "Actions: ") + player.Nickname);
        foreach (var action in (player.Deleted?new[]{"hide_chat"}:player.Relation == "incoming" ? new[] { "decline", "block" } : new[] { "details", "remove", "block" })
            .Where(a=>!(a=="block"&&player.AdminLevel>0)&&!(a=="remove"&&!player.IsFriend)))
        {
            var label = action=="hide_chat"?T("Удалить чат","Delete chat"):action == "details" ? T("Профиль", "Profile") : action == "decline" ? T("Отклонить заявку", "Decline request")
                : action == "remove" ? T("Удалить из друзей", "Remove friend") : T("Заблокировать", "Block");
            var item = new MenuItem { Header = label, Style = (Style)FindResource("SocialMenuItem"), Tag = action,
                Foreground = action == "block" || action == "remove" ? new SolidColorBrush(Color.FromRgb(240, 123, 114)) : (Brush)FindResource("TextMainBrush") };
            AutomationProperties.SetName(item, label + ": " + player.Nickname);
            item.Icon = new LauncherIcon { Kind = action == "details" ? IconKind.Profile : action == "block" ? IconKind.Shield : action == "remove" ? IconKind.Trash : IconKind.Close,
                Width = 19, Height = 19, VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center, Foreground = item.Foreground };
            item.Click += async (_, e) =>
            {
                e.Handled = true; CloseSocialMenu();
                if (_account.UserId != owner || !_socialPlayers.Any(p => p.Id == player.Id && p.Relation == player.Relation)) return;
                if(action=="details"){ShowSocialDetails(_socialPlayers.First(p=>p.Id==player.Id));return;}
                await SocialFriendActionAsync(player, action);
            };
            menu.Items.Add(item);
        }
        menu.Closed += (_, _) => { SetNavState(anchor, false); if (ReferenceEquals(_socialMenu, menu)) _socialMenu = null; };
        return menu;
    }
}
