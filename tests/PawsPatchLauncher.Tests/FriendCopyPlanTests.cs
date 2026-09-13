using System.Text.Json;
using PawsPatchLauncher;

public static class FriendCopyPlanTests
{
    public static int Run()
    {
        var checks = 0;
        void Check(bool ok, string message) { checks++; if (!ok) throw new Exception("Friend copy plan: " + message); }
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (var channelName in new[] { "stable", "beta" })
        {
            var settings = new UserSettings { Mod=mod, Channel=channelName, RussianLocalization=false, GameVoiceLanguage="en" };
            var channel = new ChannelManifest { Channel=channelName, Packages =
            [
                new() { Id="arcane-wars", Version="1", Sha256=new string('A',64), Mods=[GameMod.ArcaneWars] },
                new() { Id="pawpatch-core", Version="1", Required=true, Sha256=new string('B',64), Mods=[GameMod.ArcaneWars] },
                new() { Id="immortals", Version="1", Sha256=new string('C',64), Mods=[GameMod.Immortals] },
                new() { Id="startup-base", Version="1", Sha256=new string('D',64), Mods=[GameMod.Immortals,GameMod.ArcaneWars] },
                new() { Id="pure-fixes-data", Version="1", Sha256=new string('E',64), Mods=[GameMod.Vanilla,GameMod.Immortals] },
                new() { Id="pure-fixes-runtime", Version="1", Sha256=new string('F',64), Mods=[GameMod.Vanilla,GameMod.Immortals] },
                new() { Id="game-localization-en", Version="1", Sha256=new string('1',64), Mods=[GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars] },
                new() { Id="game-voice-ru", Version="1", Sha256=new string('2',64) }
            ] };
            var entry = new ModLibraryEntry { Mod=mod, Channel=channelName, ContentId=ModLibrary.ContentId(channel,mod) };
            Check(FriendCopyPlan.Create(channel,settings,null,_=>true).Action==FriendCopyAction.Install, "missing target even when files cached");
            var ready = FriendCopyPlan.Create(channel,settings,entry,_=>true);
            Check(ready.Action==FriendCopyAction.Apply && ready.DownloadCount==0, "retained current target should apply without downloads");
            Check(FriendCopyPlan.Create(channel,settings,new ModLibraryEntry { Mod=mod, Channel=channelName=="beta"?"stable":"beta", ContentId=entry.ContentId },_=>true).Action==FriendCopyAction.Install, "other channel confused with target");
            var update = JsonSerializer.Deserialize<ChannelManifest>(JsonSerializer.Serialize(channel))!;
            update.Packages.First(p=>ModLibrary.BelongsTo(p,mod)&&!GameLanguages.IsLanguage(p)).Version="2";
            Check(FriendCopyPlan.Create(update,settings,entry,_=>true).Action==FriendCopyAction.Update, "target update missed");
            var unrelated = JsonSerializer.Deserialize<ChannelManifest>(JsonSerializer.Serialize(channel))!;
            unrelated.Packages.First(p=>!ModLibrary.BelongsTo(p,mod)&&!GameLanguages.IsLanguage(p)).Version="2";
            Check(FriendCopyPlan.Create(unrelated,settings,entry,_=>true).Action==FriendCopyAction.Apply, "another mod update leaked");
            var absentId=ModLibrary.Packages(channel,mod).First().Id;
            var repair=FriendCopyPlan.Create(channel,settings,entry,p=>p.Id!=absentId);
            Check(repair.Action==FriendCopyAction.Install && repair.Repair && repair.DownloadCount==1, "missing cached component not identified");
            var language=FriendCopyPlan.Create(channel,settings,entry,p=>p.Id!="game-localization-en");
            Check(language.Action==FriendCopyAction.Apply && language.DownloadCount==1, "language confused with mod installation");
        }
        return checks;
    }
}
