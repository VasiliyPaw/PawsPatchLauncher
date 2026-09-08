namespace PawsPatchLauncher;

public static class UpdateDetector
{
    // Channel names and launcher preferences do not change the installed game.
    public static bool HasSettingsChanges(InstallState state, IReadOnlyCollection<PackageRelease> selected, UserSettings desired)
        => HasModuleChanges(state, selected) || state.AppliedSettings is { } applied
            && (applied.IndependentHostility != desired.IndependentHostility
                || !applied.DesyncMode.Equals(desired.DesyncMode, StringComparison.OrdinalIgnoreCase));

    // A cached channel can be applied locally, without pretending a download is an update.
    // Missing unselected options must not mark an otherwise current installation outdated.
    public static bool NeedsDownload(InstallState state, IReadOnlyCollection<PackageRelease> selected,
        Func<PackageRelease, bool> cached)
        => selected.Any(package => !Matches(state, package) && !cached(package));

    public static bool HasRemoteUpdate(InstallState state, IReadOnlyCollection<PackageRelease> selected,
        Func<PackageRelease, bool> cached)
        => selected.Any(package => (package.Required || state.Modules.ContainsKey(package.Id))
            && !Matches(state, package) && !cached(package));

    private static bool Matches(InstallState state, PackageRelease package)
        => state.Modules.TryGetValue(package.Id, out var installed) && installed.Enabled
            && installed.Version.Equals(package.Version, StringComparison.OrdinalIgnoreCase)
            && installed.ArchiveSha256.Equals(package.Sha256, StringComparison.OrdinalIgnoreCase)
            && installed.Priority == package.Priority;

    public static bool HasModuleChanges(InstallState state, IReadOnlyCollection<PackageRelease> selected)
    {
        var desiredIds = selected.Select(package => package.Id).ToHashSet(StringComparer.OrdinalIgnoreCase);
        if (state.Modules.Keys.Any(id => !desiredIds.Contains(id))) return true;

        foreach (var package in selected)
        {
            if (!state.Modules.TryGetValue(package.Id, out var installed)) return true;
            if (!installed.Enabled ||
                !installed.Version.Equals(package.Version, StringComparison.OrdinalIgnoreCase) ||
                !installed.ArchiveSha256.Equals(package.Sha256, StringComparison.OrdinalIgnoreCase) ||
                installed.Priority != package.Priority)
                return true;
        }

        return false;
    }
}
