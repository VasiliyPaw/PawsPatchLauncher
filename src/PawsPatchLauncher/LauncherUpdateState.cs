namespace PawsPatchLauncher;

/// <summary>Session-wide launcher availability, unrelated to patch selection or pins.</summary>
public sealed class LauncherUpdateState
{
    public LauncherRelease? Latest { get; private set; }

    public static bool IsValid(LauncherRelease? release)
        => release is { Size: > 0, Sha256.Length: 64, Urls.Count: > 0 }
            && Version.TryParse(release.Version, out var version) && version > new Version(0, 0, 0)
            && release.Sha256.All(Uri.IsHexDigit) && release.Urls.All(url => !string.IsNullOrWhiteSpace(url));

    public void Observe(LauncherRelease? release)
    {
        if (!IsValid(release)) return;
        // A stale mirror, patch channel switch, pin or temporary failure cannot
        // retract an update already found in this session. Same-version assets
        // are immutable, so a conflicting hash does not replace the first result.
        if (Latest is not null && Version.Parse(release!.Version) <= Version.Parse(Latest.Version)) return;
        Latest = new LauncherRelease { Version = release!.Version, Size = release.Size,
            Sha256 = release.Sha256, Urls = release.Urls.ToList() };
    }
}
