using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class CommunityTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var checks=0;
        void Check(bool condition,string why){checks++;if(!condition)throw new Exception("Community: "+why);}
        Check(new UserSettings().CommunityNotifications=="mentions","notifications default to mentions");
        foreach(var body in new[]{"@paw","Hello @PAW!","(@paw)","@paw. Next sentence","@paw\nhello"})
            Check(CommunityChat.Mentions(body,"paw"),"exact mention: "+body);
        foreach(var body in new[]{"@paws","@paw_2","@paw-other","@paw.other","user@paw","@@paw","paw"})
            Check(!CommunityChat.Mentions(body,"paw"),"not a mention: "+body);
        Check(CommunityChat.Mentions("Hi @p.aw-2!","p.aw-2"),"username punctuation is literal");
        Check(!CommunityChat.Mentions("@anyone",""),"guest has no mention");
        var tracker=new CommunityNotificationTracker();var me=Guid.NewGuid();var author=Guid.NewGuid();
        CommunityMessage N(long n,string body)=>new(n,Guid.NewGuid(),author,"author","Author",body,DateTimeOffset.UtcNow,false,0);
        var batch=new[]{N(1,"@paw old")};
        Check(!tracker.Observe("ru",batch,me.ToString(),"paw","all"),"initial history silent");
        batch=batch.Append(N(2,"hello")).ToArray();Check(!tracker.Observe("ru",batch,me.ToString(),"paw","mentions"),"ordinary message silent in mentions mode");
        batch=batch.Append(N(3,"@paw hi")).ToArray();Check(tracker.Observe("ru",batch,me.ToString(),"paw","mentions"),"new mention sounds");
        Check(!tracker.Observe("ru",batch,me.ToString(),"paw","mentions"),"repeat poll silent");
        Check(!tracker.Observe("en",batch,me.ToString(),"paw","all"),"other channel has independent baseline");
        batch=batch.Append(N(4,"@paw muted")).ToArray();Check(!tracker.Observe("ru",batch,me.ToString(),"paw","mute"),"muted arrivals silent");
        Check(!tracker.Observe("ru",batch,me.ToString(),"paw","all"),"unmute does not replay arrivals");
        batch=batch.Append(N(5,"hello all")).ToArray();Check(tracker.Observe("ru",batch,me.ToString(),"paw","all"),"all mode sounds for ordinary messages");
        batch=batch.Append(N(6,"@paw self") with {SenderId=me}).Append(N(7,"@paw removed") with {Removed=true}).ToArray();
        Check(!tracker.Observe("ru",batch,me.ToString(),"paw","all"),"own and removed messages silent");
        Check(!tracker.Observe("ru",batch,Guid.NewGuid().ToString(),"paw","all"),"account change resets baseline");
        async Task Reject(Func<Task> run){try{await run();}catch(AccountException){checks++;return;}throw new Exception("Community: rejection expected");}
        foreach(var available in new[]{470d,650,850,1200,1600,2400})
        {
            var wide=CommunityChat.Width(available,0);var narrow=CommunityChat.Width(available,1);
            Check(wide>=narrow&&wide<=620,"default is bounded");
            Check(CommunityChat.Width(available, double.NaN)==wide,"corrupt width safe");
            Check(CommunityChat.Width(available, double.PositiveInfinity)==wide,"infinite width safe");
            if(available>=760)Check(available-CommunityChat.Width(available,double.MaxValue)>=470,"main page keeps usable width");
        }
        var settings=new UserSettings{CommunityWidth=435,CommunityChannel="en",CommunityRead=new(){{"ru",123},{"en",52}}};
        var copy=JsonSerializer.Deserialize(JsonSerializer.Serialize(settings,LauncherJsonContext.Default.UserSettings),LauncherJsonContext.Default.UserSettings)!;
        Check(copy.CommunityWidth==435&&copy.CommunityChannel=="en"&&copy.CommunityRead["ru"]==123,"preferences roundtrip");
        foreach(var bad in new[]{""," \t\r\n","bad\u0001",new string('a',1001)})await Reject(()=>{CommunityChat.Validate(bad);return Task.CompletedTask;});
        CommunityChat.Validate(string.Concat(Enumerable.Repeat("🙂",1000)));checks++;
        await Reject(()=>{CommunityChat.ValidateChannel("fr");return Task.CompletedTask;});
        var owner=Guid.NewGuid();var id=Guid.NewGuid();var invalid=false;var calls=0;var language="ru";var unchanged=false;
        object Message()=>new{ordinal=invalid?0:1,message_id=id,sender_id=owner,nickname="FixturePaw",display_name="Fixture Paw",body="Привет",created_at=DateTimeOffset.UtcNow,removed=false,admin_level=0};
        using var service=new AccountService(new AccountSessionStore(Path.Combine(root,"community-account")),new Handler(async request=>
        {
            calls++; var path=request.RequestUri!.AbsolutePath;
            if(path.EndsWith("/paw_community_read"))
            {
                Check(request.Headers.Authorization is null,"guest read contains no access token");
                using var payload=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                Check(payload.RootElement.GetProperty("channel").GetString()==language,"selected language sent");
                if(unchanged)
                {
                    var cursor=payload.RootElement.GetProperty("before_ordinal");
                    Check(payload.RootElement.GetProperty("known_revision").GetString()==(cursor.ValueKind==JsonValueKind.Null?"0123456789abcdef0123456789abcdef":null),"cache revision sent only for latest page");
                    return Reply(new{status="ok",revision="0123456789abcdef0123456789abcdef",unchanged=true});
                }
                return Reply(new{status="ok",revision="0123456789abcdef0123456789abcdef",messages=new[]{Message()},more=false,history_revision=0,trimmed=false});
            }
            throw new Exception("Unexpected community route "+path);
        }));
        var messages=await service.ReadCommunityAsync("ru");Check(messages.Count==1&&messages[0].Body=="Привет","guest sees messages");
        language="en";await service.ReadCommunityAsync("en");
        unchanged=true;Check((await service.ReadCommunityAsync("en")).Count==1,"unchanged response retains history");unchanged=false;
        var before=calls;await Reject(()=>service.SendCommunityAsync("ru",id,"guest"));Check(calls==before,"guest cannot send via service");
        await Reject(()=>service.ReadCommunityAsync("unknown"));Check(calls==before,"invalid channel rejected locally");
        invalid=true;await Reject(()=>service.ReadCommunityAsync("en"));
        invalid=false;
        await Reject(()=>service.ReadCommunityPageAsync("en",0));
        await Reject(()=>service.ReadCommunityPageAsync("en",1));
        var historical=await service.ReadCommunityPageAsync("en",2);Check(historical.Messages.Single().Ordinal==1,"older page cursor accepted");
        unchanged=true;await Reject(()=>service.ReadCommunityPageAsync("en",2));unchanged=false;

        CommunityMessage M(int n)=>new(n,Guid.NewGuid(),owner,"FixturePaw","Fixture Paw","Text :ch_sword: 🙂",DateTimeOffset.UtcNow,false,0);
        var all=Enumerable.Range(1,1000).Select(M).ToArray();var history=new CommunityHistory();
        Check(history.Merge(new(all[900..],true,0,false),false,true)&&history.Messages.Count==100,"first page loads only 100");
        var reference=history.Messages;history.Merge(new(all[900..],true,0,false),false,true);
        Check(ReferenceEquals(reference,history.Messages),"unchanged snapshot preserves data identity");
        history.Merge(new(all[800..900],true,0,false),true,false);
        Check(history.Visible.Count()==200&&history.Messages.Count==200&&history.ViewStart==0,"older page extends bounded viewport");
        for(var end=800;end>0;end-=100)history.Merge(new(all[(end-100)..end],end>100,0,false),true,false);
        Check(history.Messages.Count==1000&&history.Visible.Count()==200&&!history.More,"all pages reachable with 200 visible controls");
        history.ViewStart=300;var anchor=history.Visible.First().Id;
        history.Merge(new(all[950..].Append(M(1001)).ToArray(),true,0,false),false,false);
        Check(history.Visible.First().Id==anchor&&history.Messages.Count==1001,"arrival preserves history position");
        Check(!history.Merge(new(all[..100],true,1,true),true,false),"stale older page cannot cross trim revision");
        history.Merge(new(all[900..],true,1,true),false,false);
        Check(history.Messages.Count==100&&history.Trimmed&&history.Revision==1,"trim invalidates all retained older pages");
        Check(!history.Merge(new(all[..100],true,0,false),false,true),"late pre-trim response rejected");
        history.Merge(new(Enumerable.Range(2000,100).Select(M).ToArray(),true,1,true),false,false);
        Check(history.Messages.Count==100&&history.Messages[0].Ordinal==2000,"offline gap does not join unrelated pages");
        history.Append(M(2100));Check(history.AtNewest&&history.Messages.Count==101,"sent message follows latest history");
        var writeStore=new AccountSessionStore(Path.Combine(root,"community-signedin"));
        int writes=0;var lost=true;var seenIds=new HashSet<Guid>();var refuse=false;
        using var member=new AccountService(writeStore,new Handler(async request=>
        {
            var path=request.RequestUri!.AbsolutePath;
            var user=new{id=owner,email="fixture@example.invalid"};
            if(path.EndsWith("/token"))return Reply(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user});
            if(path.EndsWith("/user"))return Reply(user);
            if(path.EndsWith("paw_profiles"))return Reply(new[]{new{id=owner,nickname="FixturePaw",display_name="Fixture Paw"}});
            if(path.EndsWith("/paw_launcher_session"))return Reply(new{status="ok"});
            Check(request.Headers.Authorization?.Parameter=="fixture-access","write uses authenticated session");
            Check(request.Headers.Contains("x-paw-launcher"),"write binds launcher instance");
            if(path.EndsWith("/paw_community_send"))
            {
                using var payload=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());var p=payload.RootElement;
                Check(p.GetProperty("channel").GetString()=="en","write uses selected channel");
                writes++;var messageId=p.GetProperty("message_id").GetGuid();seenIds.Add(messageId);
                if(lost){lost=false;throw new HttpRequestException("fixture response lost");}
                if(refuse)return Reply(new{status="rate_limit"});
                return Reply(new{status="ok",message=new{ordinal=8,message_id=messageId,sender_id=owner,nickname="FixturePaw",display_name="Fixture Paw",body=p.GetProperty("body").GetString(),created_at=DateTimeOffset.UtcNow,removed=false,admin_level=0}});
            }
            if(path.EndsWith("/paw_community_remove"))return Reply(new{status="ok"});
            throw new Exception("Unexpected signed-in route "+path);
        }));
        await member.SignInAsync("fixture@example.invalid","fixture-password");
        var sendId=Guid.NewGuid();await Reject(()=>member.SendCommunityAsync("en",sendId,"Let's play"));
        var sent=await member.SendCommunityAsync("en",sendId,"Let's play");
        Check(writes==2&&seenIds.Count==1&&sent.Id==sendId,"explicit retry preserves message identity");
        refuse=true;await Reject(()=>member.SendCommunityAsync("en",Guid.NewGuid(),"rate limited"));
        await member.RemoveCommunityAsync(sendId);checks++;
        Console.WriteLine($"COMMUNITY CLIENT PASS {checks}");return checks;
    }
    private static HttpResponseMessage Reply(object value)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(value),Encoding.UTF8,"application/json")};
    private sealed class Handler(Func<HttpRequestMessage,Task<HttpResponseMessage>> send):HttpMessageHandler
    {protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken token)=>send(request);}
}
