namespace PawsPatchLauncher;

public static class ChangelogReadState
{
    private static string Id(ChannelManifest? manifest, string category)
        => string.Join("|", manifest?.Changelog
            .Where(entry => entry.Category.Equals(category, StringComparison.OrdinalIgnoreCase))
            .Select(entry => entry.Version + ":" + entry.PublishedAt) ?? []);

    private static string Key(ChannelManifest manifest, string category)
        => category.Equals("launcher", StringComparison.OrdinalIgnoreCase)
            ? "launcher" : "patch:" + manifest.Channel.ToLowerInvariant();

    public static bool IsUnread(UserSettings settings, ChannelManifest? manifest, string category)
    {
        var id = Id(manifest, category);
        return manifest is not null && id.Length > 0
            && settings.ReadChangelogs.GetValueOrDefault(Key(manifest, category)) != id;
    }

    public static bool MarkViewed(UserSettings settings, ChannelManifest? manifest, string category, bool isVisible)
    {
        if (!isVisible || manifest is null || !IsUnread(settings, manifest, category)) return false;
        settings.ReadChangelogs[Key(manifest, category)] = Id(manifest, category);
        return true;
    }
}
