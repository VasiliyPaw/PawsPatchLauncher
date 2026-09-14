using System.IO;
using System.Net;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class GameParticipantChecks
{
    internal static void Run(string language,string output)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated profile required");
        Directory.CreateDirectory(output);new SettingsStore().Save(new UserSettings{Language=language,ModNoticeSeen=true});
        var w=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null){Left=-32000,Top=-32000,Width=1050,Height=680,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual};
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        object? Call(string name,params object?[] values)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,values);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name)=>(T)w.FindName(name);
        var checks=0;void Check(bool ok,string why){if(!ok)throw new Exception("Game participants UI: "+why);checks++;}
        var owner=Guid.NewGuid();var host=Guid.NewGuid();var guest=Guid.NewGuid();var revision=DateTimeOffset.UtcNow;
        var hostProfile=new GameParticipantProfile(host,"host","Друг / Friend");
        var guestProfile=new GameParticipantProfile(guest,"guest","Участник / Participant",revision);
        var a=new GameActivity("match",true,1850,192,256,Players:[new("host","Host",false,hostProfile,1,"#F5BD55"),new("guest","Game nickname",false,guestProfile,2,"#9A68D4"),new("bot","Computer",true,Team:2,Color:"#478BDC")]);
        var friend=new SocialPlayer(host,"host","friend",Presence:"playing",DisplayName:hostProfile.DisplayName,Activity:a.Summary());
        var participant=new SocialPlayer(guest,"guest","friend",Presence:"playing",DisplayName:guestProfile.DisplayName,AvatarRevision:revision,IsFriend:false,Activity:a.Summary());
        var avatarCalls=0;var profileCalls=0;var requestCalls=0;
        var drawing=new DrawingVisual();using(var dc=drawing.RenderOpen()){dc.DrawRectangle(Brushes.MediumPurple,null,new Rect(0,0,256,256));dc.DrawEllipse(Brushes.Gold,null,new Point(128,128),75,75);}
        var bmp=new RenderTargetBitmap(256,256,96,96,PixelFormats.Pbgra32);bmp.Render(drawing);
        var encoder=new JpegBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bmp));using var encoded=new MemoryStream();encoder.Save(encoded);var jpeg=encoded.ToArray();
        System.Net.Http.HttpResponseMessage Json(object value)=>new(HttpStatusCode.OK){Content=new System.Net.Http.StringContent(JsonSerializer.Serialize(value))};
        var handler=new AccountChecks.Handler(r=>Task.FromResult(r.RequestUri!.AbsolutePath switch
        {
            var path when path.EndsWith("/token")=>Json(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user=new{id=owner,email="fixture@example.invalid"}}),
            var path when path.EndsWith("/paw_profiles")=>Json(new[]{new{id=owner,nickname="fixture"}}),
            _=>throw new InvalidOperationException("Unexpected network request in participant fixture")
        }));
        using var service=new AccountService(new AccountSessionStore(System.IO.Path.Combine(ActivityStore.Root,"participants-"+owner)),handler);
        Task Open()=> (Task)Call("ShowGameActivityAsync",host)!;
        Grid Avatar()=> (Grid)C<ContentControl>("SocialDetailsAvatar").Content;
        Button RosterButton(Guid id)=>C<StackPanel>("GameActivityBody").Children.OfType<StackPanel>().SelectMany(g=>g.Children.OfType<Border>()).Select(b=>b.Child).OfType<Button>().Single(b=>Equals(b.Tag,id));
        void Capture(string name)
        {
            w.UpdateLayout();var view=(FrameworkElement)w.Content;var b=new RenderTargetBitmap((int)view.ActualWidth,(int)view.ActualHeight,96,96,PixelFormats.Pbgra32);b.Render(view);
            var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(b));using var file=File.Create(System.IO.Path.Combine(output,name+"-"+language+".png"));png.Save(file);
        }
        async Task Scenario()
        {
            await service.SignInAsync("fixture@example.invalid","fixture-password",remember:false);Field<AccountService>("_account").Dispose();Set("_account",service);Call("RenderAccount");
            Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)new[]{friend});Set("_socialListReceived",DateTimeOffset.UtcNow);Call("SetActivePage","friends");
            Set("_gameActivityReadOverride",(Func<Guid,CancellationToken,Task<GameActivityDetails?>>)((_,_)=>Task.FromResult<GameActivityDetails?>(new(a,DateTimeOffset.UtcNow))));
            Set("_gameAvatarReadOverride",(Func<Guid,CancellationToken,Task<byte[]?>>)((_,_)=>{avatarCalls++;return Task.FromResult<byte[]?>(jpeg);}));
            Set("_gameProfileReadOverride",(Func<Guid,CancellationToken,Task<SocialPlayer>>)((_,_)=>{profileCalls++;return Task.FromResult(participant);}));
            Call("ShowSocialDetails",friend);await Task.Delay(230);
            var generation=Field<int>("_socialDetailsGeneration");
            Avatar().RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,Environment.TickCount,MouseButton.Left){RoutedEvent=Mouse.MouseUpEvent});
            Check(Field<int>("_socialDetailsGeneration")==generation&&Avatar().Cursor!=Cursors.Hand,"profile avatar reopens current profile");
            Call("ShowSocialDetails",friend);Check(Field<int>("_socialDetailsGeneration")==generation,"same profile repeat restarts animation");
            await Open();await Task.Delay(250);
            var guestButton=RosterButton(guest);
            var marker=(Grid)((Grid)guestButton.Content).Children[0];
            Check(((Grid)((ContentControl)marker.Children[0]).Content).Children[0] is Ellipse{Fill:ImageBrush},"recognized nonfriend does not show downloaded photo");
            Check(avatarCalls==1,"photo fetched more than once");
            Check(((SolidColorBrush)((Border)marker.Children[1]).Background).Color==(Color)ColorConverter.ConvertFromString("#9A68D4"),"photo lost player color");
            Capture("participants");
            await (Task)Call("RefreshGameActivityAsync")!;Check(avatarCalls==1&&ReferenceEquals(guestButton,RosterButton(guest)),"unchanged refresh reloads photo or rebuilds row");
            guestButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(260);
            Check(profileCalls==1&&Field<Guid?>("_socialDetailsPeer")==guest&&C<Border>("GameActivityOverlay").Visibility==Visibility.Collapsed,"participant card does not open matching profile");
            Check(Avatar().Children[0] is Ellipse{Fill:ImageBrush},"opened profile loses avatar");
            Check(C<Button>("SocialDetailsRemoveButton").IsEnabled&&Equals(C<Button>("SocialDetailsRemoveButton").Tag,"request"),"new participant lacks add friend action");
            Check(C<Button>("SocialDetailsCopyButton").Visibility==Visibility.Collapsed,"untrusted nonfriend configuration became copyable");
            Call("PruneSocialProfiles");Check(Field<Guid?>("_socialDetailsPeer")==guest,"normal friend refresh closes participant profile");
            Capture("participant-profile");
            var requestGate=new TaskCompletionSource();
            Set("_profileFriendRequestOverride",(Func<SocialPlayer,CancellationToken,Task>)((p,_)=>{Check(p.Id==guest,"request targeted different player");requestCalls++;return requestGate.Task;}));
            var requesting=(Task)Call("RequestProfileFriendAsync",participant)!;await (Task)Call("RequestProfileFriendAsync",participant)!;
            Check(requestCalls==1,"double click sent duplicate requests");requestGate.SetResult();await requesting;
            Check(!C<Button>("SocialDetailsRemoveButton").IsEnabled&&C<Button>("SocialDetailsRemoveButton").Content.ToString()==(language=="ru"?"Заявка отправлена":"Request sent"),"acknowledged request leaves add enabled");
            Call("RenderSocialDetails",participant with{Relation="incoming"});Check(Equals(C<Button>("SocialDetailsRemoveButton").Tag,"accept"),"incoming request not actionable");
            Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)new[]{friend});Call("ShowSocialDetails",friend);await Open();
            var profileGate=new TaskCompletionSource<SocialPlayer>();
            Set("_gameProfileReadOverride",(Func<Guid,CancellationToken,Task<SocialPlayer>>)((_,_)=>profileGate.Task));
            var opening=(Task)Call("OpenGameParticipantProfileAsync",guestProfile)!;Call("CloseGameActivity");profileGate.SetResult(participant);await opening;
            Check(Field<Guid?>("_socialDetailsPeer")==host,"late profile response replaces closed window");
            await Open();Call("CloseGameActivity");Check(avatarCalls==1,"reopen redownloads unchanged photo");
            Field<System.Collections.IDictionary>("_gameParticipantAvatars").Clear();
            var avatarGate=new TaskCompletionSource<byte[]?>();Set("_gameAvatarReadOverride",(Func<Guid,CancellationToken,Task<byte[]?>>)((_,_)=>avatarGate.Task));
            var loading=Open();Call("CloseSocialDetails");avatarGate.SetResult(jpeg);await loading;
            Check(!Field<System.Collections.IDictionary>("_gameParticipantAvatars").Contains(guest)&&C<Border>("SocialDetailsOverlay").Visibility==Visibility.Collapsed,"late avatar restores closed profile/cache");
            Console.WriteLine($"GAME PARTICIPANTS UI PASS {checks} {language}");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(30)};
            timer.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start();try{Dispatcher.PushFrame(frame);}finally{timer.Stop();}if(!task.IsCompleted)throw new TimeoutException();task.GetAwaiter().GetResult();
        }
        finally{Set("_busy",false);w.Close();}
    }
}
