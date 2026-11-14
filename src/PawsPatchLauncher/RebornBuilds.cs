using System.Text.Json;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public sealed record RebornBuild(Guid Id, string Channel, string Version, long Size, string Sha256, string Executable,
    DateTimeOffset PublishedAt, Dictionary<string,string> Notes, string DownloadProvider = "supabase",
    string? GitHubRepository = null, long? GitHubRepositoryId = null, long? GitHubAssetId = null)
{
    public static bool IsChannel(string channel) => channel is "stable" or "beta";
    public static void Validate(RebornBuild build)
    {
        if (build.Id == Guid.Empty || !IsChannel(build.Channel) || string.IsNullOrEmpty(build.Version) || !Regex.IsMatch(build.Version, @"\A[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}\z")
            || build.Size is < 1 or > 17179869184 || build.Sha256 is not { Length:64 } || !build.Sha256.All(Uri.IsHexDigit)
            || string.IsNullOrEmpty(build.Executable) || !Regex.IsMatch(build.Executable, @"\A[A-Za-z0-9][A-Za-z0-9_. -]{0,100}\.exe\z", RegexOptions.IgnoreCase)
            || build.Executable.Contains("..") || build.Notes is null || build.Notes.Count > 6 || build.Notes.Any(n => n.Value is null || n.Value.Length > 10000 || n.Key is not ("ru" or "en" or "uk" or "cs" or "de" or "fr")))
            throw new InvalidDataException("Invalid Reborn build metadata.");
        if (build.DownloadProvider == "github")
        {
            if (build.GitHubRepository is null || !Regex.IsMatch(build.GitHubRepository,@"\A[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}\z")
                || build.GitHubRepositoryId is not (> 0 and <= 9007199254740991) || build.GitHubAssetId is not (> 0 and <= 9007199254740991))
                throw new InvalidDataException("Invalid Reborn GitHub metadata.");
        }
        else if (build.DownloadProvider != "supabase" || build.GitHubRepository is not null || build.GitHubRepositoryId is not null || build.GitHubAssetId is not null)
            throw new InvalidDataException("Invalid Reborn download provider.");
    }
    public static RebornBuild Read(JsonElement row)
    {
        try
        {
        var notes = row.GetProperty("notes").EnumerateObject().ToDictionary(n => n.Name,n => n.Value.GetString() ?? "");
        var build = new RebornBuild(row.GetProperty("id").GetGuid(),row.GetProperty("channel").GetString()!,row.GetProperty("version").GetString()!,
            row.GetProperty("size").GetInt64(),row.GetProperty("sha256").GetString()!,row.GetProperty("executable").GetString()!,row.GetProperty("published_at").GetDateTimeOffset(),notes,
            row.TryGetProperty("download_provider",out var provider) ? provider.GetString()! : "supabase",
            row.TryGetProperty("github_repository",out var repository) && repository.ValueKind != JsonValueKind.Null ? repository.GetString() : null,
            row.TryGetProperty("github_repository_id",out var repositoryId) && repositoryId.ValueKind != JsonValueKind.Null ? repositoryId.GetInt64() : null,
            row.TryGetProperty("github_asset_id",out var assetId) && assetId.ValueKind != JsonValueKind.Null ? assetId.GetInt64() : null);
        Validate(build); return build;
        }
        catch (Exception error) when (error is KeyNotFoundException or InvalidOperationException or FormatException or ArgumentException)
        { throw new InvalidDataException("Invalid Reborn build response.",error); }
    }
    public string Note(string language) => Notes.GetValueOrDefault(language,Notes.GetValueOrDefault("en",Notes.GetValueOrDefault("ru","")));
}

public sealed record RebornTicket(RebornBuild Build, Uri Url, DateTimeOffset ExpiresAt, DateTimeOffset? UrlExpiresAt = null);

public static class RebornDownloadPolicy
{
    public static bool SameBuild(RebornBuild a, RebornBuild b) => a.Id == b.Id && a.Channel == b.Channel && a.Version == b.Version
        && a.Sha256.Equals(b.Sha256,StringComparison.OrdinalIgnoreCase) && a.Size == b.Size && a.Executable == b.Executable
        && a.DownloadProvider == b.DownloadProvider && a.GitHubRepository == b.GitHubRepository
        && a.GitHubRepositoryId == b.GitHubRepositoryId && a.GitHubAssetId == b.GitHubAssetId;

    public static void Validate(RebornTicket ticket, Uri storage, DateTimeOffset now)
    {
        RebornBuild.Validate(ticket.Build);
        var url = ticket.Url;
        if (url.Scheme != "https" || url.Port != 443 || url.UserInfo.Length > 0 || url.Fragment.Length > 0 || url.OriginalString.Length > 12000
            || string.IsNullOrEmpty(url.Query) || ticket.ExpiresAt <= now || ticket.ExpiresAt > now.AddMinutes(3))
            throw new InvalidDataException("Invalid Reborn download ticket.");
        if (ticket.Build.DownloadProvider == "supabase")
        {
            if (url.Host != storage.Host || url.Port != storage.Port
                || url.AbsolutePath != $"/storage/v1/object/sign/paw-reborn-builds/{ticket.Build.Channel}/{ticket.Build.Id}.zip")
                throw new InvalidDataException("Invalid Reborn storage URL.");
            return;
        }
        var expiry = url.Query[1..].Split('&').Where(p => p.StartsWith("se=",StringComparison.Ordinal)).ToArray();
        var signature = url.Query[1..].Split('&').Where(p => p.StartsWith("sig=",StringComparison.Ordinal)).ToArray();
        if (url.Host != "release-assets.githubusercontent.com"
            || !Regex.IsMatch(url.AbsolutePath,$@"\A/github-production-release-asset/{ticket.Build.GitHubRepositoryId}/[A-Za-z0-9-]+\z")
            || signature.Length != 1 || signature[0].Length <= 4 || expiry.Length != 1 || !DateTimeOffset.TryParse(Uri.UnescapeDataString(expiry[0][3..]),System.Globalization.CultureInfo.InvariantCulture,System.Globalization.DateTimeStyles.None,out var upstreamExpiry)
            || ticket.UrlExpiresAt != upstreamExpiry || upstreamExpiry <= now || ticket.ExpiresAt > upstreamExpiry)
            throw new InvalidDataException("Invalid Reborn GitHub URL.");
    }
}
