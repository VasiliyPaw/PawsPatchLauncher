namespace PawsPatchLauncher;

public static class GameCompatibilityPolicy
{
    public static bool Supports(GameRequirement requirement, string hash)
        => requirement.K2ExeSha256.Contains(hash, StringComparer.OrdinalIgnoreCase);

    public static bool NativePath(string path)
        => new[] { ".exe", ".dll", ".com", ".bat", ".cmd", ".ps1", ".asi" }
            .Contains(Path.GetExtension(path), StringComparer.OrdinalIgnoreCase);

    public static bool HasNativeModules(InstallState state)
        => state.Modules.Values.Any(m => m.Enabled && m.Files.Any(f => NativePath(f.Path)));

    public static bool SelectedRuntimeNeedsUpdate(InstallState active, UserSettings selection, string hash, GameRequirement? archived, bool supported)
        => ModLibrary.IsActive(active, selection) && (InstalledRuntimeNeedsUpdate(active, hash, archived)
            || active.AppliedSettings?.DataOnly == true && supported);

    public static bool CanOfferUpdate(bool installedSelection, bool executableFeatures, bool problem,
        ChannelManifest selected, ChannelManifest? latest, string mod, string hash)
        => installedSelection && executableFeatures && problem && latest is not null
            && ModLibrary.HasUpdate(selected, latest, mod) && Supports(GameMod.Requirement(latest, mod), hash);

    public static bool InstalledRuntimeNeedsUpdate(InstallState state, string hash, GameRequirement? archived)
    {
        if (!HasNativeModules(state)) return false;
        if (state.BaseGameSha256 is { Length: > 0 } previous)
            return !previous.Equals(hash, StringComparison.OrdinalIgnoreCase);
        var requirement = state.GameRequirement ?? archived;
        if (requirement?.K2ExeSha256.Count > 0) return !Supports(requirement, hash);
        // Legacy launcher runtimes were all built from this exact Steam executable.
        // Unknown installed native modules must be reapplied before launching as well.
        return !hash.Equals("1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45", StringComparison.OrdinalIgnoreCase);
    }

    public static void ValidateDataModules(IEnumerable<InstalledModule> modules)
    {
        if (modules.Any(m => m.Files.Any(f => NativePath(f.Path)) || m.Remove.Any(NativePath)))
            throw new InvalidDataException("A file-only package contains executable changes.");
    }
}
