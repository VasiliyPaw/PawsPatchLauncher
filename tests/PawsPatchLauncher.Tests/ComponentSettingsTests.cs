using PawsPatchLauncher;
using System.Text.Json;

internal static class ComponentSettingsTests
{
    public static int Run()
    {
        var count = 0;
        void Check(bool ok, string detail) { count++; if (!ok) throw new Exception(detail); }
        var ids = new[] { "arcane-wars", "pawpatch-core", "startup-base", "common-ui", "localization-ru",
            "player-colors", "desync-continue", "roaming-profile-standard-with-new", "roaming-profile-standard-no-new",
            "roaming-profile-x4-no-new", "roaming-profile-x2-with-new", "roaming-profile-x2-no-new", "siege-balance-standard", "powers-shards-original" };
        var feed = new ChannelManifest { ColorDesyncContinue = true, IndependentColorHostility = true,
            Packages = ids.Select((id, i) => new PackageRelease { Id = id, Version = "1", Sha256 = new string((char)('A' + i % 6), 64),
                Required = i < 4, Priority = i }).ToList() };
        InstallState Installed(UserSettings settings) => new() { AppliedSettings = settings,
            Modules = GamePackageSelector.Select(feed, settings, settings.RussianLocalization, settings.CustomPlayerColors)
            .ToDictionary(p => p.Id, p => new InstalledModule { Enabled = true, Version = p.Version, ArchiveSha256 = p.Sha256, Priority = p.Priority }) };
        UserSettings Clone(UserSettings settings) => JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!;
        foreach (var channel in new[] { "stable", "beta" })
        foreach (var spawn in new[] { "standard", "x2", "x4" })
        for (var bits = 0; bits < 128; bits++)
        {
            bool Bit(int n) => (bits & 1 << n) != 0;
            var settings = new UserSettings { Channel = channel, RoamingSpawnMode = spawn,
                RussianLocalization = Bit(0), CustomPlayerColors = Bit(1), DesyncMode = Bit(2) ? "continue" : "official",
                IndependentHostility = Bit(3), AdditionalRoamingCompanies = Bit(4), SiegeBalance = Bit(5), DisablePowersAndShards = Bit(6) };
            var state = Installed(settings);
            var selected = GamePackageSelector.Select(feed, settings, settings.RussianLocalization, settings.CustomPlayerColors);
            Check(ConfigurationCode.Create(ConfigurationCode.Parse(ConfigurationCode.Create(settings))) == ConfigurationCode.Create(settings), "SP2 friend-code round trip");
            Check(!UpdateDetector.HasSettingsChanges(state, selected, settings), "Unchanged selection pending");
            var changed = Clone(settings); changed.IndependentHostility = !settings.IndependentHostility;
            Check(UpdateDetector.HasSettingsChanges(state, selected, changed), "Native-only hostility lost");
            changed.IndependentHostility = settings.IndependentHostility; changed.Channel = channel == "stable" ? "beta" : "stable";
            changed.Language = "en"; changed.PreparedChannel = "old";
            Check(!UpdateDetector.HasSettingsChanges(state, selected, changed), "Revert/channel/UI preference marked pending");
            Check(!UpdateDetector.NeedsDownload(state, selected, _ => false), "Identical installed files need download");
            if (spawn == "x2")
                Check(selected.Count(p => p.Id.StartsWith("roaming-profile-")) == 1
                    && selected.Any(p => p.Id == "roaming-profile-x2-" + (settings.AdditionalRoamingCompanies ? "with-new" : "no-new")), "x2 not composed");
        }
        var baseline = new UserSettings();
        var previous = Installed(baseline);
        var desired = GamePackageSelector.Select(feed, baseline, true, false);
        var extraOption = feed.Packages.Single(p => p.Id == "roaming-profile-x2-with-new");
        Check(!UpdateDetector.HasRemoteUpdate(previous, [..desired, extraOption], _ => false), "Enabling uncached option misreported as new patch");
        Check(UpdateDetector.NeedsDownload(previous, [..desired, extraOption], _ => false), "Uncached option not downloadable through Apply");
        var update = desired.First(); update.Sha256 = new string('F', 64);
        Check(UpdateDetector.HasModuleChanges(previous, desired), "Changed archive not pending");
        Check(UpdateDetector.NeedsDownload(previous, desired, _ => false), "New remote version has no update button");
        Check(!UpdateDetector.NeedsDownload(previous, desired, _ => true), "Cached channel asks to redownload");
        Check(UpdateDetector.HasModuleChanges(previous, desired), "Cached channel fails to require application");
        var persisted = JsonSerializer.Deserialize(JsonSerializer.Serialize(previous, LauncherJsonContext.Default.InstallState), LauncherJsonContext.Default.InstallState)!;
        Check(UpdateDetector.HasSettingsChanges(persisted, desired, baseline), "Restart loses installed baseline");
        Console.WriteLine($"COMPONENT SETTINGS PASS {count}: 768 combinations, x2 joint profiles, SP2, apply/revert/native changes, channel/cache/restart");
        return count;
    }
}
