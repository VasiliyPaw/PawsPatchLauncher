namespace PawsPatchLauncher;

public static class GameExecutableSelector
{
    public static string Select(LauncherConfiguration configuration, UserSettings settings, ChannelManifest? channel)
    {
        settings = EffectiveSettings.ForFeed(settings, channel);
        if (settings.DataOnly) return "k2.exe";
        if (!GameMod.IsArcaneWars(settings))
            return settings.PawPatchEnabled && GameMod.HasPureFixes(channel) ? "k2_paws_pure_fixes_1372.exe"
                : settings.Mod == GameMod.Immortals && HasMenuRuntime(channel) ? "k2_paws_menu_1372.exe" : "k2.exe";
        var name = Select(configuration, settings.CustomPlayerColors, settings.DesyncMode == "continue",
            settings.IndependentHostility, settings.PawPatchEnabled && HasCommonUi(channel), SupportsIndependentColors(channel));
        if (!settings.PawPatchEnabled && name == "k2.exe" && HasMenuRuntime(channel)) return "k2_paws_menu_1372.exe";
        return !settings.PawPatchEnabled && name != "k2.exe" ? name.Replace("k2_paws_", "k2_aw_") : name;
    }
    public static string Select(
        LauncherConfiguration configuration,
        bool colorsEnabled,
        bool continueAfterDesync,
        bool independentHostility,
        bool commonUiAvailable = false,
        bool independentColorsAvailable = false)
    {
        return (colorsEnabled, continueAfterDesync, independentHostility) switch
        {
            (true, true, false) when independentColorsAvailable => "k2_paws_lobby_colors_mp_nohostility_sync_1372.exe",
            (true, false, false) when independentColorsAvailable => "k2_paws_lobby_colors_mp_nohostility_1372.exe",
            (true, true, _) => "k2_paws_lobby_colors_mp_sync_1372.exe",
            (true, _, _) => "k2_paws_lobby_colors_mp_1372_experimental.exe",
            (false, true, true) => "k2_paws_sync_family_herd_relations_1372.exe",
            (false, true, false) => "k2_paws_sync_continue_1372.exe",
            (false, false, true) => configuration.PreferredGameExecutable,
            _ => commonUiAvailable ? "k2_paws_ui_1372.exe" : "k2.exe"
        };
    }

    // Old signed channels remain launchable until the mandatory module arrives.
    // New channels must install it before launching, including the all-off profile.
    public static bool HasCommonUi(ChannelManifest? channel)
        => channel?.Packages.Any(p => p.Id.Equals("common-ui", StringComparison.OrdinalIgnoreCase) && p.Required) == true;

    public static bool HasMenuRuntime(ChannelManifest? channel)
        => channel?.Packages.Any(p => p.Id == "menu-runtime") == true;

    public static bool SupportsColorDesyncContinue(ChannelManifest? channel)
        => channel is { ColorDesyncContinue: true }
            && channel.Packages.Any(p => p.Id == "player-colors");

    public static bool SupportsIndependentColors(ChannelManifest? channel)
        => channel is { IndependentColorHostility: true }
            && channel.Packages.Any(p => p.Id.Equals("player-colors", StringComparison.OrdinalIgnoreCase));
}
