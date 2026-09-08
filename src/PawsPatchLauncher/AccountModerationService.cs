using System.Text.Json;
namespace PawsPatchLauncher;

public sealed record AdminPlayer(Guid Id,string Nickname,string DisplayName,DateTimeOffset CreatedAt,int AdminLevel,bool Protected,
    DateTimeOffset? BannedAt,DateTimeOffset? BanUntil,string BanReason,DateTimeOffset? DeletedAt,bool Purging,bool IsNew);
public sealed record AdminBan(Guid Id,string Email,DateTimeOffset CreatedAt,DateTimeOffset? Until,string Reason);
public sealed record AdminPage(IReadOnlyList<AdminPlayer> Users,IReadOnlyList<AdminBan> Bans,bool More,DateTimeOffset ServerTime);

public sealed partial class AccountService
{
    // Cached presentation state is never used as server authorization.
    public int AdminLevel => State==AccountState.SignedIn&&!Restricted ? _session?.AdminLevel??0 : 0;
    public bool ProtectedAdmin => _session?.ProtectedAdmin==true;
    public DateTimeOffset? BannedAt => _session?.BannedAt;
    public DateTimeOffset? BanUntil => _session?.BanUntil;
    public string BanReason => _session?.BanReason??"";
    public DateTimeOffset? DeletedAt => _session?.DeletedAt;
    public bool Banned => BannedAt is not null && (BanUntil is null||BanUntil>_clock());
    public bool Restricted => Banned||DeletionPending;
    private void EnsureAccountEditable()
    {
        if(Restricted)throw new AccountException(DeletionPending?"account_deletion_pending":"account_banned");
    }
    private async Task<string> ResolveRestrictionAsync(string status,CancellationToken ct)
    {
        // A ban can arrive after the profile refresh but before a legacy social RPC.
        // Do not mistake its rejected actor for an expired login and sign the player out.
        if(status is "session_expired" or "account_banned" or "account_deletion_pending")
        {
            try{await LoadProfileAsync(ct).ConfigureAwait(false);}catch(AccountException){}
            if(Restricted)return DeletionPending?"account_deletion_pending":"account_banned";
        }
        return status;
    }
    internal static DateTimeOffset? ModerationDate(JsonElement data,string name)=>data.TryGetProperty(name,out var v)&&v.ValueKind==JsonValueKind.String?v.GetDateTimeOffset():null;
    internal static int ModerationInt(JsonElement data,string name)=>data.TryGetProperty(name,out var v)&&v.ValueKind==JsonValueKind.Number?v.GetInt32():0;
    internal static bool ModerationBool(JsonElement data,string name)=>data.TryGetProperty(name,out var v)&&v.ValueKind==JsonValueKind.True;

    public Task<AdminPage> GetAdminPageAsync(string section,string query,int page,CancellationToken ct=default)
        => SocialRpcAsync("paw_admin_list",new{section,query,page},data=>
        {
            var items=data.GetProperty("items");
            if(items.GetArrayLength()>51)throw new AccountException("invalid_response");
            var time=ModerationDate(data,"server_time")??throw new AccountException("invalid_response");
            var users=new List<AdminPlayer>();var bans=new List<AdminBan>();
            foreach(var row in items.EnumerateArray().Take(50))
                if(section=="bans")bans.Add(new(row.GetProperty("id").GetGuid(),Text(row,"email"),ModerationDate(row,"created_at")??time,ModerationDate(row,"until_at"),Text(row,"reason")));
                else users.Add(new(row.GetProperty("id").GetGuid(),Text(row,"nickname"),Text(row,"display_name"),ModerationDate(row,"created_at")??time,
                    ModerationInt(row,"admin_level"),ModerationBool(row,"protected_admin"),ModerationDate(row,"banned_at"),ModerationDate(row,"ban_until"),Text(row,"ban_reason"),ModerationDate(row,"deleted_at"),
                    ModerationDate(row,"purge_started_at") is not null,ModerationBool(row,"is_new")));
            return new AdminPage(users,bans,items.GetArrayLength()>50,time);
        },ct);
    public Task AdminActionAsync(string action,Guid target,string reason="",DateTimeOffset? until=null,int? level=null,CancellationToken ct=default)
        =>SocialRpcAsync("paw_admin_action",new{action,target,reason,until_at=until,level},_=>true,ct);
    public Task StartAdminChatAsync(Guid target,CancellationToken ct=default)=>SocialRpcAsync("paw_admin_chat",new{target},_=>true,ct);
    public Task<SocialPlayer> GetPlayerProfileAsync(Guid target,CancellationToken ct=default)
        =>SocialRpcAsync("paw_player_profile",new{target},data=>ReadSocialPlayer(data.GetProperty("player")),ct);
    public Task<JsonElement> GetAdminStatusAsync(CancellationToken ct=default)
        =>SocialRpcAsync("paw_admin_status",new{},data=>data.Clone(),ct);
    public Task<JsonElement> GetAdminResourcesAsync(CancellationToken ct=default)
        =>SocialRpcAsync("paw_admin_resources",new{},data=>data.Clone(),ct);
}
