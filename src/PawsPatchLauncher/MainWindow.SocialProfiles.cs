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
    private void ClearSocialProfiles()
    {
        _socialAvatars.Clear(); _socialAvatarGeneration++; _socialPresenceNext=default;_socialListReceived=default;
        CloseSocialDetails();
    }
    private Grid SocialAvatar(Guid player,double size,bool status)
    {
        var own=player.ToString()==_account.UserId;
        var photo=own && _accountAvatarOwner==_account.UserId ? _accountAvatar : _socialAvatars.GetValueOrDefault(player).image;
        var deleted=_socialPlayers.FirstOrDefault(p=>p.Id==player)?.Deleted==true;
        if(deleted)photo=null;
        var view=new Grid { Width=size,Height=size,Background=Brushes.Transparent };
        if(!own && !deleted && _socialPlayers.Any(p=>p.Id==player&&p.Relation=="friend"))
        {
            view.Cursor=System.Windows.Input.Cursors.Hand;
            view.MouseLeftButtonUp+=(_,e)=>{e.Handled=true;var friend=_socialPlayers.FirstOrDefault(p=>p.Id==player&&p.Relation=="friend");if(friend is not null)ShowSocialDetails(friend);};
        }
        view.Children.Add(new Ellipse { Fill=photo ?? (Brush)SocialBrush("#334C68"),Stroke=SocialBrush("#607A94"),StrokeThickness=1 });
        if(photo is null)view.Children.Add(new LauncherIcon { Kind=IconKind.Person,Width=size*.58,Height=size*.58,HorizontalAlignment=HorizontalAlignment.Center,VerticalAlignment=VerticalAlignment.Center,Foreground=SocialBrush("#CCD7E4") });
        if(status&&!deleted)
        {
            var contact=_socialPlayers.FirstOrDefault(p=>p.Id==player)??(_adminViewedPlayer?.Id==player?_adminViewedPlayer:null);
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
        try { if(directory is not null)state=await Task.Run(()=>new ModuleInstaller(directory).LoadState()); }
        catch { /* Unknown is more accurate than publishing unapplied UI settings. */ }
        if(_account.UserId!=owner.ToString())return;
        var values=new Dictionary<string,bool>();
        var settings=state?.AppliedSettings;
        if(settings is not null)
        {
            values["core"]=state!.Modules.TryGetValue("pawpatch-core",out var core)&&core.Enabled;
            values["russian"]=settings.RussianLocalization; values["colors"]=settings.CustomPlayerColors;
            values["desync"]=settings.DesyncMode!="official"; values["hostility"]=settings.IndependentHostility;
            values["roaming"]=settings.RoamingSpawnMode!="standard"; values["additional_roaming"]=settings.AdditionalRoamingCompanies;
            values["siege"]=settings.SiegeBalance; values["powers_shards"]=settings.DisablePowersAndShards; values["large_maps"]=settings.LargeMapSizes;
        }
        await _account.PublishConfigurationPresenceAsync(playing,settings?.Channel is "stable" or "beta" ? settings.Channel : "unknown",values,
            settings is not null && values.GetValueOrDefault("core") ? ConfigurationCode.Create(settings) : null,_accountLifetime.Token);
        _socialPresenceNext=DateTimeOffset.UtcNow.AddSeconds(8);
    }
    private void PruneSocialProfiles()
    {
        foreach(var id in _socialAvatars.Keys.Where(id=>!_socialPlayers.Any(p=>p.Id==id && p.Relation=="friend" && p.AvatarRevision==_socialAvatars[id].revision)).ToArray())
        { _socialAvatars.Remove(id);_socialAvatarGeneration++; }
        if(_socialDetailsPeer is Guid peer)
        {
            var player=_socialPlayers.FirstOrDefault(p=>p.Id==peer && p.Relation=="friend")??(_account.AdminLevel>0&&_adminViewedPlayer?.Id==peer?_adminViewedPlayer:null);
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
        }
        catch(AccountException e) when(e.Code is not ("session_expired" or "session_replaced" or "unauthorized")) { }
        catch(OperationCanceledException) when(!_accountLifetime.IsCancellationRequested) { }
    }
}
