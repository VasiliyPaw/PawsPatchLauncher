using System.Windows;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private Guid? _publicProfilePeer;
    private int _publicProfileVersion;
    private bool _publicProfileRefreshing;
    private DispatcherTimer? _publicProfileTimer;
    private Func<Guid,CancellationToken,Task<SocialPlayer>>? _publicProfileReadOverride = null;

    private string PublicProfileError(string code) => code == "profile_blocked"
        ? T("Этот игрок заблокировал вас. Профиль недоступен.","This player has blocked you. Their profile is unavailable.")
        : code == "profile_hidden" ? T("Вы заблокировали этого игрока. Разблокируйте его, чтобы открыть профиль.","You blocked this player. Unblock them to view their profile.")
        : T("Не удалось открыть профиль. Проверьте подключение и повторите попытку.","Could not open the profile. Check your connection and try again.");

    private void ClearPublicProfile()
    {
        _publicProfileVersion++; _publicProfilePeer = null; _publicProfileTimer?.Stop();
    }

    private async Task OpenPublicProfileCardAsync(Guid target)
    {
        if (ConfirmationActive || AccountConnectionBlocked) return;
        var version = ++_publicProfileVersion; var owner = _account.UserId;
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);
            timeout.CancelAfter(TimeSpan.FromSeconds(10));
            var player = await (_publicProfileReadOverride?.Invoke(target,timeout.Token) ?? _account.GetPublicPlayerProfileAsync(target,timeout.Token));
            if (version != _publicProfileVersion || owner != _account.UserId || _accountLifetime.IsCancellationRequested) return;
            if (player.Id != target || player.Deleted) throw new AccountException("player_unavailable");
            // The server checked blocks before returning the full profile. A
            // cached chat/directory identity cannot bypass that check.
            ShowAuthorizedPublicProfile(player);
        }
        catch (Exception error) when (error is AccountException or OperationCanceledException or System.Net.Http.HttpRequestException)
        {
            if (version == _publicProfileVersion && owner == _account.UserId)
            {
                if (_socialDetailsPeer == target && error is AccountException { Code: "profile_blocked" or "profile_hidden" }) CloseSocialDetails();
                ShowToast(() => PublicProfileError(error is AccountException a ? a.Code : "network"),true);
            }
        }
    }

    private void ShowAuthorizedPublicProfile(SocialPlayer player)
    {
        _activityViewedPlayer = player; ShowSocialDetails(player); _publicProfilePeer = player.Id;
        _publicProfileTimer ??= new DispatcherTimer { Interval = TimeSpan.FromSeconds(15) };
        _publicProfileTimer.Stop(); _publicProfileTimer.Tick -= PublicProfileTimer_Tick; _publicProfileTimer.Tick += PublicProfileTimer_Tick;
        _publicProfileTimer.Start();
    }

    private async void PublicProfileTimer_Tick(object? sender, EventArgs e) => await RefreshPublicProfileAsync();

    private async Task RefreshPublicProfileAsync()
    {
        if (_publicProfilePeer is not Guid target || _publicProfileRefreshing || SocialDetailsOverlay.Visibility != Visibility.Visible
            || AccountConnectionBlocked || ConfirmationActive) return;
        var version = _publicProfileVersion; var owner = _account.UserId; _publicProfileRefreshing = true;
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token); timeout.CancelAfter(TimeSpan.FromSeconds(8));
            var player = await (_publicProfileReadOverride?.Invoke(target,timeout.Token) ?? _account.GetPublicPlayerProfileAsync(target,timeout.Token));
            if (version != _publicProfileVersion || owner != _account.UserId || player.Id != target) return;
            _activityViewedPlayer = player; RenderSocialDetails(SocialDetailsPlayer() ?? player);
        }
        catch (AccountException error) when (error.Code is "profile_blocked" or "profile_hidden" or "player_unavailable")
        {
            if (version == _publicProfileVersion && owner == _account.UserId)
            {
                _gameActivityCache.Remove(target); _gameParticipantAvatars.Remove(target); _socialAvatars.Remove(target);
                CloseSocialDetails(); ShowToast(() => PublicProfileError(error.Code),true);
            }
        }
        catch (Exception error) when (error is AccountException or OperationCanceledException or System.Net.Http.HttpRequestException) { }
        finally { _publicProfileRefreshing = false; }
    }
}
