using PawsPatchLauncher;

internal static class PawDependencyTests
{
    internal static int Run()
    {
        var n=0;void Check(bool ok,string why){if(!ok)throw new Exception("Paw dependency: "+why);n++;}
        var feed=new ChannelManifest { Packages=[new(){Id="arcane-wars"},new(){Id="startup-base"},new(){Id="aw-localization-ru"},
            new(){Id="menu-runtime"},new(){Id="player-colors"},new(){Id="pawpatch-core",Required=true}] };
        static bool Disabled(UserSettings s)=>!s.CustomPlayerColors&&!s.IndependentHostility&&!s.AdditionalRoamingCompanies
            &&!s.SiegeBalance&&!s.DisablePowersAndShards&&!s.LargeMapSizes&&s.DesyncMode=="official"&&s.RoamingSpawnMode=="standard";
        foreach(var russian in new[]{false,true})
        foreach(var spawn in new[]{"standard","x2","x4"})
        for(var bits=0;bits<64;bits++)
        {
            var preferences=new UserSettings { PawPatchEnabled=false,RussianLocalization=russian,RoamingSpawnMode=spawn,
                CustomPlayerColors=(bits&1)!=0,IndependentHostility=(bits&2)!=0,AdditionalRoamingCompanies=(bits&4)!=0,
                SiegeBalance=(bits&8)!=0,DisablePowersAndShards=(bits&16)!=0,DesyncMode=(bits&32)!=0?"continue":"official" };
            var active=EffectiveSettings.ForFeed(preferences,feed);
            Check(Disabled(active)&&active.RussianLocalization==russian,"Active projection retained options or changed text language");
            var selected=GamePackageSelector.Select(feed,preferences,russian,preferences.CustomPlayerColors);
            var expected=new[]{"arcane-wars","startup-base","menu-runtime"}.Concat(russian?new[]{"aw-localization-ru"}:[]);
            Check(selected.Select(p=>p.Id).Order().SequenceEqual(expected.Order()),"Raw legacy preferences selected standalone patch packages");
            Check(GameExecutableSelector.Select(new(),preferences,feed)=="k2_paws_menu_1372.exe","Launch chose a component executable without its core");
            Check(FriendConfiguration.TryParse(ConfigurationCode.Create(preferences),"stable",out var parsed)&&Disabled(parsed),"Peer configuration restored disabled components");
        }
        var oldCode=ConfigurationCode.Parse("PAW-BETA-IW1-SP4-RM1-SG1-LM0-RU1-CL1-OOS1-PP0-VOEN");
        Check(Disabled(oldCode)&&oldCode.RussianLocalization&&GameLanguages.Voice(oldCode)=="en","Legacy import bypassed dependency or changed speech");
        var target=new UserSettings();ConfigurationCode.Apply(oldCode,target);Check(Disabled(target)&&!target.PawPatchEnabled,"Applying a copied configuration bypassed dependency");
        var changed=new UserSettings{CustomPlayerColors=true,DesyncMode="continue",RussianLocalization=true,GameVoiceLanguage="en"};
        GameMod.SetPawPatch(changed,false);Check(Disabled(changed)&&changed.RussianLocalization&&GameLanguages.Voice(changed)=="en","Master switch changed languages or kept components");
        GameMod.SetPawPatch(changed,true);Check(!changed.CustomPlayerColors&&!changed.SiegeBalance&&changed.RoamingSpawnMode=="standard","Re-enabling the core silently restored disabled options");
        var before=new InstallState{AppliedSettings=new UserSettings{PawPatchEnabled=false,IndependentHostility=true,DesyncMode="continue"}};
        Check(UpdateDetector.HasSettingsChanges(before,[],EffectiveSettings.ForChannel(before.AppliedSettings)),"Legacy applied executable settings were marked ready without applying");
        Console.WriteLine($"PAW DEPENDENCY PASS {n}: all 384 stale option profiles, package and runtime selection, languages, legacy import, master toggle and unapplied migration.");
        return n;
    }
}
