using System.Text.Json;
using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private SocialPlayer? _ownPlayerCard;
    private GameActivityDetails? _ownActivity;
    private bool _ownCardOpening;
    private SocialPlayer CreateOwnPlayerCard(Guid id, InstallState? state, SocialVersions versions, bool playing)
    {
        var applied = state?.AppliedSettings is { } settings ? EffectiveSettings.ForChannel(settings) : null;
        return new SocialPlayer(id, _account.Nickname, "self", Presence: playing ? "playing" : "online",
            LastSeen: DateTimeOffset.UtcNow, PlayingSince: playing ? _ownPlayerCard?.PlayingSince : null,
            Channel: applied?.Channel ?? "unknown", Components: JsonSerializer.Serialize(applied is null ? new Dictionary<string,bool>() : FriendConfiguration.Components(applied)),
            AvatarRevision: _account.AvatarChangedAt, Configuration: applied is null ? null : FriendConfiguration.Create(applied),
            DisplayName: _account.DisplayName, AdminLevel: _account.AdminLevel, CreatedAt: _account.CreatedAt,
            IsFriend: false, PawsTeam: _account.PawsTeam, Versions: versions, Activity: playing ? _ownActivity?.Activity.Summary() : null);
    }
    private async void OwnPlayerProfile_Click(object sender, RoutedEventArgs e) { e.Handled=true; await ShowOwnPlayerCardAsync(); }
    private async Task ShowOwnPlayerCardAsync()
    {
        if (_ownCardOpening || ConfirmationActive || AccountConnectionBlocked || _account.State!=AccountState.SignedIn || !Guid.TryParse(_account.UserId, out var owner)) return;
        _ownCardOpening=true;
        var generation=_socialDetailsGeneration;
        var directory=_game?.Directory; var playing=IsGameRunning();
        try
        {
            var result=await Task.Run(() =>
            {
                InstallState? state=null; ChannelManifest? installed=null;
                try
                {
                    if(directory is not null) state=new ModuleInstaller(directory).LoadState();
                    if(state?.ReleaseId is { Length:64 } release && state.AppliedSettings is { } selection) installed=_feedClient.LoadArchived(release,selection.Channel);
                }
                catch { /* Display unknown instead of unpublished settings. */ }
                return (state, versions:SocialVersions.Installed(state,installed,SelfUpdater.CurrentVersion.ToString()));
            });
            if(generation!=_socialDetailsGeneration || _account.UserId!=owner.ToString() || AccountConnectionBlocked || ConfirmationActive)return;
            _ownPlayerCard=CreateOwnPlayerCard(owner,result.state,result.versions,playing);
            CloseGameActivity();ShowSocialDetails(_ownPlayerCard);
        }
        finally { _ownCardOpening=false; }
    }
    private GameActivityDetails? OwnGameActivityDetails()
    {
        if(_ownActivity is not { } details || DateTimeOffset.UtcNow-details.ObservedAt>TimeSpan.FromSeconds(40) || !Guid.TryParse(_account.UserId,out var owner))return null;
        var profile=new GameParticipantProfile(owner,_account.Nickname,_account.DisplayName,_account.AvatarChangedAt);
        return details with { Activity=details.Activity with { Players=details.Activity.Players?.Select(p => p.Key==details.Activity.Self && !p.Bot ? p with { Profile=profile } : p).ToArray() } };
    }
}
