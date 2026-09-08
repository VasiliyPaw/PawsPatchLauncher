using PawsPatchLauncher;

public static class FriendConfigurationTests
{
    public static int Run()
    {
        var count = 0;
        void Check(bool ok, string why) { count++; if (!ok) throw new Exception("Friend configuration: " + why); }
        foreach (var channel in new[] { "stable", "beta" })
        foreach (var spawn in new[] { "standard", "x2", "x4" })
        for (var mask = 0; mask < 128; mask++)
        {
            var original = new UserSettings { Channel = channel, RoamingSpawnMode = spawn,
                IndependentHostility = (mask & 1) != 0, RussianLocalization = (mask & 2) != 0,
                CustomPlayerColors = (mask & 4) != 0, DesyncMode = (mask & 8) != 0 ? "continue" : "official",
                AdditionalRoamingCompanies = (mask & 16) != 0, SiegeBalance = (mask & 32) != 0, DisablePowersAndShards = (mask & 64) != 0 };
            var code = ConfigurationCode.Create(original);
            Check(FriendConfiguration.TryParse(code, channel, out var restored), "valid snapshot denied");
            Check(ConfigurationCode.Create(restored) == code && restored.RoamingSpawnMode == spawn, "roundtrip lost options");
            var local = new UserSettings { GamePath = @"C:\LocalGame", Language = "en", Channel = "stable" };
            ConfigurationCode.Apply(restored, local);
            Check(local.GamePath == @"C:\LocalGame" && local.Language == "en" && ConfigurationCode.Create(local) == code, "personal options overwritten");
        }
        const string valid = "PAW-BETA-IW0-SP2-RM1-SG0-LM1-RU1-CL1-OOS1-PS0";
        foreach (var invalid in new[] { "", valid + "\n", valid + "-URL-https://example.com", valid.Replace("SP2", "SP3"),
            valid.Replace("LM1", "LM0"), valid.ToLowerInvariant(), new string('x', 129) })
            Check(!FriendConfiguration.TryParse(invalid, "beta", out _), "malformed accepted");
        Check(!FriendConfiguration.TryParse(valid, "stable", out _), "mismatched channel accepted");
        Check(!FriendConfiguration.TryParse(null, "unknown", out _), "legacy data guessed");
        FriendConfiguration.TryParse(valid, "beta", out var settings);
        var feed = new ChannelManifest { Channel = "beta" };
        try { FriendConfiguration.ValidateFeed(settings, feed); Check(false, "unsupported feed accepted"); }
        catch (InvalidDataException) { Check(true, "unsupported feed rejected"); }
        Console.WriteLine($"FRIEND CONFIGURATION PASS {count}: exact options, all 768 combinations, local preferences, bounded input and unsupported feeds");
        return count;
    }
}
