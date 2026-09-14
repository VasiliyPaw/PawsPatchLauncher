using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly Dictionary<Guid,(DateTimeOffset? revision,ImageBrush? image)> _socialAvatars = new();
    private int _socialAvatarGeneration;
    private Guid? _socialDetailsPeer;
    private DateTimeOffset _socialPresenceNext;
    private DateTimeOffset _socialListReceived;
    private readonly KohanActivityReader _gameActivityReader = new();
    private void ClearSocialProfiles()
    {
        _socialAvatars.Clear(); _socialAvatarGeneration++; _socialPresenceNext=default;_socialListReceived=default;
        _gameActivityCache.Clear();
        _gameParticipantAvatars.Clear();
        _socialListLoading = _socialListFailed = false;
        CloseSocialDetails();
    }
    private Grid SocialAvatar(Guid player,double size,bool status,bool openProfile=true)
    {
        var own=player.ToString()==_account.UserId;
        var photo=own && _accountAvatarOwner==_account.UserId ? _accountAvatar : _socialAvatars.GetValueOrDefault(player).image ?? _gameParticipantAvatars.GetValueOrDefault(player).image;
        if(!own && _gameParticipantAvatars.TryGetValue(player,out var participant)
            && (!_socialAvatars.TryGetValue(player,out var friendAvatar) || participant.revision>=friendAvatar.revision))photo=participant.image;
        var deleted=_socialPlayers.FirstOrDefault(p=>p.Id==player)?.Deleted==true;
        if(deleted)photo=null;
        var view=new Grid { Width=size,Height=size,Background=Brushes.Transparent };
        if(openProfile && !own && !deleted && _socialPlayers.Any(p=>p.Id==player&&p.Relation=="friend"))
        {
            view.Cursor=System.Windows.Input.Cursors.Hand;
            view.MouseLeftButtonUp+=(_,e)=>{e.Handled=true;var friend=_socialPlayers.FirstOrDefault(p=>p.Id==player&&p.Relation=="friend");if(friend is not null)ShowSocialDetails(friend);};
        }
        view.Children.Add(new Ellipse { Fill=photo ?? (Brush)SocialBrush("#334C68"),Stroke=SocialBrush("#607A94"),StrokeThickness=1 });
        if(photo is null)view.Children.Add(new LauncherIcon { Kind=IconKind.Person,Width=size*.58,Height=size*.58,HorizontalAlignment=HorizontalAlignment.Center,VerticalAlignment=VerticalAlignment.Center,Foreground=SocialBrush("#CCD7E4") });
        if(status&&!deleted)
        {
            var contact=_socialPlayers.FirstOrDefault(p=>p.Id==player)??(_adminViewedPlayer?.Id==player?_adminViewedPlayer:null)
                ??(_activityViewedPlayer?.Id==player?_activityViewedPlayer:null);
            var presence=contact is {Available:true}?contact.Presence:"offline";
            view.Children.Add(new Ellipse { Width=size>=60?20:16,Height=size>=60?20:16,HorizontalAlignment=HorizontalAlignment.Right,VerticalAlignment=VerticalAlignment.Bottom,
                Fill=SocialBrush(presence=="playing"?"#5CE5A1":presence=="online"?"#72ACFF":"#718095"),Stroke=SocialBrush("#11243B"),StrokeThickness=2.5,ToolTip=SocialStatusName(presence) });
        }
        return view;
    }
    private string SocialStatusName(string status)=> status=="playing"?T("Играет", "Playing"):status=="online"?T("В сети", "Online"):T("Не в сети", "Offline");

    private async Task PublishSocialPresenceAsync(Guid owner)
    {
        if(ActivityStore.IsSmokeTest || DateTimeOffset.UtcNow<_socialPresenceNext)return;
        var playing=IsGameRunning();
        var directory=_game?.Directory;
        InstallState? state=null;
        var versions=new SocialVersions(SelfUpdater.CurrentVersion.ToString());
        try { if(directory is not null) (state,versions)=await Task.Run(()=>
        {
            var appliedState=new ModuleInstaller(directory).LoadState();
            ChannelManifest? installed=null;
            try { if(appliedState.ReleaseId is { Length:64 } release && appliedState.AppliedSettings is { } selection)
                installed=_feedClient.LoadArchived(release,selection.Channel); } catch { }
            return (appliedState,SocialVersions.Installed(appliedState,installed,SelfUpdater.CurrentVersion.ToString()));
        }); }
        catch { /* Unknown is more accurate than publishing unapplied UI settings. */ }
        if(_account.UserId!=owner.ToString())return;
        var shareActivity=_settings.ShareGameActivity;
        var activity=playing && shareActivity && _account.CanTryGameActivity ? await Task.Run(()=>_gameActivityReader.Read(directory,state)) : null;
        if(_account.UserId!=owner.ToString()||_accountLifetime.IsCancellationRequested)return;
        var values=new Dictionary<string,bool>();
        var settings=state?.AppliedSettings is { } applied ? EffectiveSettings.ForChannel(applied) : null;
        if(settings is not null) values=FriendConfiguration.Components(settings);
        await _account.PublishConfigurationPresenceAsync(playing,settings?.Channel is "stable" or "beta" ? settings.Channel : "unknown",values,
            settings is not null ? FriendConfiguration.Create(settings) : null,_accountLifetime.Token,versions,activity);
        _socialPresenceNext=DateTimeOffset.UtcNow.AddSeconds(8);
    }
    private void PruneSocialProfiles()
    {
        foreach(var id in _socialAvatars.Keys.Where(id=>!_socialPlayers.Any(p=>p.Id==id && p.Relation=="friend" && p.AvatarRevision==_socialAvatars[id].revision)).ToArray())
        { _socialAvatars.Remove(id);_socialAvatarGeneration++; }
        if(_socialDetailsPeer is Guid peer)
        {
            var player=SocialDetailsPlayer();
            if(player is null)CloseSocialDetails();
            else if(SocialDetailsOverlay.Visibility==Visibility.Visible)RenderSocialDetails(player);
        }
    }
    private async Task RefreshSocialProfilesAsync(Guid owner)
    {
        PruneSocialProfiles();
        // Load at most one changed avatar per poll. No signed URLs, disk cache or public bucket.
        var player=_socialPlayers.FirstOrDefault(p=>p.Relation=="friend" && !p.Deleted && p.AvatarRevision is not null && !_socialAvatars.ContainsKey(p.Id));
        if(player is null)return;
        try
        {
            using var timeout=CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);timeout.CancelAfter(TimeSpan.FromSeconds(10));
            var jpeg=await _account.GetFriendAvatarAsync(player.Id,timeout.Token);
            if(_account.UserId!=owner.ToString() || !_socialPlayers.Any(p=>p.Id==player.Id && p.Relation=="friend" && p.AvatarRevision==player.AvatarRevision))return;
            var image=jpeg is null?null:new ImageBrush(AccountAvatarImage.Decode(jpeg,normalized:true)){Stretch=Stretch.UniformToFill};image?.Freeze();
            _socialAvatars[player.Id]=(player.AvatarRevision,image);_socialAvatarGeneration++;
            RenderSocialRows();RenderSocialMessages();
            if(_socialDetailsPeer==player.Id)RenderSocialDetails(player);
        }
        catch(AccountException e) when(e.Code is not ("session_expired" or "session_replaced" or "unauthorized")) { }
        catch(OperationCanceledException) when(!_accountLifetime.IsCancellationRequested) { }
    }
}
