namespace PawsPatchLauncher;

public static class GameExecutableSelector
{
    public static string Select(
        LauncherConfiguration configuration,
        bool colorsEnabled,
        bool continueAfterDesync,
        bool independentHostility)
    {
        return (colorsEnabled, continueAfterDesync, independentHostility) switch
        {
            (true, _, _) => "k2_paws_lobby_colors_mp_1372_experimental.exe",
            (false, true, true) => "k2_paws_sync_family_herd_relations_1372.exe",
            (false, true, false) => "k2_paws_sync_continue_1372.exe",
            (false, false, true) => configuration.PreferredGameExecutable,
            _ => "k2.exe"
        };
    }
}
