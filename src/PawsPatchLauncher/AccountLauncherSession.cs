using System.Net.Http;

namespace PawsPatchLauncher;

public sealed partial class AccountService
{
    // Per running service/process, never copied from the persisted session.
    private readonly Guid _launcherId = Guid.NewGuid();
    private bool _launcherClaimed;
    private bool _restoreAttempted;

    private async Task LauncherRequestAsync(string action, CancellationToken ct, Guid? previous = null)
    {
        using var result = await RequestAsync(HttpMethod.Post, "rpc/paw_launcher_session", new { action, previous },
            _session!.AccessToken, ct, database: true).ConfigureAwait(false);
        var status = Text(result.RootElement, "status");
        if (status != "ok") throw new AccountException(status is "session_replaced" or "session_expired" or "account_busy" ? status : "invalid_response");
    }

    private async Task ClaimLauncherAsync(string action, CancellationToken ct)
    {
        var prior = _session!.LauncherId;
        await LauncherRequestAsync(action, ct, prior == Guid.Empty ? null : prior).ConfigureAwait(false);
        _session.LauncherId = _launcherId;
        if (_session.LoginId == Guid.Empty) _session.LoginId = Guid.NewGuid();
        _launcherClaimed = true;
        SaveSession(_session);
    }

    private bool SameStoredLogin(AccountSession? stored) => stored is not null && _session is not null
        && stored.UserId == _session.UserId && stored.LoginId == _session.LoginId && stored.LauncherId == _session.LauncherId;

    // Must hold the storage lock. A displaced process must never delete the winner's credentials.
    private void ClearOwnedSession()
    {
        if (_remember && SameStoredLogin(_store.Read())) _store.Clear();
    }

    private void ReadOwnedSession()
    {
        if (!_remember) return;
        var stored = _store.Read();
        if (_session is null)
        {
            if (!_restoreAttempted) { _session = stored; _restoreAttempted = true; }
            return;
        }
        if (!SameStoredLogin(stored))
        {
            var code = stored?.UserId != _session.UserId ? "session_expired" : "session_replaced";
            SetGuest();
            throw new AccountException(code);
        }
        _session = stored;
    }

    private async Task EstablishLoginAsync(AccountSession session, bool remember, CancellationToken ct)
    {
        _session = session;
        _remember = remember;
        _restoreAttempted = true;
        _launcherClaimed = false;
        try
        {
            await ClaimLauncherAsync("claim", ct).ConfigureAwait(false);
            if (!remember) _store.Clear();
        }
        catch { SetGuest(); throw; }
        try { await LoadProfileAsync(ct).ConfigureAwait(false); _sessionVerifiedAt = _clock(); }
        catch { State = AccountState.Offline; throw; }
    }
}
