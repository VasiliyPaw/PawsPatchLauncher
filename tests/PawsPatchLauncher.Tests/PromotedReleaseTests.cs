using PawsPatchLauncher;

public static class PromotedReleaseTests
{
    public static int Run()
    {
        var count = 0;
        void Check(bool value, string message) { if (!value) throw new Exception(message); count++; }
        foreach (var channel in new[] { "stable", "beta" })
        {
            var feed = new ChannelManifest { Channel = channel, ColorDesyncContinue = true, IndependentColorHostility = true,
                Packages = [new() { Id = "player-colors" }, new() { Id = "common-ui", Required = true }] };
            Check(GameExecutableSelector.SupportsIndependentColors(feed), "Independent colors unavailable.");
            Check(GameExecutableSelector.SupportsColorDesyncContinue(feed), "Combined bypass unavailable.");
            for (var bits = 0; bits < 256; bits++)
            {
                bool B(int bit) => (bits & (1 << bit)) != 0;
                var settings = new UserSettings { Channel = channel, RussianLocalization = B(0), CustomPlayerColors = B(1),
                    DesyncMode = B(2) ? "continue" : "official", IndependentHostility = B(3), RoamingSpawnMode = B(4) ? "x4" : "standard",
                    AdditionalRoamingCompanies = B(5), SiegeBalance = B(6), DisablePowersAndShards = B(7) };
                var active = EffectiveSettings.ForFeed(settings, feed);
                var code = ConfigurationCode.Create(active);
                var parsed = ConfigurationCode.Parse(code);
                Check(ConfigurationCode.Create(parsed) == code && parsed.CustomPlayerColors == settings.CustomPlayerColors
                    && parsed.IndependentHostility == settings.IndependentHostility && parsed.DesyncMode == settings.DesyncMode,
                    "A released setting was silently changed: " + code);
                var exe = GameExecutableSelector.Select(new(), B(1), B(2), B(3), true, true);
                Check(exe.Contains("nohostility") == (B(1) && !B(3)), "Colors selected family-enabled helper when disabled.");
            }
        }
        Check(!GameExecutableSelector.SupportsIndependentColors(new() { Channel = "beta", ColorDesyncContinue = true }), "Old feed enabled missing variants.");
        Check(PatchGuide.Current().Version == "0.2.0" && PatchGuide.Entries.All(e => e.Category != "beta"), "Beta feature left unpromoted.");
        Check(PatchGuide.Entries.Single(e => e.Id == "colors").Category == "optional", "Released colors not configurable.");
        Check(PatchGuide.Entries.Single(e => e.Id == "badge-lighting").Category == "always", "Seven badge fixes not mandatory.");
        Console.WriteLine($"PROMOTED RELEASE PASS {count}: 512 independent configurations, both channels, friend-code round trips and guide");
        return count;
    }
}
