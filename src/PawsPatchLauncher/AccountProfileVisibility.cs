namespace PawsPatchLauncher;

public sealed record ProfileVisibility(string Configuration = "all", string Activity = "all")
{
    public static bool Valid(string value) => value is "all" or "friends" or "nobody";
}

public sealed partial class AccountService
{
    public Task<ProfileVisibility> ReadProfileVisibilityAsync(CancellationToken ct = default) => VisibilityRpcAsync(null, ct);
    public Task<ProfileVisibility> SaveProfileVisibilityAsync(ProfileVisibility value, CancellationToken ct = default)
    {
        if (!ProfileVisibility.Valid(value.Configuration) || !ProfileVisibility.Valid(value.Activity)) throw new ArgumentException("Invalid profile visibility");
        return VisibilityRpcAsync(value, ct);
    }
    private Task<ProfileVisibility> VisibilityRpcAsync(ProfileVisibility? value, CancellationToken ct) =>
        SocialRpcAsync("paw_profile_visibility", new { configuration_visibility = value?.Configuration, activity_visibility = value?.Activity }, json =>
        {
            var result = new ProfileVisibility(Text(json, "configuration_visibility"), Text(json, "activity_visibility"));
            if (!ProfileVisibility.Valid(result.Configuration) || !ProfileVisibility.Valid(result.Activity)) throw new AccountException("invalid_response");
            return result;
        }, ct);
}
