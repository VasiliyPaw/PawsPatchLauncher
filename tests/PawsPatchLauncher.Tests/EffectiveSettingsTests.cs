using PawsPatchLauncher;

public static class EffectiveSettingsTests
{
    public static int Run()
    {
        var count = 0;
        void Check(bool result, string message) { if (!result) throw new Exception(message); count++; }
        var preferences = new UserSettings { Channel = "stable", CustomPlayerColors = true, DisablePowersAndShards = false };
        var release = new ChannelManifest { Channel = "stable" };
        var beta = new ChannelManifest { Channel = "beta", Packages = [new() { Id = "player-colors" }] };
        var active = EffectiveSettings.ForFeed(preferences, release);
        Check(preferences.CustomPlayerColors && !active.CustomPlayerColors, "Release mutated remembered Beta colors or left them active.");
        Check(!ReferenceEquals(active, preferences), "Effective configuration aliases remembered settings.");
        Check(!active.DisablePowersAndShards && active.RussianLocalization == preferences.RussianLocalization, "Unrelated choices were changed.");
        Check(!ConfigurationCode.Parse(ConfigurationCode.Create(preferences)).CustomPlayerColors, "Release friend code is not importable/effective.");
        Check(ConfigurationCode.Create(preferences) == ConfigurationCode.Create(active), "Remembered color changed the Release shared identity.");
        Check(!EffectiveSettings.ForFeed(preferences, beta).CustomPlayerColors, "Mismatched feed enabled Beta colors in Release.");
        preferences.Channel = "beta";
        Check(EffectiveSettings.ForFeed(preferences, beta).CustomPlayerColors, "Returning to Beta lost remembered colors.");
        Check(ConfigurationCode.Parse(ConfigurationCode.Create(EffectiveSettings.ForFeed(preferences, beta))).CustomPlayerColors, "Beta code lost active colors.");
        Check(!EffectiveSettings.ForFeed(preferences, new() { Channel = "beta" }).CustomPlayerColors, "Pinned Beta without a colors package advertised colors.");
        Check(!EffectiveSettings.ForFeed(preferences, null).CustomPlayerColors && preferences.CustomPlayerColors, "Unavailable feed changed remembered preference.");
        preferences.CustomPlayerColors = false;
        Check(!EffectiveSettings.ForFeed(preferences, beta).CustomPlayerColors, "Explicitly disabled Beta colors were enabled.");
        preferences.LargeMapSizes = false;
        Check(EffectiveSettings.ForFeed(preferences, beta).LargeMapSizes && !preferences.LargeMapSizes, "Permanent map option was not normalized independently.");
        var siege = PatchGuide.Entries.Single(e => e.Id == "siege");
        Check(siege.BodyRu.Contains("урон") && siege.BodyRu.Contains("не только") && siege.BodyEn.Contains("damage"), "Siege guide still describes cost only.");
        Console.WriteLine($"EFFECTIVE SETTINGS PASS {count}: active/remembered isolation, channel/package masking, importable codes, option preservation and siege scope");
        return count;
    }
}
