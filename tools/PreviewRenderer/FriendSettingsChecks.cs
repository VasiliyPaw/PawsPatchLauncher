using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class FriendSettingsChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Fixture only");
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        var checks = 0;
        void Check(bool ok, string why) { checks++; if (!ok) throw new Exception("Friend settings: " + why); }
        async Task Scenario(string scenario)
        {
            var w = new MainWindow();
            object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
            void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
            T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
            T Control<T>(string name) => (T)w.FindName(name);
            try
            {
                Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Invoke("ApplyLanguage"); SocialChecks.Populate(w, "details");
                var settings = Field<UserSettings>("_settings");
                settings.Channel = "stable"; settings.RoamingSpawnMode = "x4"; settings.GamePath = @"C:\fixture-local";
                settings.RussianLocalization = scenario == "same_localization";
                var baseline = ConfigurationCode.Create(settings);
                var game = Path.Combine(ActivityStore.Root, "friend-copy-game-" + Guid.NewGuid());
                Directory.CreateDirectory(game);
                Set("_game", new GameInstallation(game, Path.Combine(game, "k2.exe"), null, null));
                var running = false; Set("_gameRunningProbe", (Func<bool>)(() => running));
                var friend = Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p => p.Relation == "friend");
                Invoke("ShowSocialDetails", friend);
                var launch = Control<Button>("LaunchButton");
                running = true; Invoke("RefreshGameLaunchState");
                Check(!launch.IsEnabled && launch.Content.ToString() == (language == "ru" ? "Игра запущена" : "Game running"), "running launch button");
                Check(!Control<Button>("SocialDetailsCopyButton").IsEnabled, "copy enabled during game");
                running = false; Invoke("RefreshGameLaunchState"); Check(launch.IsEnabled, "launch remains disabled after exit");
                Set("_busy", true); Invoke("RefreshGameLaunchState"); Check(!launch.IsEnabled, "busy launch enabled");
                Check(!Control<Button>("AccountLogoutButton").IsEnabled, "logout enabled during apply"); Set("_busy", false);
                Set("_checkingFeed", true); Invoke("RefreshGameLaunchState"); Check(!launch.IsEnabled, "feed check launch enabled"); Set("_checkingFeed", false);
                Invoke("RefreshGameLaunchState");
                var content = (FrameworkElement)w.Content;
                foreach (var size in new[] { new Size(1440,900), new Size(1050,680) })
                {
                    content.Measure(size); content.Arrange(new Rect(size)); content.UpdateLayout();
                    foreach (var name in new[] { "SocialDetailsAvatar", "SocialDetailsClose", "SocialDetailsCopyButton" })
                    {
                        var view = Control<FrameworkElement>(name); var box = view.TransformToAncestor(content).TransformBounds(new Rect(view.RenderSize));
                        Check(box.Width > 20 && box.Left >= 0 && box.Right <= size.Width && box.Top >= 0 && box.Bottom <= size.Height, "clipped " + name);
                    }
                }
                Check(Control<StackPanel>("SocialDetailsComponents").Children.Count == 9, "component chips differ from Components tab");
                var feed = new ChannelManifest { Channel = "beta", ColorDesyncContinue = true, IndependentColorHostility = true,
                    Packages = new[] { "pawpatch-core", "player-colors", "localization-ru", "desync-continue", "roaming-profile-x2-with-new",
                        "roaming-profile-x2-no-new", "powers-shards-original" }.Select(id => new PackageRelease { Id=id, Required=id=="pawpatch-core" }).ToList() };
                var reads = 0; var applied = 0;
                Set("_friendSettingsReadOverride", (Func<Task<IReadOnlyList<SocialPlayer>>>)(() => {
                    reads++;
                    if (scenario == "network") throw new IOException("Fixture network failure");
                    IReadOnlyList<SocialPlayer> result = scenario == "removed" ? [] : [friend];
                    if (scenario == "changed" && reads == 3) result = [friend with { Configuration = friend.Configuration!.Replace("SP2","SP4") }];
                    return Task.FromResult(result);
                }));
                Set("_friendSettingsFeedOverride", (Func<string,Task<ChannelManifest?>>)(channel => {
                    Check(channel == "beta", "wrong channel requested");
                    if (scenario == "game_during_load") running = true;
                    return Task.FromResult<ChannelManifest?>(scenario == "unsupported" ? new ChannelManifest { Channel="beta" } : feed);
                }));
                Set("_friendSettingsApplyOverride", (Func<ChannelManifest,UserSettings,Func<Task>,Task>)(async (f,s,guard) => {
                    await guard();
                    if (scenario == "apply_failure") throw new IOException("Fixture install failure");
                    Check(s.Channel=="beta" && s.RoamingSpawnMode=="x2" && !s.DisablePowersAndShards && s.GamePath==@"C:\fixture-local", "wrong snapshot");
                    Check(ConfigurationCode.Create(settings)==baseline, "preferences changed before file commit"); applied++;
                }));
                if (scenario == "running") running = true;
                var task = (Task)Invoke("CopyFriendSettingsAsync")!;
                if (scenario != "running")
                {
                    Check(Control<Border>("ConfirmationOverlay").Visibility == Visibility.Visible && reads == 0 && applied == 0, "work started before confirmation");
                    Check(Control<Border>("SocialDetailsOverlay").Visibility == Visibility.Visible && !Control<Border>("SocialDetailsOverlay").IsEnabled, "details hidden instead of preserved under confirmation");
                    var localization=Control<CheckBox>("ConfirmationLocalizationToggle");
                    Check(localization.IsChecked==false && localization.Visibility==(scenario=="same_localization"?Visibility.Collapsed:Visibility.Visible), "localization opt-in default/visibility");
                    var diff=ConfigurationCode.Parse(friend.Configuration!);diff.RussianLocalization=settings.RussianLocalization;
                    Check(Control<TextBlock>("ConfirmationPathText").Text==string.Join("\n",ConfigurationChanges.Describe(settings,diff,language=="ru")), "confirmation missing actual changed components");
                    if(scenario=="localization")localization.IsChecked=true;
                    Check(LauncherIcon.GetKind(Control<Button>("ConfirmationDeleteButton"))==IconKind.Copy, "confirmation icon");
                    if (scenario == "account_changed")
                        Set("_account", new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root,"guest-"+Guid.NewGuid()))));
                    await (Task)Invoke("CompleteConfirmationAsync", scenario != "cancel")!;
                }
                await task;
                var successful=scenario is "success" or "localization" or "same_localization";
                var expected=ConfigurationCode.Parse(friend.Configuration!);expected.RussianLocalization=scenario is "localization" or "same_localization";
                Check(applied == (successful ? 1 : 0), "unexpected apply " + scenario);
                Check(ConfigurationCode.Create(settings) == (successful ? ConfigurationCode.Create(expected) : baseline), "incorrect preference commit " + scenario);
                if (scenario == "cancel") Check(Control<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible, "cancel did not return to details");
            }
            finally { w.Close(); }
        }
        var dispatcher = Dispatcher.CurrentDispatcher;
        SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(dispatcher));
        try
        {
            async Task All() { foreach (var s in new[] { "cancel", "running", "network", "removed", "changed", "game_during_load", "unsupported", "apply_failure", "account_changed", "success", "localization", "same_localization" }) await Scenario(s); }
            var task = All(); var frame = new DispatcherFrame(); var timeout = new DispatcherTimer { Interval = TimeSpan.FromSeconds(40) };
            timeout.Tick += (_,_) => frame.Continue=false; timeout.Start();
            _ = task.ContinueWith(_ => dispatcher.BeginInvoke(new Action(() => frame.Continue=false)));
            if (!task.IsCompleted) Dispatcher.PushFrame(frame);
            timeout.Stop(); if (!task.IsCompleted) throw new TimeoutException("Friend settings checks");
            task.GetAwaiter().GetResult();
            Console.WriteLine($"FRIEND SETTINGS UI PASS {checks} {language}: launch state, responsive details, cancel, network/game/account/friend changes, unsupported feed, failed/successful apply");
        }
        finally { SynchronizationContext.SetSynchronizationContext(null); }
    }
}
