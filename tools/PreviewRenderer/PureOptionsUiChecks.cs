using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class PureOptionsUiChecks
{
    internal static void Run(string configPath)
    {
        if (!ActivityStore.IsSmokeTest) throw new Exception("Disposable profile required");
        var config=JsonSerializer.Deserialize(File.ReadAllText(configPath),LauncherJsonContext.Default.LauncherConfiguration)!;
        var client=new FeedClient(config);
        var feeds=new[]{"stable","beta"}.Select(c=>Task.Run(()=>client.GetChannelAsync(c)).GetAwaiter().GetResult()!).ToArray();
        int count=0;
        void Check(bool ok,string why){count++;if(!ok)throw new Exception(why);}
        foreach(var language in new[]{"ru","en","de","fr","cs","uk"})
        {
            new SettingsStore().Save(new UserSettings{Language=language,ModNoticeSeen=true});
            var w=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null){Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual};
            const BindingFlags f=BindingFlags.Instance|BindingFlags.NonPublic;
            void Set(string n,object? v)=>typeof(MainWindow).GetField(n,f)!.SetValue(w,v);
            object? Call(string n,params object[] a)=>typeof(MainWindow).GetMethod(n,f)!.Invoke(w,a);
            T C<T>(string n)=>(T)w.FindName(n);
            var prefs=(UserSettings)typeof(MainWindow).GetField("_settings",f)!.GetValue(w)!;
            var loc=(PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text",f)!.GetValue(w)!;
            loc.SetLanguage(language);
            try
            {
                foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals})
                foreach(var feed in feeds)
                {
                    prefs.Mod=mod;prefs.Channel=feed.Channel;
                    GameMod.SetPawPatch(prefs,true);GameMod.SetColors(prefs,true);GameMod.SetDesync(prefs,true);
                    Set("_channel",feed);Set("_latestChannel",feed);Set("_offeredModChannel",feed);Set("_colorsAvailable",true);
                    Set("_compatibilityState",GameCompatibilityState.Supported);
                    Call("ApplyLanguage");Call("SetActivePage","modules");Call("RefreshModControls");
                    bool beta=feed.Channel=="beta";
                    foreach(var card in new[]{"ColorsModuleCard","OosModuleCard"})Check(C<Border>(card).Visibility==(beta?Visibility.Visible:Visibility.Collapsed),mod+feed.Channel+card);
                    foreach(var card in new[]{"IndependentHostilityCard","RoamingSpawnCard","AdditionalRoamingCard","SiegeBalanceCard"})Check(C<Border>(card).Visibility==Visibility.Collapsed,"AW card leaked");
                    var help=(string)Call("CoreHelpText")!;
                    Check(help.Length>200&&help.Contains("Dvorak"),"Missing core help "+language);
                    if(language is not ("ru" or "en"))Check(!help.Contains("Faster native saved-game transfers")&&!help.Contains("Optional Beta switches"),"Untranslated core help "+language);
                    if(!beta)continue;
                    var colors=C<CheckBox>("ColorsToggle");var sync=C<CheckBox>("IgnoreDesyncToggle");var core=C<CheckBox>("PawPatchToggle");
                    Check(colors.IsChecked==true&&sync.IsChecked==true&&colors.IsEnabled&&sync.IsEnabled,"Beta on controls "+mod);
                    core.IsChecked=false;Call("PawPatchChanged",core,new RoutedEventArgs());
                    Check(colors.IsChecked==false&&sync.IsChecked==false&&!colors.IsEnabled&&!sync.IsEnabled,"Master off left controls active");
                    core.IsChecked=true;Call("PawPatchChanged",core,new RoutedEventArgs());
                    Check(colors.IsChecked==true&&sync.IsChecked==true,"Master on lost mod choices");
                    Set("_compatibilityState",GameCompatibilityState.Unsupported);Call("RefreshPawComponentDependency");
                    Check(colors.IsChecked==false&&sync.IsChecked==false&&!colors.IsEnabled&&!sync.IsEnabled,"Unsupported EXE controls active");
                }
            }
            finally{w.Close();}
        }
        Console.WriteLine($"PURE OPTIONS UI PASS {count}: two modes, both channels, all six languages, master switch, unsupported executable");
    }
}
