using PawsPatchLauncher;

internal static class LanguageCatalogTests
{
    internal static int Run()
    {
        var n=0;void Check(bool ok,string reason){if(!ok)throw new Exception(reason);n++;}
        foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})
        {
            PackageRelease P(string id,string version="1")=>new(){Id=id,Version=version,Mods=[mod],Sha256=new('A',64),ExecutableIndependent=true};
            var installed=new ChannelManifest{Channel="stable",Packages=[P(mod),P("game-localization-en"),P("vanilla-localization-ru"),P("immortals-localization-ru")]};
            var offered=new ChannelManifest{Channel="stable",Packages=[..installed.Packages,P("game-voice-ru")]};
            var settings=new UserSettings{Mod=mod,PawPatchEnabled=false,RussianLocalization=false,GameVoiceLanguage="ru"};
            Check(ReferenceEquals(GameLanguages.SelectionCatalog(installed,offered,settings),offered),"unchanged retained mod freezes split-language catalog");
            settings.PinnedRelease=new('B',64);
            Check(ReferenceEquals(GameLanguages.SelectionCatalog(installed,offered,settings),installed),"explicit pin silently promoted");
            settings.PinnedRelease=null;
            offered.Packages=offered.Packages.Select(p=>p.Id==mod?P(mod,"2"):p).ToList();
            Check(ReferenceEquals(GameLanguages.SelectionCatalog(installed,offered,settings),installed),"gameplay update silently selected");
            Check(ReferenceEquals(GameLanguages.SelectionCatalog(installed,null,settings),installed),"offline catalog lost");
        }
        Console.WriteLine($"LANGUAGE CATALOG PASS {n}: retained mod catalog upgrades, pins, gameplay isolation and offline fallback");return n;
    }
}
