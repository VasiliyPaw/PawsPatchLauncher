using System.IO.Compression;
using System.Text.Json;
using PawsPatchLauncher;

internal static class RebornTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var checks=0;void Check(bool ok,string why){if(!ok)throw new Exception("Reborn: "+why);checks++;}
        var fixture=Path.Combine(root,"reborn");Directory.CreateDirectory(fixture);var install=Path.Combine(fixture,"installed");
        async Task<(RebornBuild Build,string Archive)> Package(string channel,params (string Path,string Content,int? Attributes)[] entries)
        {
            var path=Path.Combine(fixture,Guid.NewGuid()+".zip");
            using(var archive=ZipFile.Open(path,ZipArchiveMode.Create))foreach(var item in entries)
            {var entry=archive.CreateEntry(item.Path);if(item.Attributes is int value)entry.ExternalAttributes=value;using var writer=new StreamWriter(entry.Open());writer.Write(item.Content);}
            return (new(Guid.NewGuid(),channel,"0.1.0",new FileInfo(path).Length,await CryptoAndIO.Sha256Async(path),"KohanReborn.exe",DateTimeOffset.UtcNow,new()),path);
        }
        async Task Reject(Func<Task> work,string why)
        {try{await work();throw new Exception("Expected rejection: "+why);}catch(Exception e)when(e is IOException or InvalidDataException or JsonException or AccountException or OperationCanceledException){checks++;}}
        var stable=await Package("stable",("KohanReborn.exe","fixture executable; never run",null),("Assets/data.bin","release data",null));
        var beta=await Package("beta",("KohanReborn.exe","beta fixture; never run",null),("data.pck","beta data",null));
        var authorizations=0;Task Authorize(){authorizations++;return Task.CompletedTask;}
        Check(Path.GetDirectoryName(RebornInstall.ChannelPath(install,"stable"))==Path.GetFullPath(install)&&Path.GetFileName(RebornInstall.ChannelPath(install,"stable"))=="Release"&&Path.GetFileName(RebornInstall.ChannelPath(install,"beta"))=="Beta","channel folders must share a root and use stable Release/Beta names");
        Check(RebornInstall.Installed(install,"stable") is null,"empty installation invented a build");
        await RebornInstall.InstallAsync(install,stable.Build,stable.Archive,Authorize,CancellationToken.None);
        Check(RebornInstall.Installed(install,"stable")?.Id==stable.Build.Id&&RebornInstall.Installed(install,"beta") is null,"Release did not install independently");
        await RebornInstall.InstallAsync(install,beta.Build,beta.Archive,Authorize,CancellationToken.None);
        Check(RebornInstall.Installed(install,"stable")?.Id==stable.Build.Id&&RebornInstall.Installed(install,"beta")?.Id==beta.Build.Id,"Beta changed the Release install");
        await RebornInstall.InstallAsync(install,stable.Build,stable.Archive,Authorize,CancellationToken.None);
        Check(authorizations==3&&RebornInstall.Installed(install,"stable")?.Id==stable.Build.Id,"same verified build is not safely retryable");
        foreach(var path in new[]{"../escape.exe","/root.exe","C:/outside.exe","data/../../outside.exe","data/file:stream","CON.txt"})
        {
            var bad=await Package("stable",("KohanReborn.exe","fixture",null),(path,"bad",null));
            await Reject(()=>RebornInstall.InstallAsync(install,bad.Build,bad.Archive,Authorize,CancellationToken.None),"unsafe path "+path);
        }
        var collision=await Package("stable",("KohanReborn.exe","one",null),("kohanreborn.EXE","two",null));
        await Reject(()=>RebornInstall.InstallAsync(install,collision.Build,collision.Archive,Authorize,CancellationToken.None),"case-insensitive collision");
        var link=await Package("stable",("KohanReborn.exe","fixture",null),("link","outside",unchecked((int)0xA1FF0000)));
        await Reject(()=>RebornInstall.InstallAsync(install,link.Build,link.Archive,Authorize,CancellationToken.None),"archive symlink");
        var missing=await Package("stable",("only-data.bin","no exe",null));
        await Reject(()=>RebornInstall.InstallAsync(install,missing.Build,missing.Archive,Authorize,CancellationToken.None),"missing executable");
        await Reject(()=>RebornInstall.InstallAsync(install,stable.Build with{Sha256=new('0',64)},stable.Archive,Authorize,CancellationToken.None),"wrong archive hash");
        var revoked=await Package("stable",("KohanReborn.exe","unauthorized build",null));
        await Reject(()=>RebornInstall.InstallAsync(install,revoked.Build,revoked.Archive,()=>throw new AccountException("reborn_access_denied"),CancellationToken.None),"revoked role");
        await Reject(()=>RebornInstall.InstallAsync(install,revoked.Build,revoked.Archive,Authorize,new CancellationToken(true)),"cancelled install");
        Check(RebornInstall.Installed(install,"stable")?.Id==stable.Build.Id&&RebornInstall.Installed(install,"beta")?.Id==beta.Build.Id,"failed update changed an active build");
        Check(!Directory.EnumerateDirectories(install,".staging-*",SearchOption.AllDirectories).Any(),"owned staging directories left after failure");
        await File.WriteAllTextAsync(Path.Combine(Path.GetDirectoryName(RebornInstall.Executable(install,stable.Build))!,"keep.txt"),"user content");
        await Reject(()=>RebornInstall.InstallAsync(install,stable.Build,stable.Archive,Authorize,CancellationToken.None),"existing user files");
        Check(File.ReadAllText(Path.Combine(Path.GetDirectoryName(RebornInstall.Executable(install,stable.Build))!,"keep.txt"))=="user content","user files were overwritten");
        await Reject(()=>Task.Run(()=>RebornBuild.Validate(stable.Build with{Channel="../beta"})),"invalid channel");
        var foreignRoot=Path.Combine(fixture,"foreign");Directory.CreateDirectory(RebornInstall.ChannelPath(foreignRoot,"stable"));
        var foreignMarker=Path.Combine(RebornInstall.ChannelPath(foreignRoot,"stable"),"active.json");await File.WriteAllTextAsync(foreignMarker,"unrelated user file");
        await Reject(()=>RebornInstall.InstallAsync(foreignRoot,stable.Build,stable.Archive,Authorize,CancellationToken.None),"foreign marker");
        Check(File.ReadAllText(foreignMarker)=="unrelated user file"&&RebornInstall.Installed(foreignRoot,"stable") is null,"unrelated marker was overwritten or accepted");
        var translated=stable.Build with{Id=Guid.NewGuid(),Notes=new(){["ru"]=new('Ж',10000),["uk"]=new('І',10000)}};
        await RebornInstall.InstallAsync(install,translated,stable.Archive,Authorize,CancellationToken.None);
        Check(RebornInstall.Installed(install,"stable")?.Notes["uk"].Length==10000,"valid localized changelog exceeds installation-marker limit");
        var historyRelease=stable.Build with { PublishedAt=DateTimeOffset.Parse("2026-11-10T12:00:00Z"),Notes=new(){["ru"]="Релиз",["en"]="Release",["uk"]="Українські зміни",["cs"]="České změny",["de"]="Deutsche Änderungen",["fr"]="Modifications françaises"} };
        var historyBeta=beta.Build with { PublishedAt=historyRelease.PublishedAt.AddDays(1),Notes=new(){["en"]="Beta notes"} };
        var historyOld=historyRelease with { Id=Guid.NewGuid(),Version="0.0.9",PublishedAt=historyRelease.PublishedAt.AddDays(-1) };
        var rows=RebornHistory.Entries([historyRelease,historyOld,historyBeta],"all","fr");
        Check(rows.Count==3&&rows[0].Branch=="beta"&&rows[2].Entry.Version=="0.0.9","history omits older builds or sorts by wrong date");
        Check(RebornHistory.Entries([historyRelease,historyOld,historyBeta],"stable","ru").Count==2&&RebornHistory.Entries([historyRelease,historyOld,historyBeta],"beta","ru").Count==1,"history channel filtering");
        foreach(var lang in new[]{"ru","en","uk","cs","de","fr"})
            Check(RebornHistory.Entries([historyRelease],"stable",lang)[0].LocalizedBody==historyRelease.Notes[lang],"history ignores translated notes: "+lang);
        Check(rows[0].LocalizedBody=="Beta notes","history missing-translation fallback");
        var read=new UserSettings();var french=RebornHistory.Entries([historyRelease],"stable","fr")[0];
        Check(ChangelogTimeline.MarkViewed(read,[french],true)&&!ChangelogTimeline.IsUnread(read,RebornHistory.Entries([historyRelease],"stable","uk")[0]),"changing interface language marks the same history unread");
        var edited=historyRelease with { Notes=new(historyRelease.Notes){["uk"]="Змінений текст"} };
        Check(ChangelogTimeline.IsUnread(read,RebornHistory.Entries([edited],"stable","fr")[0]),"edited translated notes are not marked unread");
        Check(!ChangelogTimeline.IsUnread(read,RebornHistory.Entries([historyRelease with {Notes=historyRelease.Notes.Reverse().ToDictionary(n=>n.Key,n=>n.Value)}],"stable","fr")[0]),"dictionary key order changes history identity");
        var player=Guid.NewGuid();var historyCalls=0;var mode="valid";
        object Wire(RebornBuild b)=>new {id=b.Id,channel=b.Channel,version=b.Version,size=b.Size,sha256=b.Sha256,executable=b.Executable,published_at=b.PublishedAt,notes=b.Notes};
        var largeRows=Enumerable.Range(0,20).Select(i=>Wire(historyRelease with {Id=Guid.NewGuid(),Version="0.1."+i,Notes=new(){["ru"]=new('Ж',10000)}})).ToArray();
        var largeResponse=JsonSerializer.Serialize(new{status="ok",releases=largeRows});
        Check(System.Text.Encoding.UTF8.GetByteCount(largeResponse)>350000,"history transport fixture must exceed the ordinary portal limit");
        using(var account=new AccountService(new AccountSessionStore(Path.Combine(fixture,"history-account")),new AccountTests.FakeAuth(request=>
        {
            var path=request.RequestUri!.AbsolutePath;var user=new{id=player,email="reborn@example.invalid"};
            if(path.EndsWith("/token"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user})));
            if(path.EndsWith("/user"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(user)));
            if(path.EndsWith("paw_profiles"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new[]{new{id=player,nickname="reborn",paws_team=true}})));
            if(path.EndsWith("/reborn-builds"))
            {
                historyCalls++;Check((request.RequestUri.Query=="?action=history&protocol=2"||mode=="unpublished")&&request.Headers.Authorization?.Scheme=="Bearer"&&request.Headers.Contains("x-paw-launcher"),"history must use an authenticated private endpoint and launcher session");
                if(mode=="unpublished"||mode=="other404")return Task.FromResult(new System.Net.Http.HttpResponseMessage(System.Net.HttpStatusCode.NotFound){Content=new System.Net.Http.StringContent(mode=="unpublished"?"{\"code\":\"NOT_FOUND\",\"message\":\"Requested function was not found\"}":"{\"status\":\"invalid_request\"}")});
                return Task.FromResult(mode=="denied"?new System.Net.Http.HttpResponseMessage(System.Net.HttpStatusCode.Forbidden){Content=new System.Net.Http.StringContent("{\"status\":\"reborn_access_denied\"}")}:
                    AccountTests.Ok(mode=="duplicate"?JsonSerializer.Serialize(new{status="ok",releases=new[]{Wire(historyRelease),Wire(historyRelease)}}):mode=="oversized"?JsonSerializer.Serialize(new{status="ok",releases=Enumerable.Range(0,201).Select(_=>Wire(historyRelease)).ToArray()}):largeResponse));
            }
            throw new Exception("Unexpected Reborn history fixture route");
        })))
        {
            await account.SignInAsync("reborn@example.invalid","fixture-password");
            Check((await account.GetRebornHistoryAsync()).Count==20,"bounded multilingual history response was truncated by ordinary portal limit");
            mode="unpublished";Check((await account.GetRebornHistoryAsync()).Count==0&&(await account.GetRebornBuildsAsync()).Count==0,"missing undeployed read endpoint must give intentionally empty channels");
            foreach(var test in new[]{("other404","service_error"),("duplicate","invalid_response"),("oversized","invalid_response"),("denied","reborn_access_denied")})
            {
                mode=test.Item1;try{await account.GetRebornHistoryAsync();throw new Exception("Expected history rejection");}catch(AccountException error){Check(error.Code==test.Item2,"history error mapping: "+mode);}
            }
        }
        Check(historyCalls==7,"history transport performed unexpected requests");
        checks += await RebornDownloadTests.RunAsync(fixture);
        Console.WriteLine($"REBORN INSTALL PASS {checks}: independent channels, verification, safe extraction, retry, revocation, cancellation and preserved installations; no EXE executed");return checks;
    }
}
