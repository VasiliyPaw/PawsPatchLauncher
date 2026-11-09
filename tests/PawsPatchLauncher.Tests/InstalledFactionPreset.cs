using System.Security.Cryptography;
using System.Text.Json;
using PawsPatchLauncher;

internal static class InstalledFactionPreset
{
    internal static async Task RunAsync(string sourceGame, string output, string sourceCache, string voiceCache)
    {
        sourceGame = Path.GetFullPath(sourceGame); output = Path.GetFullPath(output);
        if (output.StartsWith(sourceGame + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
            || sourceGame.StartsWith(output + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new IOException("Choose a fresh output outside the installed game.");
        var beforeState = File.ReadAllBytes(Path.Combine(sourceGame, ".pawpatch/state.json"));
        if (Directory.Exists(output) && (!File.Exists(Path.Combine(output, "game/.pawpatch/state.json"))
            || !beforeState.SequenceEqual(File.ReadAllBytes(Path.Combine(output, "game/.pawpatch/state.json")))))
            throw new IOException("Existing output is not an unchanged source snapshot.");
        var sourceInstaller = new ModuleInstaller(sourceGame); var state = sourceInstaller.LoadState();
        var settings = state.AppliedSettings is { } applied
            ? JsonSerializer.Deserialize(JsonSerializer.Serialize(applied, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!
            : throw new IOException("No applied installed mod settings.");
        var release = state.ReleaseId ?? throw new IOException("The installed release is unknown.");
        var config = SettingsStore.LoadConfiguration(); config.CacheRoot = sourceCache;
        var sourceClient = new FeedClient(config); var channel = sourceClient.LoadArchived(release, settings.Channel);
        var originalLibrary = new ModLibrary(sourceGame).Find(settings.Mod, settings.Channel) ?? throw new IOException("The installed mod library is missing.");
        if (originalLibrary.ReleaseId != release) throw new IOException("The active and stored release differ.");
        var originalCode = FriendConfiguration.Create(settings);
        var game = Path.Combine(output, "game"); Directory.CreateDirectory(game);
        var copied = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        void CopyGameFile(string relative)
        {
            relative = CryptoAndIO.NormalizeRelativePath(relative);
            if (!copied.Add(relative)) return;
            var source = CryptoAndIO.SafeChildPath(sourceGame, relative); var target = CryptoAndIO.SafeChildPath(game, relative);
            if ((File.GetAttributes(source) & FileAttributes.ReparsePoint) != 0) throw new IOException("Linked game file: " + relative);
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            if (File.Exists(target))
            {
                if (!SHA256.HashData(File.ReadAllBytes(source)).SequenceEqual(SHA256.HashData(File.ReadAllBytes(target)))) throw new IOException("Existing snapshot file changed: " + relative);
            }
            else File.Copy(source, target);
        }
        void CopyTree(string source, string target)
        {
            if (!Directory.Exists(source)) return;
            if ((File.GetAttributes(source) & FileAttributes.ReparsePoint) != 0) throw new IOException("Linked source directory: " + source);
            Directory.CreateDirectory(target);
            foreach (var path in Directory.EnumerateFiles(source))
            {
                if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new IOException("Linked source file: " + path);
                File.Copy(path, Path.Combine(target, Path.GetFileName(path)), true);
            }
            foreach (var path in Directory.EnumerateDirectories(source)) CopyTree(path, Path.Combine(target, Path.GetFileName(path)));
        }
        foreach (var name in new[] { "k2.exe", "Data.rwd", "Music.rwd" }) CopyGameFile(name);
        foreach (var path in Directory.EnumerateFiles(sourceGame).Where(p => Path.GetExtension(p).Equals(".dll", StringComparison.OrdinalIgnoreCase)
            || Path.GetExtension(p).Equals(".ini", StringComparison.OrdinalIgnoreCase) || Path.GetFileName(p).Equals("steam_appid.txt", StringComparison.OrdinalIgnoreCase)))
            CopyGameFile(Path.GetFileName(path));
        foreach (var path in MultiplayerCheck.Expected(state).Where(p => p.Value is not null).Select(p => p.Key)) CopyGameFile(path);
        foreach (var folder in new[] { "mss", "skins", "Warchest", "Mods", "startup", "data/User" })
            CopyTree(Path.Combine(sourceGame, folder), Path.Combine(game, folder));
        CopyGameFile(".pawpatch/state.json");
        foreach (var original in state.Originals.Values.Where(p => p.BackupRelativePath is not null))
            CopyGameFile(".pawpatch/originals/" + original.BackupRelativePath);
        var retained = originalLibrary.Packages.Concat(channel.Packages.Where(p => state.Modules.ContainsKey(p.Id))).DistinctBy(p => p.Id).ToArray();
        foreach (var package in retained)
        {
            if (!sourceInstaller.IsPrepared(package)) throw new IOException("The stored component is unavailable: " + package.Id);
            CopyTree(Path.Combine(sourceGame, ".pawpatch/packages", package.Id, package.Version), Path.Combine(game, ".pawpatch/packages", package.Id, package.Version));
        }
        Console.WriteLine("COPIED_INSTALLED_MOD " + settings.Mod + " " + release + " " + copied.Count + " files; no mod archive download");
        var beforeFiles = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var path in copied.Where(p => !p.StartsWith(".pawpatch", StringComparison.OrdinalIgnoreCase)
            && !p.Replace('\\', '/').StartsWith("data/Audio/", StringComparison.OrdinalIgnoreCase)))
            beforeFiles[path] = await CryptoAndIO.Sha256Async(CryptoAndIO.SafeChildPath(game, path));
        settings.GamePath = game; settings.GameVoiceLanguage = "custom";
        settings.FactionVoiceLanguages = new() { ["royalist"] = "fr", ["council"] = "en", ["nationalist"] = "de", ["ceyah"] = "ru", ["fallen"] = "en", ["other"] = "ru" };
        settings.PinnedRelease = release; settings.PreparedChannel = settings.Channel; settings.PreparedFeedFingerprint = release;
        settings.ModNoticeSeen = true; ModChannelSelection.Remember(settings);
        var effective = EffectiveSettings.ForFeed(settings, channel);
        var selected = GamePackageSelector.Select(channel, effective, effective.RussianLocalization, effective.CustomPlayerColors);
        if (FriendConfiguration.Create(settings) != originalCode) throw new Exception("Gameplay settings changed during preset preparation.");
        var installer = new ModuleInstaller(game); var desired = new Dictionary<string, InstalledModule>();
        config.CacheRoot = voiceCache; var voices = new FeedClient(config);
        foreach (var package in selected)
        {
            if (!installer.IsPrepared(package))
            {
                if (!package.Id.StartsWith("game-voice-")) throw new Exception("Preset would require a mod reinstall: " + package.Id);
                desired[package.Id] = await installer.PrepareAsync(package, await voices.GetCachedPackageAsync(package));
            }
            else desired[package.Id] = await installer.PrepareAsync(package, "");
            if (state.Modules.TryGetValue(package.Id, out var old) && old.Version == desired[package.Id].Version && old.ArchiveSha256 == desired[package.Id].ArchiveSha256)
                desired[package.Id].DownloadedAt = old.DownloadedAt;
        }
        await installer.ReconcileAsync(desired, settings: effective, releaseId: release, gameRequirement: state.GameRequirement, baseGameSha256: state.BaseGameSha256);
        if ((await installer.VerifyAsync(allowCustomHotkeys: true)).Count != 0) throw new Exception("Prepared preset file verification failed.");
        if (UpdateDetector.HasSettingsChanges(installer.LoadState(), selected, effective)) throw new Exception("Prepared preset still requires Apply settings.");
        foreach (var (path, hash) in beforeFiles)
            if (!hash.Equals(await CryptoAndIO.Sha256Async(CryptoAndIO.SafeChildPath(game, path)), StringComparison.OrdinalIgnoreCase)) throw new Exception("Non-audio file changed: " + path);
        await new ModLibrary(game).RememberAsync(channel, settings.Mod); await new ModLibrary(game).RememberLanguagesAsync(selected);
        var profile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PawsPatchLauncher-FactionVoicesPresetTest-20261109");
        Directory.CreateDirectory(profile);
        var sourceSettingsPath = Path.Combine(sourceCache, "settings.json");
        if (File.Exists(sourceSettingsPath)) settings.Language = JsonSerializer.Deserialize(File.ReadAllText(sourceSettingsPath), LauncherJsonContext.Default.UserSettings)!.Language;
        var destinationSettings = Path.Combine(profile, "settings.json");
        if (File.Exists(destinationSettings)) File.Copy(destinationSettings, Path.Combine(output, "previous-test-settings.json"));
        await File.WriteAllTextAsync(destinationSettings, JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings));
        var archive = Path.Combine(profile, "cache/releases", release + ".json"); Directory.CreateDirectory(Path.GetDirectoryName(archive)!);
        File.Copy(Path.Combine(sourceCache, "releases", release + ".json"), archive, true);
        var finalConfig = SettingsStore.LoadConfiguration(); finalConfig.CacheRoot = Path.Combine(profile, "cache");
        var finalChannel = new FeedClient(finalConfig).LoadArchived(release, settings.Channel);
        foreach (var package in ModLibrary.Packages(finalChannel, settings.Mod))
            if (!installer.IsPrepared(package)) throw new Exception("Stored mod would not be ready offline: " + package.Id);
        var executable = GameExecutableSelector.Select(finalConfig, effective, finalChannel);
        var critical = await MultiplayerCheck.CriticalAsync(game, installer.LoadState(), Path.Combine(game, executable), state.GameRequirement ?? new GameRequirement());
        if (critical.Count != 0) throw new Exception("Critical game verification: " + string.Join("; ", critical.Take(4)));
        if (await FactionVoiceRuntime.PrepareAsync(game, effective) is null) throw new Exception("Faction routing was not armed.");
        if (!beforeState.SequenceEqual(File.ReadAllBytes(Path.Combine(sourceGame, ".pawpatch/state.json")))) throw new Exception("The source game state changed during the snapshot.");
        var proof = new { sourceGame, game, profile, settings.Mod, settings.Channel, release, gameplayUnchanged = true, nonAudioFilesUnchanged = beforeFiles.Count,
            sourceStateUnchanged = true, needsApply = false, modDownloads = 0, voices = settings.FactionVoiceLanguages, executable };
        await File.WriteAllTextAsync(Path.Combine(output, "preset-preparation.json"), JsonSerializer.Serialize(proof, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("INSTALLED_FACTION_PRESET_PASS " + beforeFiles.Count + " unchanged non-audio files; ready to launch; no mod reinstall");
    }
}
