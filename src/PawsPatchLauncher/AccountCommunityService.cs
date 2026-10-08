using System.Net.Http;

namespace PawsPatchLauncher;

public sealed partial class AccountService
{
    public async Task<int> ReadCommunityOnlineAsync(CancellationToken ct = default)
    {
        using var response = await RequestAsync(HttpMethod.Post, "rpc/paw_community_online", new { }, null, ct, database: true).ConfigureAwait(false);
        var root = response.RootElement;
        if (Text(root, "status") != "ok" || !root.TryGetProperty("online", out var value) || !value.TryGetInt32(out var count) || count < 0)
            throw new AccountException("invalid_response");
        return count;
    }

    public async Task<byte[]?> ReadCommunityAvatarAsync(Guid author, DateTimeOffset revision, CancellationToken ct = default)
    {
        if (author == Guid.Empty) throw new AccountException("invalid_avatar");
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(10));
        using var request = new HttpRequestMessage(HttpMethod.Get, ProjectUrl + "/storage/v1/object/authenticated/paw-avatars/" + author.ToString("D") + "/avatar.jpg?v=" + revision.ToUnixTimeMilliseconds());
        request.Headers.Add("apikey", PublishableKey);
        using var response = await _http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token).ConfigureAwait(false);
        if (response.StatusCode is System.Net.HttpStatusCode.NotFound or System.Net.HttpStatusCode.BadRequest or System.Net.HttpStatusCode.Forbidden) return null;
        if (!response.IsSuccessStatusCode) throw new AccountException("network");
        if (response.Content.Headers.ContentLength > 204800) throw new AccountException("invalid_avatar");
        await using var source = await response.Content.ReadAsStreamAsync(timeout.Token).ConfigureAwait(false);
        using var output = new MemoryStream();
        var buffer = new byte[8192];
        int count;
        while ((count = await source.ReadAsync(buffer, timeout.Token).ConfigureAwait(false)) != 0)
        {
            if (output.Length + count > 204800) throw new AccountException("invalid_avatar");
            output.Write(buffer, 0, count);
        }
        return output.ToArray();
    }

    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, (string Revision, CommunityPage Page)> _communityCache = new();
    public async Task<IReadOnlyList<CommunityMessage>> ReadCommunityAsync(string channel, CancellationToken ct = default)
        => (await ReadCommunityPageAsync(channel, ct: ct).ConfigureAwait(false)).Messages;

    public async Task<CommunityPage> ReadCommunityPageAsync(string channel, long? before = null, CancellationToken ct = default)
    {
        // The same intentionally public endpoint is used by guests and members;
        // never expose account tokens to a separate chat service.
        CommunityChat.ValidateChannel(channel);
        if (before <= 0) throw new AccountException("invalid_message");
        var cached = _communityCache.GetValueOrDefault(channel);
        using var response = await RequestAsync(HttpMethod.Post, "rpc/paw_community_read", new { channel, known_revision = before is null ? cached.Revision : null, before_ordinal = before }, null, ct, database: true).ConfigureAwait(false);
        var root = response.RootElement;
        var revision = Text(root, "revision");
        if (Text(root, "status") != "ok" || revision.Length != 32 || !revision.All(Uri.IsHexDigit)) throw new AccountException("invalid_response");
        if (root.TryGetProperty("unchanged", out var unchanged) && unchanged.ValueKind == System.Text.Json.JsonValueKind.True)
        {
            if (before is not null || cached.Page is null || cached.Revision != revision) throw new AccountException("invalid_response");
            return cached.Page;
        }
        if (!root.TryGetProperty("messages", out var list)
            || list.ValueKind != System.Text.Json.JsonValueKind.Array || list.GetArrayLength() > 100)
            throw new AccountException("invalid_response");
        var messages = list.EnumerateArray().Select(CommunityChat.Read).ToArray();
        if (messages.Zip(messages.Skip(1)).Any(pair => pair.First.Ordinal >= pair.Second.Ordinal)
            || messages.Select(m => m.Id).Distinct().Count() != messages.Length
            || before is not null && messages.Any(m => m.Ordinal >= before)) throw new AccountException("invalid_response");
        if (!root.TryGetProperty("more", out var more) || more.ValueKind is not (System.Text.Json.JsonValueKind.True or System.Text.Json.JsonValueKind.False)
            || !root.TryGetProperty("trimmed", out var trimmed) || trimmed.ValueKind is not (System.Text.Json.JsonValueKind.True or System.Text.Json.JsonValueKind.False)
            || !root.TryGetProperty("history_revision", out var historyRevision) || !historyRevision.TryGetInt64(out var generation) || generation < 0
            || more.GetBoolean() && messages.Length != CommunityHistory.PageSize) throw new AccountException("invalid_response");
        var page = new CommunityPage(messages, more.GetBoolean(), generation, trimmed.GetBoolean());
        if (before is null) _communityCache[channel] = (revision, page);
        return page;
    }

    public Task<CommunityMessage> SendCommunityAsync(string channel, Guid id, string body, CancellationToken ct = default)
    {
        CommunityChat.ValidateChannel(channel); CommunityChat.Validate(body);
        if (id == Guid.Empty || !Guid.TryParse(UserId, out var owner)) throw new AccountException("session_expired");
        return SocialRpcAsync("paw_community_send", new { channel, message_id = id, body }, root =>
        {
            var message = CommunityChat.Read(root.GetProperty("message"));
            if (message.Id != id || message.SenderId != owner || (!message.Removed && message.Body != body))
                throw new AccountException("invalid_response");
            return message;
        }, ct);
    }

    public Task RemoveCommunityAsync(Guid id, CancellationToken ct = default)
        => SocialRpcAsync("paw_community_remove", new { message_id = id }, _ => true, ct);
}
