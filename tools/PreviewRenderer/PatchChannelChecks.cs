using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class PatchChannelChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Patch channel checks require --smoke-test.");
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        var root = Path.Combine(ActivityStore.Root, "channel-fixture", Guid.NewGuid().ToString("N")); Directory.CreateDirectory(root);
        ChannelManifest Feed(string channel) => new() { Channel = channel, Packages = [
            new() { Id = "arcane-wars", Version = "1", Required = true, Sha256 = new string('A',64), Size = 1 },
            new() { Id = "pawpatch-core", Version = "1", Required = true, Sha256 = new string('B',64), Size = 1 }
        ] };
        var beta = Feed("beta"); var release = Feed("stable");
        var config = new LauncherConfiguration { FeedUrls = [Path.Combine(root,"stable.json")], BetaFeedUrls = [Path.Combine(root,"beta.json")], CacheRoot = Path.Combine(root,"cache") };
        File.WriteAllText(config.FeedUrls[0], JsonSerializer.Serialize(release, LauncherJsonContext.Default.ChannelManifest));
        File.WriteAllText(config.BetaFeedUrls[0], JsonSerializer.Serialize(beta, LauncherJsonContext.Default.ChannelManifest));
        var cached = new List<string>();
        foreach (var package in beta.Packages)
        {
            var path = Path.Combine(config.CacheRoot,"downloads",package.Id,package.Version,package.Sha256+".zip"); Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllBytes(path, [1]); cached.Add(path); // Only cache-presence fixtures; never downloaded or installed.
        }
        var applied = new UserSettings { Channel = "beta", RussianLocalization = false, CustomPlayerColors = false };
        var state = new InstallState { ReleaseId = ChannelFingerprint.Create(beta), AppliedSettings = applied };
        foreach (var package in beta.Packages) state.Modules.Add(package.Id, new InstalledModule { Version=package.Version, Enabled=true, Priority=package.Priority, ArchiveSha256=package.Sha256 });
        var game = Path.Combine(root,"game"); Directory.CreateDirectory(Path.Combine(game,".pawpatch"));
        var statePath = Path.Combine(game,".pawpatch","state.json");
        File.WriteAllText(statePath, JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState));
        var originalState = File.ReadAllText(statePath);
        var window = new MainWindow(config, null) { Width=1050, Height=680, Left=-30000, Top=-30000, WindowStartupLocation=WindowStartupLocation.Manual, ShowActivated=false, ShowInTaskbar=false };
        object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name,flags)!.Invoke(window,args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name,flags)!.GetValue(window)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name,flags)!.SetValue(window,value);
        T Control<T>(string name) => (T)window.FindName(name);
        var settings = Field<UserSettings>("_settings");
        ConfigurationCode.Apply(applied,settings); settings.PinnedRelease=null; settings.PreparedChannel="beta"; settings.PreparedFeedFingerprint=state.ReleaseId;
        Set("_game", new GameInstallation(game,Path.Combine(game,"k2.exe"),"test","beta")); Set("_channel", beta); Set("_latestChannel", beta);
        Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);
        Control<CheckBox>("RussianToggle").IsChecked=false;
        Invoke("ApplyLanguage"); Invoke("SetActivePage","settings"); window.Show(); window.UpdateLayout();
        int checks=0;
        void Check(bool value,string message) { if (!value) throw new InvalidOperationException(message); checks++; }
        bool NeedsPreparation() => (bool)Invoke("NeedsChannelPreparation", beta,state)!;
        bool SelectedButtonsAreGold()
        {
            foreach (var name in new[] { "HeaderBetaRadio", "SettingsBetaRadio" })
            {
                var radio = Control<RadioButton>(name);
                var border = (Border)radio.Template.FindName("ModeBorder", radio);
                if (border.Background is not SolidColorBrush brush || brush.Color != Color.FromRgb(0x4A, 0x3C, 0x20)) return false;
            }
            return true;
        }
        async Task Scenario()
        {
            await Task.Delay(250);
            Check(SelectedButtonsAreGold(), "Initial selected channel is not visibly highlighted.");
            Check(!NeedsPreparation(),"Current prepared Beta incorrectly needs preparation.");
            var footer=Control<TextBlock>("LauncherVersionText").Text;
            Check(Version.TryParse(footer,out _),"Launcher version includes a patch channel.");
            Check(Control<RadioButton>("HeaderBetaRadio").IsChecked==true && Control<RadioButton>("SettingsBetaRadio").IsChecked==true,"Initial channel selectors disagree.");
            await (Task)Invoke("ChangeChannelAsync",false)!;
            Check(settings.Channel=="stable" && Control<RadioButton>("HeaderReleaseRadio").IsChecked==true && Control<RadioButton>("SettingsReleaseRadio").IsChecked==true,"Release selection not synchronized.");
            await (Task)Invoke("ChangeChannelAsync",true)!;
            await Task.Delay(250);
            Check(SelectedButtonsAreGold(), "Returning to Beta lost its selected highlight.");
            Check(settings.Channel=="beta" && !Field<bool>("_patchUpdateAvailable") && !Field<bool>("_settingsPending"),"Beta->Release->Beta produced a false update.");
            Check(Control<TextBlock>("LauncherVersionText").Text==footer,"Patch selection changed launcher version.");
            Check(File.ReadAllText(statePath)==originalState,"Channel selection changed installed files/state without applying.");
            settings.PinnedRelease="same-channel-pin"; var current=Field<ChannelManifest>("_channel");
            await (Task)Invoke("ChangeChannelAsync",true)!;
            Check(settings.PinnedRelease=="same-channel-pin" && ReferenceEquals(current,Field<ChannelManifest>("_channel")),"Re-clicking selected channel reset its pinned release."); settings.PinnedRelease=null;
            Set("_checkingFeed",true); Invoke("SyncPatchChannelControls");
            Check(!Control<RadioButton>("HeaderReleaseRadio").IsEnabled && !Control<RadioButton>("SettingsBetaRadio").IsEnabled,"Channel controls remain active during a feed check.");
            await (Task)Invoke("ChangeChannelAsync",false)!;
            Check(settings.Channel=="beta" && Control<RadioButton>("HeaderBetaRadio").IsChecked==true,"Busy channel change left inconsistent selection.");
            Set("_checkingFeed",false); Invoke("SyncPatchChannelControls");
            File.Delete(cached[0]); Invoke("RefreshStatus");
            Check(Field<bool>("_patchUpdateAvailable"),"Missing cache was incorrectly treated as ready.");
            File.WriteAllBytes(cached[0],[1]); Invoke("RefreshStatus");
            Check(!Field<bool>("_patchUpdateAvailable"),"Restored cache did not clear preparation state.");
            beta.Packages[1].Version="2"; Set("_channel",beta); Invoke("RefreshStatus");
            Check(Field<bool>("_patchUpdateAvailable") && Control<TextBlock>("ReadyStatusText").Text.Contains(language=="ru" ? "обновление патча" : "Patch update"),"Real new patch version was hidden.");
            Check(File.ReadAllText(statePath)==originalState,"Checks modified installed state.");
            Console.WriteLine($"PATCH CHANNEL PASS {checks} {language}: selector synchronization, no-op/pinned release, check locking, Beta->Release->Beta, missing cache, true new version; disposable local feeds only");
        }
        try
        {
            var task=window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame=new DispatcherFrame();
            var timer=new DispatcherTimer { Interval=TimeSpan.FromSeconds(20) }; timer.Tick+=(_,_)=>frame.Continue=false;
            task.ContinueWith(_=>window.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("Channel checks did not complete."); task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}
