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
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (var channel in new[] { "stable", "beta" })
        foreach (var patch in new[] { false, true })
        foreach (var dataOnly in new[] { false, true })
        foreach (var textRu in new[] { false, true })
        foreach (var voice in new[] { "en", "ru" })
        {
            var source = new UserSettings { Mod = mod, Channel = channel, RussianLocalization = textRu, GameVoiceLanguage = voice, DataOnly = dataOnly };
            GameMod.SetPawPatch(source, patch);
            source = EffectiveSettings.ForChannel(source);
            var sourceCode = ConfigurationCode.Create(source);
            Check(FriendConfiguration.TryParse(sourceCode, channel, out var parsed), "split speech/file-only code rejected: " + sourceCode);
            Check(ConfigurationCode.Create(parsed) == sourceCode, "legacy language fields misread");
            var shared = FriendConfiguration.Create(source);
            Check(!shared.Contains("RU1") && !shared.Contains("-VO"), "personal language in shared configuration");
            foreach (var localMod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
            {
                var local = new UserSettings { Mod = localMod, RussianLocalization = !textRu, GameVoiceLanguage = voice == "ru" ? "en" : "ru", Language = "en", GamePath = @"C:\LocalGame" };
                var target = FriendConfiguration.WithLocalLanguages(parsed, local);
                Check(target.Mod == mod && target.Channel == channel && GameMod.PawPatchSelected(target) == patch, "copied the wrong mod/patch");
                Check(target.RussianLocalization == local.RussianLocalization && GameLanguages.Voice(target) == GameLanguages.Voice(local), "incoming language overwrote local preferences");
                Check(FriendConfiguration.Matches(source, target), "language-only difference requests another apply");
                Check(ConfigurationCode.Create(source) == sourceCode, "source configuration was mutated");
                ConfigurationCode.Apply(target, local);
                Check(local.Mod == mod && GameMod.PawPatchSelected(local) == patch && local.RussianLocalization == !textRu && GameLanguages.Voice(local) != voice,
                    "mod import failed or copied localization");
                Check(local.GamePath == @"C:\LocalGame" && local.Language == "en", "personal device settings overwritten");
            }
            var components = FriendConfiguration.Components(source);
            Check(!components.ContainsKey("russian") && components["core"] == patch, "wrong player card patch/language component");
            Check(mod == GameMod.ArcaneWars || components.Count == 1, "Arcane Wars components leaked into another mod card");
        }
        foreach (var invalid in new[] { valid + "-VOCS", valid + "-TXCS", valid + "-VORU-VOEN", valid + "-TXDE-TXFR", valid + "-VORU\n", valid + "-DATA-VORU-URL", "PAW-STABLE-VANILLA-DATA" })
            Check(!FriendConfiguration.TryParse(invalid, invalid.StartsWith("PAW-BETA-") ? "beta" : "stable", out _), "invalid extended configuration accepted");
        FriendConfiguration.TryParse(valid, "beta", out var settings);
        var feed = new ChannelManifest { Channel = "beta" };
        try { FriendConfiguration.ValidateFeed(settings, feed); Check(false, "unsupported feed accepted"); }
        catch (InvalidDataException) { Check(true, "unsupported feed rejected"); }
        Console.WriteLine($"FRIEND CONFIGURATION PASS {count}: exact options, all 768 combinations, local preferences, bounded input and unsupported feeds");
        return count;
    }
}
