using System.Net.Http;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed partial class AccountService
{
    public Task ChangeDisplayNameAsync(string name,CancellationToken ct=default)
    {
        ValidateDisplayName(name);
        return WithAccountAsync(async()=>{
            EnsureAccountEditable();
            using var result=await RequestAsync(HttpMethod.Post,"rpc/paw_change_display_name",new{candidate=name},_session!.AccessToken,ct,database:true);
            var status=await ResolveRestrictionAsync(Text(result.RootElement,"status"),ct);
            if(status is "account_banned" or "account_deletion_pending")throw new AccountException(status);
            if(status is not ("ok" or "unchanged")){
                if(status=="display_name_cooldown")await LoadProfileAsync(ct);
                throw new AccountException(status is "invalid_display_name" or "display_name_cooldown" or "session_expired" or "session_replaced" or "profile_missing"?status:"invalid_response");
            }
            await LoadProfileAsync(ct);
        },ct);
    }
    public async Task ChangeNicknameAsync(string nickname, CancellationToken cancellationToken = default)
    {
        ValidateNickname(nickname);
        nickname=NormalizeUsername(nickname);
        await WithAccountAsync(async () =>
        {
            EnsureAccountEditable();
            using var result = await RequestAsync(HttpMethod.Post, "rpc/paw_change_nickname", new { candidate = nickname }, _session!.AccessToken, cancellationToken, database: true).ConfigureAwait(false);
            var status = await ResolveRestrictionAsync(Text(result.RootElement, "status"),cancellationToken);
            if(status is "account_banned" or "account_deletion_pending")throw new AccountException(status);
            if (status is not ("ok" or "unchanged"))
            {
                if (status == "nickname_cooldown") await LoadProfileAsync(cancellationToken).ConfigureAwait(false);
                throw new AccountException(status is "session_replaced" or "session_expired" or "nickname_cooldown" or "nickname_taken" or "invalid_nickname" or "profile_missing" ? status : "invalid_response");
            }
            await LoadProfileAsync(cancellationToken).ConfigureAwait(false);
        }, cancellationToken).ConfigureAwait(false);
    }

    public async Task ChangeEmailAsync(string newEmail, string currentPassword, CancellationToken cancellationToken = default)
    {
        newEmail = ValidateEmail(newEmail);
        ValidateCurrentPassword(currentPassword);
        await WithAccountAsync(async () =>
        {
            if (string.Equals(_session!.Email, newEmail, StringComparison.OrdinalIgnoreCase)) throw new AccountException("same_email");
            await AccountActionAsync(new { action = "email", email = newEmail, current_password = currentPassword }, cancellationToken).ConfigureAwait(false);
            // Do not pretend the pending address is already confirmed. /user remains the source of truth.
        }, cancellationToken).ConfigureAwait(false);
    }

    public async Task ChangePasswordAsync(string currentPassword, string newPassword, string confirmation, CancellationToken cancellationToken = default)
    {
        ValidateNewPassword(newPassword, confirmation); ValidateCurrentPassword(currentPassword);
        if (currentPassword == newPassword) throw new AccountException("same_password");
        await WithAccountAsync(async () =>
        {
            await AccountActionAsync(new { action = "password", password = newPassword, current_password = currentPassword }, cancellationToken, updateSession: true).ConfigureAwait(false);
        }, cancellationToken).ConfigureAwait(false);
    }

    private static void ValidateCurrentPassword(string value)
    { if (value.Length is < 1 or > 128) throw new AccountException("current_password_required"); }

    public static void ValidateNewPassword(string password, string confirmation)
    {
        if (password.Length is < 6 or > 128) throw new AccountException("weak_password");
        if (password != confirmation) throw new AccountException("password_mismatch");
    }

    private async Task ReauthenticateAsync(string password, CancellationToken cancellationToken)
    {
        using var response = await RequestAsync(HttpMethod.Post, "token?grant_type=password", new { email = _session!.Email, password }, null, cancellationToken).ConfigureAwait(false);
        var fresh = ParseSession(response.RootElement);
        if (fresh.UserId != _session.UserId) throw new AccountException("session_expired");
        fresh.Nickname = _session.Nickname; fresh.CreatedAt = _session.CreatedAt; fresh.NicknameChangedAt = _session.NicknameChangedAt;
        cancellationToken.ThrowIfCancellationRequested();
        SaveSession(fresh);
    }

    private async Task WithAccountAsync(Func<Task> action, CancellationToken cancellationToken)
    {
        var expectedId = UserId;
        await RestoreAsync(cancellationToken, reuseRecent: true).ConfigureAwait(false);
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            using var fileLock = await _store.LockAsync(cancellationToken).ConfigureAwait(false);
            ReadOwnedSession();
            if (_session is null || _session.UserId != expectedId || State != AccountState.SignedIn) throw new AccountException("session_expired");
            try { await action().ConfigureAwait(false); }
            catch (AccountException error) when (error.Code is "session_expired" or "session_replaced" or "unauthorized")
            { ClearOwnedSession(); SetGuest(); throw; }
        }
        finally { _gate.Release(); }
    }

    public async Task RequestRecoveryAsync(string email, CancellationToken cancellationToken = default)
    {
        email = ValidateEmail(email);
        // Deliberately no account-existence response: the UI always shows the same neutral message.
        using var result = await RequestAsync(HttpMethod.Post, "recover", new { email }, null, cancellationToken).ConfigureAwait(false);
    }

    public static object RecoveryProof(string email, string proof)
    {
        email = ValidateEmail(email);
        var token = RecoveryCode.Normalize(proof);
        if (!RecoveryCode.IsComplete(token)) throw new AccountException("invalid_recovery_code");
        // Codes remain strings (leading zeroes matter) and are verified only by Supabase Auth.
        return new { type = "recovery", email, token };
    }

    public async Task<bool> ResetPasswordAsync(string email, string proof, string newPassword, string confirmation, CancellationToken cancellationToken = default)
    {
        email = ValidateEmail(email); ValidateNewPassword(newPassword, confirmation);
        var body = RecoveryProof(email, proof);
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        AccountSession? recovery = null;
        try
        {
            if (_session is not null) throw new AccountException("sign_out_first");
            using var verified = await RequestAsync(HttpMethod.Post, "verify", body, null, cancellationToken).ConfigureAwait(false);
            recovery = ParseSession(verified.RootElement);
            if (!string.Equals(recovery.Email, email, StringComparison.OrdinalIgnoreCase)) throw new AccountException("invalid_recovery");
            using var user = await RequestAsync(HttpMethod.Put, "user", new { password = newPassword }, recovery.AccessToken, cancellationToken).ConfigureAwait(false);
            ReadUser(user.RootElement, recovery, recovery.UserId);
            try
            {
                using var logout = await RequestAsync(HttpMethod.Post, "logout?scope=global", null, recovery.AccessToken, cancellationToken).ConfigureAwait(false);
                recovery = null; return true;
            }
            catch (AccountException) { return false; } // Password changed, but do not claim every session was revoked.
        }
        finally
        {
            if (recovery is not null)
            {
                try { using var logout = await RequestAsync(HttpMethod.Post, "logout?scope=local", null, recovery.AccessToken, cancellationToken).ConfigureAwait(false); }
                catch (Exception error) when (error is AccountException or OperationCanceledException) { }
            }
            // A recovery token never enters ordinary account state or persistent storage.
            _gate.Release();
        }
    }
}
