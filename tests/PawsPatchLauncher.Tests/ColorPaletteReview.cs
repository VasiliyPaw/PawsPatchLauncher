using PawsPatchLauncher;
using System.Text.Json;

static class ColorPaletteReview
{
    public static void Labels()
    {
        int count=0;
        foreach(var lang in UiLanguages.Choices.Select(x=>x.Code))
        foreach(var key in new[]{"modules.colors.desc","modules.colors.help"})
        {
            var text=new Localization(lang);
            foreach(int value in new[]{48,49,0,100})
            {
                var expected=value is >=16 and <=64?value:49;
                var actual=text.ColorText(key,new ChannelManifest{PlayerColorCount=value});
                if(!actual.Contains(expected.ToString()) || actual.Contains((expected==48?49:48).ToString()))
                    throw new Exception("Wrong localized palette count: "+lang+" "+key);
                count++;
            }
        }
        var old=JsonSerializer.Deserialize("{}",LauncherJsonContext.Default.ChannelManifest)!;
        if(old.PlayerColorCount!=49)throw new Exception("Legacy palette metadata changed");
        Console.WriteLine("COLOR_LABELS_PASS "+(count+1));
    }

    public static async Task StageAsync(string gameRoot,string feedRoot)
    {
        if(System.Diagnostics.Process.GetProcessesByName("k2").Any())throw new Exception("Close game before review installation");
        var root=Path.GetFullPath(feedRoot);
        var config=JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(root,"launcher.config.json")),LauncherJsonContext.Default.LauncherConfiguration)!;
        config.CacheRoot=Path.Combine(root,"validation-cache");
        var feed=await new FeedClient(config).GetChannelAsync("beta")??throw new Exception("Missing beta");
        if(feed.PlayerColorCount!=48)throw new Exception("Not a 48-color review");
        var installer=new ModuleInstaller(Path.GetFullPath(gameRoot));var state=installer.LoadState();var settings=state.AppliedSettings;
        if(settings is not {Mod:GameMod.ArcaneWars,Channel:"beta",PawPatchEnabled:true,DataOnly:false})throw new Exception("Expected existing full Arcane Wars beta");
        var desired=new Dictionary<string,InstalledModule>(state.Modules,StringComparer.OrdinalIgnoreCase);
        foreach(var id in new[]{"pawpatch-core","common-ui","player-colors"})
        {
            if(!desired.ContainsKey(id)&&id=="player-colors")continue;
            var p=feed.Packages.Single(x=>x.Id==id);var archive=Path.GetFullPath(p.Urls[0]);
            if(!archive.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Review archive escaped local folder");
            if(await CryptoAndIO.Sha256Async(archive)!=p.Sha256)throw new Exception("Review archive changed");
            desired[id]=await installer.PrepareAsync(p,archive);
        }
        await installer.ReconcileAsync(desired,settings:settings,releaseId:ChannelFingerprint.Create(feed),gameRequirement:state.GameRequirement,baseGameSha256:state.BaseGameSha256);
        await GameMenuMetadata.WriteAsync(gameRoot,feed,settings);
        var errors=await installer.VerifyAsync();
        if(errors.Count!=0)throw new Exception(string.Join(";",errors));
        Console.WriteLine("COLOR_REVIEW_INSTALLED settings preserved; normal installer verification passed.");
    }
}
