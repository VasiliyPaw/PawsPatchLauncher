using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private string? _chatHeaderAvatarKey;
    private void FriendsChatProfile_Click(object sender,RoutedEventArgs e)
    {
        if(ConfirmationActive)return;
        var friend=_socialPlayers.FirstOrDefault(p=>p.Id==_socialPeer&&p.Relation=="friend");
        if(friend is not null)ShowSocialDetails(friend);
    }
    private void RenderSocialMessages()
    {
        RenderHistoryControls();
        RefreshOfferActions();
        var context = _account.UserId + "|" + _text.Language + "|" + _socialSection + "|" + _socialPeer + "|" + _socialAvatarGeneration + "|" + _account.AvatarChangedAt + "|" +_account.AdminLevel+"|"+ string.Join(";", _socialPlayers.Select(p => p.Id + ":" + p.Nickname + ":" + p.Name + ":" + p.Relation+":"+p.AdminLevel+":"+p.Banned+":"+p.Deleted));
        context += "|" + string.Join(";",_socialOffers.Where(o=>o.Sender==_socialPeer||o.Recipient==_socialPeer).OrderBy(o=>o.Id).Select(o=>o.Id+":"+o.State));
        context += "|" + string.Join(";",_sendingOffers.Values.Select(o=>o.Id+":"+o.State));
        context += "|" + _account.DisplayName;
        context += "|" + _socialLoadedChat;
        context += "|" + _historyViewStart + "|" + _historyRevision;
        if (_socialRenderedContext == context && _socialRenderedMessages.SequenceEqual(_socialMessages) && _socialRenderedPending.SequenceEqual(_socialPending)) return;
        _socialRenderedContext = context; _socialRenderedMessages = _socialMessages; _socialRenderedPending = _socialPending;
        var arrivalVersion=++_messageArrivalVersion;
        FriendsChatCard.Visibility = _socialPeer is null || _socialSection != "chats" ? Visibility.Collapsed : Visibility.Visible;
        FriendsChatEmptyCard.Visibility = _socialSection == "chats" && _socialPeer is null && _socialPlayers.Any(p => p.Relation == "friend") ? Visibility.Visible : Visibility.Collapsed;
        var chatFriend=_socialPlayers.FirstOrDefault(p=>p.Id==_socialPeer);
        FriendsChatName.Text=chatFriend is null?"":PlayerDisplayName(chatFriend);
        FriendsChatUsername.Text=chatFriend is null?"":PlayerUsername(chatFriend);
        foreach(var badge in FriendsChatTitle.Inlines.OfType<System.Windows.Documents.InlineUIContainer>().ToArray())FriendsChatTitle.Inlines.Remove(badge);
        FriendsChatMark.Text=chatFriend?.Banned==true?PlayerMarker(chatFriend):"";
        if(chatFriend is {AdminLevel:>0,Deleted:false})FriendsChatTitle.Inlines.Add(new System.Windows.Documents.InlineUIContainer(AdministratorBadge(chatFriend.AdminLevel)));
        FriendsChatMark.Foreground=SocialBrush(chatFriend?.Banned==true?"#FFB1A8":"#F2C867");
        FriendsChatMark.ToolTip=chatFriend?.Banned==true?BanDescription(chatFriend.BannedAt,chatFriend.BanUntil,chatFriend.BanReason):T("Роль подтверждена сервером","Server-verified role");
        FriendsChatTitle.ToolTip=chatFriend is null?null:chatFriend.Name+" · @"+chatFriend.Nickname;
        FriendsChatProfileButton.IsEnabled=chatFriend?.Relation=="friend"&&chatFriend.Deleted==false;
        System.Windows.Automation.AutomationProperties.SetName(FriendsChatProfileButton,T("Профиль: ","Profile: ")+chatFriend?.Name);
        var avatarKey=chatFriend is null?null:chatFriend.Id+"|"+_socialAvatarGeneration+"|"+chatFriend.Deleted;
        if(_chatHeaderAvatarKey!=avatarKey)
        {
            _chatHeaderAvatarKey=avatarKey;
            FriendsChatHeaderAvatar.Content=chatFriend is null?null:SocialAvatar(chatFriend.Id,38,false);
        }
        var oldOffset = FriendsChatScroll.VerticalOffset;
        var atEnd = FriendsChatScroll.ScrollableHeight - oldOffset < 20;
        ResetChatMedia();
        FriendsMessagesPanel.Children.Clear(); FriendsOutboxPanel.Children.Clear(); FriendsOtherOutboxPanel.Children.Clear();
        var visibleMessages=_socialMessages.Skip(_historyViewStart).Take(HistoryVisibleLimit).Concat(_sendingOffers.Values.Where(o=>o.Sender.ToString()==_account.UserId&&o.Recipient==_socialPeer&&!_socialMessages.Any(m=>m.MessageId==o.Id)).Select(o=>new SocialMessage(o.Sender,o.Id,o.Recipient,"","offer",o.CreatedAt)));
        var timeline = visibleMessages.Select(m => (time: m.CreatedAt, message: (SocialMessage?)m, pending: (PendingSocialMessage?)null))
            .Concat(_socialPending.Where(p => p.Target == _socialPeer && !_socialMessages.Any(m => m.SenderId == p.Owner && m.MessageId == p.Id))
                .Select(p => (time: p.CreatedAt, message: (SocialMessage?)null, pending: (PendingSocialMessage?)p))).OrderBy(x => x.time).ToArray();
        var scope=ChatArrivalScope;
        var arrived=_messageArrivals.Observe(scope, timeline.Select(e=>(e.message?.SenderId??e.pending!.Owner,e.message?.MessageId??e.pending!.Id)),_socialLoadedChat==scope);
        if(_historyNavigating)arrived.Clear();
        var entrances=new List<FrameworkElement>();
        foreach (var entry in timeline)
        {
            var isNew=arrived.Contains((entry.message?.SenderId??entry.pending!.Owner,entry.message?.MessageId??entry.pending!.Id));
            if(entry.message is SocialMessage message && (_sendingOffers.GetValueOrDefault(message.MessageId) ?? _socialOffers.FirstOrDefault(o=>o.Id==message.MessageId&&o.Sender==message.SenderId)) is SocialOffer offer)
            { var card=RenderOfferCard(offer); card.Tag=message.MessageId; FriendsMessagesPanel.Children.Add(card); if(isNew)entrances.Add(card); continue; }
            var sender = entry.message?.SenderId ?? entry.pending!.Owner;
            var own = sender.ToString() == _account.UserId;
            var pending = entry.pending;
            var failed = pending?.Error.Length > 0;
            var row = new Grid { Margin = new Thickness(own ? 20 : 0, 0, own ? 0 : 20, 10), Tag = pending?.Id ?? entry.message!.MessageId };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = own ? new GridLength(1, GridUnitType.Star) : GridLength.Auto });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = own ? GridLength.Auto : new GridLength(1, GridUnitType.Star) });
            var avatar = SocialAvatar(sender, 30, false); avatar.Margin = new Thickness(own ? 8 : 0, 2, own ? 0 : 8, 0); avatar.VerticalAlignment = VerticalAlignment.Top;
            Grid.SetColumn(avatar, own ? 1 : 0); row.Children.Add(avatar);
            var bubble = new Border { Background = SocialBrush(failed ? "#3B222C" : pending is not null ? "#112234" : own ? "#244361" : "#192F49"),
                BorderBrush = SocialBrush(failed ? "#C36368" : "#344E68"), BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(9), Padding = new Thickness(10, 8, 10, 8) };
            Grid.SetColumn(bubble, own ? 0 : 1); row.Children.Add(bubble);
            var content = new StackPanel(); bubble.Child = content;
            if(pending is null&&ChatMedia.Find(entry.message!.Body).Count>0)
                bubble.HorizontalAlignment=own?HorizontalAlignment.Right:HorizontalAlignment.Left;
            var author=_socialPlayers.FirstOrDefault(p=>p.Id==sender);
            var header=new TextBlock { Text = (own ? T("Вы", "You") : author is not null ? PlayerDisplayName(author)+(author.Deleted?"":" · "+PlayerUsername(author)) : T("Игрок", "Player")) + " · " + ChatTime(entry.time), ToolTip=ChatDate(entry.time), FontSize = 11, Foreground = SocialBrush("#B4C8DC"),VerticalAlignment=VerticalAlignment.Center };
            var level=own?_account.AdminLevel:author?.AdminLevel??0;if(level>0&&author?.Deleted!=true)header.Inlines.Add(new System.Windows.Documents.InlineUIContainer(AdministratorBadge(level)));
            content.Children.Add(header);
            content.Children.Add(new TextBlock { Tag="message-body",Text = entry.message is {Kind:"offer"}&&author?.Deleted==true?T("Предложение недоступно: аккаунт удалён.","Offer unavailable: account deleted."):entry.message?.Body ?? pending!.Body, TextWrapping = TextWrapping.Wrap, FontSize = 14,
                Foreground = SocialBrush(pending is not null && !failed ? "#8195AD" : "#F4F1E7"), Margin = new Thickness(0, 4, 0, 0) });
            if(pending is null)AddChatMedia(content,entry.message!.Body);
            if (pending is not null)
            {
                content.Children.Add(new TextBlock { Text = failed ? SocialError(pending.Error) : T("Отправляется…", "Sending…"), TextWrapping = TextWrapping.Wrap, FontSize = 11,
                    Foreground = SocialBrush(failed ? "#F69B9F" : "#8195AD"), Margin = new Thickness(0, 6, 0, 0) });
                if (failed)
                {
                    var actions = new WrapPanel();
                    actions.Children.Add(SocialButton(T("Повторить", "Retry"), () => ChangePendingSocialAsync(pending, true)));
                    actions.Children.Add(SocialButton(T("Удалить", "Delete"), () => ChangePendingSocialAsync(pending, false)));
                    content.Children.Add(actions);
                }
            }
            FriendsMessagesPanel.Children.Add(row);
            if(isNew)entrances.Add(row);
        }
        RefreshOfferActions();
        if (!_historyPreserveScroll) { if (atEnd) FriendsChatScroll.ScrollToEnd(); else FriendsChatScroll.ScrollToVerticalOffset(oldOffset); }
        if(_activePage=="friends" && _socialSection=="chats")
            foreach(var row in entrances.TakeLast(4)) ScheduleSocialArrival(row,FriendsChatScroll,
                ()=>arrivalVersion==_messageArrivalVersion && scope==ChatArrivalScope && _activePage=="friends" && _socialSection=="chats");
    }
    private static SolidColorBrush SocialBrush(string color) => new((Color)ColorConverter.ConvertFromString(color));
    private static string ChatTime(DateTimeOffset time)=>time.ToLocalTime().ToString("HH:mm:ss",System.Globalization.CultureInfo.InvariantCulture);
    private string ChatDate(DateTimeOffset time)=>time.ToLocalTime().ToString(_text.Language=="ru"?"dd.MM.yyyy HH:mm:ss":"yyyy-MM-dd HH:mm:ss",System.Globalization.CultureInfo.InvariantCulture);
}
