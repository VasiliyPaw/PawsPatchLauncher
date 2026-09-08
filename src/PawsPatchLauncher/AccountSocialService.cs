using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace PawsPatchLauncher;

public sealed record SocialPlayer(Guid Id, string Nickname, string Relation, int Unread=0,
    string Presence="offline", DateTimeOffset? LastSeen=null, DateTimeOffset? PlayingSince=null,
    string Channel="unknown", string Components="{}", DateTimeOffset? AvatarRevision=null, string? Configuration=null,string? DisplayName=null,
    int AdminLevel=0,DateTimeOffset? BannedAt=null,DateTimeOffset? BanUntil=null,string BanReason="",DateTimeOffset? DeletedAt=null,DateTimeOffset? CreatedAt=null,bool IsFriend=true)
{
    public string Name=>Deleted?"Удалённый аккаунт":string.IsNullOrEmpty(DisplayName)?Nickname:DisplayName;
    public bool Deleted=>DeletedAt is not null;
    public bool Banned=>BannedAt is not null&&(BanUntil is null||BanUntil>DateTimeOffset.UtcNow);
    public bool Available=>!Deleted&&!Banned;
}
public sealed record SocialMessage(
    [property: JsonPropertyName("sender_id")] Guid SenderId,
    [property: JsonPropertyName("message_id")] Guid MessageId,
    [property: JsonPropertyName("recipient_id")] Guid RecipientId,
    [property: JsonPropertyName("body")] string Body,
    [property: JsonPropertyName("kind")] string Kind,
    [property: JsonPropertyName("created_at")] DateTimeOffset CreatedAt,
    [property: JsonPropertyName("ordinal")] long Ordinal=0);

public sealed record SocialMessagePage(IReadOnlyList<SocialMessage> Messages, IReadOnlyList<SocialOffer> Offers,
    bool More, long Revision, bool Trimmed);

public sealed partial class AccountService
{
    private async Task<T> SocialRpcAsync<T>(string route, object body, Func<JsonElement,T> read, CancellationToken ct)
    {
        T result = default!;
        await WithAccountAsync(async () =>
        {
            if(Restricted)throw new AccountException(Banned?"account_banned":"account_deletion_pending");
            using var response = await RequestAsync(HttpMethod.Post, "rpc/"+route, body, _session!.AccessToken, ct, database:true).ConfigureAwait(false);
            var status = await ResolveRestrictionAsync(Text(response.RootElement,"status"),ct).ConfigureAwait(false);
            if (status != "ok") throw new AccountException(status switch {
                "session_expired" or "session_replaced" or "player_unavailable" or "friend_limit" or "request_missing" or "friend_required"
                or "invalid_message" or "message_conflict" or "rate_limit" or "message_limit"
                or "offer_expired" or "offer_unavailable" or "invalid_offer" or "invalid_save" or "storage_limit" or "configuration_matches" => status,
                "admin_required" or "higher_role_required" or "protected_account" or "self_moderation" or "invalid_ban" or "restore_expired"
                or "account_banned" or "account_deletion_pending" or "admin_cannot_block" or "account_busy" => status,
                _ => "service_error" });
            result = read(response.RootElement);
        },ct).ConfigureAwait(false);
        return result;
    }

    public Task<IReadOnlyList<SocialPlayer>> GetFriendsAsync(CancellationToken ct=default) =>
        SocialRpcAsync<IReadOnlyList<SocialPlayer>>("paw_social_list", new {}, json =>
        {
            var items=json.GetProperty("players");
            if (items.GetArrayLength()>10000) throw new AccountException("invalid_response");
            return items.EnumerateArray().Select(ReadSocialPlayer).ToArray();
        },ct);

    internal static SocialPlayer ReadSocialPlayer(JsonElement p)
    {
                var name=Text(p,"nickname"); var relation=Text(p,"relation"); ValidateNickname(name);
                var displayName=Text(p,"display_name");if(displayName.Length==0)displayName=name;ValidateDisplayName(displayName);
                if (relation is not ("friend" or "incoming" or "outgoing" or "blocked")) throw new AccountException("invalid_response");
                var unread=p.TryGetProperty("unread",out var count)?count.GetInt32():0;
                if(unread is <0 or >10000 || relation!="friend" && unread!=0)throw new AccountException("invalid_response");
                var presence=Text(p,"presence"); if(presence.Length==0)presence="offline";
                var channel=Text(p,"channel"); if(channel.Length==0)channel="unknown";
                if(presence is not ("offline" or "online" or "playing") || channel is not ("stable" or "beta" or "unknown"))throw new AccountException("invalid_response");
                DateTimeOffset? Date(string key)=>p.TryGetProperty(key,out var v) && v.ValueKind==JsonValueKind.String?v.GetDateTimeOffset():null;
                var components=p.TryGetProperty("components",out var c)?c.GetRawText():"{}";
                if(components.Length>2048 || c.ValueKind is not (JsonValueKind.Undefined or JsonValueKind.Object))throw new AccountException("invalid_response");
                var configuration=Text(p,"configuration");
                return new SocialPlayer(p.GetProperty("id").GetGuid(),NormalizeUsername(name),relation,unread,presence,Date("last_seen"),Date("playing_since"),channel,components,Date("avatar_revision"),
                    FriendConfiguration.TryParse(configuration,channel,out _) ? configuration : null,displayName,
                    ModerationInt(p,"admin_level"),Date("banned_at"),Date("ban_until"),Text(p,"ban_reason"),Date("deleted_at"),Date("created_at"),
                    !p.TryGetProperty("is_friend",out var friendship)||friendship.ValueKind==JsonValueKind.True);
    }

    public Task FriendActionAsync(string action, Guid? target=null, string? nickname=null, CancellationToken ct=default)
    {
        if (action is not ("request" or "accept" or "decline" or "cancel" or "remove" or "block" or "unblock" or "hide_chat")) throw new ArgumentException("Invalid friend action.");
        if (action=="request") ValidateNickname(nickname ?? "");
        else if (target is null || target==Guid.Empty) throw new AccountException("player_unavailable");
        return SocialRpcAsync("paw_friend_action",new {action,target,candidate=nickname is null?null:NormalizeUsername(nickname)}, _=>true,ct);
    }

    public Task PublishPresenceAsync(bool playing,string channel,IReadOnlyDictionary<string,bool> components,CancellationToken ct=default)
        => SocialRpcAsync("paw_presence",new{playing,channel,components},_=>true,ct);

    public Task PublishConfigurationPresenceAsync(bool playing,string channel,IReadOnlyDictionary<string,bool> components,string? configuration,CancellationToken ct=default)
        => SocialRpcAsync("paw_presence",new{playing,channel,components,configuration},_=>true,ct);

    public Task<int> MarkMessagesReadAsync(Guid target,Guid lastMessage,CancellationToken ct=default)
    {
        if(target==Guid.Empty || lastMessage==Guid.Empty)throw new AccountException("invalid_message");
        return SocialRpcAsync("paw_mark_messages_read",new{target,last_message=lastMessage},json=> {
            var unread=json.GetProperty("unread").GetInt32();
            if(unread is <0 or >10000)throw new AccountException("invalid_response");
            return unread;
        },ct);
    }

    public static void ValidateMessage(string body,string kind)
    {
        if (string.IsNullOrWhiteSpace(body) || body.Length >2000 || kind is not ("text" or "config")
            || body.Any(c=>char.IsControl(c) && c is not ('\n' or '\r' or '\t')))
            throw new AccountException("invalid_message");
    }

    public Task<SocialMessage> SendMessageAsync(Guid target,Guid messageId,string body,string kind="text",CancellationToken ct=default)
    {
        ValidateMessage(body,kind);
        if (target==Guid.Empty || messageId==Guid.Empty) throw new AccountException("invalid_message");
        if (!Guid.TryParse(UserId,out var owner)) throw new AccountException("session_expired");
        return SocialRpcAsync("paw_send_message", new {target,message_id=messageId,body,kind},json=> {
            var item=ReadSocialMessage(json.GetProperty("message"));
            if (item.SenderId!=owner || item.RecipientId!=target || item.MessageId!=messageId || item.Body!=body || item.Kind!=kind)
                throw new AccountException("invalid_response");
            return item;
        },ct);
    }

    public Task<IReadOnlyList<SocialMessage>> GetMessagesAsync(Guid target,CancellationToken ct=default)
    {
        if (!Guid.TryParse(UserId,out var owner)) throw new AccountException("session_expired");
        return SocialRpcAsync<IReadOnlyList<SocialMessage>>("paw_read_messages",new {target},json=> {
            var items=json.GetProperty("messages");
            if (items.GetArrayLength()>50) throw new AccountException("invalid_response");
            return items.EnumerateArray().Select(p=> {
                var item=ReadSocialMessage(p);
                if (!((item.SenderId==owner && item.RecipientId==target)||(item.SenderId==target && item.RecipientId==owner)))
                    throw new AccountException("invalid_response");
                return item;
            }).ToArray();
        },ct);
    }

    public Task<SocialMessagePage> GetMessagePageAsync(Guid target, SocialMessage? before = null, CancellationToken ct = default)
    {
        if (!Guid.TryParse(UserId, out var owner)) throw new AccountException("session_expired");
        if (target == Guid.Empty || target == owner || before is not null && (before.Ordinal <= 0
            || !((before.SenderId == owner && before.RecipientId == target) || (before.SenderId == target && before.RecipientId == owner))))
            throw new AccountException("invalid_message");
        return SocialRpcAsync("paw_read_message_page", new { target, before_time = before?.CreatedAt, before_ordinal = before?.Ordinal }, json =>
        {
            var items = json.GetProperty("messages"); var cards = json.GetProperty("offers");
            if (items.GetArrayLength() > 50 || cards.GetArrayLength() > 50) throw new AccountException("invalid_response");
            var messages = items.EnumerateArray().Select(ReadSocialMessage).ToArray();
            if (messages.Any(m => m.Ordinal <= 0 || !((m.SenderId == owner && m.RecipientId == target) || (m.SenderId == target && m.RecipientId == owner)))
                || messages.Select(m => m.Ordinal).Distinct().Count() != messages.Length
                || before is not null && messages.Any(m => m.CreatedAt > before.CreatedAt || m.CreatedAt == before.CreatedAt && m.Ordinal >= before.Ordinal))
                throw new AccountException("invalid_response");
            var offers = cards.EnumerateArray().Select(o => ReadOffer(o, target)).ToArray();
            if (offers.Any(o => !messages.Any(m => m.MessageId == o.Id && m.SenderId == o.Sender))
                || offers.Select(o=>o.Id).Distinct().Count()!=offers.Length
                || json.GetProperty("more").GetBoolean() && messages.Length!=50) throw new AccountException("invalid_response");
            var revision = json.GetProperty("history_revision").GetInt64();
            if (revision < 0) throw new AccountException("invalid_response");
            return new SocialMessagePage(messages.OrderBy(m => m.CreatedAt).ThenBy(m => m.Ordinal).ToArray(), offers,
                json.GetProperty("more").GetBoolean(), revision, json.GetProperty("trimmed").GetBoolean());
        }, ct);
    }

    private static SocialMessage ReadSocialMessage(JsonElement data)
    {
        var item=data.Deserialize<SocialMessage>() ?? throw new AccountException("invalid_response");
        ValidateMessage(item.Body,item.Kind);
        if (item.MessageId==Guid.Empty || item.SenderId==Guid.Empty || item.RecipientId==Guid.Empty || item.SenderId==item.RecipientId)
            throw new AccountException("invalid_response");
        return item;
    }
}
