namespace PawsPatchLauncher;

public static class ConfigurationCode
{
    public static UserSettings Parse(string code)
    {
        var voiceCode = code.Trim().ToUpperInvariant();
        if (voiceCode.EndsWith("-VOEN") || voiceCode.EndsWith("-VORU"))
        {
            var settings = Parse(voiceCode[..^5]);
            settings.GameVoiceLanguage = voiceCode[^2..].ToLowerInvariant();
            return settings;
        }
        var parts = code.Trim().ToUpperInvariant().Split('-');
        if (parts.Length >= 3 && parts[0] == "PAW" && parts[1] is "BETA" or "STABLE" && parts[2] is "VANILLA" or "IMMORTALS")
        {
            var mod = new UserSettings { Mod = parts[2] == "VANILLA" ? GameMod.Vanilla : GameMod.Immortals,
                Channel = parts[1].ToLowerInvariant(), RussianLocalization = false };
            var index = 3;
            if (index < parts.Length && parts[index] is "RU0" or "RU1") mod.RussianLocalization = parts[index++] == "RU1";
            if (index < parts.Length && parts[index] == "PP1") { GameMod.SetPawPatch(mod, true); index++; }
            if (index < parts.Length && parts[index] == "DATA" && (GameMod.PawPatchSelected(mod) || mod.Mod == GameMod.Immortals)) { mod.DataOnly = true; index++; }
            if (index != parts.Length) throw new FormatException("Invalid mod configuration field.");
            return EffectiveSettings.ForChannel(mod);
        }
        var core = parts.LastOrDefault() != "PP0";
        var dataOnly = parts.LastOrDefault() == "DATA";
        if (dataOnly) parts = parts[..^1];
        core = parts.LastOrDefault() != "PP0";
        if (!core) parts = parts[..^1];
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
            PawPatchEnabled = core,
            DataOnly = dataOnly,
            Channel = parts[1].ToLowerInvariant(), IndependentHostility = Flag(2, "IW"),
            AdditionalRoamingCompanies = Flag(4, "RM"), SiegeBalance = Flag(5, "SG"),
            LargeMapSizes = Flag(6, "LM"), RussianLocalization = Flag(7, "RU"),
            CustomPlayerColors = Flag(8, "CL"), DesyncMode = Flag(9, "OOS") ? "continue" : "official",
            DisablePowersAndShards = parts.Length == 10 || Flag(10, "PS"),
            RoamingSpawnMode = parts[3] switch { "SP4" => "x4", "SP2" => "x2", "SP1" => "standard", _ => throw new FormatException("Invalid SP field") }
        };
        if (result.LargeMapSizes != core)
            throw new FormatException("This combination is not supported by this launcher.");
        if (dataOnly && (result.CustomPlayerColors || result.IndependentHostility || result.DesyncMode != "official"))
            throw new FormatException("Executable features are not available in file-only mode.");
        return EffectiveSettings.ForChannel(result);
    }

    public static void Apply(UserSettings source, UserSettings target)
    {
        GameMod.Validate(source);
        ModChannelSelection.Remember(target);
        if (target.Mod != source.Mod || target.Channel != source.Channel) target.PinnedRelease = null;
        target.Channel = source.Channel;
        target.Mod = source.Mod;
        ModChannelSelection.Remember(target);
        target.RussianLocalization = source.RussianLocalization;
        target.GameVoiceLanguage = GameLanguages.Voice(source);
        // Importing another mod keeps remembered Arcane Wars components.
        if (!GameMod.IsArcaneWars(source))
        {
            GameMod.SetPawPatch(target, GameMod.PawPatchSelected(source));
            return;
        }
        GameMod.SetPawPatch(target, source.PawPatchEnabled);
        target.RussianLocalization = source.RussianLocalization;
        target.CustomPlayerColors = source.CustomPlayerColors;
        target.DesyncMode = source.DesyncMode;
        target.IndependentHostility = source.IndependentHostility;
        target.RoamingSpawnMode = source.RoamingSpawnMode;
        target.AdditionalRoamingCompanies = source.AdditionalRoamingCompanies;
        target.SiegeBalance = source.SiegeBalance;
        target.DisablePowersAndShards = source.DisablePowersAndShards;
        target.LargeMapSizes = source.PawPatchEnabled;
        if (!target.PawPatchEnabled) GameMod.DisableArcaneComponents(target);
    }

    public static string Create(UserSettings settings)
    {
        var code = CreateComponents(settings);
        return GameLanguages.Voice(settings) == (settings.RussianLocalization ? "ru" : "en")
            ? code : code + "-VO" + GameLanguages.Voice(settings).ToUpperInvariant();
    }

    private static string CreateComponents(UserSettings settings)
    {
        settings = EffectiveSettings.ForChannel(settings);
        var channel = settings.Channel.Equals("beta", StringComparison.OrdinalIgnoreCase) ? "BETA" : "STABLE";
        if (!GameMod.IsArcaneWars(settings)) return $"PAW-{channel}-{(GameMod.IsVanilla(settings) ? "VANILLA" : "IMMORTALS")}{(settings.RussianLocalization ? "-RU1" : "")}{(settings.PawPatchEnabled ? "-PP1" : "")}{(settings.DataOnly ? "-DATA" : "")}";
        var spawn = settings.RoamingSpawnMode.ToLowerInvariant() switch { "x4" => "4", "x2" => "2", _ => "1" };
        var oos = settings.DesyncMode.Equals("continue", StringComparison.OrdinalIgnoreCase) ? "1" : "0";
        // Legacy codes already mean powers/shards disabled; preserve their fingerprints.
        var powers = settings.DisablePowersAndShards ? "" : "-PS0";
        return $"PAW-{channel}-IW{Bit(settings.IndependentHostility)}-SP{spawn}-RM{Bit(settings.AdditionalRoamingCompanies)}-SG{Bit(settings.SiegeBalance)}-LM{Bit(settings.PawPatchEnabled)}-RU{Bit(settings.RussianLocalization)}-CL{Bit(settings.CustomPlayerColors)}-OOS{oos}{powers}{(settings.PawPatchEnabled ? "" : "-PP0")}{(settings.DataOnly ? "-DATA" : "")}";
    }

    private static int Bit(bool value) => value ? 1 : 0;
}
