using System.IO.Compression;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class CustomVoiceTests
{
    static async Task<System.Diagnostics.Process> ExitedLauncherAsync(int code)
    {
        var start = new System.Diagnostics.ProcessStartInfo(Environment.ProcessPath!)
        { UseShellExecute = false, CreateNoWindow = true, WindowStyle = System.Diagnostics.ProcessWindowStyle.Hidden, RedirectStandardInput = true };
        if (Path.GetFileNameWithoutExtension(start.FileName).Equals("dotnet", StringComparison.OrdinalIgnoreCase))
            start.ArgumentList.Add(typeof(CustomVoiceTests).Assembly.Location);
        start.ArgumentList.Add("--exit-code-probe");
        var child = System.Diagnostics.Process.Start(start)!;
        try
        {
            await child.StandardInput.WriteLineAsync(code.ToString(System.Globalization.CultureInfo.InvariantCulture)); child.StandardInput.Close();
            await child.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(15));
            if (child.ExitCode != code) throw new Exception("Owned launcher exit probe failed");
            return child;
        }
        catch { if (!child.HasExited) child.Kill(); child.Dispose(); throw; }
    }

    internal static async Task<int> RunReadinessAsync(string root)
    {
        var checks = 0;
        void Check(bool ok, string why) { if (!ok) throw new Exception("Faction readiness: " + why); checks++; }
        var settings = new UserSettings { Mod = GameMod.ArcaneWars, PawPatchEnabled = true };
        var state = new InstallState { AppliedSettings = settings };
        var core = new InstalledModule { Enabled = true, Version = "0.5.1-beta.1" };
        state.Modules["pawpatch-core"] = core;
        // A loose INI is deliberately present without a declared capability.
        await File.WriteAllTextAsync(Path.Combine(root, "paws_presentation.ini"), "[Runtime]\nstartupReadyEvent=1\n");
        Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "old-helper.exe"), "loose INI made an old helper wait");
        core.Files.Add(new ModuleFile { Path = "paws_presentation.ini" });
        Check(FactionVoiceRuntime.RequiresPresentationReady(state, "new-helper.exe"), "managed Arcane capability was ignored");
        core.Version = "0.0.0";
        Check(FactionVoiceRuntime.RequiresPresentationReady(state, "new-helper.exe"), "capability incorrectly depends on a version label");
        Check(!FactionVoiceRuntime.RequiresPresentationReady(state, Path.Combine(root, "K2.EXE")), "raw k2.exe waits for a helper event");
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals })
        {
            settings.Mod = mod; GameMod.SetPawPatch(settings, true);
            Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "unmigrated Pure helper waits for Arcane capability");
            var pure = new InstalledModule { Enabled = true, Version = "0.5.0" };
            state.Modules["pure-fixes-runtime"] = pure;
            Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "old Pure runtime without capability waits");
            pure.Files.Add(new ModuleFile { Path = "paws_presentation.ini" });
            Check(FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "new Pure capability ignored in " + mod);
            Check(!FactionVoiceRuntime.RequiresPresentationReady(state, Path.Combine(root, "k2.exe")), "raw Pure k2.exe waits for a helper event");
            settings.PawPatchEnabled = false;
            Check(FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "inactive Arcane master flag overrides Pure selection");
            settings.PawPatchEnabled = true; GameMod.SetPawPatch(settings, false);
            Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "disabled Pure patch waits despite Arcane master flag");
            GameMod.SetPawPatch(settings, true); settings.DataOnly = true;
            Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "Pure data-only waits for a helper event");
            settings.DataOnly = false; pure.Enabled = false;
            Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "disabled Pure runtime supplies capability");
            pure.Enabled = true; pure.Files[0].Path = "data/paws_presentation.ini";
            Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "wrong Pure capability path is accepted");
            state.Modules.Remove("pure-fixes-runtime");
            Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "pure-helper.exe"), "inactive Arcane owner supplies Pure capability");
        }
        settings.Mod = GameMod.ArcaneWars; settings.PawPatchEnabled = false;
        Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "helper.exe"), "disabled patch requires an event");
        settings.PawPatchEnabled = true; settings.DataOnly = true;
        Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "helper.exe"), "data-only mode requires an event");
        settings.DataOnly = false; core.Enabled = false;
        Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "helper.exe"), "disabled module supplies capability");
        core.Enabled = true; core.Files[0].Path = "data/paws_presentation.ini";
        Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "helper.exe"), "different manifest path supplies capability");
        core.Files[0].Path = "PAWS_PRESENTATION.INI";
        Check(FactionVoiceRuntime.RequiresPresentationReady(state, "helper.exe"), "Windows manifest path casing changes capability");
        state.Modules.Remove("pawpatch-core"); state.Modules["common-ui"] = core;
        Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "helper.exe"), "unrelated package supplies core capability");
        state.Modules["pawpatch-core"] = core; state.AppliedSettings = null;
        Check(!FactionVoiceRuntime.RequiresPresentationReady(state, "helper.exe"), "missing installed settings supply capability");

        using var game = System.Diagnostics.Process.GetCurrentProcess();
        var ticks = game.StartTime.ToUniversalTime().Ticks;
        var name = FactionVoiceRuntime.PresentationReadyEventName(game.Id, ticks);
        Check(name == "Local\\PawPresentationReady-" + game.Id.ToString(System.Globalization.CultureInfo.InvariantCulture) + "-" + ticks.ToString(System.Globalization.CultureInfo.InvariantCulture), "event key is not game PID plus UTC ticks");
        Check(!FactionVoiceRuntime.PresentationReady(game), "absent event is ready");
        var unexpectedlyCreated = EventWaitHandle.TryOpenExisting(name, out var absent);
        absent?.Dispose(); Check(!unexpectedlyCreated, "launcher created the helper event");
        using (var stale = new EventWaitHandle(true, EventResetMode.ManualReset, FactionVoiceRuntime.PresentationReadyEventName(game.Id, ticks - 1)))
            Check(!FactionVoiceRuntime.PresentationReady(game), "stale signaled event bypassed readiness");
        using (var ready = new EventWaitHandle(false, EventResetMode.ManualReset, name))
        {
            Check(!FactionVoiceRuntime.PresentationReady(game), "unsignaled event is ready");
            ready.Set(); Check(FactionVoiceRuntime.PresentationReady(game), "signaled event is not ready");
            Check(FactionVoiceRuntime.PresentationReady(game), "launcher consumed/reset a manual-reset event");
        }
        using (var syncOnly = new EventWaitHandle(false, EventResetMode.ManualReset, name))
        {
            var security = new EventWaitHandleSecurity(); security.SetAccessRuleProtection(true, false);
            security.AddAccessRule(new EventWaitHandleAccessRule(WindowsIdentity.GetCurrent().User!, EventWaitHandleRights.Synchronize, AccessControlType.Allow));
            syncOnly.SetAccessControl(security);
            // The producer's existing handle retains Modify; a fresh consumer
            // may only wait. This ACL is confined to our temporary test object.
            Check(!FactionVoiceRuntime.PresentationReady(game), "wait-only unsignaled event is ready");
            syncOnly.Set();
            Check(FactionVoiceRuntime.PresentationReady(game), "wait-only consumer requires unnecessary Modify rights");
            try
            {
                var opened = EventWaitHandle.TryOpenExisting(name, out var excessRights);
                excessRights?.Dispose(); Check(!opened, "synchronize-only ACL unexpectedly grants Modify");
            }
            catch (UnauthorizedAccessException) { Check(true, "default Modify open denied as expected"); }
        }
        using var failed = await ExitedLauncherAsync(23);
        foreach (var phase in new[] { "waiting-for-game", "waiting-for-helper-ready", "waiting-for-native-code", "waiting-for-audio-definitions" })
        {
            try { FactionVoiceRuntime.EnsureLauncherSucceeded(failed, phase); Check(false, "failed helper ignored in " + phase); }
            catch (FactionVoiceException error)
            { Check(error.Code == "faction-voice-startup" && error.InnerException!.Message.Contains(phase) && error.InnerException.Message.Contains("23"), "wrong helper failure phase/code"); }
        }
        using var succeeded = await ExitedLauncherAsync(0);
        FactionVoiceRuntime.EnsureLauncherSucceeded(succeeded, "waiting-for-audio-definitions");
        FactionVoiceRuntime.EnsureLauncherSucceeded(null, "waiting-for-game");
        Check(true, "successful/no helper rejected");
        Console.WriteLine($"FACTION READINESS PASS {checks}: mode-owned Arcane/Pure capability, raw/old/disabled paths, synchronize-only ACL, absent/stale/unsignaled/ready events and failed helper in every startup phase");
        return checks;
    }

    internal static async Task RebuildInstalledAsync(string directory)
    {
        var installer = new ModuleInstaller(directory); var state = installer.LoadState();
        var settings = state.AppliedSettings ?? throw new Exception("Missing installed settings");
        var desired = new Dictionary<string, InstalledModule>();
        var unchanged = new Dictionary<string, string>();
        foreach (var (id, installed) in state.Modules.Where(p => !CustomVoices.IsGenerated(p.Key)))
        {
            var module = await installer.ReadPreparedAsync(new PackageRelease { Id = id, Version = installed.Version, Sha256 = installed.ArchiveSha256, Priority = installed.Priority });
            module.DownloadedAt = installed.DownloadedAt; module.Enabled = installed.Enabled; desired[id] = module;
            foreach (var file in installed.Files.Where(f => !f.Path.Replace('\\', '/').StartsWith("data/Audio/", StringComparison.OrdinalIgnoreCase)))
                unchanged[file.Path] = await CryptoAndIO.Sha256Async(CryptoAndIO.SafeChildPath(directory, file.Path));
        }
        await installer.ReconcileAsync(desired, settings: settings, releaseId: state.ReleaseId, gameRequirement: state.GameRequirement, baseGameSha256: state.BaseGameSha256,
            ensureGameClosed: () => { if (System.Diagnostics.Process.GetProcessesByName("k2").Length != 0) throw new Exception("Close the game before regenerating speech definitions."); });
        if ((await installer.VerifyAsync()).Count != 0) throw new Exception("Rebuilt speech file verification failed");
        foreach (var (path, hash) in unchanged)
            if (hash != await CryptoAndIO.Sha256Async(CryptoAndIO.SafeChildPath(directory, path))) throw new Exception("Non-audio file changed: " + path);
        var table = File.ReadAllText(Path.Combine(directory, "data/Audio/paws_faction_voices.tgi"));
        if (!table.StartsWith("[Audio") || table.Contains("// Local faction speech")) throw new Exception("Invalid generated TGI prefix");
        Console.WriteLine("INSTALLED FACTION REBUILD PASS: cached components only; generated TGI has no unsupported comment; " + unchanged.Count + " non-audio hashes unchanged; installed files verified");
    }

    internal static async Task RunInstalledLaunchAsync(string directory, string helper)
    {
        directory = Path.GetFullPath(directory);
        var path = Path.Combine(directory, "k2.exe");
        if (System.Diagnostics.Process.GetProcessesByName("k2").Any(p => p.MainModule?.FileName.Equals(path, StringComparison.OrdinalIgnoreCase) == true))
            throw new Exception("The test game is already running.");
        var state = new ModuleInstaller(directory).LoadState();
        var plan = await FactionVoiceRuntime.PrepareAsync(directory, state.AppliedSettings ?? throw new Exception("Missing installed settings"));
        var started = DateTimeOffset.UtcNow;
        using var launcher = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(Path.Combine(directory, helper))
        { WorkingDirectory = directory, UseShellExecute = false, CreateNoWindow = true, WindowStyle = System.Diagnostics.ProcessWindowStyle.Hidden })!;
        try
        {
            await FactionVoiceRuntime.InstallAsync(directory, plan, started, launcher);
            await Task.Delay(10000);
            using var game = System.Diagnostics.Process.GetProcessesByName("k2").Single(p => p.StartTime.ToUniversalTime() >= started.UtcDateTime.AddSeconds(-1)
                && p.MainModule?.FileName.Equals(path, StringComparison.OrdinalIgnoreCase) == true);
            if (game.HasExited || game.MainWindowHandle == IntPtr.Zero) throw new Exception("Real game did not remain open after faction speech setup.");
            Console.WriteLine("INSTALLED FACTION LAUNCH PASS: shipped helper, real k2.exe, registered parallel audio definitions, installed native dispatch, visible game window; process=" + game.Id);
        }
        finally
        {
            foreach (var game in System.Diagnostics.Process.GetProcessesByName("k2"))
            using (game)
                if (game.StartTime.ToUniversalTime() >= started.UtcDateTime.AddSeconds(-1) && game.MainModule?.FileName.Equals(path, StringComparison.OrdinalIgnoreCase) == true)
                { game.Kill(); await game.WaitForExitAsync(); }
            if (!launcher.HasExited) { launcher.Kill(); await launcher.WaitForExitAsync(); }
        }
    }

    internal static async Task RunHookFixtureAsync(string executable, string output)
    {
        Directory.CreateDirectory(output); var marker = Path.Combine(Path.GetFullPath(output), Guid.NewGuid().ToString("N"));
        using var child = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(executable)
        { ArgumentList = { marker }, UseShellExecute = false, CreateNoWindow = true, WindowStyle = System.Diagnostics.ProcessWindowStyle.Hidden, RedirectStandardOutput = true, RedirectStandardError = true })!;
        try
        {
            var ready = await child.StandardOutput.ReadLineAsync().WaitAsync(TimeSpan.FromSeconds(15));
            if (ready is null || !ready.StartsWith("READY ")) throw new Exception("Owned native fixture did not start");
            var image = uint.Parse(ready[6..]);
            var open = typeof(FactionVoiceRuntime).GetMethod("OpenProcess", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)!;
            using var handle = (Microsoft.Win32.SafeHandles.SafeProcessHandle)open.Invoke(null, new object[] { 0x438u, false, child.Id })!;
            if (!(bool)typeof(FactionVoiceRuntime).GetMethod("HasVoiceDefinitions", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)!.Invoke(null, new object[] { handle, image })!) throw new Exception("Registered native cue preflight failed");
            var settings = new UserSettings { GameVoiceLanguage = "custom" }; CustomVoices.Initialize(settings, "en"); settings.FactionVoiceLanguages["royalist"] = "ru";
            var payload = FactionVoiceRuntime.Build(image, 0x10000000, settings);
            byte[] CallBytes() => (byte[])typeof(FactionVoiceRuntime).GetMethod("Read", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)!.Invoke(null, new object[] { handle, image + (uint)payload.Site, payload.Guard.Length })!;
            var phase = "waiting-for-game";
            if (FactionVoiceRuntime.TryInstall(handle, child, image, settings, true, null, ref phase) || !CallBytes().SequenceEqual(payload.Guard)) throw new Exception("Native patch installed without helper readiness despite registered cues");
            using var readyEvent = new EventWaitHandle(false, EventResetMode.ManualReset,
                FactionVoiceRuntime.PresentationReadyEventName(child.Id, child.StartTime.ToUniversalTime().Ticks));
            if (FactionVoiceRuntime.TryInstall(handle, child, image, settings, true, null, ref phase) || !CallBytes().SequenceEqual(payload.Guard)) throw new Exception("Native patch installed before helper signal");
            using (var failed = await ExitedLauncherAsync(23))
            {
                readyEvent.Set();
                try { FactionVoiceRuntime.TryInstall(handle, child, image, settings, true, failed, ref phase); throw new Exception("Failed helper installed native patch"); }
                catch (FactionVoiceException) { if (!CallBytes().SequenceEqual(payload.Guard)) throw new Exception("Failed helper changed native call"); }
                readyEvent.Reset();
            }
            readyEvent.Set();
            if (!FactionVoiceRuntime.TryInstall(handle, child, image, settings, true, null, ref phase)) throw new Exception("Native patch did not install after helper signal");
            await Task.Delay(300); File.WriteAllText(marker + ".done", "done");
            await child.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(15)); var text = await child.StandardOutput.ReadToEndAsync();
            if (child.ExitCode != 0 || !text.Contains("NATIVE_CALLS_OK")) throw new Exception("Native fixture failed: " + child.ExitCode + " " + text + await child.StandardError.ReadToEndAsync());
            Console.WriteLine("FACTION VOICE WINDOWS INSTALL PASS: live 32-bit fixture; ready audio alone cannot install; absent/unsignaled event and failed helper preserve native call; signaled event permits guarded installation and continued real x86 calls");
        }
        finally { if (!child.HasExited) child.Kill(); }
    }

    internal static async Task RunPublishedAsync(string sourceGame, string output, string repository)
    {
        var root = Path.GetFullPath(output);
        if (Directory.Exists(root)) throw new IOException("Choose a fresh isolated directory.");
        var config = JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(repository, "src/PawsPatchLauncher/launcher.config.json")), LauncherJsonContext.Default.LauncherConfiguration)!;
        var envelope = JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(repository, "feed/v3/stable.json")), LauncherJsonContext.Default.SignedFeedEnvelope)!;
        var raw = Convert.FromBase64String(envelope.Payload);
        if (!CryptoAndIO.VerifySignature(raw, envelope.Signature, config.PublicKeyPem)) throw new Exception("Invalid catalog signature");
        var feed = JsonSerializer.Deserialize(raw, LauncherJsonContext.Default.ChannelManifest)!;
        var game = Path.Combine(root, "game"); Directory.CreateDirectory(game);
        File.Copy(Path.Combine(sourceGame, "Data.rwd"), Path.Combine(game, "Data.rwd"));
        config.CacheRoot = Environment.GetEnvironmentVariable("PAWS_TEST_VOICE_CACHE") ?? Path.Combine(root, "cache");
        var client = new FeedClient(config); var installer = new ModuleInstaller(game); var modules = new Dictionary<string, InstalledModule>();
        foreach (var package in feed.Packages.Where(p => p.Id.StartsWith("game-voice-")))
            modules[package.Id] = await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null));
        var settings = new UserSettings { Mod = GameMod.Vanilla, PawPatchEnabled = false, GameVoiceLanguage = "custom" };
        foreach (var (group, language) in CustomVoices.Groups.Zip(new[] { "ru", "fr", "de", "en", "fr", "ru" })) settings.FactionVoiceLanguages[group] = language;
        var checks = 0;
        void Check(bool ok, string why) { if (!ok) throw new Exception("Published faction voices: " + why); checks++; }
        async Task Apply()
        {
            var selected = CustomVoices.SelectedLanguages(settings).Where(v => v != "en").Select(v => "game-voice-" + v).ToDictionary(id => id, id => modules[id]);
            await installer.ReconcileAsync(selected, settings: settings);
            Check((await installer.VerifyAsync()).Count == 0, "installed hashes differ");
        }
        await Apply();
        var state = installer.LoadState(); var generated = state.Modules[CustomVoices.ModuleId];
        Check(generated.Files.Count > 4000, "all parallel languages were not staged");
        foreach (var (id, module) in modules)
        foreach (var file in module.Files)
        {
            var path = file.Path.Replace('\\', '/')[11..];
            var installed = Path.Combine(game, FactionVoiceResources.NamespacePath(id[11..], path));
            Check(File.Exists(installed) && (await CryptoAndIO.Sha256Async(installed)).Equals(file.Sha256, StringComparison.OrdinalIgnoreCase), "parallel voice resource differs");
        }
        var table = File.ReadAllText(Path.Combine(game, "data/Audio/paws_faction_voices.tgi"));
        Check(table.StartsWith("[Audio") && !table.Contains("// Local faction speech"), "generated TGI contains an unsupported line comment");
        foreach (System.Text.RegularExpressions.Match list in System.Text.RegularExpressions.Regex.Matches(table, @"(?im)^\s*files\s*=\s*([^\r\n]+)"))
        foreach (var path in list.Groups[1].Value.Split(',').Select(p => p.Trim()))
            Check(File.Exists(Path.Combine(game, "data/Audio", path)), "generated cue references a missing file");
        Check(table.Contains("paws_voice_en_swordsman_select") && table.Contains("paws_voice_fr_swordsman_select"), "the same human cue does not offer both faction languages");
        var version = generated.Version;
        settings.FactionVoiceLanguages["royalist"] = "de"; await Apply();
        Check(installer.LoadState().Modules[CustomVoices.ModuleId].Version == version, "changing faction preferences rebuilt parallel recordings");
        settings.GameVoiceLanguage = "fr"; await Apply();
        Check(!installer.LoadState().Modules.ContainsKey(CustomVoices.ModuleId) && !File.Exists(Path.Combine(game, "data/Audio/paws_faction_voices.tgi")), "ordinary speech left faction definitions active");
        settings.GameVoiceLanguage = "en"; await Apply();
        settings.GameVoiceLanguage = "custom"; await Apply();
        var damaged = installer.LoadState().Modules[CustomVoices.ModuleId].Files.First(f => f.Path.EndsWith(".wav", StringComparison.OrdinalIgnoreCase));
        await File.WriteAllTextAsync(Path.Combine(game, damaged.Path), "damaged fixture");
        Check((await installer.VerifyAsync()).Count > 0, "damaged recording was not detected"); await Apply();
        await installer.UninstallAsync(); Check(!File.Exists(Path.Combine(game, "data/Audio/paws_faction_voices.tgi")), "uninstall left generated definitions");
        Console.WriteLine($"PUBLISHED FACTION VOICES PASS {checks}: signed RU/DE/FR packages, parallel languages and cue references, preference reuse, standard/custom switching, repair and uninstall; source game unchanged");
    }

    internal static async Task<int> RunAsync(string root)
    {
        var count = 0;
        void Check(bool ok, string why) { if (!ok) throw new Exception("Custom voices: " + why); count++; }
        count += await FactionVoiceCommentTests.RunAsync(root);
        count += await RunReadinessAsync(root);
        var settings = new UserSettings { Mod = GameMod.Vanilla, GameVoiceLanguage = "ru" };
        foreach (var alreadyMoved in new[] { false, true })
        {
            var game = Path.Combine(root, "migration-" + alreadyMoved);
            var cache = Path.Combine(game, ".pawpatch/packages", alreadyMoved ? CustomVoices.ModuleId : CustomVoices.LegacyModuleId, "abc123");
            Directory.CreateDirectory(cache);
            var manifest = new ModuleArchiveManifest { Id = CustomVoices.LegacyModuleId, Version = "abc123" };
            await File.WriteAllTextAsync(Path.Combine(cache, "module.json"), JsonSerializer.Serialize(manifest, LauncherJsonContext.Default.ModuleArchiveManifest));
            await File.WriteAllTextAsync(Path.Combine(cache, "retained-audio"), "existing recordings");
            var installed = new InstallState { AppliedSettings = settings };
            installed.Modules[CustomVoices.LegacyModuleId] = new InstalledModule { Version = "abc123", Enabled = true };
            await File.WriteAllTextAsync(Path.Combine(game, ".pawpatch/state.json"), JsonSerializer.Serialize(installed, LauncherJsonContext.Default.InstallState));
            var installer = new ModuleInstaller(game);
            await FactionVoiceRuntime.PrepareAsync(game, settings);
            var migrated = installer.LoadState();
            Check(migrated.Modules.ContainsKey(CustomVoices.ModuleId) && !migrated.Modules.ContainsKey(CustomVoices.LegacyModuleId), "legacy speech identity was not migrated");
            var newCache = Path.Combine(game, ".pawpatch/packages", CustomVoices.ModuleId, "abc123");
            Check(await File.ReadAllTextAsync(Path.Combine(newCache, "retained-audio")) == "existing recordings", "migration replaced prepared recordings");
            Check(JsonSerializer.Deserialize(await File.ReadAllTextAsync(Path.Combine(newCache, "module.json")), LauncherJsonContext.Default.ModuleArchiveManifest)!.Id == CustomVoices.ModuleId, "migration left an obsolete cache identity");
            var snapshot = await File.ReadAllTextAsync(Path.Combine(game, ".pawpatch/state.json"));
            await installer.MigrateFactionVoiceModuleAsync();
            Check(await File.ReadAllTextAsync(Path.Combine(game, ".pawpatch/state.json")) == snapshot, "migration is not idempotent");
        }
        CustomVoices.Initialize(settings, "ru"); settings.GameVoiceLanguage = "custom";
        settings.FactionVoiceLanguages["royalist"] = "fr"; settings.FactionVoiceLanguages["ceyah"] = "en";
        settings.FactionVoiceLanguages["council"] = "de";
        var original = CustomVoices.Signature(settings);
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (var voice in GameLanguages.VoiceChoices)
        {
            settings.Mod = mod; settings.GameVoiceLanguage = voice;
            var saved = JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!;
            CustomVoices.Initialize(saved, voice); saved.GameVoiceLanguage = "custom";
            Check(CustomVoices.Signature(saved) == original, "regular voice/mod/save/restart discarded the remembered setup");
            var imported = ConfigurationCode.Parse(ConfigurationCode.Create(saved));
            Check(CustomVoices.Signature(imported) == original, "configuration code lost the custom setup");
        }
        settings.Mod = GameMod.Vanilla; settings.GameVoiceLanguage = "custom";
        var copied = FriendConfiguration.WithLocalLanguages(new UserSettings(), settings);
        Check(CustomVoices.Signature(copied) == original && !ReferenceEquals(copied.FactionVoiceLanguages, settings.FactionVoiceLanguages), "copying a player replaced or aliased local voices");
        Check(!FriendConfiguration.Create(settings).Contains("-VF"), "personal voices leaked into the social configuration");
        var target = JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!;
        ConfigurationCode.Apply(new UserSettings { Mod = GameMod.Vanilla, GameVoiceLanguage = "en" }, target);
        target.GameVoiceLanguage = "custom";
        Check(CustomVoices.Signature(target) == original, "importing a regular voice erased inactive choices");
        var before = JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!; settings.FactionVoiceLanguages["royalist"] = "de";
        Check(UpdateDetector.HasSettingsChanges(new InstallState { AppliedSettings = before }, [], settings), "a changed faction in the same package set is not pending");
        before.GameVoiceLanguage = settings.GameVoiceLanguage = "en";
        Check(!UpdateDetector.HasSettingsChanges(new InstallState { AppliedSettings = before }, [], settings), "inactive custom preferences require reinstalling a regular voice");

        foreach (var (image, cave) in new[] { (0x460000u, 0x10000000u), (0x15000000u, 0x29000000u) })
        {
            settings.GameVoiceLanguage = "custom";
            var native = FactionVoiceRuntime.Build(image, cave, settings);
            Check(native.Guard.SequenceEqual(Convert.FromHexString("e88c87d5ff")), "native call guard changed");
            Check(BitConverter.ToUInt32(native.Bytes, native.State + 4) == image, "native image relocation failed");
            for (var i = 0; i < CustomVoices.Groups.Count; i++)
                Check(BitConverter.ToUInt32(native.Bytes, native.State + 8 + i * 4) == GameLanguages.VoiceChoices.ToList().IndexOf(CustomVoices.Language(settings, CustomVoices.Groups[i])), "native faction map changed");
        }
        Check(CustomVoices.SelectedLanguages(settings).SequenceEqual(GameLanguages.VoiceChoices), "custom speech did not request parallel language packs");
        Check(FriendlyErrors.Describe(new FactionVoiceException("faction-voice-version")).Code == "faction-voice-version", "unsupported native game has no explanation");
        foreach (var language in new[] { "uk", "cs", "de", "fr" })
            Check(UiLanguages.GameLanguageName("custom", language) != "Custom" && CustomVoices.Groups.All(g => CustomVoices.Label(g, language).Length > 0), "missing UI translation");
        Console.WriteLine($"CUSTOM VOICES PASS {count}: persisted inactive setup, codes, social isolation, faction-native payloads and relocated maps");
        return count;
    }
}
