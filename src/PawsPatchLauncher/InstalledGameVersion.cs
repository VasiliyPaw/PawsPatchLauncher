using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public enum GameVersionRelation { Supported, Older, Newer, Different, Unknown }

public static partial class InstalledGameVersion
{
    public static string? Read(string path)
    {
        try
        {
            var info = FileVersionInfo.GetVersionInfo(path);
            if (Version.TryParse(info.ProductVersion, out var product) && product > new Version(0, 0, 0, 0)) return product.ToString();
            if (Version.TryParse(info.FileVersion, out var file) && file > new Version(0, 0, 0, 0)) return file.ToString();
            // Kohan II has no Windows version resource; its own version is a NUL-delimited UTF-16 string.
            using var stream = File.OpenRead(path);
            if (stream.Length > 128 * 1024 * 1024) return null;
            var bytes = new byte[(int)stream.Length]; stream.ReadExactly(bytes);
            if (stream.ReadByte() != -1) return null;
            var text = Encoding.Unicode.GetString(bytes);
            var versions = VersionString().Matches(text).Select(m => m.Groups[1].Value)
                .Where(v => Version.TryParse(v, out var parsed) && parsed > new Version(0, 0, 0, 0)).Distinct().ToArray();
            return versions.Length == 1 ? versions[0] : null;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or ArgumentException) { return null; }
    }

    public static GameVersionRelation Compare(string? installed, string? steamBuild, GameRequirement requirement, GameCompatibilityState state)
    {
        if (state == GameCompatibilityState.Supported) return GameVersionRelation.Supported;
        if (state != GameCompatibilityState.Unsupported) return GameVersionRelation.Unknown;
        if (Version.TryParse(installed, out var actual) && Version.TryParse(requirement.Version, out var expected))
        {
            actual = new(actual.Major, actual.Minor, Math.Max(actual.Build, 0), Math.Max(actual.Revision, 0));
            expected = new(expected.Major, expected.Minor, Math.Max(expected.Build, 0), Math.Max(expected.Revision, 0));
            if (actual < expected) return GameVersionRelation.Older;
            if (actual > expected) return GameVersionRelation.Newer;
        }
        if (ulong.TryParse(steamBuild, out var build) && ulong.TryParse(requirement.SteamBuild, out var supported))
        {
            if (build < supported) return GameVersionRelation.Older;
            if (build > supported) return GameVersionRelation.Newer;
        }
        return GameVersionRelation.Different;
    }

    [GeneratedRegex("\\0([0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,4}(?:\\.[0-9]{1,4})?)\\0")]
    private static partial Regex VersionString();
}
