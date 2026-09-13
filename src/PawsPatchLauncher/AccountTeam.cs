using System.Net.Http;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed partial class AccountService
{
    private bool _teamProfileSupported = true;
    private const string ProfileColumns = "id,nickname,display_name,display_name_changed_at,created_at,nickname_changed_at,email_changed_at,password_changed_at,avatar_changed_at,deletion_pending,admin_level,protected_admin,banned_at,ban_until,ban_reason,deleted_at";

    private async Task<JsonDocument> ReadTeamProfileAsync(CancellationToken ct)
    {
        Task<JsonDocument> Read(bool team) => RequestAsync(HttpMethod.Get,
            "paw_profiles?select=" + ProfileColumns + (team ? ",paws_team" : "") + "&id=eq." + _session!.UserId,
            null, _session.AccessToken, ct, database: true);
        try { return await Read(_teamProfileSupported).ConfigureAwait(false); }
        catch (AccountException error) when (error.Code == "team_role_unavailable" && _teamProfileSupported)
        {
            // Older servers remain usable; absent membership never grants team access.
            _teamProfileSupported = false;
            return await Read(false).ConfigureAwait(false);
        }
    }
}
