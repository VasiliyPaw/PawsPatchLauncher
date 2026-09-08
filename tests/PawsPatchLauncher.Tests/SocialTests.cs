using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class SocialTests
{
    internal static async Task<int> RunAsync(string root)
    {
        int checks=0;
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Social: "+why);}
        async Task Reject(Func<Task> action,string? code=null) {
            try {await action();} catch(Exception e) when(e is AccountException or InvalidDataException or InvalidOperationException or OperationCanceledException) {
                Check(code is null || e is AccountException ae && ae.Code==code,"wrong error: "+e.Message);return;
            }
            throw new Exception("Social: expected rejection "+code);
        }
        var owner=Guid.NewGuid();var peer=Guid.NewGuid();var outsider=Guid.NewGuid();
        var boxRoot=Path.Combine(root,"social");var box=new SocialOutbox(boxRoot);
        var message=new PendingSocialMessage(owner,peer,Guid.NewGuid(),"fixture-private-message","text");
        await box.AddAsync(message);await box.AddAsync(message);
        Check((await box.ReadAsync(owner)).Count==1,"enqueue is not idempotent");
        var disk=await File.ReadAllBytesAsync(Path.Combine(boxRoot,"account","outbox",owner.ToString("N")+".dat"));
        Check(!Encoding.UTF8.GetString(disk).Contains("fixture-private"),"outbox plaintext");
        Check((await new SocialOutbox(boxRoot).ReadAsync(owner)).Single()==message,"restart changed ID/body");
        Check((await box.ReadAsync(outsider)).Count==0,"other account sees queue");
        await Reject(()=>box.AddAsync(message with {Body="altered"}));
        await Task.WhenAll(Enumerable.Range(0,10).Select(i=>new SocialOutbox(boxRoot).AddAsync(message with{Id=Guid.NewGuid(),Body="Concurrent "+i})));
        Check((await box.ReadAsync(owner)).Count==11,"parallel process queue lost entries");
        await box.FailAsync(owner,message.Id,"friend_required");
        Check((await box.ReadAsync(owner)).Single(m=>m.Id==message.Id).Error=="friend_required","permanent failure missing");
        Check(!message.TimedOut(message.CreatedAt.AddSeconds(59.999)),"early send timeout");
        Check(message.TimedOut(message.CreatedAt.AddSeconds(60)),"one minute deadline missing");
        await box.RetryAsync(owner,message.Id);
        var retried=(await box.ReadAsync(owner)).Single(m=>m.Id==message.Id);
        Check(retried.Id==message.Id && retried.Body==message.Body && retried.Error=="" && retried.RetriedAt is not null,"retry changed deduplication key/body");
        await box.FailAttemptAsync(message,"delivery_timeout");
        Check((await box.ReadAsync(owner)).Single(m=>m.Id==message.Id).Error=="","late prior attempt poisoned retry");
        await box.FailAttemptAsync(retried,"delivery_timeout");
        Check((await new SocialOutbox(boxRoot).ReadAsync(owner)).Single(m=>m.Id==message.Id).Error=="delivery_timeout","timeout not durable on restart");
        await box.RemoveAsync(owner,message.Id);await box.RemoveAsync(owner,message.Id);
        Check((await box.ReadAsync(owner)).Count==10,"discard not idempotent");
        var legacyRoot=Path.Combine(root,"legacy-social");var legacyDir=Path.Combine(legacyRoot,"account","outbox");Directory.CreateDirectory(legacyDir);
        var legacyFile=Path.Combine(legacyDir,owner.ToString("N")+".dat");
        var oldJson=JsonSerializer.SerializeToUtf8Bytes(new[]{new{message.Owner,message.Target,message.Id,message.Body,message.Kind,Error=""}});
        var protect=typeof(AccountService).Assembly.GetType("PawsPatchLauncher.WindowsUserProtection")!.GetMethod("Transform",System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.NonPublic)!;
        await File.WriteAllBytesAsync(legacyFile,(byte[])protect.Invoke(null,new object[]{oldJson,true})!);
        File.SetLastWriteTimeUtc(legacyFile,DateTime.UtcNow.AddMinutes(-2));
        var legacyBox=new SocialOutbox(legacyRoot);var legacyMessage=(await legacyBox.ReadAsync(owner)).Single();
        Check(legacyMessage.TimedOut(DateTimeOffset.UtcNow),"legacy attempt restarted its deadline");
        Check((await new SocialOutbox(legacyRoot).ReadAsync(owner)).Single().CreatedAt==legacyMessage.CreatedAt,"legacy read/restart changed timestamp");
        await legacyBox.FailAttemptAsync(legacyMessage,"delivery_timeout");
        Check((await legacyBox.ReadAsync(owner)).Single().Error=="delivery_timeout","legacy failure not persisted");
        foreach(var text in new[]{""," ","\u00a0", "\0",new string('x',2001)})
            await Reject(()=>{AccountService.ValidateMessage(text,"text");return Task.CompletedTask;},"invalid_message");
        AccountService.ValidateMessage("Строка 1\nстрока 2\t🙂","text");checks++;
        await Reject(()=>{AccountService.ValidateMessage("test","executable");return Task.CompletedTask;},"invalid_message");
        var calls=0;var rows=new Dictionary<Guid,SocialMessage>();var loseReply=true;var foreignReply=false;var authOwner=owner;
        var unread=2;var relation="friend";var remaining=1;var marker=Guid.NewGuid();var receiptCalls=0;
        const string exactCode="PAW-BETA-IW0-SP2-RM1-SG0-LM1-RU1-CL1-OOS1-PS0";
        string? peerConfiguration=null;
        var store=new AccountSessionStore(Path.Combine(root,"social-account"));
        using(var service=new AccountService(store,new Mock(async req=> {
            Check(req.RequestUri!.Host=="trdzsdclscuwwmxnepyt.supabase.co","foreign origin");
            var path=req.RequestUri.AbsolutePath;
            var user=new {id=authOwner,email="fixture@example.invalid"};
            if(path.EndsWith("/token"))return Ok(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user});
            if(path.EndsWith("/user"))return Ok(user);
            if(path.EndsWith("paw_profiles"))return Ok(new[]{new{id=authOwner,nickname="FixturePaw"}});
            Check(req.Headers.Authorization?.Parameter=="fixture-access","missing session");
            if(path.EndsWith("paw_social_list"))return Ok(new{status="ok",players=new[]{new{id=peer,nickname="FixtureFriend",relation,unread,channel="beta",configuration=peerConfiguration}}});
            if(path.EndsWith("paw_presence")) {
                using var body=JsonDocument.Parse(await req.Content!.ReadAsStringAsync());
                Check(body.RootElement.GetProperty("configuration").GetString()==exactCode && body.RootElement.GetProperty("channel").GetString()=="beta"
                    && body.RootElement.EnumerateObject().Count()==4,"exact presence RPC contract");
                return Ok(new{status="ok"});
            }
            if(path.EndsWith("paw_mark_messages_read")) {
                using var body=JsonDocument.Parse(await req.Content!.ReadAsStringAsync());var p=body.RootElement;
                Check(p.GetProperty("target").GetGuid()==peer && p.GetProperty("last_message").GetGuid()==marker,"read marker not the displayed incoming ID");
                receiptCalls++;return Ok(new{status="ok",unread=remaining});
            }
            if(path.EndsWith("paw_send_message")) {
                using var body=JsonDocument.Parse(await req.Content!.ReadAsStringAsync());var p=body.RootElement;
                var id=p.GetProperty("message_id").GetGuid();calls++;
                if(!rows.ContainsKey(id))rows.Add(id,new(owner,id,peer,p.GetProperty("body").GetString()!,"text",DateTimeOffset.UtcNow));
                if(loseReply){loseReply=false;throw new HttpRequestException("fixture-private-server-detail");}
                return Ok(new{status="ok",message=rows[id]});
            }
            if(path.EndsWith("paw_read_messages"))return Ok(new{status="ok",messages=foreignReply?new[]{new SocialMessage(outsider,Guid.NewGuid(),peer,"foreign","text",DateTimeOffset.UtcNow)}:rows.Values.ToArray()});
            throw new Exception("Unexpected fixture route");
        }))) {
            await service.SignInAsync("fixture@example.invalid","fixture-password");
            Check((await service.GetFriendsAsync()).Single().Id==peer,"friend response");
            Check((await service.GetFriendsAsync()).Single().Unread==2,"unread response");
            Check((await service.GetFriendsAsync()).Single().Configuration is null,"legacy config invented");
            peerConfiguration=exactCode;Check((await service.GetFriendsAsync()).Single().Configuration==exactCode,"exact friend config lost");
            peerConfiguration=exactCode.Replace("BETA","STABLE");Check((await service.GetFriendsAsync()).Single().Configuration is null,"wrong channel config trusted");
            peerConfiguration=exactCode+"\n";Check((await service.GetFriendsAsync()).Single().Configuration is null,"invalid config trusted");
            await service.PublishConfigurationPresenceAsync(true,"beta",new Dictionary<string,bool>{{"core",true}},exactCode);
            peerConfiguration=null;
            Check(await service.MarkMessagesReadAsync(peer,marker)==1,"newer unseen message lost");
            foreach(var invalid in new[]{-1,10001}) {
                unread=invalid;await Reject(()=>service.GetFriendsAsync(),"invalid_response");
                remaining=invalid;await Reject(()=>service.MarkMessagesReadAsync(peer,marker),"invalid_response");
            }
            unread=2;relation="incoming";await Reject(()=>service.GetFriendsAsync(),"invalid_response");
            unread=0;Check((await service.GetFriendsAsync()).Single().Unread==0,"request unread zero");
            relation="friend";remaining=0;
            var beforeReceipt=receiptCalls;
            await Reject(()=>service.MarkMessagesReadAsync(Guid.Empty,marker));
            await Reject(()=>service.MarkMessagesReadAsync(peer,Guid.Empty));
            Check(receiptCalls==beforeReceipt,"invalid marker reached server");
            await Reject(()=>service.SendMessageAsync(peer,message.Id,message.Body),"network");
            var retry=await service.SendMessageAsync(peer,message.Id,message.Body);
            Check(calls==2 && rows.Count==1 && retry.MessageId==message.Id,"lost response duplicate");
            Check((await service.GetMessagesAsync(peer)).Count==1,"chat response");
            foreignReply=true;await Reject(()=>service.GetMessagesAsync(peer),"invalid_response");
            // A second instance/account overwrites the saved identity. No RPC may run for it.
            var stored=store.Read()!;stored.UserId=outsider.ToString();store.Save(stored);authOwner=outsider;
            var before=calls;await Reject(()=>service.SendMessageAsync(peer,Guid.NewGuid(),"wrong owner"),"session_expired");
            Check(calls==before,"queue sent as another account");
        }
        foreach(var body in new[]{"{}","gateway limit", "{\"code\":\"over_email_send_rate_limit\"}","{\"error_code\":\"over_email_send_rate_limit\"}"}) {
            using var service=new AccountService(new AccountSessionStore(Path.Combine(root,Guid.NewGuid().ToString())),new Mock(_=>Task.FromResult(new HttpResponseMessage((HttpStatusCode)429){Content=new StringContent(body)})));
            await Reject(()=>service.RequestRecoveryAsync("fixture@example.invalid"),body.Contains("over_email")?"email_rate_limit":"rate_limit");
        }
        byte[] Bytes(byte value){var data=new byte[64];"TGCK"u8.CopyTo(data);Array.Fill(data,value,16,48);return data;}
        var original=Bytes(1);var replacement=Bytes(2);
        var descriptor=SaveTransferGuard.Describe("Тестовый сейв.RSG",replacement);
        var saveRoot=Path.Combine(root,"transfer-saves");
        foreach(var name in new[]{"../escape.RSG","C:\\evil.RSG","evil.exe","CON.RSG","CON .RSG","COM1.RSG","COM¹.RSG","a.RSG:stream",".RSG","a.RSG ","a/RSG","hidden\u202e.RSG"})
            await Reject(()=>{SaveTransferGuard.ValidateDescriptor(descriptor with{FileName=name});return Task.CompletedTask;});
        foreach(var size in new long[]{0,15,SaveTransferGuard.MaximumBytes+1})
            await Reject(()=>{SaveTransferGuard.ValidateDescriptor(descriptor with{Size=size});return Task.CompletedTask;});
        await Reject(()=>{SaveTransferGuard.ValidateBytes(descriptor,original);return Task.CompletedTask;});
        var fake=Bytes(2);fake[0]=0;
        await Reject(()=>{SaveTransferGuard.Describe("fake.RSG",fake);return Task.CompletedTask;});
        await Reject(()=>SaveTransferGuard.InstallAsync(saveRoot,descriptor,replacement,null,()=>true));
        Check(!Directory.Exists(saveRoot),"running game changed save directory");
        var first=await SaveTransferGuard.InstallAsync(saveRoot,SaveTransferGuard.Describe(descriptor.FileName,original),original,null,()=>false);
        Check(first.BackupPath is null && File.ReadAllBytes(first.Path).SequenceEqual(original),"new install");
        await Reject(()=>SaveTransferGuard.InstallAsync(saveRoot,descriptor,replacement,null,()=>false));
        Check(File.ReadAllBytes(first.Path).SequenceEqual(original),"unconfirmed overwrite");
        await Reject(()=>SaveTransferGuard.InstallAsync(saveRoot,descriptor,replacement,descriptor.Sha256,()=>false));
        var second=await SaveTransferGuard.InstallAsync(saveRoot,descriptor,replacement,Convert.ToHexString(SHA256.HashData(original)),()=>false);
        Check(File.ReadAllBytes(second.Path).SequenceEqual(replacement),"replacement failed");
        Check(second.BackupPath is not null && File.ReadAllBytes(second.BackupPath).SequenceEqual(original),"backup not exact");
        var gameChecks=0;
        await Reject(()=>SaveTransferGuard.InstallAsync(saveRoot,descriptor,replacement,descriptor.Sha256,()=>++gameChecks>1));
        Check(!Directory.EnumerateFiles(saveRoot,"*.tmp").Any(),"staged leftovers");
        Console.WriteLine($"SOCIAL + SAVE FOUNDATION PASS {checks}: mocked retry/identity, encrypted queue, restricted names/size/hash, safe overwrite backup; no live user data");
        return checks;
    }
    private static HttpResponseMessage Ok(object data)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(data),Encoding.UTF8,"application/json")};
    private sealed class Mock(Func<HttpRequestMessage,Task<HttpResponseMessage>> send):HttpMessageHandler
    {protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>
        request.RequestUri!.AbsolutePath.EndsWith("/paw_launcher_session") ? Task.FromResult(Ok(new {status="ok"})) : send(request);}
}
