using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly ArrivalSnapshot<(Guid Sender, Guid Message)> _messageArrivals = new();
    private readonly ArrivalSnapshot<Guid> _requestArrivals = new();
    private string? _socialLoadedChat;
    private long _messageArrivalVersion;
    private long _requestArrivalVersion;
    private string? _badgeArrivalOwner;
    private IReadOnlyList<SocialPlayer> _badgeArrivalPlayers = [];
    private bool _badgeArrivalReady;
    private string ChatArrivalScope => _account.UserId + "|" + _socialPeer;

    private void ScheduleSocialArrival(FrameworkElement row, ScrollViewer viewport, Func<bool> current)
    {
        Dispatcher.BeginInvoke(DispatcherPriority.Loaded, new Action(() =>
        {
            if (!current() || !row.IsVisible || !viewport.IsVisible || !viewport.IsAncestorOf(row)) return;
            var bounds=row.TransformToAncestor(viewport).TransformBounds(new Rect(row.RenderSize));
            if (bounds.IntersectsWith(new Rect(viewport.RenderSize))) ArrivalMotion.Enter(row);
        }));
    }

    private void PulseSocialNotifications(bool guest)
    {
        var ready=!guest && _socialListReceived!=default;
        if (ready && _badgeArrivalReady && _badgeArrivalOwner==_account.UserId)
        {
            var incoming=_socialPlayers.Any(p=>p.Relation=="incoming" && !_badgeArrivalPlayers.Any(old=>old.Id==p.Id&&old.Relation=="incoming"));
            var unread=_socialPlayers.Any(p=>p.Relation=="friend" && VisibleUnread(p)>0
                && p.Unread > (_badgeArrivalPlayers.FirstOrDefault(old=>old.Id==p.Id&&old.Relation=="friend")?.Unread ?? 0));
            if (incoming || unread) ScheduleBadgePulse(FriendsNavBadge);
            if (incoming) ScheduleBadgePulse(FriendsRequestsBadge);
            if (unread) ScheduleBadgePulse(FriendsChatsBadge);
        }
        _badgeArrivalOwner=_account.UserId; _badgeArrivalReady=ready; _badgeArrivalPlayers=_socialPlayers;
    }

    private void ScheduleBadgePulse(Border badge)
    {
        if(!badge.IsVisible)return;
        var owner=_account.UserId; var players=_socialPlayers;
        Dispatcher.BeginInvoke(DispatcherPriority.Loaded,new Action(()=>
        {
            if(_account.UserId==owner && ReferenceEquals(players,_socialPlayers)) ArrivalMotion.Pulse(badge);
        }));
    }
}
