using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public static class FriendConfiguration
{
    // Only finite gameplay options. Never paths, URLs, executable names or credentials from peers.
    public static bool TryParse(string? code, string channel, out UserSettings settings)
    {
        settings = new UserSettings();
        if (code is null || code.Length > 128 || !Regex.IsMatch(code,
            @"\APAW-(STABLE|BETA)-((VANILLA|IMMORTALS)(-RU[01])?(-PP1)?(-DATA)?|IW[01]-SP[124]-RM[01]-SG[01]-LM[01]-RU[01]-CL[01]-OOS[01](-PS[01])?(-PP0)?(-DATA)?)(-TX(DE|FR|CS|UK))?(-VO(EN|RU|DE|FR))?\z")) return false;
        try { settings = ConfigurationCode.Parse(code); return settings.Channel == channel; }
        catch (FormatException) { return false; }
    }

    // Peer configurations contain gameplay only. Keep accepting older language
    // fields on the wire, but never include them in copying or equality checks.
    public static UserSettings WithLocalLanguages(UserSettings incoming, UserSettings local)
    {
        var result = EffectiveSettings.ForChannel(incoming);
        GameLanguages.SetText(result, GameLanguages.Text(local));
        result.GameVoiceLanguage = GameLanguages.Voice(local);
        return result;
    }

    public static string Create(UserSettings settings)
        => ConfigurationCode.Create(WithLocalLanguages(settings, new UserSettings { RussianLocalization = false, GameVoiceLanguage = "en" }));

    public static bool Matches(UserSettings first, UserSettings second) => Create(first) == Create(second);

    public static Dictionary<string, bool> Components(UserSettings preferences)
    {
        var settings = EffectiveSettings.ForChannel(preferences);
        var values = new Dictionary<string, bool> { ["core"] = GameMod.PawPatchSelected(settings) };
        if (!GameMod.IsArcaneWars(settings)) return values;
        values["colors"] = settings.CustomPlayerColors;
        values["desync"] = settings.DesyncMode != "official";
        values["hostility"] = settings.IndependentHostility;
        values["roaming"] = settings.RoamingSpawnMode != "standard";
        values["additional_roaming"] = settings.AdditionalRoamingCompanies;
        values["siege"] = settings.SiegeBalance;
        values["powers_shards"] = settings.DisablePowersAndShards;
        values["large_maps"] = settings.LargeMapSizes;
        return values;
    }

    public static void ValidateFeed(UserSettings settings, ChannelManifest channel)
    {
        settings = EffectiveSettings.ForChannel(settings);
        if (GameMod.IsArcaneWars(settings) && settings.PawPatchEnabled && !channel.Packages.Any(p => p.Id == "pawpatch-core" && p.Required))
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
