namespace PawsPatchLauncher;

public sealed partial class AccountService
{
    public Task<SocialPlayer> GetPublicPlayerProfileAsync(Guid target, CancellationToken ct = default)
    {
        if (target == Guid.Empty) throw new AccountException("player_unavailable");
        return SocialRpcAsync("paw_profile_card", new { target }, data =>
        {
            var player = ReadSocialPlayer(data.GetProperty("player"));
            if (player.Id != target || player.Deleted) throw new AccountException("invalid_response");
            return player;
        }, ct);
    }
}
