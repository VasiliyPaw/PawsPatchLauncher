using System.Net;
using System.Text.Json;
using PawsPatchLauncher;

internal static class HistoryNetworkTests
{
    internal static async Task<int> RunAsync(string root)
    {
        int n=0;void Check(bool ok,string message){n++;if(!ok)throw new Exception("History/network: "+message);}
        var id=Guid.NewGuid();var peer=Guid.NewGuid();var time=DateTimeOffset.UtcNow;var calls=new List<string>();
        var badPage=false;var banned=false;var reject=false;
        var store=new AccountSessionStore(Path.Combine(root,"history-network"));
        using var account=new AccountService(store,new Transport(async request=>
        {
            var path=request.RequestUri!.AbsolutePath;calls.Add(path);
            var user=new{id,email="history@example.invalid"};
            if(path.EndsWith("/token"))return AccountTests.Ok(JsonSerializer.Serialize(new{access_token="fixture-token",refresh_token="fixture-refresh",expires_in=3600,user}));
            if(path.EndsWith("/user"))return AccountTests.Ok(JsonSerializer.Serialize(user));
            if(path.EndsWith("paw_launcher_session"))return AccountTests.Ok("{\"status\":\"ok\"}");
            if(path.EndsWith("paw_profiles"))return AccountTests.Ok(JsonSerializer.Serialize(new[]{new{id,nickname="history",display_name="History",banned_at=banned?(DateTimeOffset?)time:null}}));
            if(path.EndsWith("paw_social_list"))return AccountTests.Ok(reject?"{\"status\":\"account_banned\"}":"{\"status\":\"ok\",\"players\":[]}");
            if(path.EndsWith("paw_read_message_page"))
            {
                using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                Check(body.RootElement.GetProperty("target").GetGuid()==peer,"wrong peer query");
                var cursor=body.RootElement.GetProperty("before_ordinal");
                var ordinal=cursor.ValueKind==JsonValueKind.Null?100:cursor.GetInt64()-1;
                return AccountTests.Ok(JsonSerializer.Serialize(new{status="ok",messages=Enumerable.Range((int)ordinal-49,50).Select(i=>new SocialMessage(id,Guid.NewGuid(),badPage?Guid.NewGuid():peer,"Fixture","text",time,i)).ToArray(),offers=Array.Empty<object>(),more=true,history_revision=1,trimmed=true}));
            }
            throw new Exception("Unexpected fixture route "+path);
        }),()=>time);
        await account.SignInAsync("history@example.invalid","fixture-password");calls.Clear();
        for(var i=0;i<30;i++){await account.GetFriendsAsync();time=time.AddMilliseconds(900);}
        Check(calls.Count==30&&calls.All(p=>p.EndsWith("paw_social_list")),"fresh session repeats Auth/profile/lease");
        time=time.AddSeconds(5);calls.Clear();
        await Task.WhenAll(Enumerable.Range(0,20).Select(_=>account.GetFriendsAsync()));
        Check(calls.Count==23,"parallel expired-cache calls did not share one 3-request refresh");
        Check(calls.Count(p=>p.EndsWith("/user"))==1&&calls.Count(p=>p.EndsWith("paw_profiles"))==1,"redundant Auth/profile refresh");
        calls.Clear();await account.RestoreAsync(reuseRecent:true);Check(calls.Count==0,"background timer bypasses shared cache");
        await account.RestoreAsync();Check(calls.Count==3,"explicit restore must still verify remotely");
        var page=await account.GetMessagePageAsync(peer);Check(page.Messages.Count==50&&page.More&&page.Trimmed&&page.Revision==1,"page metadata");
        var older=await account.GetMessagePageAsync(peer,page.Messages[0]);Check(older.Messages[0].Ordinal<page.Messages[0].Ordinal,"compound cursor order");
        badPage=true;bool denied=false;try{await account.GetMessagePageAsync(peer);}catch(AccountException e){denied=e.Code=="invalid_response";}Check(denied,"foreign dialog message leaked");badPage=false;
        var saved=store.Read()!;saved.ExpiresAt=time.ToUnixTimeSeconds()+80;store.Save(saved);calls.Clear();
        await account.GetFriendsAsync();Check(calls.Any(p=>p.EndsWith("/token")),"token expiring inside cache was not refreshed");
        banned=reject=true;denied=false;try{await account.GetFriendsAsync();}catch(AccountException e){denied=e.Code=="account_banned";}
        Check(denied&&account.Banned&&account.State==AccountState.SignedIn,"server ban during cache not reflected / signed player out");
        Console.WriteLine($"HISTORY / NETWORK PASS {n}: cached transport 30 calls instead of 120; concurrent refresh 23 instead of 80; synthetic clock/network only");
        return n;
    }
    private sealed class Transport(Func<HttpRequestMessage,Task<HttpResponseMessage>> respond):HttpMessageHandler
    {protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>respond(request);}
}
