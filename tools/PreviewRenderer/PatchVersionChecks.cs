using System.Reflection;
using System.Windows.Controls;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class PatchVersionChecks
{
    internal static void Run(string language)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Disposable profile required");
        var w=new MainWindow();const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        string Text(string name)=>((TextBlock)w.FindName(name)).Text;
        var count=0;void Check(bool ok,string why){count++;if(!ok)throw new Exception("Patch version UI: "+why);}
        try
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Call("ApplyLanguage");var settings=Field<UserSettings>("_settings");
            typeof(MainWindow).GetField("_installedGameVersion",flags)!.SetValue(w,"1.3.72");
            foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals})
            foreach(var branch in new[]{"stable","beta"})
            {
                settings.Mod=mod;settings.Channel=branch;GameMod.SetPawPatch(settings,true);
                var feed=new ChannelManifest {Channel=branch,Packages=[new(){Id="pure-fixes-data",Version="1.0.0-pure.1"}],ModGuides=[new(){Id=mod,PatchGuide=new(){Version="1.0.0-local.2"}}]};
                typeof(MainWindow).GetField("_channel",flags)!.SetValue(w,feed);Call("SyncPatchChannelControls");
                Check(Text("ModPatchVersionText").StartsWith("Paw's Patch 0.1.0 ·"),"component version");
                var state=new InstallState {AppliedSettings=new(){Mod=mod,Channel=branch,VanillaPawPatchEnabled=true,ImmortalsPawPatchEnabled=true},Modules=new(){["pure-fixes-data"]=new(){Enabled=true,Version="1.0.0-pure.1"}}};
                state.Modules[mod]=new(){Enabled=true,Version="2.1.0"};
                var modLabel=GameMod.Name(mod)+" "+(mod==GameMod.Vanilla?"1.3.72":"2.1");
                Call("RefreshInstalledPatchVersions",state);
                Check(Text("PatchVersionText")=="0.1.0"&&Text("InstalledPatchText")==modLabel+"\nPaw's Patch 0.1.0","home/footer installed version");
                GameMod.SetPawPatch(state.AppliedSettings,false);Call("RefreshInstalledPatchVersions",state);
                Check(Text("PatchVersionText")=="-"&&!Text("InstalledPatchText").Contains("0.1.0"),"disabled patch label");
                state.AppliedSettings.Mod=GameMod.ArcaneWars;Call("RefreshInstalledPatchVersions",state);
                Check(Text("PatchVersionText")=="-"&&Text("InstalledPatchText")=="Arcane Wars —","footer changed before applying the selected mode");
            }
            Console.WriteLine($"PATCH VERSION UI PASS {count} {language}: component, home, footer, disabled and unapplied modes");
        }
        finally{w.Close();}
    }
}
