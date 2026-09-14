using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class PerModChannelChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Disposable smoke profile required.");
        var root = Path.Combine(ActivityStore.Root, "per-mod-channels"); Directory.CreateDirectory(root);
        ChannelManifest Feed(string branch) => new()
        {
            Channel = branch, Packages = [new() { Id = "arcane-wars", Version = "0.82", Size = 1, Sha256 = new string('A',64) },
                new() { Id = "pawpatch-core", Required = true, Version = branch == "beta" ? "2-beta.1" : "1", Size = 1, Sha256 = new string('B',64) },
                new() { Id = "immortals", Version = "2.1", Size = 1, Sha256 = new string('C',64) },
                new() { Id = "pure-fixes-data", Version = "1", Size = 1, Sha256 = new string('D',64) },
                new() { Id = "pure-fixes-runtime", Version = "1", Size = 1, Sha256 = new string('E',64) }]
        };
        var stable = Feed("stable"); var beta = Feed("beta");
        var config = new LauncherConfiguration { FeedUrls = [Path.Combine(root,"stable.json")], BetaFeedUrls = [Path.Combine(root,"beta.json")], CacheRoot = Path.Combine(root,"cache") };
        void SaveFeeds()
        {
            File.WriteAllText(config.FeedUrls[0],JsonSerializer.Serialize(stable,LauncherJsonContext.Default.ChannelManifest));
            File.WriteAllText(config.BetaFeedUrls[0],JsonSerializer.Serialize(beta,LauncherJsonContext.Default.ChannelManifest));
        }
        SaveFeeds();
        var profile = new UserSettings { Mod = GameMod.ArcaneWars, ModNoticeSeen = true, RussianLocalization = true, Language = language };
        new SettingsStore().Save(profile);
        var window = new MainWindow(config, null) { Width = 1050, Height = 780, Left = -32000, Top = -32000,
            WindowStartupLocation = WindowStartupLocation.Manual, ShowActivated = false, ShowInTaskbar = false };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name,flags)!.Invoke(window,args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name,flags)!.GetValue(window)!;
        T Control<T>(string name) => (T)window.FindName(name);
        typeof(MainWindow).GetField("_game",flags)!.SetValue(window,null);
        var settings = Field<UserSettings>("_settings");
        FixtureAccess.AllowArcaneWars(window);
        Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);
        Call("ApplyLanguage"); Call("SetActivePage","modules"); window.Show(); window.UpdateLayout();
        int count = 0;
        void Check(bool ok,string why) { count++; if (!ok) throw new InvalidOperationException("Per-mod channel UI: " + why); }
        async Task Settled()
        {
            var deadline = DateTimeOffset.UtcNow.AddSeconds(8);
            while ((Field<bool>("_busy") || Field<bool>("_checkingFeed")) && DateTimeOffset.UtcNow < deadline) await Task.Delay(25);
            await Task.Delay(180); window.UpdateLayout();
            Check(!Field<bool>("_busy") && !Field<bool>("_checkingFeed"),"Channel check did not settle");
        }
        async Task SelectMod(string name)
        {
            Check(Control<RadioButton>(name).IsEnabled,"Mod selector is disabled");
            Control<RadioButton>(name).IsChecked = true; await Settled();
        }
        async Task Scenario()
        {
            await (Task<bool>)Call("CheckFeedAsync",false)!;
            Check(window.FindName("HeaderReleaseRadio") is null && window.FindName("SettingsBetaRadio") is null,"Global selectors remain");
            Check(Control<RadioButton>("ModBetaRadio").IsEnabled,"Available AW beta is hidden");
            Check(Control<RadioButton>("ModBetaRadio").IsVisible,"Selector is outside the visible Paw card");
            Control<RadioButton>("ModBetaRadio").IsChecked = true; await Settled();
            Check(settings.Channel == "beta","Beta click did not change AW selection");
            Check(Control<FrameworkElement>("HelpOverlay").Visibility == Visibility.Visible,"First beta notice missing");
            Check(Control<TextBlock>("HelpTitleText").Text.Contains("Arcane Wars"),"Notice refers to another mod");
            await (Task)Call("CloseHelpAsync")!;
            Check(settings.BetaNoticesSeen.Contains(GameMod.ArcaneWars),"Beta notice not remembered");
            await SelectMod("ImmortalsModRadio");
            Check(settings.Mod == GameMod.Immortals && settings.Channel == "stable","AW beta leaked into Immortals");
            Check(Control<RadioButton>("ModReleaseRadio").IsChecked == true && !Control<RadioButton>("ModBetaRadio").IsEnabled,"Unavailable Immortals beta is selectable");
            Check(Control<RadioButton>("ModBetaRadio").ToolTip?.ToString()?.Contains(language == "ru" ? "недоступна" : "not yet") == true,"No unavailable-beta explanation");
            await SelectMod("VanillaModRadio");
            Check(settings.Channel == "stable" && !Control<RadioButton>("ModBetaRadio").IsEnabled,"Vanilla inherited AW beta");
            await SelectMod("ArcaneWarsModRadio");
            Check(settings.Channel == "beta" && Control<RadioButton>("ModBetaRadio").IsChecked == true,"AW did not remember beta");
            Check(Control<FrameworkElement>("HelpOverlay").Visibility != Visibility.Visible,"Beta notice repeats on mod return");
            Check(settings.RussianLocalization,"Mod/channel change reset game language");
            Check(Control<TextBlock>("ModPatchVersionText").Text.Contains("2-beta.1"),"Paw version is not displayed");
            settings.PinnedRelease="keep-this-pin";
            await (Task)Call("ChangeChannelAsync",true)!;
            Check(settings.PinnedRelease=="keep-this-pin","Re-click discarded pin"); settings.PinnedRelease=null;
            beta.Packages.Single(p=>p.Id=="pure-fixes-runtime").Version="2-beta.1"; SaveFeeds();
            await (Task<bool>)Call("CheckFeedAsync",false)!;
            await SelectMod("ImmortalsModRadio");
            Check(Control<RadioButton>("ModBetaRadio").IsEnabled,"New Immortals beta stayed disabled");
            Control<RadioButton>("ModBetaRadio").IsChecked=true; await Settled();
            Check(settings.Channel=="beta" && Control<TextBlock>("HelpTitleText").Text.Contains("Immortals"),"Immortals beta/notice is wrong");
            await (Task)Call("CloseHelpAsync")!;
            await SelectMod("VanillaModRadio");
            Check(settings.Channel=="stable","Second beta choice changed Vanilla");
            var restored=new SettingsStore().Load(); ModChannelSelection.SelectMod(restored,GameMod.ArcaneWars);
            Check(restored.Channel=="beta","AW choice lost on restart");
            ModChannelSelection.SelectMod(restored,GameMod.Immortals);
            Check(restored.Channel=="beta","Immortals choice lost on restart");
            Check(!Directory.Exists(Path.Combine(root,".pawpatch")),"Selecting channels installed game files");
            // Help follows the selected mod's signed guide, including historical
            // versions; native-only features must be listed as unavailable in
            // data-only compatibility mode while the hotkey file still works.
            var dvorak=new PatchGuideEntry("dvorak","always","","","","");
            var transfer=new PatchGuideEntry("fast-save-transfer","beta","","","","");
            var selectedGuide=new PatchGuideDocument { Entries=[dvorak,transfer] };
            beta.ModGuides=[new() { Id=GameMod.Vanilla,PatchGuide=selectedGuide },
                new() { Id=GameMod.Immortals,PatchGuide=new() { Entries=[dvorak] } }];
            typeof(MainWindow).GetField("_channel",flags)!.SetValue(window,beta);
            settings.Mod=GameMod.Vanilla;
            string Help(bool partial)=>(string)Call("PureFixesDescription",partial)!;
            var nativeText=language=="ru"?"передача сохранений":"saved-game transfers";
            Check(Help(false).Contains("Dvorak")&&Help(false).Contains(nativeText),"Pure beta features missing from help");
            var partial=Help(true);var unavailable=partial.IndexOf(language=="ru"?"Недоступны":"Unavailable",StringComparison.Ordinal);
            Check(partial.IndexOf("Dvorak",StringComparison.Ordinal)<unavailable&&partial.IndexOf(nativeText,StringComparison.Ordinal)>unavailable,
                "Native transfer advertised as available for an incompatible executable");
            settings.Mod=GameMod.Immortals;
            Check(Help(false).Contains("Dvorak")&&!Help(false).Contains(nativeText),"Another mod's beta transfer leaked into stable help");
            selectedGuide.Entries.Clear();settings.Mod=GameMod.Vanilla;
            Check(!Help(false).Contains("Dvorak")&&!Help(false).Contains(nativeText),"Historical patch advertises newer features");
            // Exercise the actual rendered guide: pure modes have no category
            // tabs, so a Beta entry must remain visible in their single section.
            foreach(var mod in new[] { GameMod.Vanilla,GameMod.Immortals })
            {
                var guide=JsonSerializer.Deserialize<ModGuideDocument>(JsonSerializer.Serialize(GuideCatalog.Resolve(null,mod)))!;
                guide.PatchGuide=new() { Version="2-beta.1",Entries=[
                    new("dvorak","always","Камера Dvorak","Dvorak camera","Клавиши камеры.","Camera keys."),
                    new("fast-save-transfer","beta","Передача сохранений","Save transfer","Быстрая передача.","Faster transfer.")] };
                beta.ModGuides=[guide]; settings.Channel="beta";settings.Mod=mod;
                typeof(MainWindow).GetField("_channel",flags)!.SetValue(window,beta);
                typeof(MainWindow).GetField("_latestChannel",flags)!.SetValue(window,beta);
                typeof(MainWindow).GetField("_guideSubject",flags)!.SetValue(window,mod);
                typeof(MainWindow).GetField("_guideVariant",flags)!.SetValue(window,"patch");
                Call("RefreshAboutPage"); window.UpdateLayout();
                var cards=Control<StackPanel>("AboutEntriesPanel").Children.OfType<Border>().ToArray();
                Check(cards.Any(c=>Equals(c.Tag,"fast-save-transfer"))&&Control<WrapPanel>("AboutTabsPanel").Visibility==Visibility.Collapsed,
                    mod+" Beta transfer is hidden in the single-section guide");
                guide.PatchGuide.Version="1";guide.PatchGuide.Entries.RemoveAt(1);
                stable.ModGuides=[guide];settings.Channel="stable";
                typeof(MainWindow).GetField("_channel",flags)!.SetValue(window,stable);
                typeof(MainWindow).GetField("_latestChannel",flags)!.SetValue(window,stable);
                Call("RefreshAboutPage");window.UpdateLayout();
                Check(!Control<StackPanel>("AboutEntriesPanel").Children.OfType<Border>().Any(c=>Equals(c.Tag,"fast-save-transfer")),
                    mod+" stable guide retained the previous Beta feature");
            }
            Console.WriteLine($"PER-MOD CHANNEL UI PASS {count} {language}: actual controls, independent choices, alternate feed discovery, unavailable beta, first notice, restart and language; local feeds only");
        }
        try
        {
            var task=window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame=new DispatcherFrame();
            var timeout=new DispatcherTimer { Interval=TimeSpan.FromSeconds(40) }; timeout.Tick+=(_,_)=>frame.Continue=false;
            task.ContinueWith(_=>window.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timeout.Start();try { Dispatcher.PushFrame(frame); } finally { timeout.Stop(); }
            if(!task.IsCompleted) throw new TimeoutException("Per-mod channel UI test timed out."); task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}
