using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly Dictionary<string,FriendVersionCatalog> _friendVersionCatalogs=[];
    private readonly HashSet<string> _friendVersionLoading=[];
    private readonly Dictionary<string,DateTimeOffset> _friendVersionFailures=[];
    private Func<Task<string>>? _friendLauncherVersionOverride=null;

    private string LatestFriendLauncherVersion(string? candidate=null)
    {
        var version=SelfUpdater.CurrentVersion;
        foreach(var text in new[]{candidate,_launcherUpdates.Latest?.Version})
            if(SocialVersions.TryLauncher(text,out var parsed) && parsed>version)version=parsed;
        return version.ToString();
    }

    private FriendVersionCatalog ObserveFriendVersionCatalog(ChannelManifest channel,string launcher)
    {
        var catalog=FriendVersionCatalog.Create(channel,LatestFriendLauncherVersion(launcher));
        _friendVersionCatalogs[channel.Channel]=catalog;_friendVersionFailures.Remove(channel.Channel);
        return catalog;
    }

    private PeerVersionStatus FriendVersionStatus(SocialPlayer player)
    {
        if(player.Versions is null)return PeerVersionStatus.Unknown;
        if(SocialVersions.TryLauncher(player.Versions.Launcher,out var installed)
            && SocialVersions.TryLauncher(LatestFriendLauncherVersion(),out var latest) && installed<latest)
        {
            var known=_friendVersionCatalogs.GetValueOrDefault(player.Channel);
            return known is null ? PeerVersionStatus.OldLauncher : PeerVersionPolicy.Check(player,known with {Launcher=latest.ToString()});
        }
        if(_friendVersionFailures.TryGetValue(player.Channel,out var failed) && failed>DateTimeOffset.UtcNow.AddSeconds(-30))return PeerVersionStatus.Unavailable;
        var catalog=_friendVersionCatalogs.GetValueOrDefault(player.Channel);
        if(catalog is not null && catalog.CheckedAt<DateTimeOffset.UtcNow.AddSeconds(-30))catalog=null;
        return PeerVersionPolicy.Check(player,catalog is null?null:catalog with {Launcher=LatestFriendLauncherVersion(catalog.Launcher)});
    }

    private string FriendVersionWarning(PeerVersionStatus status) => status switch
    {
        PeerVersionStatus.OldLauncher => T("У игрока устарел лаунчер. Копирование недоступно, пока он не обновит лаунчер.", "The player's launcher is outdated. Copying is unavailable until they update it."),
        PeerVersionStatus.OldPatch => T("У игрока неактуальный выпуск мода или патча. Копирование недоступно, пока он не обновит его и не применит настройки.", "The player's mod or patch release is out of date. Copying is unavailable until they update it and apply their settings."),
        PeerVersionStatus.OldLauncherAndPatch => T("У игрока устарели лаунчер и патч. Копирование недоступно, пока он не обновит их и не применит настройки.", "The player's launcher and patch are outdated. Copying is unavailable until they update both and apply their settings."),
        PeerVersionStatus.Unknown => T("Игрок не передаёт сведения о версиях. Копирование недоступно: ему нужно обновить лаунчер и применить настройки патча.", "The player's versions are unavailable. Copying is disabled: they need to update the launcher and apply their patch settings."),
        PeerVersionStatus.Checking => T("Проверяем версии лаунчера и патча игрока…", "Checking the player's launcher and patch versions…"),
        PeerVersionStatus.Unavailable => T("Не удалось проверить актуальность версий. Копирование временно недоступно. Повторно откройте карточку чуть позже.", "Could not check the latest versions. Copying is temporarily unavailable. Reopen this card shortly."),
        _ => ""
    };

    private void RequireCurrentPeerVersions(SocialPlayer player,FriendVersionCatalog catalog)
    {
        var status=PeerVersionPolicy.Check(player,catalog with {Launcher=LatestFriendLauncherVersion(catalog.Launcher)});
        if(status!=PeerVersionStatus.Current)throw new FriendCopyException(()=>FriendVersionWarning(status));
    }

    private async Task<string> ReadLatestFriendLauncherAsync(CancellationToken token)
    {
        if(_friendLauncherVersionOverride is not null)return await _friendLauncherVersionOverride().WaitAsync(token);
        var release=await _feedClient.GetLauncherUpdateAsync(token,TimeSpan.FromSeconds(3));
        _launcherUpdates.Observe(release);
        return LatestFriendLauncherVersion(release?.Version);
    }

    private async Task RefreshPeerVersionsAsync(SocialPlayer player)
    {
        if(ActivityStore.IsSmokeTest || player.Versions is null || player.Channel is not ("stable" or "beta")
            || _friendVersionLoading.Contains(player.Channel))return;
        if(_friendVersionCatalogs.TryGetValue(player.Channel,out var existing) && existing.CheckedAt>DateTimeOffset.UtcNow.AddSeconds(-30))return;
        if(_friendVersionFailures.TryGetValue(player.Channel,out var failed) && failed>DateTimeOffset.UtcNow.AddSeconds(-30))return;
        _friendVersionLoading.Add(player.Channel);
        var owner=_account.UserId;
        try
        {
            using var timeout=CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);timeout.CancelAfter(TimeSpan.FromSeconds(12));
            var feedTask=_feedClient.GetChannelAsync(player.Channel,timeout.Token);
            var launcherTask=ReadLatestFriendLauncherAsync(timeout.Token);
            await Task.WhenAll(feedTask,launcherTask);
            var channel=await feedTask ?? throw new InvalidDataException("Missing version catalog.");
            ObserveFriendVersionCatalog(_feedClient.KnownChannel(player.Channel)??channel,await launcherTask);
        }
        catch { _friendVersionFailures[player.Channel]=DateTimeOffset.UtcNow; }
        finally
        {
            _friendVersionLoading.Remove(player.Channel);
            if(_account.UserId==owner)
            {
                RefreshSocialCopyAvailability();RefreshOfferActions();
            }
        }
    }
}
