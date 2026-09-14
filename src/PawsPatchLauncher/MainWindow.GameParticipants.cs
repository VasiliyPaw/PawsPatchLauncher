using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly Dictionary<Guid,(DateTimeOffset? revision,ImageBrush? image)> _gameParticipantAvatars = new();
    private readonly Dictionary<Guid,List<ContentControl>> _gameActivityAvatarViews = new();
    private bool _gameActivityOpeningProfile;
    private CancellationTokenSource? _gameAvatarReadLifetime;
    // Isolated UI checks replace transport, never real accounts or friendships.
    private Func<Guid,CancellationToken,Task<byte[]?>>? _gameAvatarReadOverride = null;
    private Func<Guid,CancellationToken,Task<SocialPlayer>>? _gameProfileReadOverride = null;
    private Func<SocialPlayer,CancellationToken,Task>? _profileFriendRequestOverride = null;

    private async Task RefreshShownProfileAvatarAsync(SocialPlayer player,int generation)
    {
        if(player.AvatarRevision is null || _account.UserId==player.Id.ToString()
            || _socialAvatars.TryGetValue(player.Id,out var friend)&&friend.revision==player.AvatarRevision
            || _gameParticipantAvatars.TryGetValue(player.Id,out var cached)&&cached.revision==player.AvatarRevision)return;
        var owner=_account.UserId;
        try
        {
            using var timeout=CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);timeout.CancelAfter(TimeSpan.FromSeconds(8));
            var bytes=await (_gameAvatarReadOverride?.Invoke(player.Id,timeout.Token)??_account.GetFriendAvatarAsync(player.Id,timeout.Token));
            var image=bytes is null?null:new ImageBrush(AccountAvatarImage.Decode(bytes,normalized:true)){Stretch=Stretch.UniformToFill};image?.Freeze();
            if(generation!=_socialDetailsGeneration||owner!=_account.UserId||_socialDetailsPeer!=player.Id)return;
            if(_gameParticipantAvatars.Count>=64&&!_gameParticipantAvatars.ContainsKey(player.Id))_gameParticipantAvatars.Remove(_gameParticipantAvatars.Keys.First());
            _gameParticipantAvatars[player.Id]=(player.AvatarRevision,image);
            SocialDetailsAvatar.Content=SocialAvatar(player.Id,68,true,openProfile:false);
            RefreshAvatarPreviewAvailability();
        }
        catch(Exception error) when(error is AccountException or OperationCanceledException or System.Net.Http.HttpRequestException or System.IO.IOException) { }
    }

    private async Task RefreshGameParticipantAvatarsAsync(GameActivityDetails details,int generation)
    {
        if(_gameActivityLifetime is null)return;
        using var budget=CancellationTokenSource.CreateLinkedTokenSource(_gameActivityLifetime.Token);
        budget.CancelAfter(TimeSpan.FromSeconds(8));
        _gameAvatarReadLifetime=budget;
        var token=budget.Token;
        var owner=_account.UserId;
        try
        {
        var profiles=(details.Activity.Players??[]).Where(p=>!p.Bot&&p.Profile is not null).Select(p=>p.Profile!).DistinctBy(p=>p.Id).ToArray();
        foreach(var id in _gameParticipantAvatars.Keys.Where(id=>!profiles.Any(p=>p.Id==id)&&_activityViewedPlayer?.Id!=id).ToArray())
            _gameParticipantAvatars.Remove(id);
        foreach(var profile in profiles)
        {
            if(generation!=_gameActivityGeneration||token.IsCancellationRequested||owner!=_account.UserId)return;
            if(profile.Id.ToString()==owner)continue;
            if(_socialAvatars.TryGetValue(profile.Id,out var friend)&&friend.revision==profile.AvatarRevision)continue;
            if(_gameParticipantAvatars.TryGetValue(profile.Id,out var cached)&&cached.revision==profile.AvatarRevision)continue;
            ImageBrush? brush=null;
            try
            {
                if(profile.AvatarRevision is not null)
                {
                    using var timeout=CancellationTokenSource.CreateLinkedTokenSource(token);timeout.CancelAfter(TimeSpan.FromSeconds(8));
                    var bytes=await (_gameAvatarReadOverride?.Invoke(profile.Id,timeout.Token)??_account.GetFriendAvatarAsync(profile.Id,timeout.Token));
                    if(bytes is not null){brush=new ImageBrush(AccountAvatarImage.Decode(bytes,normalized:true)){Stretch=Stretch.UniformToFill};brush.Freeze();}
                }
            }
            catch(Exception error) when(error is AccountException or OperationCanceledException or System.Net.Http.HttpRequestException or System.IO.IOException)
            { continue; } // An image must not hide the roster. The next open/poll may retry.
            if(generation!=_gameActivityGeneration||token.IsCancellationRequested||owner!=_account.UserId)return;
            _gameParticipantAvatars[profile.Id]=(profile.AvatarRevision,brush);
            if(_gameActivityAvatarViews.TryGetValue(profile.Id,out var views))
                foreach(var view in views)view.Content=SocialAvatar(profile.Id,34,false,openProfile:false);
            if(_socialDetailsPeer==profile.Id)
            {
                SocialDetailsAvatar.Content=SocialAvatar(profile.Id,68,true,openProfile:false);
                RefreshAvatarPreviewAvailability();
            }
        }
        }
        finally { if(ReferenceEquals(_gameAvatarReadLifetime,budget))_gameAvatarReadLifetime=null; }
    }

    private async Task OpenGameParticipantProfileAsync(GameParticipantProfile profile)
    {
        if(_gameActivityOpeningProfile||AccountConnectionBlocked||ConfirmationActive||_gameActivityLifetime is null
            ||!(_gameActivityShown?.Activity.Players?.Any(p=>!p.Bot&&p.Profile?.Id==profile.Id)??false))return;
        if(profile.Id.ToString()==_account.UserId){CloseGameActivity();await ShowOwnPlayerCardAsync();return;}
        _gameActivityOpeningProfile=true;
        _gameAvatarReadLifetime?.Cancel(); // Profile navigation takes priority over cosmetic downloads on the account transport.
        var generation=_gameActivityGeneration;var owner=_account.UserId;
        using var timeout=CancellationTokenSource.CreateLinkedTokenSource(_gameActivityLifetime.Token);timeout.CancelAfter(TimeSpan.FromSeconds(8));
        GameActivityStatus.Text=T("Открываю профиль…","Opening profile…");
        try
        {
            var player=_socialPlayers.FirstOrDefault(p=>p.Id==profile.Id&&p.Relation=="friend")
                ??await (_gameProfileReadOverride?.Invoke(profile.Id,timeout.Token)??_account.GetPlayerProfileAsync(profile.Id,timeout.Token));
            if(generation!=_gameActivityGeneration||owner!=_account.UserId||timeout.IsCancellationRequested)return;
            if(player.Id!=profile.Id||player.Deleted)throw new AccountException("player_unavailable");
            CloseGameActivity();
            _activityViewedPlayer=player;ShowSocialDetails(player);
        }
        catch(Exception error) when(error is AccountException or OperationCanceledException or System.Net.Http.HttpRequestException)
        {
            if(generation==_gameActivityGeneration)GameActivityStatus.Text=T("Не удалось открыть профиль. Игрок мог выйти из лобби или потерять подключение. Попробуйте ещё раз.",
                "Could not open the profile. The player may have left the lobby or disconnected. Try again.");
        }
        finally{if(generation==_gameActivityGeneration)_gameActivityOpeningProfile=false;}
    }

    private async Task RequestProfileFriendAsync(SocialPlayer player)
    {
        if(player.IsFriend||!player.Available||player.Relation is "outgoing" or "blocked"||SocialDetailsPlayer()?.Id!=player.Id)return;
        await SocialOperationAsync(async owner=>
        {
            if(_profileFriendRequestOverride is not null)await _profileFriendRequestOverride(player,_accountLifetime.Token);
            else await _account.FriendActionAsync("request",player.Id,player.Nickname,_accountLifetime.Token);
            if(_account.UserId!=owner.ToString())return;
            // Commit the acknowledged request immediately, even if the following list refresh fails.
            var pending=player with{Relation="outgoing",IsFriend=false,Unread=0};
            _socialPlayers=_socialPlayers.Where(p=>p.Id!=player.Id).Append(pending).ToArray();
            if(_socialDetailsPeer==player.Id){_activityViewedPlayer=pending;RenderSocialDetails(pending);}
            RenderSocialRows();RenderSocialNotifications();
            ShowToast(()=>T("Заявка отправлена.","Friend request sent."));
            _socialNextPoll=default;
        });
    }
}
