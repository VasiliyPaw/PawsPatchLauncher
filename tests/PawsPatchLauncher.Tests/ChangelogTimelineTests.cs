using System.Text.Json;
using PawsPatchLauncher;
namespace PawsPatchLauncher.Tests;
internal static class ChangelogTimelineTests
{
    internal static int Run()
    {
        int count = 0;
        void Check(bool value, string reason) { if (!value) throw new Exception(reason); count++; }
        LocalizedText Both(string s) => new() { Ru=s, En=s };
        var formatted=ChangelogTextLayout.Parse("## Заголовок\n\nТекст строки\n\n- Первый пункт\n- Второй пункт");
        Check(formatted.Select(x=>x.Kind).SequenceEqual([ChangelogTextKind.Heading,ChangelogTextKind.Paragraph,ChangelogTextKind.Bullet,ChangelogTextKind.Bullet])&&formatted[0].Text=="Заголовок","markdown headings and bullets become UI lines");
        Check(ChangelogTextLayout.Preview("## Заголовок\n\nПервый абзац\n\nВторой абзац").StartsWith("## Заголовок\n\nПервый абзац"),"preview preserves its visible heading");
        ChangelogEntry Entry(string mod, string source, string version, string body="body") => new() { Category=source, Mods=[mod], Version=version, PublishedAt="2026-09-10", Title=Both(source+version), Body=Both(body) };
        var stable = new ChannelManifest { Channel="stable", PublishedAt="2026-09-10" };
        var beta = new ChannelManifest { Channel="beta", PublishedAt="2026-09-11" };
        foreach (var mod in new[] {GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})
        { stable.Changelog.Add(Entry(mod,"patch","1")); beta.Changelog.Add(Entry(mod,"patch","2")); stable.Changelog.Add(Entry(mod,"mod","3")); beta.Changelog.Add(Entry(mod,"mod","3")); }
        stable.Changelog.Add(Entry("","launcher","4")); beta.Changelog.Add(Entry("","launcher","4"));
        ChannelManifest?[] feeds=[stable,beta];
        foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})
        {
            foreach(var branch in new[]{"stable","beta","all"})
            {
                var patch=ChangelogTimeline.Entries(feeds,mod,"patch",branch);
                Check(patch.Count==(branch=="all"?2:1),"branch filtering"); Check(patch.All(x=>x.Subject==mod&&x.Source=="patch"),"mod isolation");
                var settings=new UserSettings { Mod=mod };
                Check(patch.All(x=>ChangelogTimeline.IsUnread(settings,x)),"new entries missing badges");
                Check(!ChangelogTimeline.MarkViewed(settings,patch,false),"hidden history marked read");
                Check(ChangelogTimeline.MarkViewed(settings,patch,true),"visible history not marked");
                Check(patch.All(x=>!ChangelogTimeline.IsUnread(settings,x)),"read state not retained");
                Check(ChangelogTimeline.Entries(feeds,mod,"mod","all").Where(x=>!x.Overview).All(x=>ChangelogTimeline.IsUnread(settings,x)),"patch view read mod history");
                var other=mod==GameMod.Vanilla?GameMod.Immortals:GameMod.Vanilla;
                Check(ChangelogTimeline.Entries(feeds,other,"patch",branch).All(x=>ChangelogTimeline.IsUnread(settings,x)),"another mod was marked");
                var reloaded=JsonSerializer.Deserialize(JsonSerializer.Serialize(settings,LauncherJsonContext.Default.UserSettings),LauncherJsonContext.Default.UserSettings)!;
                Check(patch.All(x=>!ChangelogTimeline.IsUnread(reloaded,x)),"restart lost read state");
            }
            var mods=ChangelogTimeline.Entries(feeds,mod,"mod","beta");
            Check(mods.Count(x=>x.Entry.Version=="3")==1,"author release duplicated between feeds");
            Check(mods.All(x=>x.Source=="mod"&&x.Branch==""),"author mod incorrectly uses patch branch");
        }
        Check(ChangelogTimeline.Entries(feeds,"launcher","all","all").Count==1,"launcher duplicate");
        var legacy=new UserSettings { Mod=GameMod.ArcaneWars,ReadChangelogs=new(){["patch:stable"]="1:2026-09-10"} };
        var old=ChangelogTimeline.Entries(feeds,GameMod.ArcaneWars,"patch","stable");
        Check(!ChangelogTimeline.IsUnread(legacy,old[0]),"legacy state migration");
        ChangelogTimeline.MarkViewed(legacy,old,true); old[0].Entry.Body.Ru="edited";
        Check(ChangelogTimeline.IsUnread(legacy,old[0]),"corrected release stays read");
        stable.Changelog.Insert(0,Entry(GameMod.ArcaneWars,"patch","5"));
        var updated=ChangelogTimeline.Entries(feeds,GameMod.ArcaneWars,"patch","stable");
        Check(updated[0].Entry.Version=="5","release ordering");
        var same=Entry(GameMod.ArcaneWars,"patch","5"); same.Title=Both("Second note for same version"); stable.Changelog.Add(same);
        Check(ChangelogTimeline.Entries(feeds,GameMod.ArcaneWars,"patch","stable").Count==3,"same-version notes lost");
        var vanilla=ChangelogTimeline.Entries([],GameMod.Vanilla,"mod","all");
        Check(vanilla.Count==0,"invented original game history");
        var immortal=ChangelogTimeline.Entries([],GameMod.Immortals,"mod","all");
        Check(immortal.Any(x=>x.Overview&&x.Entry.PublishedAt==""),"missing honest mod overview");
        Check(immortal.Where(x=>x.Overview).All(x=>!ChangelogTimeline.IsUnread(new(),x)),"overview creates fake update");
        var aw=ChangelogTimeline.Entries([],GameMod.ArcaneWars,"mod","all");
        Check(aw.Count(x=>!x.Overview)==3,"bundled author changes unavailable offline");
        Check(aw.Where(x=>!x.Overview).All(x=>x.Entry.PublishedAt==""),"invented source dates");
        var bytes=JsonSerializer.Serialize(stable); ChangelogTimeline.Entries(feeds,GameMod.ArcaneWars,"all","all");
        Check(bytes==JsonSerializer.Serialize(stable),"signed source mutated");
        Console.WriteLine($"TIMELINE PASS {count}: sources, all mod/channel directions, migration, restart, edits, duplicates, offline author releases and honest missing dates");
        return count;
    }
}
