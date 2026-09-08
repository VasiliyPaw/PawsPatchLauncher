using System.Net;
using System.Net.Http;
using System.Text.Json;
using PawsPatchLauncher;

internal static class LauncherSessionTests
{
    internal static async Task<int> RunAsync(string root)
    {
        int checks=0;
        void Check(bool value,string why) { checks++; if(!value) throw new Exception("Launcher session: "+why); }
        async Task Replaced(Func<Task> action)
        {
            try { await action(); throw new Exception("Expected replaced session"); }
            catch(AccountException e) { Check(e.Code=="session_replaced","unexpected "+e.Code); }
        }
        var server=new Server();
        AccountSessionStore Store(string name)=>new(Path.Combine(root,"launcher-session",name));
        AccountService Client(AccountSessionStore store)=>new(store,new Handler(server));
        var local=Store("local");
        using var first=Client(local);
        await first.SignInAsync("fixture@example.invalid","secret");
        var initial=local.Read()!;
        Check(initial.LauncherId!=Guid.Empty && initial.LoginId!=Guid.Empty,"missing protected ownership");
        using var restarted=Client(local);
        await restarted.RestoreAsync();
        Check(restarted.State==AccountState.SignedIn,"remembered restart");
        Check(local.Read()!.LauncherId!=initial.LauncherId && local.Read()!.LoginId==initial.LoginId,"restart did not rotate instance");
        await Replaced(()=>first.RestoreAsync());
        Check(first.State==AccountState.Guest && File.Exists(local.SessionPath),"loser cleared winner credentials");
        var before=server.Logouts;
        await first.SignOutAsync(); await first.RestoreAsync();
        Check(first.State==AccountState.Guest && server.Logouts==before,"loser adopted/revoked winner");
        await restarted.RestoreAsync();
        Check(restarted.State==AccountState.SignedIn,"winner stopped after loser logout");
        var claims=server.Claims;
        for(int i=0;i<5;i++) await restarted.RestoreAsync();
        Check(server.Claims==claims,"poll takes ownership");

        var remoteStore=Store("vm");
        using var remote=Client(remoteStore);
        await remote.SignInAsync("fixture@example.invalid","secret");
        await Replaced(()=>restarted.GetFriendsAsync());
        Check(restarted.State==AccountState.Guest && !File.Exists(local.SessionPath),"remote takeover did not clear old UI/store");
        Check((await remote.GetFriendsAsync()).Count==0,"remote social access denied");
        Check(File.Exists(remoteStore.SessionPath),"takeover removed remote storage");
        var remoteId=remoteStore.Read()!.LauncherId;
        var saved=remoteStore.Read()!; saved.ExpiresAt=0; remoteStore.Save(saved);
        await remote.RestoreAsync();
        Check(remoteStore.Read()!.LauncherId==remoteId,"refresh changed launcher owner");
        Check(server.Refreshes==1,"refresh missing");

        // Stale logout before the old process has polled must not call Auth logout.
        using var newer=Client(Store("newer"));
        await newer.SignInAsync("fixture@example.invalid","secret");
        before=server.Logouts;
        Check(await remote.SignOutAsync(),"old already-displaced logout failed");
        Check(server.Logouts==before,"old logout reached Auth");
        await newer.RestoreAsync(); Check(newer.State==AccountState.SignedIn,"newer revoked by stale logout");

        // A lost reply after resume committed: retry with SAME instance is idempotent.
        var disk=Store("lost-reply");
        using(var seed=Client(disk)) await seed.SignInAsync("fixture@example.invalid","secret");
        using var retry=Client(disk);
        server.DropResumeReply=true;
        try { await retry.RestoreAsync(); throw new Exception("Expected network error"); }
        catch(AccountException e) { Check(e.Code=="network","wrong lost reply status"); }
        Check(retry.State==AccountState.Offline && File.Exists(disk.SessionPath),"lost reply erased remember");
        await retry.RestoreAsync(); Check(retry.State==AccountState.SignedIn,"resume retry kicked itself");

        // A delayed older successful Auth response cannot steal a later login.
        var delayedStore=Store("delayed");
        using var delayed=Client(delayedStore);
        server.DelayNextClaim=true;
        var pending=delayed.SignInAsync("fixture@example.invalid","secret");
        await server.ClaimStarted.Task;
        using var latest=Client(Store("latest"));
        await latest.SignInAsync("fixture@example.invalid","secret");
        server.ContinueClaim.TrySetResult();
        await Replaced(()=>pending);
        Check(delayed.State==AccountState.Guest && !File.Exists(delayedStore.SessionPath),"failed claim became signed in");
        await latest.RestoreAsync(); Check(latest.State==AccountState.SignedIn,"older delayed claim displaced latest");
        Check(await latest.SignOutAsync(),"current logout failed");
        Check(latest.State==AccountState.Guest,"logout not guest");
        Check(server.Releases>0 && server.Logouts>0,"logout skipped server release/revocation");
        using var memoryOnly=Client(Store("memory-only"));
        await memoryOnly.SignInAsync("fixture@example.invalid","secret",remember:false);
        Check(!File.Exists(Store("memory-only").SessionPath),"remember off wrote credentials");
        await memoryOnly.RestoreAsync(); Check(memoryOnly.State==AccountState.SignedIn,"memory session cannot check");
        server.Revoked=true;
        try { await memoryOnly.RestoreAsync(); throw new Exception("Expected expired"); }
        catch(AccountException e) { Check(e.Code=="session_expired","revocation result"); }
        Check(memoryOnly.State==AccountState.Guest,"revocation kept profile");
        // A cached session may reach the guarded read RPC once after remote takeover.
        // It must be rejected there and clear the old client immediately (asserted above).
        Check(server.UnauthorizedDataCalls==1,"displaced cached client was not rejected exactly once");
        Console.WriteLine($"LAUNCHER SESSION PASS {checks}: two stores/processes, restart, no ping-pong, stale logout, lost reply, delayed login, refresh and remember; mocked network");
        return checks;
    }

    private sealed class Handler(Server server):HttpMessageHandler
    { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>server.Send(request,ct); }
    private sealed class Server
    {
        private readonly string _user=Guid.NewGuid().ToString();
        private readonly object _gate=new();
        private int _issued,_active;
        private string _instance="";
        private bool _released;
        public int Claims,Logouts,Releases,Refreshes,UnauthorizedDataCalls;
        public bool DropResumeReply,DelayNextClaim,Revoked;
        public TaskCompletionSource ClaimStarted=new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource ContinueClaim=new(TaskCreationOptions.RunContinuationsAsynchronously);
        private HttpResponseMessage Json(object data)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(data))};
        private object User()=>new{id=_user,email="fixture@example.invalid"};
        private HttpResponseMessage Session(int id)=>Json(new{access_token="access-"+id,refresh_token="refresh-"+id,expires_in=3600,user=User()});
        public async Task<HttpResponseMessage> Send(HttpRequestMessage req,CancellationToken ct)
        {
            var path=req.RequestUri!.AbsolutePath;
            using var body=JsonDocument.Parse(req.Content is null?"{}":await req.Content.ReadAsStringAsync(ct));
            string action=body.RootElement.TryGetProperty("action",out var a)?a.GetString()!:"";
            if(path.EndsWith("paw_launcher_session") && action=="claim" && DelayNextClaim)
            { DelayNextClaim=false; ClaimStarted.TrySetResult(); await ContinueClaim.Task.WaitAsync(ct); }
            lock(_gate)
            {
                if(req.RequestUri.Query.Contains("grant_type=password")) return Session(++_issued);
                if(req.RequestUri.Query.Contains("grant_type=refresh_token")) { Refreshes++; return Session(int.Parse(body.RootElement.GetProperty("refresh_token").GetString()!.Split('-')[1])); }
                var token=req.Headers.Authorization?.Parameter;
                int session=token is null?0:int.Parse(token.Split('-')[1]);
                if(path.EndsWith("/user"))return Json(User());
                if(path.EndsWith("/logout")){Logouts++;return Json(new{});}
                var instance=req.Headers.GetValues("x-paw-launcher").Single();
                if(path.EndsWith("paw_launcher_session"))
                {
                    if(Revoked)return Json(new{status="session_expired"});
                    var owns=session==_active && instance==_instance && !_released;
                    if(action=="check")return Json(new{status=owns?"ok":"session_replaced"});
                    if(action=="release") {if(owns){_released=true;Releases++;}return Json(new{status=owns?"ok":"session_replaced"});}
                    Claims++;
                    var prior=body.RootElement.GetProperty("previous").GetString();
                    if(!owns && _active!=0 && (action=="claim"?session<=_active:session!=_active||prior!=_instance||_released)) return Json(new{status="session_replaced"});
                    _active=session;_instance=instance;_released=false;
                    if(action=="resume" && DropResumeReply){DropResumeReply=false;throw new HttpRequestException("Mock dropped response");}
                    return Json(new{status="ok"});
                }
                if(session!=_active||instance!=_instance||_released) {UnauthorizedDataCalls++;return Json(new{status="session_replaced"});}
                if(path.Contains("paw_profiles"))return Json(new[]{new{id=_user,nickname="FixturePaw"}});
                if(path.EndsWith("paw_social_list"))return Json(new{status="ok",players=Array.Empty<object>()});
                throw new Exception("Unexpected session fixture route");
            }
        }
    }
}
