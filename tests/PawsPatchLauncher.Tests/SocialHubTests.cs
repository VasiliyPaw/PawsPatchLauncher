using PawsPatchLauncher;
using System.Text.Json;

public static class SocialHubTests
{
    private sealed class Clock : TimeProvider
    {
        public DateTimeOffset Now = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => Now;
    }
    public static async Task<int> RunAsync(string root)
    {
        int count=0;
        void Check(bool ok,string why){count++;if(!ok)throw new Exception("Social hub: "+why);}
        var clock=new Clock(); var feedback=new OperationFeedback(clock);
        feedback.Show(()=>"notice",duration:TimeSpan.FromSeconds(3));
        var version=feedback.Version;
        Check(feedback.Remaining==TimeSpan.FromSeconds(3),"initial animation duration");
        Check(feedback.Progress==0,"initial progress");
        clock.Now+=TimeSpan.FromSeconds(1.5);Check(Math.Abs(feedback.Progress-.5)<.001,"half progress");
        Check(feedback.Remaining==TimeSpan.FromSeconds(1.5)&&feedback.Version==version,"reading progress restarted animation");
        clock.Now+=TimeSpan.FromSeconds(1.5);Check(feedback.Progress==1&&feedback.Message is null,"expiry");
        Check(feedback.Remaining is null&&feedback.Version>version,"expiry did not invalidate animation identity");
        feedback.Show(()=>"error",true,TimeSpan.FromSeconds(8),true);
        clock.Now+=TimeSpan.FromSeconds(4);Check(Math.Abs(feedback.Progress-.5)<.001,"failure progress");
        feedback.Show(()=>"replacement",duration:TimeSpan.FromSeconds(3));Check(feedback.Progress==0,"replacement resets progress");
        version=feedback.Version;feedback.Show(()=>"replacement",duration:TimeSpan.FromSeconds(3));
        Check(feedback.Version>version&&feedback.Remaining==TimeSpan.FromSeconds(3),"same text did not renew animation");
        feedback.Show(()=>"persistent",true);Check(!feedback.HasExpiry&&feedback.Progress==0,"persistent errors unchanged");
        Check(feedback.Remaining is null,"persistent notice invented animation duration");
        feedback.Show(()=>"elapsed",duration:TimeSpan.FromMilliseconds(1));clock.Now+=TimeSpan.FromSeconds(1);
        Check(feedback.Remaining==TimeSpan.Zero,"remaining duration became negative");
        feedback.Show(()=>"older",true,TimeSpan.FromSeconds(8),true);clock.Now+=TimeSpan.FromSeconds(2);
        var snapshot=feedback.Snapshot();feedback.Show(()=>"newer",duration:TimeSpan.FromSeconds(3));
        Check(snapshot.Message=="older"&&snapshot.Failed&&snapshot.Remaining==TimeSpan.FromSeconds(6),"stack snapshot changed text/style/deadline");
        clock.Now+=TimeSpan.FromSeconds(3);
        Check(feedback.Message is null&&snapshot.Message=="older","latest expiry cleared older notice");
        clock.Now+=TimeSpan.FromSeconds(3);Check(snapshot.Message is null,"older notice did not expire independently");
        var translation="first language";feedback.Show(()=>translation);snapshot=feedback.Snapshot();translation="second language";
        Check(snapshot.Message==translation,"archived toast lost localization callback");
        feedback.Clear();Check(snapshot.Message==translation,"clearing latest cleared archived state");
        var archive=Path.Combine(root,"download-date-fixture.zip");
        Check(PackageDownloadDate.Read(archive) is null,"legacy archive invented date");
        var before=DateTimeOffset.UtcNow; await PackageDownloadDate.RecordAsync(archive);
        var date=PackageDownloadDate.Read(archive);
        Check(date>=before&&date<=DateTimeOffset.UtcNow,"verified archive completion date");
        var installed=new InstallState {Modules=new() {["pawpatch-core"]=new InstalledModule {Version="test",Enabled=true,DownloadedAt=date}}};
        var state=JsonSerializer.Deserialize(JsonSerializer.Serialize(installed,LauncherJsonContext.Default.InstallState),LauncherJsonContext.Default.InstallState)!;
        Check(state.Modules["pawpatch-core"].DownloadedAt==date,"state/rollback timestamp round trip");
        await File.WriteAllTextAsync(archive+".downloaded-at","malformed");
        Check(PackageDownloadDate.Read(archive) is null,"corrupt metadata accepted");
        await File.WriteAllTextAsync(archive+".downloaded-at",DateTimeOffset.UtcNow.AddYears(1).ToString("O"));
        Check(PackageDownloadDate.Read(archive) is null,"future metadata accepted");
        await File.WriteAllTextAsync(archive+".downloaded-at",new string('x',1024));
        Check(PackageDownloadDate.Read(archive) is null,"unbounded metadata");
        await File.WriteAllBytesAsync(archive,[1,2,3,4]);
        var package=new PackageRelease {Id="date-test",Version="1",Size=4,Sha256=await CryptoAndIO.Sha256Async(archive),Urls=[archive]};
        var client=new FeedClient(new LauncherConfiguration {CacheRoot=Path.Combine(root,"dated-download-cache")});
        var cached=await client.DownloadVerifiedAsync(package,null);
        var completedAt=PackageDownloadDate.Read(cached);
        Check(completedAt is not null,"real verified completion not stamped");
        Check(await client.DownloadVerifiedAsync(package,null)==cached&&PackageDownloadDate.Read(cached)==completedAt,"cache hit changed date");
        File.Delete(cached+".downloaded-at");
        await client.DownloadVerifiedAsync(package,null);
        Check(PackageDownloadDate.Read(cached) is null,"legacy cache hit fabricated historical date");
        var broken=new PackageRelease {Id="date-test",Version="bad",Size=4,Sha256=new string('0',64),Urls=[archive]};
        var rejected=false;
        try { await client.DownloadVerifiedAsync(broken,null); } catch(AggregateException) { rejected=true; }
        Check(rejected&&!Directory.EnumerateFiles(Path.Combine(client.CacheDirectory,"downloads","date-test","bad"),"*.downloaded-at").Any(),
            "unverified download stamped");
        Console.WriteLine($"SOCIAL HUB POLICY PASS {count}: notification lifecycle, verified download dates and legacy/rollback metadata");
        return count;
    }
}
