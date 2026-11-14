using System.Text.Json;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public sealed record RebornBuild(Guid Id, string Channel, string Version, long Size, string Sha256, string Executable,
    DateTimeOffset PublishedAt, Dictionary<string,string> Notes)
{
    public static bool IsChannel(string channel) => channel is "stable" or "beta";
    public static void Validate(RebornBuild build)
    {
        if (build.Id == Guid.Empty || !IsChannel(build.Channel) || string.IsNullOrEmpty(build.Version) || !Regex.IsMatch(build.Version, @"\A[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}\z")
            || build.Size is < 1 or > 17179869184 || build.Sha256 is not { Length:64 } || !build.Sha256.All(Uri.IsHexDigit)
            || string.IsNullOrEmpty(build.Executable) || !Regex.IsMatch(build.Executable, @"\A[A-Za-z0-9][A-Za-z0-9_. -]{0,100}\.exe\z", RegexOptions.IgnoreCase)
            || build.Executable.Contains("..") || build.Notes is null || build.Notes.Count > 6 || build.Notes.Any(n => n.Value is null || n.Value.Length > 10000 || n.Key is not ("ru" or "en" or "uk" or "cs" or "de" or "fr")))
            throw new InvalidDataException("Invalid Reborn build metadata.");
    }
    public static RebornBuild Read(JsonElement row)
    {
        try
        {
        var notes = row.GetProperty("notes").EnumerateObject().ToDictionary(n => n.Name,n => n.Value.GetString() ?? "");
        var build = new RebornBuild(row.GetProperty("id").GetGuid(),row.GetProperty("channel").GetString()!,row.GetProperty("version").GetString()!,
            row.GetProperty("size").GetInt64(),row.GetProperty("sha256").GetString()!,row.GetProperty("executable").GetString()!,row.GetProperty("published_at").GetDateTimeOffset(),notes);
        Validate(build); return build;
        }
        catch (Exception error) when (error is KeyNotFoundException or InvalidOperationException or FormatException or ArgumentException)
        { throw new InvalidDataException("Invalid Reborn build response.",error); }
    }
    public string Note(string language) => Notes.GetValueOrDefault(language,Notes.GetValueOrDefault("en",Notes.GetValueOrDefault("ru","")));
}

public sealed record RebornTicket(RebornBuild Build, Uri Url, DateTimeOffset ExpiresAt);
