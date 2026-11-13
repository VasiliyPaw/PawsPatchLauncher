using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class FriendDownloadChecks
{
    internal static void Run(string language,string output)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated fixture required");
        Directory.CreateDirectory(output);
        new SettingsStore().Save(new UserSettings{Language=language,ModNoticeSeen=true});
        var w=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[],CacheRoot=Path.Combine(ActivityStore.Root,"cache")},null)
            {Width=1440,Height=920,Left=-30000,Top=-30000,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual};
        const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        T Field<T>(string n)=>(T)typeof(MainWindow).GetField(n,flags)!.GetValue(w)!;
        void Set(string n,object? value)=>typeof(MainWindow).GetField(n,flags)!.SetValue(w,value);
        object? Call(string n,params object?[] args)=>typeof(MainWindow).GetMethod(n,flags)!.Invoke(w,args);
        T C<T>(string n)=>(T)w.FindName(n);
        int checks=0;void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Friend download: "+why);}
        var owner=Guid.NewGuid();var target=Guid.NewGuid();var calls=new List<string>();bool blocked=false;int activityReads=0,profileReads=0;
        var presence="playing"; TaskCompletionSource<bool>? profileGate=null;
        var offers=new Dictionary<Guid,SocialOffer>();var offerActions=new List<string>();
        var settings=new UserSettings{Channel="stable"};var configuration=FriendConfiguration.Create(settings);
        object Profile()=>new{id=target,nickname="nightwatch",display_name="Nightwatch",relation="friend",is_friend=false,
            presence,playing_since=DateTimeOffset.UtcNow.AddMinutes(-42),channel="stable",configuration,
            components=new{core=true,colors=true,roaming=false},activity=new{phase="match",multiplayer=true,elapsed=120,width=192,height=256},created_at=DateTimeOffset.UtcNow.AddMonths(-2)};
        HttpResponseMessage Json(object body)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(body))};
        using var service=new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root,"download-friends")),new AccountChecks.Handler(async request=>
        {
            var path=request.RequestUri!.AbsolutePath;
            if(path.EndsWith("/token"))return Json(new{access_token="fixture",refresh_token="fixture-refresh",expires_in=3600,user=new{id=owner,email="fixture@example.invalid"}});
            if(path.EndsWith("/paw_profiles"))return Json(new[]{new{id=owner,nickname="fixture"}});
            if(path.EndsWith("/paw_friend_action")){using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());calls.Add(body.RootElement.GetProperty("action").GetString()!);return Json(new{status="ok"});}
            if(path.EndsWith("/paw_social_list"))return Json(new{status="ok",players=Array.Empty<object>()});
            if(path.EndsWith("/paw_profile_card")){profileReads++;if(profileGate is not null)await profileGate.Task;return blocked?Json(new{status="profile_blocked"}):Json(new{status="ok",player=Profile()});}
            if(path.EndsWith("/paw_profile_activity")){activityReads++;return Json(new{status="ok",activity=new{phase="match",multiplayer=true,elapsed=120,width=192,height=256,players=Array.Empty<object>()},observed_at=DateTimeOffset.UtcNow});}
            if(path.EndsWith("/paw_offer_action"))
            {
                using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                var id=body.RootElement.GetProperty("offer_id").GetGuid();var action=body.RootElement.GetProperty("action").GetString()!;
                offerActions.Add(action);return Json(new{status="ok",offer=offers[id] with{State=action=="cancel"?"cancelled":"declined"}});
            }
            throw new InvalidOperationException("Unexpected mocked route: "+path);
        }));
        void Seed(params SocialPlayer[] players)
        {
            Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)players);Set("_socialListReceived",DateTimeOffset.UtcNow);
            Call("RenderSocialIdentity");Call("RenderSocialRows");Call("RenderSocialNotifications");
        }
        IEnumerable<Button> Buttons(DependencyObject root)
        {
            for(int i=0;i<VisualTreeHelper.GetChildrenCount(root);i++)
            {var child=VisualTreeHelper.GetChild(root,i);if(child is Button button)yield return button;foreach(var nested in Buttons(child))yield return nested;}
        }
        void Snap(string name,FrameworkElement element)
        {
            w.UpdateLayout();var drawing=new DrawingVisual();using(var dc=drawing.RenderOpen())
            {
                dc.DrawRectangle(new SolidColorBrush(Color.FromRgb(16,34,56)),null,new Rect(0,0,element.ActualWidth,element.ActualHeight));
                dc.DrawRectangle(new VisualBrush(element),null,new Rect(0,0,element.ActualWidth,element.ActualHeight));
            }
            var bmp=new RenderTargetBitmap((int)Math.Ceiling(element.ActualWidth),(int)Math.Ceiling(element.ActualHeight),96,96,PixelFormats.Pbgra32);bmp.Render(drawing);
            var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(bmp));using var file=File.Create(Path.Combine(output,name+"-"+language+".png"));png.Save(file);
        }
        async Task Scenario()
        {
            await service.SignInAsync("fixture@example.invalid","fixture-password",remember:false);
            Field<AccountService>("_account").Dispose();Set("_account",service);Call("RenderAccount");Call("SetActivePage","friends");
            var incoming=new SocialPlayer(target,"nightwatch","incoming",IsFriend:false,DisplayName:"Nightwatch");
            foreach(var phase in new[]{"Downloading patch","Verifying files","Installing update"})
            {
                Call("SetBusy",true,phase);Set("_transferReceived",(long?)52428800);Set("_transferTotal",(long?)104857600);
                var revision=Field<long>("_operationRevision");Seed(incoming);
                await (Task)Call("SocialFriendActionAsync",incoming,"accept")!;
                Check(calls.LastOrDefault()=="accept"&&Field<bool>("_busy")&&Field<long>("_operationRevision")==revision
                    &&Field<long?>("_transferReceived")==52428800,"friend acceptance runs without touching active "+phase);
            }
            foreach(var (relation,action) in new[]{("incoming","decline"),("outgoing","cancel"),("blocked","unblock")})
            {
                var p=incoming with{Relation=relation};Seed(p);await (Task)Call("SocialFriendActionAsync",p,action)!;
                Check(calls.Last()==action&&Field<bool>("_busy"),action+" works during installation");
            }
            var friend=incoming with{Relation="friend",IsFriend=true};Seed(friend);
            Call("ShowSocialDetails",friend);
            Check(C<Button>("SocialDetailsRemoveButton").IsEnabled&&C<Button>("SocialDetailsBlockButton").IsEnabled,"profile friendship actions stay enabled during download");
            Check(!C<Button>("SocialDetailsCopyButton").IsEnabled,"file-changing configuration action stays protected");Call("CloseSocialDetails");
            var before=calls.Count;var removing=(Task)Call("SocialFriendActionAsync",friend,"remove")!;
            Check(!removing.IsCompleted&&Field<bool>("_busy"),"friend removal still asks for confirmation during download");
            C<Button>("ConfirmationCancelButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await removing;
            Check(calls.Count==before&&Field<bool>("_busy"),"cancel preserves friendship and download");
            foreach(var action in new[]{"remove","block"})
            {
                Seed(friend);var task=(Task)Call("SocialFriendActionAsync",friend,action)!;
                C<Button>("ConfirmationDeleteButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await task;
                Check(calls.Last()==action&&Field<bool>("_busy"),"confirmed "+action+" preserves download");
            }
            Check(!await (Task<bool>)Call("ConfirmActionAsync","Files","Body","Path","Value","Apply")!,"game file confirmations remain blocked during another operation");
            ContextMenu? menu=null;Set("_socialMenuOpenOverride",new Action<ContextMenu>(m=>menu=m));Seed(friend);
            Call("OpenSocialContextAt",C<StackPanel>("FriendsRowsPanel"),friend.Id);Check(menu is not null,"context menu opens during download");Call("CloseSocialMenu");
            Set("_socialPeer",target);
            var incomingOffer=new SocialOffer(Guid.NewGuid(),target,owner,"config",configuration,null,null,null,"pending",DateTimeOffset.UtcNow,DateTimeOffset.UtcNow.AddMinutes(10),null,null);
            var outgoingOffer=incomingOffer with{Id=Guid.NewGuid(),Sender=owner,Recipient=target};offers[incomingOffer.Id]=incomingOffer;offers[outgoingOffer.Id]=outgoingOffer;
            C<StackPanel>("FriendsMessagesPanel").Children.Clear();
            var incomingCard=(Border)Call("RenderOfferCard",incomingOffer)!;var outgoingCard=(Border)Call("RenderOfferCard",outgoingOffer)!;
            C<StackPanel>("FriendsMessagesPanel").Children.Add(incomingCard);C<StackPanel>("FriendsMessagesPanel").Children.Add(outgoingCard);w.UpdateLayout();Call("RefreshOfferActions");
            var declineOffer=Buttons(incomingCard).Single(b=>Equals(b.CommandParameter,"offer-decline"));
            var acceptOffer=Buttons(incomingCard).Single(b=>Equals(b.CommandParameter,"offer-accept"));
            var cancelOffer=Buttons(outgoingCard).Single(b=>Equals(b.CommandParameter,"offer-cancel"));
            Check(declineOffer.IsEnabled&&cancelOffer.IsEnabled&&!acceptOffer.IsEnabled,"offer metadata actions remain active while file application stays blocked");
            declineOffer.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(40);
            cancelOffer.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(40);
            Check(offerActions.SequenceEqual(new[]{"decline","cancel"})&&Field<bool>("_busy"),"declining/cancelling offers sends only metadata RPCs without ending download");

            var examples=new[]{incoming with{Id=Guid.NewGuid(),Nickname="forest_guard",DisplayName="Лесной страж"},incoming,
                incoming with{Id=Guid.NewGuid(),Nickname="alexander_1372",DisplayName="Александр — любитель Kohan II"}};
            Seed(examples.Concat(new[]{incoming with{Id=Guid.NewGuid(),Nickname="silent_wind",DisplayName="Тихий ветер",Relation="outgoing"},incoming with{Id=Guid.NewGuid(),Nickname="kohan_player",DisplayName="Kohan Player",Relation="outgoing"}}).ToArray());
            Set("_communityOnline",(int?)3);Set("_communityOnlineReceived",DateTimeOffset.UtcNow);Call("RefreshCommunityOnline");
            Check(C<Border>("CommunityOnlineNewBadge").Visibility==Visibility.Visible,"directory discovery starts visible");
            Snap("online-new-feature",(FrameworkElement)C<Button>("CommunityOnlineButton").Parent);
            Set("_communityPlayersOverride",new Func<int,CancellationToken,Task<CommunityOnlinePage>>((_,_)=>Task.FromResult(new CommunityOnlinePage(0,3,examples.Select(p=>new CommunityOnlinePlayer(p.Id,p.Nickname,p.Name,null)).ToArray()))));
            C<Button>("CommunityOnlineButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Field<Window>("_onlineWindow").Close();
            Check(C<Border>("CommunityOnlineNewBadge").Visibility==Visibility.Collapsed&&new SettingsStore().Load().OnlineDirectorySeen,"first open persists discovery independently of launcher version");
            Call("ApplyLanguage");Check(C<Border>("CommunityOnlineNewBadge").Visibility==Visibility.Collapsed,"language refresh cannot reintroduce discovery badge");
            Snap("online-after-discovery",(FrameworkElement)C<Button>("CommunityOnlineButton").Parent);
            Call("OpenFriendsDialog","requests");await Task.Delay(250);Snap("requests-incoming",C<Border>("FriendsDialogCard"));
            Check(Buttons(C<StackPanel>("FriendsDialogRows")).Where(b=>Equals(b.Tag,"accept")).All(b=>b.IsEnabled),"incoming preview actions remain usable during active download");
            C<Border>("FriendsDialogCard").MaxWidth=430;w.UpdateLayout();await Task.Delay(100);Snap("requests-incoming-narrow",C<Border>("FriendsDialogCard"));
            foreach(var card in C<StackPanel>("FriendsDialogRows").Children.OfType<Border>())foreach(var button in Buttons(card))
            {var bounds=button.TransformToAncestor(card).TransformBounds(new Rect(button.RenderSize));Check(bounds.Left>=0&&bounds.Right<=card.ActualWidth+1,"request buttons fit narrow card");}
            C<Border>("FriendsDialogCard").MaxWidth=660;Call("SwitchSocialRequests","outgoing");await Task.Delay(180);Snap("requests-outgoing",C<Border>("FriendsDialogCard"));
            Seed();Call("RenderFriendsDialogRows");await Task.Delay(150);Snap("requests-empty",C<Border>("FriendsDialogCard"));Call("ResetFriendsDialog");

            Call("SetActivePage","modules");await (Task)Call("OpenPublicProfileCardAsync",target)!;
            Check(C<Border>("SocialDetailsOverlay").IsVisible&&C<StackPanel>("SocialDetailsComponents").Children.Count>0,"unrelated player opens a full profile during download");
            await Task.Delay(180);Snap("profile-before-request",C<Border>("SocialDetailsCard"));
            await (Task)Call("ShowGameActivityAsync",target)!;
            Check(activityReads==1&&C<Border>("GameActivityOverlay").IsVisible,"nonfriend details use the block-checked public activity endpoint");Call("CloseGameActivity");
            int requests=0;Set("_profileFriendRequestOverride",new Func<SocialPlayer,CancellationToken,Task>((p,_)=>{Check(p.Id==target,"request uses selected player UUID");requests++;return Task.CompletedTask;}));
            C<Button>("SocialDetailsRemoveButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(80);
            Check(requests==1&&Field<string>("_activePage")=="modules"&&C<Border>("SocialDetailsOverlay").IsVisible
                &&!C<Button>("SocialDetailsRemoveButton").IsEnabled,"one click sends request without navigation or second confirmation");
            Snap("profile-not-friend",C<Border>("SocialDetailsCard"));
            C<Button>("SocialDetailsRemoveButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));Check(requests==1,"sent request cannot be duplicated");
            Call("ShowFriendRequestResult",new FriendRequestResult(FriendRequestOutcome.AlreadySent,new[]{incoming with{Relation="outgoing"}}));
            var preserved=(SocialPlayer)Call("SocialDetailsPlayer")!;
            Check(preserved.Configuration==configuration&&preserved.Presence=="playing","sparse request polling preserves full authorized configuration and activity");
            blocked=true;await (Task)Call("RefreshPublicProfileAsync")!;
            Check(C<Border>("SocialDetailsOverlay").Visibility==Visibility.Collapsed,"new block closes previously visible profile");
            await (Task)Call("OpenPublicProfileCardAsync",target)!;
            Check(C<Border>("SocialDetailsOverlay").Visibility==Visibility.Collapsed,"cached identity cannot bypass block on reopen");
            Check(((string)Call("PublicProfileError","profile_blocked")!).Contains(language=="ru"?"заблокировал":"blocked"),"blocked profile has an explicit explanation");
            blocked=false;
            var session=(AccountSession)typeof(AccountService).GetField("_session",flags)!.GetValue(service)!;
            session.AdminLevel=1;
            var readsBeforeAdmin=profileReads;
            await (Task)Call("OpenAdminProfileAsync",target)!;
            var adminPlayer=(SocialPlayer)Call("SocialDetailsPlayer")!;
            Check(profileReads==readsBeforeAdmin+1&&adminPlayer.Configuration==configuration&&adminPlayer.Presence=="playing"
                &&C<StackPanel>("SocialDetailsComponents").Children.Count>0,"admin profile must fetch the same full endpoint as the online directory");
            Check(Field<Guid?>("_publicProfilePeer")==target&&Field<SocialPlayer?>("_adminViewedPlayer")?.Id==target,
                "admin profile lost public refresh or moderation lifecycle");
            var previousActivityReads=activityReads;
            await (Task)Call("ShowGameActivityAsync",target)!;
            Check(activityReads==previousActivityReads+1&&C<Border>("GameActivityOverlay").IsVisible,
                "admin profile activity used a friend-only endpoint");Call("CloseGameActivity");
            await Task.Delay(180);Snap("profile-from-admin",C<Border>("SocialDetailsCard"));
            presence="online";await (Task)Call("RefreshPublicProfileAsync")!;
            Check(((SocialPlayer)Call("SocialDetailsPlayer")!).Presence=="online","admin card did not refresh presence");
            blocked=true;await (Task)Call("RefreshPublicProfileAsync")!;
            Check(C<Border>("SocialDetailsOverlay").Visibility==Visibility.Collapsed,"admin profile bypassed a new block");
            await (Task)Call("OpenAdminProfileAsync",target)!;
            Check(C<Border>("SocialDetailsOverlay").Visibility==Visibility.Collapsed,"admin profile reopened through a block");
            blocked=false;session.AdminLevel=0;readsBeforeAdmin=profileReads;
            await (Task)Call("OpenAdminProfileAsync",target)!;
            Check(profileReads==readsBeforeAdmin,"nonadmin started an admin profile request");
            session.AdminLevel=1;profileGate=new(TaskCreationOptions.RunContinuationsAsynchronously);
            var pendingProfile=(Task)Call("OpenAdminProfileAsync",target)!;
            for(var i=0;i<100&&profileReads==readsBeforeAdmin;i++)await Task.Delay(5);
            Check(profileReads==readsBeforeAdmin+1&&!pendingProfile.IsCompleted,"admin race fixture did not reach the profile response");
            session.AdminLevel=0;profileGate.SetResult(true);await pendingProfile;profileGate=null;
            Check(C<Border>("SocialDetailsOverlay").Visibility==Visibility.Collapsed&&Field<SocialPlayer?>("_adminViewedPlayer") is null,
                "revoked admin request opened a stale privileged card");
            Call("SetBusy",false,null);
            Console.WriteLine($"FRIEND DOWNLOAD / PUBLIC PROFILE PASS {checks} {language}; mocked accounts and mutations only");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();
            var deadline=new DispatcherTimer{Interval=TimeSpan.FromSeconds(50)};deadline.Tick+=(_,_)=>frame.Continue=false;
            _=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false));deadline.Start();Dispatcher.PushFrame(frame);deadline.Stop();
            if(!task.IsCompleted)throw new TimeoutException("Friend download fixture");task.GetAwaiter().GetResult();
        }
        finally{Set("_busy",false);w.Close();}
    }
}
