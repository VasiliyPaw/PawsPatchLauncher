namespace PawsPatchLauncher;

public static class ChangelogReadState
{
    public static IEnumerable<ChangelogEntry> Entries(ChannelManifest? manifest, string category, string mod)
        => (manifest?.Changelog ?? []).Where(entry => entry.Category.Equals(category, StringComparison.OrdinalIgnoreCase)
            && (category == "launcher" || (entry.Mods.Count == 0 ? mod == GameMod.ArcaneWars : entry.Mods.Contains(mod, StringComparer.OrdinalIgnoreCase))));

    private static string Id(ChannelManifest? manifest, string category, string mod)
        => string.Join("|", Entries(manifest, category, mod).Select(entry => entry.Version + ":" + entry.PublishedAt));

    private static string Key(ChannelManifest manifest, string category, string mod)
        => category.Equals("launcher", StringComparison.OrdinalIgnoreCase)
            ? "launcher" : "patch:" + manifest.Channel.ToLowerInvariant() + (mod == GameMod.ArcaneWars ? "" : ":" + mod);

    public static bool IsUnread(UserSettings settings, ChannelManifest? manifest, string category)
    {
        var id = Id(manifest, category, settings.Mod);
        return manifest is not null && id.Length > 0
            && settings.ReadChangelogs.GetValueOrDefault(Key(manifest, category, settings.Mod)) != id;
    }

    public static bool MarkViewed(UserSettings settings, ChannelManifest? manifest, string category, bool isVisible)
    {
        if (!isVisible || manifest is null || !IsUnread(settings, manifest, category)) return false;
        settings.ReadChangelogs[Key(manifest, category, settings.Mod)] = Id(manifest, category, settings.Mod);
        return true;
    }
}
