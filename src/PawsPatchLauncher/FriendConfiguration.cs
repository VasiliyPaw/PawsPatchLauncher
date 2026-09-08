using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public static class FriendConfiguration
{
    // Only finite gameplay options. Never paths, URLs, executable names or credentials from peers.
    public static bool TryParse(string? code, string channel, out UserSettings settings)
    {
        settings = new UserSettings();
        if (code is null || code.Length > 128 || !Regex.IsMatch(code,
            @"\APAW-(STABLE|BETA)-IW[01]-SP[124]-RM[01]-SG[01]-LM1-RU[01]-CL[01]-OOS[01](-PS[01])?\z")) return false;
        try { settings = ConfigurationCode.Parse(code); return settings.Channel == channel; }
        catch (FormatException) { return false; }
    }

    public static void ValidateFeed(UserSettings settings, ChannelManifest channel)
    {
        if (!channel.Packages.Any(p => p.Id == "pawpatch-core" && p.Required))
            throw new InvalidDataException("The selected patch release does not include the required core.");
        if (settings.Channel != channel.Channel ||
            ConfigurationCode.Create(EffectiveSettings.ForFeed(settings, channel)) != ConfigurationCode.Create(settings))
            throw new InvalidDataException("The selected patch release does not support these settings.");
        _ = GamePackageSelector.Select(channel, settings, settings.RussianLocalization, settings.CustomPlayerColors);
        if (settings.CustomPlayerColors && (settings.DesyncMode == "continue" && !GameExecutableSelector.SupportsColorDesyncContinue(channel)
            || !settings.IndependentHostility && !GameExecutableSelector.SupportsIndependentColors(channel)))
            throw new InvalidDataException("The selected patch release does not support this combination.");
    }
}
