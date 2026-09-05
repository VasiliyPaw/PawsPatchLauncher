namespace PawsPatchLauncher;

public static class ConfigurationCode
{
    public static string Create(UserSettings settings)
    {
        var channel = settings.Channel.Equals("beta", StringComparison.OrdinalIgnoreCase) ? "BETA" : "STABLE";
        var spawn = settings.RoamingSpawnMode.Equals("x4", StringComparison.OrdinalIgnoreCase) ? "4" : "1";
        var oos = settings.DesyncMode.Equals("continue", StringComparison.OrdinalIgnoreCase) ? "1" : "0";
        return $"PAW-{channel}-IW{Bit(settings.IndependentHostility)}-SP{spawn}-RM{Bit(settings.AdditionalRoamingCompanies)}-SG{Bit(settings.SiegeBalance)}-LM{Bit(settings.LargeMapSizes)}-RU{Bit(settings.RussianLocalization)}-CL{Bit(settings.CustomPlayerColors)}-OOS{oos}";
    }

    private static int Bit(bool value) => value ? 1 : 0;
}
