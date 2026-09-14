using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using System.Windows.Media;
using System.Windows.Media.Imaging;
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
            Console.WriteLine("Friend copy scenario: " + scenario);
            var w = new MainWindow();
            object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
            void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
            T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
            T Control<T>(string name) => (T)w.FindName(name);
            try
            {
                Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Invoke("ApplyLanguage"); SocialChecks.Populate(w, "details");
                var settings = Field<UserSettings>("_settings");
                settings.Mod = GameMod.ArcaneWars; settings.Channel = "stable"; settings.RoamingSpawnMode = "x4"; settings.GamePath = @"C:\fixture-local";
                settings.RussianLocalization = scenario == "same_localization";
                settings.GameVoiceLanguage = scenario == "split_localization" ? "ru" : "en";
                var game = Path.Combine(ActivityStore.Root, "friend-copy-game-" + Guid.NewGuid());
                Directory.CreateDirectory(game);
                Set("_game", new GameInstallation(game, Path.Combine(game, "k2.exe"), null, null));
                var running = false; Set("_gameRunningProbe", (Func<bool>)(() => running));
                var friend = Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p => p.Relation == "friend");
                if (scenario is "immortals" or "vanilla")
                {
                    var incoming = new UserSettings { Mod = scenario, Channel = "beta", RussianLocalization = true, GameVoiceLanguage = "en" };
                    GameMod.SetPawPatch(incoming, true);
                    friend = friend with { Configuration = ConfigurationCode.Create(incoming) };
                    Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)[friend]);
                }
                if (scenario == "inactive_update") settings.Mod = GameMod.Vanilla;
                if (scenario == "equal_update") ConfigurationCode.Apply(ConfigurationCode.Parse(friend.Configuration!), settings);
                var baseline = ConfigurationCode.Create(settings);
                Invoke("ShowSocialDetails", friend);
                ((AccountSession)typeof(AccountService).GetField("_session",flags)!.GetValue(Field<AccountService>("_account"))!).PawsTeam=true;
                Set("_patchInstalled",true); Set("_settingsPending",false);
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
                Check(Control<StackPanel>("SocialDetailsComponents").Children.Count == (scenario is "immortals" or "vanilla" ? 1 : 8), "wrong mod's components in player card");
                if (scenario is "immortals" or "vanilla") Check(Control<TextBlock>("SocialDetailsChannel").Text.StartsWith(GameMod.Name(scenario, language == "ru")), "player card lost the mod name");
                var feed = new ChannelManifest { Channel = "beta", ColorDesyncContinue = true, IndependentColorHostility = true,
                    Packages = new[] { "arcane-wars", "pawpatch-core", "player-colors", "localization-ru", "desync-continue", "roaming-profile-x2-with-new",
                        "roaming-profile-x2-no-new", "powers-shards-original", "immortals", "startup-base", "pure-fixes-data", "pure-fixes-runtime", "game-voice-ru" }
                        .Select(id => new PackageRelease { Id=id, Version="2.0.0", Sha256=new string('A',64), Required=id=="pawpatch-core" }).ToList() };
                if (scenario is "inactive_update" or "equal_update" or "cached_current" or "unrelated_update")
                {
                    var saved = JsonSerializer.Deserialize<ChannelManifest>(JsonSerializer.Serialize(feed))!;
                    if (scenario is "inactive_update" or "equal_update") saved.Packages.Single(p => p.Id == "pawpatch-core").Version = "1.0.0";
                    if (scenario == "unrelated_update") saved.Packages.Single(p => p.Id == "pure-fixes-data").Version = "1.0.0";
                    await new ModLibrary(game).RememberAsync(saved, GameMod.ArcaneWars);
                    if (scenario is "cached_current" or "unrelated_update")
                        foreach (var package in feed.Packages)
                        {
                            var path = Path.Combine(game, ".pawpatch", "packages", package.Id, package.Version);
                            Directory.CreateDirectory(path); File.WriteAllText(Path.Combine(path,".verified"), package.Sha256); File.WriteAllText(Path.Combine(path,"module.json"), "{}");
                        }
                }
                var reads = 0; var applied = 0;
                var incomingSettings=ConfigurationCode.Parse(friend.Configuration!);
                friend=friend with {Versions=new SocialVersions(SelfUpdater.CurrentVersion.ToString(),incomingSettings.Mod,friend.Channel,
                    ModLibrary.ContentId(feed,incomingSettings.Mod),PawPatchVersions.ForChannel(feed,incomingSettings.Mod))};
                if(scenario is "old_launcher" or "old_both")friend=friend with {Versions=friend.Versions with {Launcher="0.1.0"}};
                if(scenario is "old_patch" or "old_both")friend=friend with {Versions=friend.Versions with {ContentId=new string('0',64)}};
                if(scenario=="unknown_versions")friend=friend with {Versions=null};
                Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)[friend]);
                Invoke("ObserveFriendVersionCatalog",feed,SelfUpdater.CurrentVersion.ToString());
                Set("_friendLauncherVersionOverride",(Func<Task<string>>)(()=>Task.FromResult(scenario=="launcher_update_during_check"?"9.0.0":SelfUpdater.CurrentVersion.ToString())));
                Invoke("RefreshSocialCopyAvailability");
                if(scenario is "old_launcher" or "old_patch" or "old_both" or "unknown_versions")
                    Check(!Control<Button>("SocialDetailsCopyButton").IsEnabled && Control<TextBlock>("SocialDetailsCopyHint").Text.Length>30,"old/unknown versions allow copying or lack warning");
                var feedReads = 0;
                var delayedFeed = new TaskCompletionSource<ChannelManifest?>(TaskCreationOptions.RunContinuationsAsynchronously);
                Set("_friendSettingsReadOverride", (Func<Task<IReadOnlyList<SocialPlayer>>>)(() => {
                    reads++;
                    if (scenario == "network") throw new IOException("Fixture network failure");
                    IReadOnlyList<SocialPlayer> result = scenario == "removed" ? [] : [friend];
                    if (scenario == "changed" && reads == 3) result = [friend with { Configuration = friend.Configuration!.Replace("SP2","SP4") }];
                    if (scenario == "old_after_consent" && reads == 3) result = [friend with { Versions=friend.Versions! with {Launcher="0.1.0"} }];
                    return Task.FromResult(result);
                }));
                Set("_friendSettingsFeedOverride", (Func<string,Task<ChannelManifest?>>)(channel => {
                    feedReads++;
                    Check(channel == "beta", "wrong channel requested");
                    if (scenario == "game_during_load") running = true;
                    if (scenario == "cancel_slow") return delayedFeed.Task;
                    if (scenario == "feed_failure") throw new IOException("Fixture feed failure");
                    return Task.FromResult<ChannelManifest?>(scenario == "unsupported" ? new ChannelManifest { Channel="beta" } : feed);
                }));
                Set("_friendSettingsApplyOverride", (Func<ChannelManifest,UserSettings,Func<Task>,Task>)(async (f,s,guard) => {
                    await guard();
                    if (scenario == "apply_failure") throw new IOException("Fixture install failure");
                    Check(ReferenceEquals(f, feed) && feedReads == 1, "applied a different release from the confirmation");
                    Check(s.Channel=="beta" && s.GamePath==@"C:\fixture-local", "wrong snapshot");
                    if (scenario is "immortals" or "vanilla") Check(s.Mod == scenario && GameMod.PawPatchSelected(s), "friend's mod/patch was not imported");
                    else Check(s.Mod==GameMod.ArcaneWars && s.RoamingSpawnMode=="x2" && !s.DisablePowersAndShards, "friend's components were not imported");
                    Check(s.RussianLocalization == settings.RussianLocalization && GameLanguages.Voice(s) == GameLanguages.Voice(settings), "copy changed local text or speech language");
                    Check(ConfigurationCode.Create(settings)==baseline, "preferences changed before file commit"); applied++;
                }));
                if (scenario == "running") running = true;
                if (scenario == "already_applied")
                {
                    Set("_friendCopyAppliedState",new InstallState{AppliedSettings=ConfigurationCode.Parse(friend.Configuration!)});
                    Set("_friendCopyAppliedVersions",friend.Versions);
                    Set("_fileCheckFailed",false);Set("_installationFailure",null);
                    Invoke("RefreshSocialCopyAvailability");
                    Check(!Control<Button>("SocialDetailsCopyButton").IsEnabled,"identical applied configuration can be copied");
                    Check(Control<Button>("SocialDetailsCopyButton").Content.ToString()==UiLanguages.Text(language,"Конфигурации совпадают","Configurations match"),"no-op button has no explanation");
                }
                var task = (Task)Invoke("CopyFriendSettingsAsync")!;
                if(scenario=="already_applied")Check(task.IsCompleted&&feedReads==0&&reads==0&&applied==0&&Control<Border>("ConfirmationOverlay").Visibility!=Visibility.Visible,"no-op started a confirmation or network operation");
                if (scenario != "running" && !task.IsCompleted)
                {
                    Check(reads == 0 && applied == 0, "mutation started before confirmation");
                    Check(Control<Border>("SocialDetailsOverlay").Visibility == Visibility.Visible && !Control<Border>("SocialDetailsOverlay").IsHitTestVisible, "details hidden instead of preserved under confirmation");
                    Check(w.FindName("ConfirmationLocalizationToggle") is null, "localization copying option remains");
                    var diff=FriendConfiguration.WithLocalLanguages(ConfigurationCode.Parse(friend.Configuration!),settings);
                    Check(Control<TextBlock>("ConfirmationPathText").Text==string.Join("\n",ConfigurationChanges.Describe(settings,diff,language=="ru")), "confirmation missing actual changed components");
                    Check(LauncherIcon.GetKind(Control<Button>("ConfirmationDeleteButton"))==IconKind.Copy, "confirmation icon");
                    if (scenario is "cancel" or "cancel_slow")
                    {
                        if (scenario == "cancel_slow")
                        {
                            Check(!Control<Button>("ConfirmationDeleteButton").IsEnabled, "pending preflight can be approved");
                            await (Task)Invoke("CompleteConfirmationAsync", true)!;
                            Check(!task.IsCompleted, "disabled action accepted");
                        }
                        await (Task)Invoke("CompleteConfirmationAsync", false)!;
                    }
                    else
                    {
                        while (!task.IsCompleted && !Control<Button>("ConfirmationDeleteButton").IsEnabled) await Task.Delay(10);
                        if (!task.IsCompleted)
                        {
                            var expectedLabel = scenario is "inactive_update" or "equal_update" ? (language=="ru" ? "Обновить и применить" : "Update and apply")
                                : scenario is "cached_current" or "unrelated_update" ? (language=="ru" ? "Применить" : "Apply")
                                : (language=="ru" ? "Установить и применить" : "Install and apply");
                            Check(Control<Button>("ConfirmationDeleteButton").Content.ToString() == expectedLabel, "wrong planned action " + scenario);
                            Check(Control<TextBlock>("ConfirmationBodyText").Text.Contains(GameMod.Name(ConfigurationCode.Parse(friend.Configuration!).Mod, language=="ru")), "missing destination mod");
                            if (scenario is "success" or "inactive_update" or "cached_current")
                            {
                                foreach (var size in new[] { new Size(1440,900),new Size(1050,680) })
                                {
                                    content.Measure(size); content.Arrange(new Rect(size)); content.UpdateLayout();
                                    var button=Control<Button>("ConfirmationDeleteButton");
                                    var bounds=button.TransformToAncestor(content).TransformBounds(new Rect(button.RenderSize));
                                    Check(bounds.Top>=0 && bounds.Bottom<=size.Height && bounds.Left>=0 && bounds.Right<=size.Width, "confirmation action clipped " + scenario);
                                    Check(button.ActualWidth>=button.DesiredSize.Width-.1, "confirmation action text clipped");
                                }
                                var card=Control<Border>("ConfirmationCard");
                                var drawing=new DrawingVisual();
                                using(var dc=drawing.RenderOpen()) dc.DrawRectangle(new VisualBrush(card),null,new Rect(0,0,card.ActualWidth,card.ActualHeight));
                                var bitmap=new RenderTargetBitmap((int)Math.Ceiling(card.ActualWidth),(int)Math.Ceiling(card.ActualHeight),96,96,PixelFormats.Pbgra32);bitmap.Render(drawing);
                                var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(bitmap));
                                var output=Path.GetFullPath("../launcher-peer-versions-round18");Directory.CreateDirectory(output);
                                using var image=File.Create(Path.Combine(output,"copy-"+scenario+"-"+language+".png"));png.Save(image);
                            }
                        }
                    }
                    if (scenario == "account_changed")
                        Set("_account", new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root,"guest-"+Guid.NewGuid()))));
                    if (scenario == "path_changed") Set("_game", new GameInstallation(game+"-other",Path.Combine(game+"-other","k2.exe"), null, null));
                    if (!task.IsCompleted && scenario is not ("cancel" or "cancel_slow")) await (Task)Invoke("CompleteConfirmationAsync", true)!;
                }
                await task;
                if (scenario == "cancel_slow")
                {
                    var newer = (Task<bool>)Invoke("ConfirmActionAsync", "Newer dialog", "Unchanged", "", "", "Apply")!;
                    Set("_busy", true);
                    delayedFeed.SetException(new IOException("Late cancelled feed")); await Task.Delay(60);
                    Check(Control<TextBlock>("ConfirmationTitleText").Text == "Newer dialog" && Field<bool>("_busy"), "late preflight changed a new dialog or busy operation");
                    Set("_busy", false); await (Task)Invoke("CompleteConfirmationAsync", false)!; await newer;
                }
                var successful=scenario is "success" or "split_localization" or "same_localization" or "immortals" or "vanilla" or "inactive_update" or "equal_update" or "cached_current" or "unrelated_update";
                var expected=FriendConfiguration.WithLocalLanguages(ConfigurationCode.Parse(friend.Configuration!),ConfigurationCode.Parse(baseline));
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
            async Task All() { foreach (var s in new[] { "cancel", "cancel_slow", "running", "feed_failure", "network", "removed", "changed", "game_during_load", "unsupported", "apply_failure", "account_changed", "path_changed", "success", "split_localization", "same_localization", "immortals", "vanilla", "inactive_update", "equal_update", "cached_current", "unrelated_update", "old_launcher", "old_patch", "old_both", "unknown_versions", "launcher_update_during_check", "old_after_consent", "already_applied" }) await Scenario(s); }
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
