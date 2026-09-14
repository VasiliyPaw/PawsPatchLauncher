namespace PawsPatchLauncher;

public enum FriendRequestOutcome { Sent, AlreadyFriends, AlreadySent, Incoming }
public sealed record FriendRequestResult(FriendRequestOutcome Outcome, IReadOnlyList<SocialPlayer> Players);

public sealed partial class AccountService
{
    public async Task<FriendRequestResult> RequestFriendAsync(string nickname, Guid? target = null, CancellationToken ct = default)
    {
        ValidateNickname(nickname);
        var owner=UserId;
        var players=await GetFriendsAsync(ct).ConfigureAwait(false);
        if(UserId!=owner)throw new AccountException("session_expired");
        var previous=FindRequestPeer(players,nickname,target);
        if(RequestOutcome(previous) is { } existing) return new(existing,players);
        await FriendActionAsync("request",target,nickname,ct).ConfigureAwait(false);
        // The existing server intentionally returns ok for an existing friendship/request too.
        // Read back the relation before claiming that a new request was sent.
        players=await GetFriendsAsync(ct).ConfigureAwait(false);
        if(UserId!=owner)throw new AccountException("session_expired");
        var current=FindRequestPeer(players,nickname,target);
        var outcome=RequestOutcome(current) ?? throw new AccountException("request_unconfirmed");
        return new(outcome==FriendRequestOutcome.AlreadySent ? FriendRequestOutcome.Sent : outcome,players);
    }
    private static SocialPlayer? FindRequestPeer(IReadOnlyList<SocialPlayer> players,string nickname,Guid? target) =>
        players.FirstOrDefault(p=>target is { } id ? p.Id==id : p.Nickname.Equals(NormalizeUsername(nickname),StringComparison.OrdinalIgnoreCase));
    private static FriendRequestOutcome? RequestOutcome(SocialPlayer? player) => player switch
    {
        { Relation:"friend", IsFriend:true } => FriendRequestOutcome.AlreadyFriends,
        { Relation:"outgoing" } => FriendRequestOutcome.AlreadySent,
        { Relation:"incoming" } => FriendRequestOutcome.Incoming,
        { Relation:"blocked" } => throw new AccountException("player_unavailable"),
        _ => null
    };
}

public partial class MainWindow
{
    private void ShowFriendRequestResult(FriendRequestResult result)
    {
        _socialPlayers=result.Players;
        if(_socialDetailsPeer is { } peer && result.Players.FirstOrDefault(p=>p.Id==peer) is { } current)
        { _activityViewedPlayer=current; RenderSocialDetails(current); }
        RenderSocialRows(); RenderSocialNotifications();
        ShowToast(()=>result.Outcome switch {
            FriendRequestOutcome.AlreadyFriends => T("Этот игрок уже у вас в друзьях.", "This player is already your friend."),
            FriendRequestOutcome.AlreadySent => T("Вы уже отправили заявку этому игроку.", "You have already sent this player a friend request."),
            FriendRequestOutcome.Incoming => T("От этого игрока уже есть входящая заявка. Примите её в разделе заявок.", "You already have a request from this player. Accept it in Requests."),
            _ => T("Заявка отправлена.", "Friend request sent.")
        });
        _socialNextPoll=default;
    }
}
