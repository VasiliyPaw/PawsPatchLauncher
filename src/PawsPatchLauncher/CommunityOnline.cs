using System.Net.Http;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed record CommunityOnlinePlayer(Guid Id, string Nickname, string DisplayName, DateTimeOffset? AvatarRevision, string Presence = "online");
public sealed record CommunityOnlinePage(int Page, int Total, IReadOnlyList<CommunityOnlinePlayer> Players)
{
    public const int PageSize = 10;
    public int PageCount => Math.Max(1, (int)(((long)Total + PageSize - 1) / PageSize));
}

public sealed partial class AccountService
{
    public async Task<CommunityOnlinePage> ReadCommunityPlayersAsync(int page, CancellationToken ct = default)
    {
        if (page < 0) throw new AccountException("invalid_page");
        using var response = await RequestAsync(HttpMethod.Post, "rpc/paw_community_players", new { page_index = page }, null, ct, database: true).ConfigureAwait(false);
        try
        {
            var root = response.RootElement;
            if (Text(root, "status") != "ok") throw new AccountException("invalid_response");
            var index = root.GetProperty("page").GetInt32();
            var total = root.GetProperty("total").GetInt32();
            var list = root.GetProperty("players");
            if (index < 0 || total < 0 || index != Math.Min(page, Math.Max(0, (int)(((long)total - 1) / CommunityOnlinePage.PageSize)))
                || list.ValueKind != JsonValueKind.Array || list.GetArrayLength() != Math.Min(CommunityOnlinePage.PageSize, Math.Max(0L, total - (long)index * CommunityOnlinePage.PageSize)))
                throw new AccountException("invalid_response");
            var players = list.EnumerateArray().Select(p =>
            {
                var player = new CommunityOnlinePlayer(p.GetProperty("id").GetGuid(), p.GetProperty("nickname").GetString()!,
                    p.GetProperty("display_name").GetString()!, p.TryGetProperty("avatar_revision", out var revision) && revision.ValueKind != JsonValueKind.Null ? revision.GetDateTimeOffset() : null,
                    p.TryGetProperty("presence", out var presence) ? presence.GetString()! : "online");
                if (player.Id == Guid.Empty || player.Nickname is null || player.DisplayName is null || player.Presence is not ("online" or "playing")) throw new AccountException("invalid_response");
                ValidateNickname(player.Nickname); ValidateDisplayName(player.DisplayName);
                return player;
            }).ToArray();
            if (players.Select(p => p.Id).Distinct().Count() != players.Length) throw new AccountException("invalid_response");
            return new(index, total, players);
        }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or AccountException)
        { throw new AccountException("invalid_response"); }
    }
}
