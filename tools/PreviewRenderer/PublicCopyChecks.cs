using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class PublicCopyChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Fixture only");
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        var checks = 0;
        void Check(bool ok, string why) { if (!ok) throw new Exception("Public copy: " + why); checks++; }
        async Task Scenario(string scenario)
        {
            var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(ActivityStore.Root, "cache") }, null);
            object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
            void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
            T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
            T C<T>(string name) => (T)w.FindName(name);
            try
            {
                Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Call("ApplyLanguage"); SocialChecks.Populate(w, "details");
                var local = Field<UserSettings>("_settings"); local.Mod = GameMod.ArcaneWars; local.Channel = "stable";
                local.GameVoiceLanguage = "custom"; CustomVoices.Initialize(local, "fr"); local.FactionVoiceLanguages["royalist"] = "ru";
                var voices = CustomVoices.Signature(local);
                var game = Path.Combine(ActivityStore.Root, "public-copy-" + Guid.NewGuid()); Directory.CreateDirectory(game);
                Set("_game", new GameInstallation(game, Path.Combine(game, "k2.exe"), null, null)); Set("_gameRunningProbe", (Func<bool>)(() => false));
                var feed = new ChannelManifest { Channel = "beta", CompanyBehaviorRevision = 1, ColorDesyncContinue = true, IndependentColorHostility = true,
                    Packages = new[] { "arcane-wars", "pawpatch-core", "player-colors", "localization-ru", "desync-continue", "roaming-profile-x2-with-new",
                        "roaming-profile-x2-no-new", "powers-shards-original", "ai-improvements", "game-voice-ru", "game-voice-de", "game-voice-fr" }
                        .Select(id => new PackageRelease { Id = id, Version = "2.0.0", Sha256 = new string('A', 64), Required = id == "pawpatch-core" }).ToList() };
                var incoming = new UserSettings { Channel = "beta", RoamingSpawnMode = "x2", DisablePowersAndShards = false, ImprovedAi = false };
                var peer = new SocialPlayer(Guid.NewGuid(), "openprofile", "none", Presence: "online", Channel: "beta", IsFriend: false,
                    Configuration: FriendConfiguration.Create(incoming), Versions: new SocialVersions(SelfUpdater.CurrentVersion.ToString(), incoming.Mod, "beta",
                        ModLibrary.ContentId(feed, incoming.Mod), PawPatchVersions.ForChannel(feed, incoming.Mod)));
                if (scenario == "hidden") peer = peer with { Configuration = null, ConfigurationHidden = true };
                var reads = 0; var applied = 0;
                Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)Array.Empty<SocialPlayer>());
                Set("_friendLauncherVersionOverride", (Func<Task<string>>)(() => Task.FromResult(SelfUpdater.CurrentVersion.ToString())));
                Set("_friendSettingsFeedOverride", (Func<string, Task<ChannelManifest?>>)(_ => Task.FromResult<ChannelManifest?>(feed)));
                Set("_friendSettingsReadOverride", (Func<Task<IReadOnlyList<SocialPlayer>>>)(() => throw new Exception("Nonfriend copy used friendship authorization")));
                Set("_publicProfileReadOverride", (Func<Guid, CancellationToken, Task<SocialPlayer>>)((id, _) =>
                {
                    Check(id == peer.Id, "revalidation requested another player"); reads++;
                    if (scenario == "blocked_later") throw new AccountException("profile_blocked");
                    return Task.FromResult(scenario == "hidden_later" ? peer with { ConfigurationHidden = true, Configuration = null }
                        : scenario == "changed_later" ? peer with { Configuration = FriendConfiguration.Create(new UserSettings()) } : peer);
                }));
                Set("_friendSettingsApplyOverride", (Func<ChannelManifest, UserSettings, Func<Task>, Task>)(async (_, snapshot, guard) =>
                {
                    await guard(); Check(CustomVoices.Signature(snapshot) == voices, "copy replaced local faction speech"); applied++;
                }));
                ((AccountSession)typeof(AccountService).GetField("_session", flags)!.GetValue(Field<AccountService>("_account"))!).PawsTeam = true;
                Call("ObserveFriendVersionCatalog", feed, SelfUpdater.CurrentVersion.ToString()); Call("ShowAuthorizedPublicProfile", peer);
                Check(w.FindName("CompareProfileButton") is null, "comparison button remains");
                if (scenario == "already_applied")
                {
                    Set("_friendCopyAppliedState", new InstallState { AppliedSettings = incoming }); Set("_friendCopyAppliedVersions", peer.Versions);
                    Set("_fileCheckFailed", false); Set("_installationFailure", null); Call("RefreshSocialCopyAvailability");
                    Check(!C<Button>("SocialDetailsCopyButton").IsEnabled && C<Button>("SocialDetailsCopyButton").Content.ToString() == UiLanguages.Text(language, "Конфигурации совпадают", "Configurations match"), "matching stranger configuration is not explained");
                }
                else Check(scenario == "hidden" ? C<Button>("SocialDetailsCopyButton").Visibility == Visibility.Collapsed : C<Button>("SocialDetailsCopyButton").IsEnabled,
                    "public copy eligibility is wrong for " + scenario);
                if (scenario != "hidden") { var verify = FriendConfiguration.WithLocalLanguages(ConfigurationCode.Parse(peer.Configuration!), local); FriendConfiguration.ValidateFeed(verify, feed); }
                var task = (Task)Call("CopyFriendSettingsAsync")!;
                if (scenario is "hidden" or "already_applied") Check(task.IsCompleted && reads == 0, "hidden or matching settings started copying");
                else
                {
                    for (var i = 0; i < 300 && !task.IsCompleted && !C<Button>("ConfirmationDeleteButton").IsEnabled; i++) await Task.Delay(10);
                    Check(!task.IsCompleted && reads == 0 && applied == 0, "public preflight " + scenario + " completed=" + task.IsCompleted + " reads=" + reads + " applied=" + applied + " result=" + Field<OperationFeedback>("_feedback").Message);
                    await (Task)Call("CompleteConfirmationAsync", true)!;
                }
                await task;
                Check(applied == (scenario == "success" ? 1 : 0), "unexpected public apply for " + scenario);
                Check(CustomVoices.Signature(local) == voices, "local remembered voices were lost");
                if (scenario == "success") Check(reads >= 3 && local.Channel == "beta", "public settings were not rechecked and committed");
            }
            finally { w.Close(); }
        }
        var dispatcher = Dispatcher.CurrentDispatcher; SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(dispatcher));
        try
        {
            async Task All() { foreach (var scenario in new[] { "success", "hidden", "already_applied", "hidden_later", "blocked_later", "changed_later" }) await Scenario(scenario); }
            var task = All(); var frame = new DispatcherFrame(); var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(40) };
            timer.Tick += (_, _) => frame.Continue = false; _ = task.ContinueWith(_ => dispatcher.BeginInvoke(() => frame.Continue = false));
            timer.Start(); if (!task.IsCompleted) Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Public copy UI"); task.GetAwaiter().GetResult();
            Console.WriteLine($"PUBLIC COPY UI PASS {checks} {language}: nonfriends, hidden/matching settings, revoked access and preserved local voices");
        }
        finally { SynchronizationContext.SetSynchronizationContext(null); }
    }
}
