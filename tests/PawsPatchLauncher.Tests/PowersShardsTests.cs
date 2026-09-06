using System.Text.Json;
using System.Text.RegularExpressions;
using PawsPatchLauncher;

public static class PowersShardsTests
{
    public static int Run()
    {
        int count = 0;
        void Check(bool valid, string message) { if (!valid) throw new Exception(message); count++; }
        var legacy = "PAW-STABLE-IW1-SP4-RM1-SG1-LM1-RU1-CL0-OOS0";
        Check(new UserSettings().DisablePowersAndShards, "Powers removal must default on.");
        Check(JsonSerializer.Deserialize("{}", LauncherJsonContext.Default.UserSettings)!.DisablePowersAndShards, "Legacy stored settings lost the default.");
        Check(ConfigurationCode.Create(new UserSettings()) == legacy, "Default legacy code/fingerprint changed.");
        Check(ConfigurationCode.Parse(legacy).DisablePowersAndShards, "Old friend codes must keep powers disabled.");
        foreach (var channel in new[] { "stable", "beta" })
        foreach (var disabled in new[] { false, true })
        {
            var settings = new UserSettings { Channel = channel, DisablePowersAndShards = disabled };
            var restored = ConfigurationCode.Parse(ConfigurationCode.Create(settings));
            Check(restored.DisablePowersAndShards == disabled && restored.Channel == channel, "Configuration roundtrip lost the powers option.");
            var saved = JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!;
            Check(saved.DisablePowersAndShards == disabled, "Persisted settings lost the powers option.");
            var target = new UserSettings(); ConfigurationCode.Apply(settings, target);
            Check(target.DisablePowersAndShards == disabled, "Import/recovery did not apply the powers option.");
        }
        foreach (var suffix in new[] { "-PS2", "-XX0", "-PS", "-PS0-PS1" })
        {
            var rejected = false; try { ConfigurationCode.Parse(legacy + suffix); } catch (FormatException) { rejected = true; }
            Check(rejected, "Malformed powers field accepted.");
        }
        Check(ConfigurationCode.Parse(legacy + "-PS1").DisablePowersAndShards, "Explicit disabled code was rejected.");
        var feed = new ChannelManifest { Packages = [
            new() { Id = "arcane-wars", Required = true }, new() { Id = "pawpatch-core", Required = true },
            new() { Id = "localization-ru" }, new() { Id = "powers-shards-original", Priority = 450, DependsOn = ["arcane-wars", "pawpatch-core"] }] };
        var before = new UserSettings();
        var after = new UserSettings { DisablePowersAndShards = false };
        var off = GamePackageSelector.Select(feed, before, false, false);
        var on = GamePackageSelector.Select(feed, after, false, false);
        Check(off.Count == 2 && on.Count == 3 && on.Any(p => p.Id == "powers-shards-original"), "Wrong overlay selection.");
        var state = new InstallState { Modules = off.ToDictionary(p => p.Id, p => new InstalledModule { Enabled = true, Version = p.Version, Priority = p.Priority, ArchiveSha256 = p.Sha256 }) };
        Check(!UpdateDetector.HasModuleChanges(state, off) && UpdateDetector.HasModuleChanges(state, on), "Launch pre-apply cannot detect powers changes.");
        state.Modules["powers-shards-original"] = new InstalledModule { Enabled = true, Version = on[^1].Version, Priority = 450 };
        Check(UpdateDetector.HasModuleChanges(state, off), "Switching removal back on leaves the overlay installed.");
        feed.Packages.RemoveAt(feed.Packages.Count - 1);
        var missing = false; try { GamePackageSelector.Select(feed, after, false, false); } catch (InvalidDataException) { missing = true; }
        Check(missing, "Missing restoration package silently ignored.");
        MultiplayerManifest Report(UserSettings settings)
        {
            var report = new MultiplayerManifest { Configuration = ConfigurationCode.Create(settings), GameBuild = "25068126", Executable = "k2.exe",
                Files = [new() { Path = "k2.exe", Sha256 = new string('A', 64) }] };
            report.Fingerprint = MultiplayerDetails.Fingerprint(report); return report;
        }
        foreach (var (a,b) in new[] { (before,after), (after,before) })
        {
            var diff = MultiplayerDetails.Compare(Report(a), Report(b));
            Check(!diff.Matches && diff.Differences.Count == 1 && diff.Differences[0].Name == "Disable Powers and Shards", "Mixed old/new reports lost the precise powers difference.");
        }
        Check(!PatchGuide.Entries.Any(e => e.Id == "placement"), "Placement entry was not removed.");
        Check(PatchGuide.Entries.Single(e => e.Id == "powers-shards").Category == "optional", "Powers is still described as mandatory.");
        var colors = PatchGuide.Entries.Single(e => e.Id == "colors");
        Check(!colors.BodyRu.Contains("удален", StringComparison.OrdinalIgnoreCase) && !colors.BodyRu.Contains("удалены") && !colors.BodyEn.Contains("removed") && !colors.BodyEn.Contains("renamed"), "Color change history remains in feature descriptions.");
        var maps = PatchGuide.Entries.Single(e => e.Id == "maps");
        Check(maps.BodyRu.Contains("вылетам") && maps.BodyEn.Contains("crashes") && maps.BodyRu.Contains("1152×1152"), "Largest-map crash warning missing.");
        Console.WriteLine($"POWERS POLICY PASS {count}: legacy defaults, settings/import/recovery, code compatibility, package selection, pre-launch detection and detailed comparison");
        return count;
    }

    public static async Task VerifyPackagesAsync(string stablePath, string betaPath, string publicKey, string outputRoot, string? previousFeedDirectory = null)
    {
        var root = Path.Combine(Path.GetFullPath(outputRoot), Guid.NewGuid().ToString("N"));
        // Fail before extracting packages if the fixture cannot exercise safe uninstall.
        RemovalSafety.CheckNoLinks(root);
        Directory.CreateDirectory(root);
        Console.WriteLine("POWERS FIXTURE START " + root);
        var config = new LauncherConfiguration { FeedUrls = [Path.GetFullPath(stablePath)], BetaFeedUrls = [Path.GetFullPath(betaPath)],
            PublicKeyPem = await File.ReadAllTextAsync(publicKey), CacheRoot = Path.Combine(root, "cache") };
        var client = new FeedClient(config);
        foreach (var channelName in new[] { "stable", "beta" })
        {
            var channel = await client.GetChannelAsync(channelName) ?? throw new Exception("Missing channel");
            var game = Path.Combine(root, channelName, "Kohan II"); Directory.CreateDirectory(game);
            await File.WriteAllTextAsync(Path.Combine(game, "k2.exe"), "fixture sentinel; never launched");
            await File.WriteAllTextAsync(Path.Combine(game, "personal-save.rsg"), "save sentinel");
            var installer = new ModuleInstaller(game);
            var prepared = new Dictionary<string, InstalledModule>();
            foreach (var package in channel.Packages)
            {
                prepared.Add(package.Id, await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null)));
                Console.WriteLine($"POWERS PREPARED {channelName} {package.Id}");
            }
            var powers = prepared["powers-shards-original"];
            if (powers.Files.Count != 160 || powers.Remove.Count != 0) throw new Exception("Unexpected restoration file set.");
            var paths = powers.Files.Select(f => f.Path).ToHashSet(StringComparer.OrdinalIgnoreCase);
            foreach (var module in prepared.Where(p => p.Key is not ("arcane-wars" or "pawpatch-core" or "powers-shards-original")))
                if (module.Value.Files.Any(f => paths.Contains(f.Path)) || module.Value.Remove.Any(paths.Contains)) throw new Exception("Powers conflicts with " + module.Key);
            foreach (var disabled in new[] { false, true, false, true })
            {
                // Exercise alternate roaming/siege/language/color selections too.
                var settings = new UserSettings { Channel = channelName, DisablePowersAndShards = disabled,
                    RussianLocalization = channelName == "beta", CustomPlayerColors = channelName == "beta",
                    RoamingSpawnMode = disabled ? "standard" : "x4", AdditionalRoamingCompanies = disabled, SiegeBalance = disabled };
                var selected = GamePackageSelector.Select(channel, settings, settings.RussianLocalization, settings.CustomPlayerColors);
                var modules = selected.ToDictionary(p => p.Id, p => prepared[p.Id]);
                Console.WriteLine($"POWERS APPLY START {channelName} disabled={disabled}");
                await installer.ReconcileAsync(modules, settings: settings, releaseId: ChannelFingerprint.Create(channel));
                Console.WriteLine($"POWERS APPLY COMPLETE {channelName} disabled={disabled}; verifying");
                if ((await installer.VerifyAsync()).Count != 0) throw new Exception("Files differ after powers reconciliation.");
                if (installer.LoadState().AppliedSettings!.DisablePowersAndShards != disabled) throw new Exception("Applied powers setting was not saved.");
                var resources = await File.ReadAllTextAsync(Path.Combine(game, "data/Game/resource_list.tgi"));
                if (Regex.IsMatch(resources, @"(?m)^\s*fixed shards\b") == disabled) throw new Exception("Resource registration does not match the selected option.");
                var faction = await File.ReadAllTextAsync(Path.Combine(game, "data/Factions/royalist.tgi"));
                if (faction.Contains("NoPowers patch:") != disabled) throw new Exception("Faction abilities do not match the selected option.");
                var expectation = MultiplayerCheck.Expected(installer.LoadState());
                foreach (var path in paths)
                {
                    var source = disabled ? prepared["pawpatch-core"] : powers;
                    if (expectation[path]!.Sha256 != source.Files.Single(f => f.Path.Equals(path, StringComparison.OrdinalIgnoreCase)).Sha256)
                        throw new Exception("Wrong winning module for " + path);
                }
                if (UpdateDetector.HasModuleChanges(installer.LoadState(), selected)) throw new Exception("Applied option still appears pending.");
                Console.WriteLine($"POWERS INSTALL PASS {channelName} disabled={disabled}: 160 exact files, all module hashes, resources/factions, applied settings, cache-only transition");
            }
            var recovery = new PatchRecovery(game);
            await recovery.RollbackAsync(installer.LoadState());
            if (installer.LoadState().AppliedSettings!.DisablePowersAndShards || (await installer.VerifyAsync()).Count != 0) throw new Exception("Rollback failed to restore powers and its settings.");
            if (previousFeedDirectory is not null)
                await VerifyLocalizationUpgradeAsync(channelName, channel, prepared, installer, game, config, previousFeedDirectory);
            await installer.UninstallAsync();
            if (await File.ReadAllTextAsync(Path.Combine(game, "personal-save.rsg")) != "save sentinel"
                || await File.ReadAllTextAsync(Path.Combine(game, "k2.exe")) != "fixture sentinel; never launched") throw new Exception("Uninstall damaged original/user data.");
            Console.WriteLine("POWERS RECOVERY / UNINSTALL PASS " + channelName);
        }
        Console.WriteLine("POWERS FIXTURES RETAINED " + root + "; game never launched");
    }

    private static async Task VerifyLocalizationUpgradeAsync(string channelName, ChannelManifest channel,
        Dictionary<string, InstalledModule> prepared, ModuleInstaller installer, string game,
        LauncherConfiguration configuration, string previousFeedDirectory)
    {
        var oldClient = new FeedClient(new LauncherConfiguration {
            FeedUrls = [Path.GetFullPath(Path.Combine(previousFeedDirectory, "stable.signed.json"))],
            BetaFeedUrls = [Path.GetFullPath(Path.Combine(previousFeedDirectory, "beta.signed.json"))],
            PublicKeyPem = configuration.PublicKeyPem, CacheRoot = configuration.CacheRoot });
        var oldFeed = await oldClient.GetChannelAsync(channelName) ?? throw new Exception("Missing previous candidate feed.");
        var repairedIds = new[] { "roaming-profile-x4-no-new", "roaming-profile-standard-no-new", "siege-balance-standard" };
        var oldPrepared = new Dictionary<string, InstalledModule>(prepared);
        foreach (var id in repairedIds)
        {
            var package = oldFeed.Packages.Single(p => p.Id == id);
            oldPrepared[id] = await installer.PrepareAsync(package, await oldClient.DownloadVerifiedAsync(package, null));
            if (oldPrepared[id].Version == prepared[id].Version) throw new Exception("Upgrade test needs distinct package versions.");
        }
        foreach (var spawn in new[] { "x4", "standard" })
        {
            var settings = new UserSettings { Channel = channelName, RussianLocalization = true,
                AdditionalRoamingCompanies = false, SiegeBalance = false, RoamingSpawnMode = spawn };
            var oldSelection = GamePackageSelector.Select(oldFeed, settings, true, false);
            var newSelection = GamePackageSelector.Select(channel, settings, true, false);
            await installer.ReconcileAsync(oldSelection.ToDictionary(p => p.Id, p => oldPrepared[p.Id]), settings: settings, releaseId: ChannelFingerprint.Create(oldFeed));
            if (!UpdateDetector.HasModuleChanges(installer.LoadState(), newSelection)) throw new Exception("Localized package upgrade not detected.");
            var oldState = MultiplayerCheck.Expected(installer.LoadState());
            await installer.ReconcileAsync(newSelection.ToDictionary(p => p.Id, p => prepared[p.Id]), settings: settings, releaseId: ChannelFingerprint.Create(channel));
            if ((await installer.VerifyAsync()).Count != 0 || UpdateDetector.HasModuleChanges(installer.LoadState(), newSelection)) throw new Exception("Upgrade did not reach a verified current state.");
            var expected = MultiplayerCheck.Expected(installer.LoadState());
            var checkedPaths = 0;
            foreach (var id in newSelection.Select(p => p.Id).Where(repairedIds.Contains))
            foreach (var file in prepared[id].Files)
            {
                var coreFile = prepared["pawpatch-core"].Files.SingleOrDefault(f => f.Path.Equals(file.Path, StringComparison.OrdinalIgnoreCase));
                if (coreFile is null) continue;
                var corePath = Path.Combine(game, ".pawpatch", "packages", "pawpatch-core", prepared["pawpatch-core"].Version, "payload", coreFile.Path);
                var coreText = await File.ReadAllTextAsync(corePath);
                var installedText = await File.ReadAllTextAsync(Path.Combine(game, file.Path));
                var keys = Regex.Matches(coreText, @"#awloc_[A-Za-z0-9_]+").Select(m => m.Value).Distinct().ToArray();
                if (keys.Any(k => !installedText.Contains(k))) throw new Exception("Installed translation reference missing: " + file.Path);
                if (keys.Length > 0) checkedPaths++;
                if (expected[file.Path]?.Sha256 != file.Sha256) throw new Exception("Repaired overlay lost precedence.");
            }
            if (checkedPaths < 13) throw new Exception("Translation upgrade fixture missed affected files.");
            await new PatchRecovery(game).RollbackAsync(installer.LoadState());
            var restored = MultiplayerCheck.Expected(installer.LoadState());
            if ((await installer.VerifyAsync()).Count != 0 || restored.Count != oldState.Count || oldState.Any(p => restored[p.Key]?.Sha256 != p.Value?.Sha256))
                throw new Exception("Old package rollback did not restore exact previous bytes.");
            Console.WriteLine($"LOCALIZATION UPGRADE / ROLLBACK PASS {channelName} {spawn}: options.1 -> options.2, {checkedPaths} localized overlay files; exact old installation restored");
        }
    }
}
