namespace PawsPatchLauncher;

public sealed class ModChannelPreference
{
    public string Channel { get; set; } = "stable";
    public string? PinnedRelease { get; set; }
}

public static class ModChannelSelection
{
    // The active fields remain the source of truth for installed snapshots and old profiles.
    public static void Remember(UserSettings settings)
    {
        settings.ModChannels ??= new();
        settings.ModChannels[settings.Mod] = new()
        {
            Channel = settings.Channel == "beta" ? "beta" : "stable",
            PinnedRelease = settings.PinnedRelease
        };
    }

    public static void SelectMod(UserSettings settings, string mod)
    {
        GameMod.Validate(new UserSettings { Mod = mod });
        Remember(settings);
        settings.Mod = mod;
        var choice = settings.ModChannels.GetValueOrDefault(mod) ?? new();
        settings.Channel = choice.Channel == "beta" ? "beta" : "stable";
        settings.PinnedRelease = choice.PinnedRelease;
        Remember(settings);
    }

    public static void SelectChannel(UserSettings settings, string channel)
    {
        if (channel is not ("stable" or "beta")) throw new ArgumentException("Unknown patch channel.", nameof(channel));
        if (settings.Channel == channel) return;
        settings.Channel = channel;
        settings.PinnedRelease = null;
        Remember(settings);
    }

    public static bool HasDistinctBeta(string mod, ChannelManifest? stable, ChannelManifest? beta)
    {
        if (beta?.Channel != "beta") return false;
        try
        {
            var packages = ModLibrary.Packages(beta, mod);
            if (!packages.Any(p => p.Id is "pawpatch-core" or "pure-fixes-data")) return false;
            // A newer stable catalog can arrive before the matching beta catalog.
            // Different package identities alone must not expose an old stable
            // copy as a separate beta for Vanilla or Immortals.
            var hasBetaPatch = packages.Any(p => p.Id is "pawpatch-core" or "common-ui" or "player-colors" or "pure-fixes-data" or "pure-fixes-runtime"
                && (p.Experimental || p.Version.Contains("beta", StringComparison.OrdinalIgnoreCase)));
            return hasBetaPatch && (stable is null || ModLibrary.HasUpdate(stable, beta, mod));
        }
        catch (InvalidDataException) { return false; }
    }
}
