namespace PawsPatchLauncher;

public static class GameExecutableSelector
{
    public static string Select(
        LauncherConfiguration configuration,
        bool colorsEnabled,
        bool continueAfterDesync,
        bool independentHostility,
        bool commonUiAvailable = false)
    {
        return (colorsEnabled, continueAfterDesync, independentHostility) switch
        {
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
}
