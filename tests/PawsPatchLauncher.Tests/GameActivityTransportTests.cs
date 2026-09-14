using System.Net;
using System.Text.Json;
using PawsPatchLauncher;

internal static class GameActivityTransportTests
{
    public static async Task<int> RunAsync(string root)
    {
        var checks=0;void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Activity transport: "+why);}
        foreach(var legacy in new[]{false,true})
        {
            var now=DateTimeOffset.UtcNow;var owner=Guid.NewGuid();var peer=Guid.NewGuid();var attempts=0;var regular=0;var mode="ok";
            var activity=new GameActivity("match",true,125,192,192,Players:[new("p1","Player",false)]);
            var versions=new SocialVersions("0.7.5.0");
            HttpResponseMessage Json(object body)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(body))};
            using var service=new AccountService(new AccountSessionStore(Path.Combine(root,"activity-transport-"+legacy)),new Mock(async request=>
            {
                var path=request.RequestUri!.AbsolutePath;
                if(path.EndsWith("/token"))return Json(new{access_token="test",refresh_token="test",expires_in=3600,user=new{id=owner,email="fixture@example.invalid"}});
                if(path.EndsWith("/auth/v1/user"))return Json(new{id=owner,email="fixture@example.invalid"});
                if(path.EndsWith("paw_profiles"))return Json(new[]{new{id=owner,nickname="fixture"}});
                if(path.EndsWith("paw_launcher_session"))return Json(new{status="ok"});
                if(path.EndsWith("paw_presence"))
                {
                    using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());var components=body.RootElement.GetProperty("components");
                    Check(SocialVersions.Read(components.GetProperty("_versions"))==versions,"version envelope retained");
                    if(components.TryGetProperty("_activity",out var payload)){attempts++;Check(GameActivity.Read(payload)?.Phase=="match","activity envelope valid");return Json(new{status=legacy?"invalid_presence":"ok"});}
                    regular++;return Json(new{status="ok"});
                }
                if(path.EndsWith("paw_game_activity"))
                {
                    if(mode=="bad_stamp")return Json(new{status="ok",activity,observed_at=17});
                    if(mode=="invalid")return Json(new{status="ok",activity=activity with{Phase="bad"},observed_at=now});
                    if(mode=="missing")return Json(new{status="ok",activity=(GameActivity?)null});
                    return Json(new{status="ok",activity,observed_at=now});
                }
                if(path.EndsWith("paw_social_list"))return Json(new{status="ok",players=new[]{new{id=peer,nickname="peer",relation="friend",presence="playing",activity=activity.Summary()}}});
                throw new Exception("Unexpected fixture route "+path);
            }),()=>now);
            await service.SignInAsync("fixture@example.invalid","fixture-password",remember:false);
            Task Send(bool playing=true)=>service.PublishConfigurationPresenceAsync(playing,"unknown",new Dictionary<string,bool>(),null,versions:versions,activity:activity);
            await Send();await Send();
            Check(attempts==(legacy?1:2)&&regular==(legacy?2:0),"older server retried on every heartbeat");
            now=now.AddMinutes(16);await Send();Check(attempts==(legacy?2:3),"server capability was never retried");
            var before=attempts;await Send(false);Check(attempts==before,"closed game sent stale activity");
            Check((await service.GetFriendsAsync()).Single().Activity?.Phase=="match","profile summary parse");
            Check((await service.GetGameActivityAsync(peer))?.Activity.Width==192,"detail response parse");
            mode="missing";Check(await service.GetGameActivityAsync(peer) is null,"unavailable details invented data");
            foreach(var malformed in new[]{"bad_stamp","invalid"})
            {
                mode=malformed;bool denied=false;try{await service.GetGameActivityAsync(peer);}catch(AccountException e){denied=e.Code=="invalid_response";}
                Check(denied,"invalid server response "+malformed);
            }
        }
        Console.WriteLine($"GAME ACTIVITY TRANSPORT PASS {checks}");return checks;
    }
    private sealed class Mock(Func<HttpRequestMessage,Task<HttpResponseMessage>> action):HttpMessageHandler
    { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>action(request); }
}
