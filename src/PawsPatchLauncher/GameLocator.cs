using Microsoft.Win32;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public sealed record GameInstallation(string Directory, string ExecutablePath, string? SteamBuild, string? Branch);

public static partial class GameLocator
{
    public static GameInstallation? Locate(string appId, string? preferredPath)
    {
        if (!string.IsNullOrWhiteSpace(preferredPath))
        {
            var direct = Validate(preferredPath, appId);
            if (direct is not null) return direct;
        }

        foreach (var library in FindSteamLibraries())
        {
            var candidate = Path.Combine(library, "steamapps", "common", "Kohan II");
            var result = Validate(candidate, appId);
            if (result is not null) return result;
        }

        return null;
    }

    public static GameInstallation? Validate(string directory, string appId)
    {
        try
        {
            var full = Path.GetFullPath(directory.Trim().Trim('"'));
            var executable = Path.Combine(full, "k2.exe");
            if (!File.Exists(executable)) return null;

            var steamApps = Directory.GetParent(Directory.GetParent(full)?.FullName ?? "")?.FullName;
            var manifestPath = steamApps is null ? null : Path.Combine(steamApps, $"appmanifest_{appId}.acf");
            string? build = null;
            string? branch = null;
            if (manifestPath is not null && File.Exists(manifestPath))
            {
                var content = File.ReadAllText(manifestPath);
                build = AcfValueRegex("buildid").Match(content) is { Success: true } buildMatch ? buildMatch.Groups[1].Value : null;
                branch = AcfValueRegex("BetaKey").Match(content) is { Success: true } branchMatch ? branchMatch.Groups[1].Value : null;
            }
            return new GameInstallation(full, executable, build, branch);
        }
        catch { return null; }
    }

    private static IEnumerable<string> FindSteamLibraries()
    {
        var found = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
        {
            using var hive = RegistryKey.OpenBaseKey(RegistryHive.CurrentUser, view);
            using var key = hive.OpenSubKey(@"Software\Valve\Steam");
            var steamPath = key?.GetValue("SteamPath") as string;
            if (string.IsNullOrWhiteSpace(steamPath) || !Directory.Exists(steamPath)) continue;
            found.Add(Path.GetFullPath(steamPath));
            var libraries = Path.Combine(steamPath, "steamapps", "libraryfolders.vdf");
            if (!File.Exists(libraries)) continue;
            foreach (Match match in LibraryPathRegex().Matches(File.ReadAllText(libraries)))
            {
                var path = match.Groups[1].Value.Replace("\\\\", "\\");
                if (Directory.Exists(path)) found.Add(Path.GetFullPath(path));
            }
        }
        return found;
    }

    [GeneratedRegex("\\\"path\\\"\\s+\\\"([^\\\"]+)\\\"", RegexOptions.IgnoreCase)]
    private static partial Regex LibraryPathRegex();

    private static Regex AcfValueRegex(string key) => new($"\\\"{Regex.Escape(key)}\\\"\\s+\\\"([^\\\"]+)\\\"", RegexOptions.IgnoreCase);
}

