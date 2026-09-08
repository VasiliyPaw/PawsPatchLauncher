using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private string _socialSection = "chats";
    private string _socialRequestSection = "incoming";
    private Guid? _socialMenuPeer;
    private bool _socialShowBlocked;
    private string _socialRowsSignature = "";

    private void SetSocialStatus(string text)
    {
        FriendsStatusText.Text = text;
        FriendsStatusText.Visibility = text.Length == 0 ? Visibility.Collapsed : Visibility.Visible;
    }

    private static void SocialBadge(Border badge, TextBlock label, int count)
    {
        var value = count > 99 ? "99+" : count.ToString();
        label.Text = value;
        badge.Visibility = count > 0 ? Visibility.Visible : Visibility.Collapsed;
    }

    private void RenderSocialNotifications()
    {
        var guest = _account is null || _account.State == AccountState.Guest;
        var incoming = guest ? 0 : _socialPlayers.Count(p => p.Relation == "incoming");
        var unread = guest ? 0 : _socialPlayers.Where(p => p.Relation == "friend").Sum(VisibleUnread);
        SocialBadge(FriendsNavBadge, FriendsNavBadgeText, _activePage == "friends" ? 0 : incoming + unread);
        if(!guest&&_account!.Restricted){FriendsNavBadgeText.Text="!";FriendsNavBadge.Visibility=Visibility.Visible;}
        SocialBadge(FriendsChatsBadge, FriendsChatsBadgeText, unread);
        SocialBadge(FriendsRequestsBadge, FriendsRequestsBadgeText, incoming);
        PulseSocialNotifications(guest);
        SetNavState(FriendsChatsTab, _socialSection == "chats");
        SetNavState(FriendsRequestsTab, _socialSection == "requests");
        FriendsBlockedTab.ToolTip=T("Заблокированные","Blocked")+" · "+_socialPlayers.Count(p=>p.Relation=="blocked");
        AutomationProperties.SetName(FriendsBlockedTab,FriendsBlockedTab.ToolTip.ToString());
        FriendsBlockedTab.Visibility=guest?Visibility.Collapsed:Visibility.Visible;
        FriendsBlockedTab.IsEnabled=!guest&&!_account!.Restricted;
        SetNavState(FriendsBlockedTab,_socialSection=="blocked");
        FriendsRequestTabs.Visibility = _socialSection == "requests" ? Visibility.Visible : Visibility.Collapsed;
        var outgoing = guest ? 0 : _socialPlayers.Count(p => p.Relation == "outgoing");
        FriendsIncomingTab.Content = T("Входящие", "Incoming") + (incoming > 0 ? " · " + incoming : "");
        FriendsOutgoingTab.Content = T("Исходящие", "Outgoing") + (outgoing > 0 ? " · " + outgoing : "");
        SetNavState(FriendsIncomingTab, _socialRequestSection == "incoming");
        SetNavState(FriendsOutgoingTab, _socialRequestSection == "outgoing");
        AutomationProperties.SetName(FriendsNav, T("Друзья", "Friends") +
            (incoming + unread > 0 ? T(", новых: ", ", new: ") + (incoming + unread) : ""));
    }

    private void FriendsChats_Click(object sender, RoutedEventArgs e) => SwitchSocialSection("chats");
    private void FriendsRequests_Click(object sender, RoutedEventArgs e) => SwitchSocialSection("requests");
    private void FriendsBlocked_Click(object sender,RoutedEventArgs e)=>SwitchSocialSection("blocked");
    private void FriendsIncoming_Click(object sender, RoutedEventArgs e) => SwitchSocialRequests("incoming");
    private void FriendsOutgoing_Click(object sender, RoutedEventArgs e) => SwitchSocialRequests("outgoing");
    private void SwitchSocialRequests(string section)
    {
        if (_socialRequestSection == section) return;
        _socialRequestSection = section; _socialMenuPeer = null;
        RenderSocialRows(); RenderSocialNotifications(); Motion.Reveal(FriendsRowsPanel);
    }

    private string SocialActionResult(string action) => action switch
    {
        "accept" => T("Друг добавлен.", "Friend added."),
        "decline" => T("Заявка отклонена.", "Request declined."),
        "cancel" => T("Заявка отменена.", "Request cancelled."),
        "remove" => T("Игрок удалён из друзей.", "Friend removed."),
        "block" => T("Игрок заблокирован.", "Player blocked."),
        "unblock" => T("Игрок разблокирован.", "Player unblocked."),
        "hide_chat" => T("Чат удалён из вашего списка.","Chat removed from your list."),
        _ => T("Готово.", "Done.")
    };
    private void SwitchSocialSection(string section)
    {
        if (_socialSection == section) return;
        _socialSection = section;
        _socialMenuPeer = null;
        SetSocialStatus("");
        RenderSocialRows();
        RenderSocialMessages();
        RenderSocialNotifications();
        Motion.Reveal(FriendsRowsPanel);
        Motion.Reveal(FriendsConversationScroll);
    }

    private void FriendsShowAdd_Click(object sender, RoutedEventArgs e)
    {
        if (FriendsAddPanel.Visibility == Visibility.Visible) Motion.Hide(FriendsAddPanel);
        else { Motion.Reveal(FriendsAddPanel); FriendsNicknameInput.Focus(); }
    }
    private void FriendsCancelAdd_Click(object sender, RoutedEventArgs e) => Motion.Hide(FriendsAddPanel);

    private void FriendsSearch_Click(object sender,RoutedEventArgs e)
    {
        if(FriendsSearchPanel.Visibility==Visibility.Visible)
        { FriendsSearchInput.Clear();Motion.Hide(FriendsSearchPanel); }
        else { Motion.Reveal(FriendsSearchPanel);FriendsSearchInput.Focus(); }
    }
    private void FriendsSearch_Changed(object sender,TextChangedEventArgs e)
    { if(_account is not null&&FriendsRowsPanel is not null)RenderSocialRows(); }
    private void FriendsClearSearch_Click(object sender,RoutedEventArgs e)
    { FriendsSearchInput.Clear();Motion.Hide(FriendsSearchPanel);FriendsSearchButton.Focus(); }
    private void FriendsSearch_KeyDown(object sender,KeyEventArgs e)
    { if(e.Key==Key.Escape) { FriendsSearchInput.Clear();Motion.Hide(FriendsSearchPanel);e.Handled=true; } }
    private void FriendsNickname_KeyDown(object sender,KeyEventArgs e)
    {
        if(e.Key==Key.Enter&&FriendsAddButton.IsEnabled) { e.Handled=true;FriendsAdd_Click(FriendsAddButton,new RoutedEventArgs()); }
        else if(e.Key==Key.Escape) { e.Handled=true;Motion.Hide(FriendsAddPanel); }
    }

    private async Task OpenSocialChatAsync(SocialPlayer player)
    {
        if (_socialBusy || _accountBusy || ConfirmationActive) return;
        if (_socialPeer == player.Id)
        {
            _socialPeer = null;
            ResetSocialHistory();
            _socialMessages = [];
            _socialLoadedChat = null;
            FriendsMessageInput.Clear();
            CloseSocialMenu();
            RenderSocialRows();
            RenderSocialMessages();
            RenderSocialIdentity();
            return;
        }
        await SocialOperationAsync(async owner =>
    {
        if (_socialPeer != player.Id) { _socialMessages = []; _socialOffers = []; ResetSocialHistory(); FriendsMessageInput.Clear(); }
        _socialPeer = player.Id;
        _socialMenuPeer = null;
        await LoadSocialChatAsync(owner);
        if (_account.UserId != owner.ToString()) return;
        RenderSocialRows();
        if (_activePage == "friends" && _socialSection == "chats") Motion.Reveal(FriendsChatCard);
        FriendsChatScroll.ScrollToEnd();
        SetSocialStatus("");
        await AcknowledgeSocialAsync(owner);
        });
    }

    private void RenderSocialRows()
    {
        PruneSocialProfiles();
        var query=FriendsSearchInput.Text.Trim().TrimStart('@');
        bool Matches(SocialPlayer player)=>query.Length==0||player.Name.Contains(query,StringComparison.OrdinalIgnoreCase)
            ||player.Nickname.Contains(query,StringComparison.OrdinalIgnoreCase);
        var arrivalScope=_account.UserId+"|"+_activePage+"|"+_socialSection+"|"+_socialRequestSection;
        var arrived=_requestArrivals.Observe(arrivalScope,
            _socialPlayers.Where(p=>p.Relation==_socialRequestSection).Select(p=>p.Id),_socialListReceived!=default);
        // Identical background polls must not rebuild focused buttons.
        var signature = _socialIdentity + "|" + _text.Language + "|" + _socialSection + "|" + _socialRequestSection + "|" +
            _socialPeer + "|" + _socialMenuPeer + "|" + _socialShowBlocked + "|" + query + "|" +
            _socialAvatarGeneration + "|" + string.Join(";", _socialPlayers.Select(p => $"{p.Id}:{p.Nickname}:{p.Name}:{p.Relation}:{VisibleUnread(p)}:{p.Presence}:{p.AvatarRevision}:{p.AdminLevel}:{p.Banned}:{p.Deleted}:{p.IsFriend}"));
        if (_socialRowsSignature == signature) return;
        _socialRowsSignature = signature;
        var arrivalVersion=++_requestArrivalVersion;
        CloseSocialMenu();
        FriendsRowsPanel.Children.Clear();
        if(_socialSection=="blocked")
        {
            FriendsRowsPanel.Children.Add(new TextBlock{Text=T("Заблокированные","Blocked"),FontSize=15,FontWeight=FontWeights.SemiBold,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,0,0,10)});
            var entries=_socialPlayers.Where(p=>p.Relation=="blocked"&&Matches(p)).ToArray();
            FriendsListEmptyText.Text=T("Заблокированных пользователей нет","No blocked users");
            FriendsListEmptyText.Visibility=entries.Length==0?Visibility.Visible:Visibility.Collapsed;
            foreach(var player in entries)RenderSocialRequest(player);return;
        }
        var friends = _socialPlayers.Where(p => p.Relation == "friend"&&Matches(p)).ToArray();
        var requests = _socialPlayers.Where(p => p.Relation == _socialRequestSection&&Matches(p)).ToArray();
        FriendsListEmptyText.Text = query.Length>0?T("Никого не найдено", "No matches"):_socialSection == "chats" ? T("Друзей пока нет", "No friends yet")
            : _socialRequestSection == "incoming" ? T("Входящих заявок пока нет", "No incoming requests") : T("Исходящих заявок пока нет", "No outgoing requests");
        FriendsListEmptyText.Visibility = (_socialSection == "chats" ? friends.Length : requests.Length) == 0
            ? Visibility.Visible : Visibility.Collapsed;
        if (_socialSection == "chats")
        {
            foreach (var player in friends) RenderSocialFriend(player);
            return;
        }
        var animated=0;
        foreach (var player in requests)
        {
            var card=RenderSocialRequest(player);
            if (arrived.Contains(player.Id) && animated++<4 && _activePage=="friends")
                ScheduleSocialArrival(card,MainOptionsScroll,()=>arrivalVersion==_requestArrivalVersion
                    && arrivalScope==_account.UserId+"|"+_activePage+"|"+_socialSection+"|"+_socialRequestSection);
        }
    }

    private void RenderSocialFriend(SocialPlayer player)
    {
        var row = new StackPanel { Margin = new Thickness(0, 6, 0, 0) };
        var line = new Grid();
        line.ColumnDefinitions.Add(new ColumnDefinition());
        var open = SocialButton("", () => OpenSocialChatAsync(player));
        open.Margin = new Thickness(0);
        open.Padding = new Thickness(10, 9, 10, 9);
        open.HorizontalContentAlignment = HorizontalAlignment.Stretch;
        AutomationProperties.SetName(open, player.Nickname);
        var content = new DockPanel();
        var badgeText = new TextBlock { FontSize = 11, Foreground = Brushes.White, VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
        var badge = new Border { Background = new SolidColorBrush(Color.FromRgb(185, 71, 87)), CornerRadius = new CornerRadius(9), MinWidth = 18, Height = 18, Padding = new Thickness(4, 0, 4, 0), Margin = new Thickness(8, 0, 0, 0), Child = badgeText };
        SocialBadge(badge, badgeText, VisibleUnread(player));
        DockPanel.SetDock(badge, Dock.Right); content.Children.Add(badge);
        var avatar=SocialAvatar(player.Id,36,true);avatar.Margin=new Thickness(0,0,10,0);DockPanel.SetDock(avatar,Dock.Left);content.Children.Add(avatar);
        content.Children.Add(SocialNameLabel(player));
        open.MouseRightButtonUp+=(_,e)=>{e.Handled=true;OpenSocialContextAt(open,player.Id);};
        open.Content = content;
        SetNavState(open, _socialPeer == player.Id);
        line.Children.Add(open);
        row.Children.Add(line);
        FriendsRowsPanel.Children.Add(row);
    }

    private Border RenderSocialRequest(SocialPlayer player)
    {
        var body = new StackPanel();
        var card = new Border { Tag=player.Id, Background = new SolidColorBrush(Color.FromRgb(22, 42, 69)),
            BorderBrush = new SolidColorBrush(Color.FromRgb(52, 77, 109)), BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(7), Padding = new Thickness(10, 6, 8, 6), Margin = new Thickness(0, 0, 0, 8), Child = body };
        var line = new Grid();
        line.ColumnDefinitions.Add(new ColumnDefinition());
        line.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var nickname = new TextBlock { Text = player.Nickname, ToolTip = player.Nickname, TextTrimming = TextTrimming.CharacterEllipsis,
            FontSize = 13, FontWeight = FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 8, 0) };
        line.Children.Add(SocialNameLabel(player));
        var actions = new StackPanel { Orientation = Orientation.Horizontal };
        var action = player.Relation == "incoming" ? "accept" : player.Relation == "blocked" ? "unblock" : "cancel";
        var label = action == "accept" ? T("Принять", "Accept") : action == "unblock" ? T("Разблокировать", "Unblock") : T("Отменить", "Cancel");
        var primary = SocialButton(label, () => SocialFriendActionAsync(player, action), action == "accept");
        primary.Margin = new Thickness(0); primary.Padding = new Thickness(8, 6, 8, 6); primary.FontSize = 12;
        AutomationProperties.SetName(primary, label + ": " + player.Nickname);
        actions.Children.Add(primary);
        if (player.Relation == "incoming")
        {
            var more = SocialMoreButton(player);
            more.Margin = new Thickness(5, 0, 0, 0); more.Width = 30; more.Padding = new Thickness(0); more.ToolTip = T("Действия", "Actions");
            AutomationProperties.SetName(more, T("Действия: ", "Actions: ") + player.Nickname);
            actions.Children.Add(more);
        }
        Grid.SetColumn(actions, 1); line.Children.Add(actions); body.Children.Add(line);
        FriendsRowsPanel.Children.Add(card);
        return card;
    }

    private static bool SocialViewCanRead(bool active, bool minimized, string page, string section,
        bool visible, double distanceFromEnd, bool overlay) =>
        active && !minimized && page == "friends" && section == "chats" && visible && !overlay
        && distanceFromEnd >= 0 && distanceFromEnd <= 20;

    private async Task AcknowledgeSocialAsync(Guid owner)
    {
        // Wait for the actual conversation layout; never acknowledge a hidden/inactive/scrolled-up view.
        await Dispatcher.InvokeAsync(() => { }, DispatcherPriority.Background);
        if (!SocialViewCanRead(IsActive, WindowState == WindowState.Minimized, _activePage, _socialSection,
                FriendsChatCard.Visibility == Visibility.Visible, FriendsChatScroll.ScrollableHeight - FriendsChatScroll.VerticalOffset,
                ConfirmationActive || SocialDetailsOverlay.Visibility == Visibility.Visible || HelpOverlay.Visibility == Visibility.Visible || BroadcastOverlay.Visibility == Visibility.Visible)
            || !HistoryAtNewest || _historyNavigating
            || SmoothScroll.IsAnimating(FriendsChatScroll) || _account.UserId != owner.ToString() || _socialPeer is not Guid peer
            || !_socialPlayers.Any(p => p.Id == peer && p.Unread > 0)) return;
        var last = _socialMessages.Where(m => m.SenderId == peer && m.RecipientId == owner).OrderBy(m => m.Ordinal).LastOrDefault();
        if (last is null) return;
        // The server validates this displayed incoming ID; newer arrivals remain unread.
        var remaining = await _account.MarkMessagesReadAsync(peer, last.MessageId, _accountLifetime.Token);
        if (_account.UserId != owner.ToString()) return;
        _socialPlayers = _socialPlayers.Select(p => p.Id == peer ? p with { Unread = remaining } : p).ToArray();
        RenderSocialRows(); RenderSocialNotifications();
    }
}
