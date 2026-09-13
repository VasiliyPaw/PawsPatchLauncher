using PawsPatchLauncher;

internal static class PawPatchVersionTests
{
    internal static int Run()
    {
        var count=0; void Check(bool ok,string reason) { count++; if(!ok)throw new Exception("Patch versions: "+reason); }
        foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals})
        foreach(var branch in new[]{"stable","beta"})
        {
            var settings=new UserSettings {Mod=mod,Channel=branch,VanillaPawPatchEnabled=true,ImmortalsPawPatchEnabled=true};
            var feed=new ChannelManifest {Channel=branch,Packages=[new(){Id="pure-fixes-data",Version="1.0.0-pure.1"},new(){Id="pawpatch-core",Version="0.3.0-beta.2"}],
                ModGuides=[new(){Id=mod,Version="2.1",PatchGuide=new(){Version="1.0.0-local.2"}}]};
            var state=new InstallState {AppliedSettings=settings,Modules=new(){["pure-fixes-data"]=new(){Enabled=true,Version="1.0.0-pure.1"},["pawpatch-core"]=new(){Enabled=false,Version="0.3.0-beta.2"}}};
            Check(PawPatchVersions.ForChannel(feed,mod)=="0.1.0","legacy guide leaks a build ID");
            Check(PawPatchVersions.Installed(state,feed)=="0.1.0","installed label differs");
            Check(PawPatchVersions.Installed(state,null)=="0.1.0","offline installed version differs");
            var ini=GameMenuMetadata.Create(feed,settings);
            Check(ini.Contains("PawPatch=0.1.0\n")&&ini.Contains("PatchChannel="+branch),"game label differs");
            Check(mod!=GameMod.Immortals||ini.Contains("ModVersion=2.1\n"),"author mod version was overwritten");
            feed.ModGuides[0].PatchGuide!.Version="0.2.0";
            Check(PawPatchVersions.ForChannel(feed,mod)=="0.2.0"&&GameMenuMetadata.Create(feed,settings).Contains("PawPatch=0.2.0\n"),"future public version frozen");
            GameMod.SetPawPatch(settings,false);
            Check(PawPatchVersions.Installed(state,feed) is null&&!GameMenuMetadata.Create(feed,settings).Contains("PawPatch="),"disabled patch claims a version");
            GameMod.SetPawPatch(settings,true);state.Modules["pure-fixes-data"].Enabled=false;
            Check(PawPatchVersions.Installed(state,feed) is null,"missing patch claims a version");
            feed.ModGuides.Clear();Check(PawPatchVersions.ForChannel(feed,mod)=="0.1.0","legacy package fallback");
            Check(PawPatchVersions.ForChannel(feed,GameMod.ArcaneWars)=="0.3.0-beta.2","AW version changed");
        }
        foreach(var version in new[]{"1.0.0-local.1","1.0.0-local.2","1.0.0-pure.1"})
        {Check(PawPatchVersions.Display(GameMod.Vanilla,version)=="0.1.0","initial aliases");Check(PawPatchVersions.Display(GameMod.ArcaneWars,version)==version,"aliases crossed mod scope");}
        Check(PawPatchVersions.ForChannel(null,GameMod.Vanilla) is null,"invented uninstalled release");
        Console.WriteLine($"PAW PATCH VERSION PASS {count}: initial aliases, separate mod versions, both branches, future releases, disabled and offline installation");
        return count;
    }
}
