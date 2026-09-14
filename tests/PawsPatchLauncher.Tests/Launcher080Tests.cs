using System.Text.Json;
using System.Text.RegularExpressions;
using PawsPatchLauncher;

public static class Launcher080Tests
{
    public static int Run()
    {
        var checks=0;
        void Check(bool value,string why){checks++;if(!value)throw new Exception("Launcher 0.8: "+why);}
        var now=DateTimeOffset.UtcNow;
        var sample=new GameActivityDetails(new GameActivity("match",true,59),now);
        var clock=new GameActivityClock();clock.Observe(sample,1000,now);
        Check(clock.Seconds(1000)==59,"first sample");Check(clock.Seconds(2000)==60,"monotonic local tick");
        clock.Observe(sample,2000,now.AddSeconds(1));Check(clock.Seconds(3000)==61,"same sample cannot reset clock");
        clock.Observe(sample with {ObservedAt=now.AddSeconds(-10),Activity=sample.Activity with{ElapsedSeconds=1}},3000,now);
        Check(clock.Seconds(3000)==61,"older sample ignored");
        clock.Observe(sample with{ObservedAt=now.AddSeconds(3),Activity=sample.Activity with{ElapsedSeconds=120}},4000,now.AddSeconds(3));
        Check(clock.Seconds(5000)==121,"authoritative sample corrects estimate");
        Check(clock.Seconds(100000)==160,"stale/offline estimate freezes after 40 seconds");
        clock.Observe(sample with{ObservedAt=now.AddSeconds(4),Activity=sample.Activity with{Phase="lobby",ElapsedSeconds=null}},5000,now.AddSeconds(4));
        Check(clock.Seconds(7000) is null,"lobby has no fabricated match time");
        clock=new();clock.Observe(sample,1000,now.AddSeconds(3));Check(clock.Seconds(1000)==62,"delivery age accounted for");
        clock=new();clock.Observe(sample,1000,now.AddSeconds(-3));Check(clock.Seconds(1000)==59,"future server timestamp clamped");
        Check(GameActivityClock.Format(3601)=="1:00:01"&&GameActivityClock.Format(60)=="01:00","minute and hour rollover");
        foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})
        foreach(var channel in new[]{"stable","beta"})
        {
            var settings=new UserSettings{Mod=mod,Channel=channel,RussianLocalization=false,GameVoiceLanguage="en"};
            var state=new InstallState{AppliedSettings=settings};
            var versions=new SocialVersions("0.8.0",mod,channel,new string('A',64),"1.0");
            var player=new SocialPlayer(Guid.NewGuid(),"fixture","friend",Channel:channel,Configuration:FriendConfiguration.Create(settings),Versions:versions);
            Check(FriendCopyPlan.MatchesApplied(player,state,versions),"matching applied settings");
            Check(FriendCopyPlan.MatchesApplied(player with{Versions=versions with{ContentId=new string('a',64)}},state,versions),"hash casing is not a different release");
            Check(!FriendCopyPlan.MatchesApplied(player,null,versions),"uninstalled target is not a no-op");
            Check(!FriendCopyPlan.MatchesApplied(player,state,versions with{ContentId=new string('B',64)}),"different content still requires update");
            Check(!FriendCopyPlan.MatchesApplied(player,state,versions with{Patch="2.0"}),"different patch still requires update");
            Check(!FriendCopyPlan.MatchesApplied(player,state,null),"unknown installed version cannot block copying");
            var local=JsonSerializer.Deserialize<UserSettings>(JsonSerializer.Serialize(settings))!;local.RussianLocalization=true;local.GameVoiceLanguage="ru";
            Check(FriendCopyPlan.MatchesApplied(player,new InstallState{AppliedSettings=local},versions),"local languages excluded");
            local.Mod=mod==GameMod.Vanilla?GameMod.Immortals:GameMod.Vanilla;
            Check(!FriendCopyPlan.MatchesApplied(player,new InstallState{AppliedSettings=local},versions),"other applied mod not confused with selection");
        }
        Check(UiLanguages.Choices.Select(c=>c.Label).SequenceEqual(new[]{"English","Русский","Čeština","Deutsch","Français"}),"autonyms");
        Check(UiLanguages.Normalize("CS")=="cs"&&UiLanguages.Normalize("ja")=="en","language normalization");
        foreach(var code in new[]{"cs","de","fr"})
        {
            using var stream=typeof(UiLanguages).Assembly.GetManifestResourceStream("PawsPatchLauncher.Assets.Languages."+code+".json");
            Check(stream is not null,"embedded language catalog");
            var catalog=JsonSerializer.Deserialize<Dictionary<string,string>>(stream!)!;Check(catalog.Count>=1000,"catalog coverage");
            foreach(var (source,translation) in catalog)
            {
                Check(!string.IsNullOrWhiteSpace(translation),"empty translation");
                Check(Regex.Matches(source,@"\{[^{}]*\}").Select(m=>m.Value).Order().SequenceEqual(Regex.Matches(translation,@"\{[^{}]*\}").Select(m=>m.Value).Order()),"altered format arguments: "+source);
            }
            Check(UiLanguages.GameLanguageName("ru",code)!="Russian","localized game language");
            var external="<player {0} — Steam>";
            Check(UiLanguages.Format(code,$"Обновляю лаунчер до {external}…",$"Updating launcher to {external}…").Contains(external),"argument data preserved verbatim");
        }
        Check(UiLanguages.GameLanguageName("en","ru")=="Английский (оригинал)","English original label");
        return checks;
    }
}
