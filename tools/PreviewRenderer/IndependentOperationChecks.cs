using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

// Real controls/handlers with mocked transport. Never show this launcher window.
internal static class IndependentOperationChecks
{
    internal static void Run(string language,string output)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated profile required");
        new SettingsStore().Save(new UserSettings{ModNoticeSeen=true,Language=language});
        var w=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null);
        const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name)=>(T)w.FindName(name);
        var count=0;void Check(bool ok,string message){if(!ok)throw new Exception("Independent actions: "+message);count++;}
        var owner=Guid.NewGuid();var peer=Guid.NewGuid();var adminCalls=0;var communityCalls=0;var downloadCalls=0;var browserCalls=0;
        var before=new UserSettings{Channel="stable"};var after=new UserSettings{Channel="stable",IgnoreZeroMorale=!before.IgnoreZeroMorale};
        var friend=new SocialPlayer(peer,"friend","friend",Configuration:FriendConfiguration.Create(after),Channel:"stable",DisplayName:"Friend");
        var saveBytes=new byte[16];Encoding.ASCII.GetBytes("TGCK").CopyTo(saveBytes,0);saveBytes[15]=7;
        var descriptor=SaveTransferGuard.Describe("fixture.rsg",saveBytes);
        var save=new SocialOffer(Guid.NewGuid(),peer,owner,"save",null,descriptor.FileName,descriptor.Size,descriptor.Sha256,"pending",DateTimeOffset.UtcNow,DateTimeOffset.UtcNow.AddMinutes(10),null,null);
        var config=save with {Id=Guid.NewGuid(),Kind="config",Configuration=friend.Configuration,FileName=null,FileSize=null,Sha256=null};
        var saves=Path.Combine(ActivityStore.Root,"independent-saves");Directory.CreateDirectory(saves);
        Set("_savesDirectory",(Func<string>)(()=>saves));
        var path=Path.Combine(saves,descriptor.FileName);var old=(byte[])saveBytes.Clone();old[15]=3;
        byte[] downloading=saveBytes;TaskCompletionSource<bool>? downloadGate=null;Guid? attempt=null;
        HttpResponseMessage Json(object data)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(data))};
        using var service=new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root,"independent-account")),new Handler(async request=>
        {
            var route=request.RequestUri!.AbsolutePath;
            if(route.EndsWith("/token"))return Json(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user=new{id=owner,email="fixture@example.invalid"}});
            if(route.EndsWith("/user"))return Json(new{id=owner,email="fixture@example.invalid"});
            if(route.EndsWith("/paw_launcher_session"))return Json(new{status="ok"});
            if(route.EndsWith("/paw_profiles"))return Json(new[]{new{id=owner,nickname="fixture"}});
            if(route.EndsWith("/paw_community_remove")){communityCalls++;return Json(new{status="ok"});}
            if(route.EndsWith("/paw_admin_action")){adminCalls++;return Json(new{status="ok"});}
            if(route.EndsWith("/paw_social_list"))return Json(new{status="ok",players=Array.Empty<object>()});
            if(route.EndsWith("/paw_community_read"))return Json(new{status="ok",messages=Array.Empty<object>(),revision=0,more=false,trimmed=false});
            if(route.EndsWith("/paw_offer_action"))
            {
                using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                var action=body.RootElement.GetProperty("action").GetString();
                if(action=="begin")attempt=body.RootElement.GetProperty("attempt").GetGuid();
                return Json(new{status="ok",offer=save with{State="applying",Attempt=attempt}});
            }
            if(route.EndsWith("/social-transfers"))
            {
                if(request.RequestUri.Query.Contains("action=download"))
                {
                    downloadCalls++;if(downloadGate is not null)await downloadGate.Task;
                    return new(HttpStatusCode.OK){Content=new ByteArrayContent(downloading){Headers={ContentType=new("application/octet-stream")}}};
                }
                return Json(new{status="ok"});
            }
            throw new InvalidOperationException("Unexpected mock route: "+route);
        }));
        Task Finish(bool accepted)=>(Task)Call("CompleteConfirmationAsync",accepted)!;
        void Seed()
        {
            Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)new[]{friend});Set("_socialListReceived",DateTimeOffset.UtcNow);Set("_socialPeer",peer);
            Call("RenderSocialIdentity");
        }
        void Preserved(object transfer,long revision,string label)
        {
            Check(ReferenceEquals(Field<object>("_activeTransfer"),transfer)&&Field<long>("_operationRevision")==revision&&Field<long?>("_transferReceived")==97,label+" modified the active transfer");
        }
        async Task Scenario()
        {
            await service.SignInAsync("fixture@example.invalid","fixture-password",remember:false);
            Field<AccountService>("_account").Dispose();Set("_account",service);Call("RenderAccount");
            var session=(AccountSession)typeof(AccountService).GetField("_session",flags)!.GetValue(service)!;
            session.AdminLevel=2;Call("RenderAccount");Seed();Call("BuildAdminLayout");
            var target=new AdminPlayer(peer,"friend","Friend",DateTimeOffset.UtcNow.AddDays(-2),0,false,null,null,"",null,false,false);
            var roleActions=0;
            Set("_adminActionOverride",(Func<string,Guid,string,DateTimeOffset?,int?,Task>)((action,id,reason,until,level)=>{Check(action=="role"&&id==peer&&level==1,"wrong role mutation");roleActions++;return Task.CompletedTask;}));
            Set("_openHelpLink",(Func<string,Task>)(_=>{browserCalls++;return Task.CompletedTask;}));
            foreach(var phase in new[]{"download","install","verify","feed","reborn"})
            {
                Set("_busy",false);Set("_checkingFeed",false);Set("_rebornBusy",false);
                if(phase=="feed"){Set("_checkingFeed",true);Set("_backgroundFeedCheck",false);}
                else if(phase=="reborn")Set("_rebornBusy",true);
                else Call("SetBusy",true,"Fixture "+phase);
                var transfer=new object();Set("_activeTransfer",transfer);Set("_transferReceived",(long?)97);Set("_transferTotal",(long?)100);
                var revision=Field<long>("_operationRevision");Seed();
                Check(C<Button>("FriendsComposerMoreButton").IsEnabled&&C<Button>("FriendsBroadcastButton").IsEnabled&&C<Button>("SendSaveBroadcastButton").IsEnabled,"outgoing actions blocked during "+phase);
                Set("_socialBusy",true);
                var role=(Task)Call("ModerateAsync",target,"role")!;
                Check(!role.IsCompleted&&C<Border>("ConfirmationOverlay").Visibility==Visibility.Visible,"role confirmation blocked during "+phase);
                var choices=C<StackPanel>("ConfirmationChangesPanel").Children.OfType<StackPanel>().SelectMany(p=>p.Children.OfType<Button>()).ToArray();
                choices.Single(b=>Equals(b.Tag,1)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                await Finish(true);await role;Set("_socialBusy",false);Preserved(transfer,revision,"role");
                var removal=(Task)Call("RemoveCommunityAsync",new CommunityMessage(1,Guid.NewGuid(),peer,"friend","Friend","fixture",DateTimeOffset.UtcNow,false,0,null))!;
                Check(!removal.IsCompleted,"community removal bypassed/blocked confirmation");await Finish(true);await removal;Preserved(transfer,revision,"community deletion");
                var url=(string)typeof(MainWindow).GetField("PrivacyPolicyUrl",BindingFlags.Static|BindingFlags.NonPublic)!.GetValue(null)!;
                var browser=(Task)Call("OpenConfirmedLinkAsync",url)!;Check(!browser.IsCompleted,"browser confirmation blocked");await Finish(true);await browser;Preserved(transfer,revision,"help link");
                var proposal=(Task<bool>)Call("ConfirmConfigurationOfferAsync",friend,FriendConfiguration.Create(before))!;
                Check(!proposal.IsCompleted&&C<Button>("ConfirmationDeleteButton").IsEnabled,"configuration sending blocked");await Finish(false);Check(!await proposal,"cancelled offer accepted");Preserved(transfer,revision,"proposal cancellation");
                Check((bool)Call("CanAcceptOffer",save)!,"save receipt blocked during "+phase);
                if(phase!="reborn")Check(!(bool)Call("CanAcceptOffer",config)!,"config acceptance bypasses file/version guards");
                Set("_activeTransfer",null);
            }
            Check(roleActions==5&&communityCalls==5&&browserCalls==5,"independent action did not reach mocked mutation");
            Set("_busy",true);Set("_checkingFeed",false);Set("_rebornBusy",false);
            var active=new object();Set("_activeTransfer",active);Set("_transferReceived",(long?)97);Set("_transferTotal",(long?)100);var stamp=Field<long>("_operationRevision");
            var denied=(Task<bool>)Call("ConfirmActionAsync","file","file","file","file","file")!;Check(denied.IsCompleted&&!await denied,"file mutation confirmation allowed during installation");
            Set("_adminBusy",true);await (Task)Call("ModerateAsync",target,"role")!;Check(Field<TaskCompletionSource<bool>?>("_confirmation") is null,"duplicate admin mutation opened");Set("_adminBusy",false);
            var stale=(Task)Call("ModerateAsync",target,"role")!;var prior=roleActions;
            C<StackPanel>("ConfirmationChangesPanel").Children.OfType<StackPanel>().SelectMany(p=>p.Children.OfType<Button>()).Single(b=>Equals(b.Tag,1)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            session.AdminLevel=0;
            await Finish(true);await stale;Check(prior==roleActions,"revoked admin sent mutation");session.AdminLevel=2;
            Set("_adminSection","bans");Set("_adminData",new AdminPage([],new[]{new AdminBan(Guid.NewGuid(),"blocked@example.invalid",DateTimeOffset.UtcNow,null,"fixture")},false,DateTimeOffset.UtcNow));Call("RenderAdminRows");
            var unban=Field<StackPanel>("_adminRows").Children.OfType<Border>().Select(b=>b.Child).OfType<StackPanel>().SelectMany(p=>p.Children.OfType<Button>()).Single();
            unban.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));Check(Field<TaskCompletionSource<bool>?>("_confirmation") is not null,"unban confirmation blocked");await Finish(true);
            for(var i=0;i<100&&(adminCalls==0||Field<bool>("_adminBusy"));i++)await Task.Delay(5);Check(adminCalls==1&&!Field<bool>("_adminBusy"),"unban did not finish API action");
            Seed();await File.WriteAllBytesAsync(path,old);
            var cancel=(Task)Call("AcceptSaveOfferAsync",save)!;
            for(var i=0;i<100&&Field<TaskCompletionSource<bool>?>("_confirmation") is null;i++)await Task.Delay(5);
            Check(!cancel.IsCompleted&&Field<bool>("_saveReceiving"),"save replacement did not open independent confirmation");await Finish(false);await cancel;
            Check(downloadCalls==0&&(await File.ReadAllBytesAsync(path)).SequenceEqual(old)&&!Field<bool>("_saveReceiving"),"cancelled replacement changed save or kept lock");Preserved(active,stamp,"save cancellation");
            downloadGate=new(TaskCreationOptions.RunContinuationsAsynchronously);
            var receive=(Task)Call("AcceptSaveOfferAsync",save)!;
            for(var i=0;i<100&&Field<TaskCompletionSource<bool>?>("_confirmation") is null;i++)await Task.Delay(5);
            await Finish(true);
            for(var i=0;i<100&&downloadCalls==0;i++)await Task.Delay(5);
            Check(downloadCalls==1&&!receive.IsCompleted&&Field<bool>("_busy")&&Field<bool>("_saveReceiving"),"save did not download independently");
            Check(!(bool)Call("CanAcceptOffer",save)!,"duplicate receiving permitted");
            await (Task)Call("AcceptSaveOfferAsync",save)!;Check(downloadCalls==1,"duplicate receive reached transport");Preserved(active,stamp,"save transfer");
            try{await (Task<OfferReceipt>)Call("BeginOfferApplicationAsync",config)!;throw new Exception("Overlapping offer application accepted");}
            catch(AccountException e){Check(e.Code=="account_busy","wrong overlap rejection");}
            var restarts=0;Set("_pendingLauncherUpdate",new LauncherRelease{Version="99.0.0",Size=1,Sha256=new('A',64),Urls=["https://fixture.invalid/launcher.exe"]});
            Set("_restartLauncher",(Func<Task>)(()=>{restarts++;return Task.CompletedTask;}));Set("_finishLauncherRestart",(Action)(()=>{}));
            Set("_busy",false);
            Check(!await (Task<bool>)Call("InstallPendingLauncherUpdateAsync",false)!&&restarts==0,"save receipt did not defer self-update independently of game busy state");
            Set("_busy",true);Set("_pendingLauncherUpdate",null);Preserved(active,stamp,"deferred self-update");
            downloadGate.SetResult(true);await receive;downloadGate=null;
            Check((await File.ReadAllBytesAsync(path)).SequenceEqual(saveBytes)&&!Field<bool>("_saveReceiving")&&Field<OfferReceipt?>("_offerApplying") is null,"save bytes/receipt completion");
            Check(Field<bool>("_busy"),"save completion unlocked installation");Preserved(active,stamp,"save completion");
            Set("_friendSettingsReadOverride",(Func<Task<IReadOnlyList<SocialPlayer>>>)(()=>Task.FromResult<IReadOnlyList<SocialPlayer>>(new[]{friend})));
            await (Task)Call("OpenBroadcastFlowAsync",false)!;
            Check(C<Border>("BroadcastOverlay").Visibility==Visibility.Visible,"broadcast cannot open during installation");
            Set("_broadcastBytes",saveBytes);Set("_broadcastSave",descriptor);Call("RefreshBroadcastKind");
            var entry=Field<System.Collections.IEnumerable>("_broadcastEntries").Cast<object>().Single();
            ((CheckBox)entry.GetType().GetProperty("Select")!.GetValue(entry)!).IsChecked=true;
            var sendGate=new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);var sent=0;
            Set("_broadcastSendOverride",(Func<Guid,Guid,string?,SaveTransferDescriptor?,byte[]?,CancellationToken,Task>)(async(from,to,code,file,bytes,ct)=>
            {Check(from==owner&&to==peer&&code is null&&file==descriptor&&bytes!.SequenceEqual(saveBytes),"wrong broadcast snapshot");sent++;await sendGate.Task;}));
            var broadcast=(Task)Call("SendBroadcastAsync")!;
            for(var i=0;i<100&&sent==0;i++)await Task.Delay(5);
            Check(sent==1&&!broadcast.IsCompleted&&Field<bool>("_offerSending")&&Field<bool>("_busy"),"outgoing save does not run independently");
            Set("_pendingLauncherUpdate",new LauncherRelease{Version="99.0.0",Size=1,Sha256=new('A',64),Urls=["https://fixture.invalid/launcher.exe"]});Set("_busy",false);
            Check(!await (Task<bool>)Call("InstallPendingLauncherUpdateAsync",false)!&&restarts==0,"outgoing transfer did not defer self-update");Set("_busy",true);Set("_pendingLauncherUpdate",null);
            Preserved(active,stamp,"broadcast send");sendGate.SetResult(true);await broadcast;
            Check(!Field<bool>("_offerSending")&&Field<bool>("_busy"),"broadcast completion unlocked installation");await (Task)Call("CloseBroadcastAsync")!;
            downloading=(byte[])saveBytes.Clone();downloading[15]^=1;
            var invalid=(Task)Call("AcceptSaveOfferAsync",save)!;
            for(var i=0;i<100&&Field<TaskCompletionSource<bool>?>("_confirmation") is null;i++)await Task.Delay(5);
            await Finish(true);await invalid;
            Check((await File.ReadAllBytesAsync(path)).SequenceEqual(saveBytes)&&Field<bool>("_busy")&&!Field<bool>("_saveReceiving"),"invalid save overwrote data/unlocked installation");Preserved(active,stamp,"failed save");
            Check(!w.IsLoaded&&!w.IsVisible,"fixture showed a launcher window");
            var report=new{passed=true,checks=count,language,headless=true,roleActions,communityCalls,browserCalls,downloadCalls};
            Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"independent-actions-"+language+".json"),JsonSerializer.Serialize(report));
            Console.WriteLine($"INDEPENDENT ACTIONS PASS {count} {language}; real hidden controls, mocked transport, isolated save files; no launcher/game window shown");
        }
        try
        {
            var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();
            var deadline=new DispatcherTimer{Interval=TimeSpan.FromSeconds(45)};deadline.Tick+=(_,_)=>frame.Continue=false;
            _=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false));deadline.Start();Dispatcher.PushFrame(frame);deadline.Stop();
            if(!task.IsCompleted)throw new TimeoutException("Independent action fixture");task.GetAwaiter().GetResult();
        }
        finally{Set("_busy",false);Set("_saveReceiving",false);Set("_rebornBusy",false);Set("_checkingFeed",false);Set("_activeTransfer",null);w.Close();}
    }
    private sealed class Handler(Func<HttpRequestMessage,Task<HttpResponseMessage>> respond):HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>respond(request);
    }
}
