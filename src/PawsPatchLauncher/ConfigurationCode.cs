namespace PawsPatchLauncher;

public static class ConfigurationCode
{
    public static UserSettings Parse(string code)
    {
        var parts = code.Trim().ToUpperInvariant().Split('-');
        if (parts.Length is not (10 or 11) || parts[0] != "PAW" || parts[1] is not ("BETA" or "STABLE"))
            throw new FormatException("PAW-STABLE-IW1-SP4-RM1-SG1-LM1-RU1-CL0-OOS0");
        bool Flag(int index, string prefix)
        {
            if (parts[index] == prefix + "0") return false;
            if (parts[index] == prefix + "1") return true;
            throw new FormatException("Invalid configuration field: " + prefix);
        }
        var result = new UserSettings
        {
            Channel = parts[1].ToLowerInvariant(), IndependentHostility = Flag(2, "IW"),
            AdditionalRoamingCompanies = Flag(4, "RM"), SiegeBalance = Flag(5, "SG"),
            LargeMapSizes = Flag(6, "LM"), RussianLocalization = Flag(7, "RU"),
            CustomPlayerColors = Flag(8, "CL"), DesyncMode = Flag(9, "OOS") ? "continue" : "official",
            DisablePowersAndShards = parts.Length == 10 || Flag(10, "PS"),
            RoamingSpawnMode = parts[3] switch { "SP4" => "x4", "SP1" => "standard", _ => throw new FormatException("Invalid SP field") }
        };
        if (!result.LargeMapSizes || result.CustomPlayerColors &&
            (result.Channel != "beta" || !result.IndependentHostility || result.DesyncMode != "official"))
            throw new FormatException("This combination is not supported by this launcher.");
        return result;
    }

    public static void Apply(UserSettings source, UserSettings target)
    {
        target.Channel = source.Channel;
        target.RussianLocalization = source.RussianLocalization;
        target.CustomPlayerColors = source.CustomPlayerColors;
        target.DesyncMode = source.DesyncMode;
        target.IndependentHostility = source.IndependentHostility;
        target.RoamingSpawnMode = source.RoamingSpawnMode;
        target.AdditionalRoamingCompanies = source.AdditionalRoamingCompanies;
        target.SiegeBalance = source.SiegeBalance;
        target.DisablePowersAndShards = source.DisablePowersAndShards;
        target.LargeMapSizes = true;
    }

    public static string Create(UserSettings settings)
    {
        settings = EffectiveSettings.ForChannel(settings);
        var channel = settings.Channel.Equals("beta", StringComparison.OrdinalIgnoreCase) ? "BETA" : "STABLE";
        var spawn = settings.RoamingSpawnMode.Equals("x4", StringComparison.OrdinalIgnoreCase) ? "4" : "1";
        var oos = settings.DesyncMode.Equals("continue", StringComparison.OrdinalIgnoreCase) ? "1" : "0";
        // Legacy codes already mean powers/shards disabled; preserve their fingerprints.
        var powers = settings.DisablePowersAndShards ? "" : "-PS0";
        return $"PAW-{channel}-IW{Bit(settings.IndependentHostility)}-SP{spawn}-RM{Bit(settings.AdditionalRoamingCompanies)}-SG{Bit(settings.SiegeBalance)}-LM1-RU{Bit(settings.RussianLocalization)}-CL{Bit(settings.CustomPlayerColors)}-OOS{oos}{powers}";
    }

    private static int Bit(bool value) => value ? 1 : 0;
}
