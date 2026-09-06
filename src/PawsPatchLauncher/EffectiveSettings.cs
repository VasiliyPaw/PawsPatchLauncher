using System.Text.Json;

namespace PawsPatchLauncher;

/// <summary>A detached active configuration, not the user's remembered channel preferences.</summary>
public static class EffectiveSettings
{
    public static UserSettings ForChannel(UserSettings preferences, bool colorsAvailable = true)
    {
        var active = JsonSerializer.Deserialize(JsonSerializer.Serialize(preferences, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!;
        active.CustomPlayerColors = preferences.CustomPlayerColors && colorsAvailable && preferences.Channel.Equals("beta", StringComparison.OrdinalIgnoreCase);
        active.LargeMapSizes = true;
        return active;
    }

    public static UserSettings ForFeed(UserSettings preferences, ChannelManifest? feed)
        => ForChannel(preferences, feed is not null && feed.Channel.Equals(preferences.Channel, StringComparison.OrdinalIgnoreCase)
            && feed.Packages.Any(p => p.Id.Equals("player-colors", StringComparison.OrdinalIgnoreCase)));
}
