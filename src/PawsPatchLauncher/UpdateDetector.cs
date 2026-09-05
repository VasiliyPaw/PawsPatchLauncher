namespace PawsPatchLauncher;

public static class UpdateDetector
{
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
