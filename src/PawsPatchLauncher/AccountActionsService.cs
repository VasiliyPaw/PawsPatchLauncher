using System.Net.Http;
namespace PawsPatchLauncher;
public sealed partial class AccountService
{
    private async Task AccountActionAsync(object body, CancellationToken cancellationToken, bool updateSession = false)
    {
        EnsureAccountEditable();
        // Refresh server timestamps even after a cooldown/rejected/uncertain response.
        // A metadata refresh failure after a successful mutation must not claim it failed.
        try
        {
            using var result = await RequestAsync(HttpMethod.Post, "account-actions", body, _session!.AccessToken, cancellationToken, portal: true).ConfigureAwait(false);
            if (updateSession)
            {
                if (!result.RootElement.TryGetProperty("session", out var data)) throw new AccountException("outcome_unknown");
                var fresh = ParseSession(data);
                if (fresh.UserId != _session.UserId) throw new AccountException("invalid_response");
                fresh.Nickname = _session.Nickname; fresh.CreatedAt = _session.CreatedAt;
                fresh.NicknameChangedAt = _session.NicknameChangedAt; fresh.EmailChangedAt = _session.EmailChangedAt;
                fresh.PasswordChangedAt = _session.PasswordChangedAt; fresh.AvatarChangedAt = _session.AvatarChangedAt;
                fresh.DeletionPending = _session.DeletionPending;
                fresh.LauncherId = _session.LauncherId; fresh.LoginId = _session.LoginId;
                SaveSession(fresh); // Respects the original Remember me selection; no password is persisted.
            }
        }
        finally
        {
            try { await LoadProfileAsync(cancellationToken).ConfigureAwait(false); }
            catch (Exception error) when (error is AccountException or OperationCanceledException) { }
        }
    }

    public Task<byte[]?> GetAvatarAsync(CancellationToken cancellationToken = default) => ReadAvatarAsync(null,cancellationToken);
    public Task<byte[]?> GetFriendAvatarAsync(Guid target,CancellationToken cancellationToken = default) => ReadAvatarAsync(target,cancellationToken);
    private async Task<byte[]?> ReadAvatarAsync(Guid? target,CancellationToken cancellationToken)
    {
        byte[]? bytes = null;
        await WithAccountAsync(async () => {
            using var result = await RequestAsync(HttpMethod.Post, "account-actions", new { action = target is null ? "avatar_get" : "friend_avatar_get", target }, _session!.AccessToken, cancellationToken, portal: true).ConfigureAwait(false);
            var encoded = Text(result.RootElement, "avatar");
            if (encoded.Length == 0) return;
            if (encoded.Length > 273068) throw new AccountException("invalid_avatar");
            try { bytes = Convert.FromBase64String(encoded); }
            catch (FormatException) { throw new AccountException("invalid_avatar"); }
            if (bytes.Length > 204800) throw new AccountException("avatar_too_large");
        }, cancellationToken).ConfigureAwait(false);
        return bytes;
    }

    public Task SetAvatarAsync(byte[] jpeg, CancellationToken cancellationToken = default)
    {
        if (jpeg.Length is < 32 or > 204800) throw new AccountException("invalid_avatar");
        var encoded = Convert.ToBase64String(jpeg); // Snapshot before awaiting: caller cannot alter an in-flight upload.
        return WithAccountAsync(() => AccountActionAsync(new { action = "avatar_set", avatar = encoded }, cancellationToken), cancellationToken);
    }
    public Task RemoveAvatarAsync(CancellationToken cancellationToken = default)
        => WithAccountAsync(() => AccountActionAsync(new { action = "avatar_remove" }, cancellationToken), cancellationToken);

    public async Task DeleteAccountAsync(string currentPassword, CancellationToken cancellationToken = default)
    {
        ValidateCurrentPassword(currentPassword);
        await WithAccountAsync(async () => {
            using var result = await RequestAsync(HttpMethod.Post, "account-actions",
                new { action = "delete", current_password = currentPassword, confirm = "DELETE_MY_ACCOUNT" },
                _session!.AccessToken, cancellationToken, portal: true).ConfigureAwait(false);
            // Only after confirmed server deletion. Never remove game files or saves.
            try { _store.Clear(); } finally { SetGuest(); }
        }, cancellationToken).ConfigureAwait(false);
    }
}
