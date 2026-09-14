using System.IO;
using System.Net;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class AvatarPreviewChecks
{
    internal static void Run(string language,string output,bool interactive=false)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated profile required");
        Directory.CreateDirectory(output);new SettingsStore().Save(new UserSettings{Language=language,ModNoticeSeen=true});
        var w=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null)
        {Left=-32000,Top=-32000,Width=1050,Height=680,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual};
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        object? Call(string name,params object?[] values)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,values);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name)=>(T)w.FindName(name);
        var checks=0;void Check(bool ok,string why){if(!ok)throw new Exception("Avatar preview UI: "+why);checks++;}
        var owner=Guid.NewGuid();var revision=DateTimeOffset.UtcNow;
        var friend=new SocialPlayer(Guid.NewGuid(),"player","friend",DisplayName:language=="ru"?"Игрок":"Player",AvatarRevision:revision);
        var missing=new SocialPlayer(Guid.NewGuid(),"no_avatar","friend",DisplayName:"No avatar");
        var guest=new SocialPlayer(Guid.NewGuid(),"participant","friend",DisplayName:"Participant",AvatarRevision:revision,IsFriend:false);
        var drawing=new DrawingVisual();
        using(var dc=drawing.RenderOpen())
        {
            dc.DrawRectangle(new LinearGradientBrush(Color.FromRgb(52,82,105),Color.FromRgb(23,45,61),90),null,new Rect(0,0,256,256));
            dc.DrawEllipse(new SolidColorBrush(Color.FromRgb(70,100,118)),null,new Point(128,128),96,96);
            var fox=new FormattedText("🦊",System.Globalization.CultureInfo.InvariantCulture,FlowDirection.LeftToRight,new Typeface("Segoe UI Emoji"),150,Brushes.DarkOrange,1);
            dc.DrawText(fox,new Point((256-fox.Width)/2,(256-fox.Height)/2));
        }
        var bitmap=new RenderTargetBitmap(256,256,96,96,PixelFormats.Pbgra32);bitmap.Render(drawing);
        var encoder=new JpegBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var encoded=new MemoryStream();encoder.Save(encoded);var jpeg=encoded.ToArray();
        var photo=new ImageBrush(AccountAvatarImage.Decode(jpeg,normalized:true)){Stretch=Stretch.UniformToFill};photo.Freeze();
        var avatarCalls=0;
        System.Net.Http.HttpResponseMessage Json(object value)=>new(HttpStatusCode.OK){Content=new System.Net.Http.StringContent(JsonSerializer.Serialize(value))};
        var handler=new AccountChecks.Handler(r=>Task.FromResult(r.RequestUri!.AbsolutePath switch
        {
            var path when path.EndsWith("/token")=>Json(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user=new{id=owner,email="fixture@example.invalid"}}),
            var path when path.EndsWith("/paw_profiles")=>Json(new[]{new{id=owner,nickname="fixture"}}),
            _=>throw new InvalidOperationException("Unexpected network request in avatar fixture")
        }));
        using var service=new AccountService(new AccountSessionStore(System.IO.Path.Combine(ActivityStore.Root,"avatar-preview-"+owner)),handler);
        void Players(params SocialPlayer[] players)=>Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)players);
        Dictionary<Guid,(DateTimeOffset? revision,ImageBrush? image)> Avatars(string field)=>Field<Dictionary<Guid,(DateTimeOffset?,ImageBrush?)>>(field);
        void Open()=>C<Button>("SocialDetailsAvatarButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Task Dismiss()=>(Task)Call("DismissAvatarPreviewAsync")!;
        bool Visible(string name)=>C<FrameworkElement>(name).Visibility==Visibility.Visible;
        bool Focused(UIElement element)=>ReferenceEquals(Keyboard.FocusedElement,element)||ReferenceEquals(FocusManager.GetFocusedElement(w),element);
        MouseButtonEventArgs Press(UIElement target)
        {
            var e=new MouseButtonEventArgs(Mouse.PrimaryDevice,Environment.TickCount,MouseButton.Left){RoutedEvent=Mouse.PreviewMouseDownEvent};target.RaiseEvent(e);return e;
        }
        KeyEventArgs KeyPress(UIElement target,Key key)
        {
            var e=new KeyEventArgs(Keyboard.PrimaryDevice,PresentationSource.FromVisual(w),Environment.TickCount,key){RoutedEvent=Keyboard.PreviewKeyDownEvent};target.RaiseEvent(e);return e;
        }
        void Capture(string name)
        {
            w.UpdateLayout();var view=(FrameworkElement)w.Content;
            var image=new RenderTargetBitmap((int)view.ActualWidth,(int)view.ActualHeight,96,96,PixelFormats.Pbgra32);image.Render(view);
            var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(image));using var file=File.Create(System.IO.Path.Combine(output,name+"-"+language+".png"));png.Save(file);
        }
        async Task Scenario()
        {
            await service.SignInAsync("fixture@example.invalid","fixture-password",remember:false);
            Field<AccountService>("_account").Dispose();Set("_account",service);Call("RenderAccount");
            Set("_gameAvatarReadOverride",(Func<Guid,CancellationToken,Task<byte[]?>>)((_,_)=>{avatarCalls++;return Task.FromResult<byte[]?>(jpeg);}));
            Players(friend,missing);Set("_socialListReceived",DateTimeOffset.UtcNow);Call("SetActivePage","friends");
            Avatars("_socialAvatars")[friend.Id]=(revision,photo);
            Call("ShowSocialDetails",friend);await Task.Delay(260);
            if(interactive)
            {
                // Explicit local fixture for Computer Use; never uses a real
                // account, real friend, or the user's running launcher window.
                w.Left=180;w.Top=100;w.ShowInTaskbar=true;w.ShowActivated=true;
                w.Title="Paw's Launcher — avatar preview test";w.Activate();
                var closed=new TaskCompletionSource();w.Closed+=(_,_)=>closed.TrySetResult();
                Console.WriteLine("AVATAR DEMO READY: local synthetic profile; close this test window when finished.");
                await closed.Task;return;
            }
            var profileGeneration=Field<int>("_socialDetailsGeneration");
            var small=C<ContentControl>("SocialDetailsAvatar").Content;
            var components=C<StackPanel>("SocialDetailsComponents");var componentRows=components.Children.Cast<object>().ToArray();
            Check(C<Button>("SocialDetailsAvatarButton").IsEnabled&&!Visible("AvatarPreviewOverlay"),"cached profile does not offer preview");
            Check(AutomationProperties.GetName(C<Button>("SocialDetailsAvatarButton"))==(language=="ru"?"Посмотреть аватарку игрока":"View player avatar"),"trigger lacks localized accessible name");
            Open();var generation=Field<int>("_avatarPreviewGeneration");Open();
            Check(generation==Field<int>("_avatarPreviewGeneration")&&profileGeneration==Field<int>("_socialDetailsGeneration"),"repeat click restarts viewer or profile");
            Check(Visible("AvatarPreviewOverlay")&&Visible("SocialDetailsOverlay")&&avatarCalls==0,"cached preview fetches or closes profile");
            Check(ReferenceEquals(C<Rectangle>("AvatarPreviewPhoto").Fill,photo),"preview does not reuse decoded cached photo");
            Check(ReferenceEquals(small,C<ContentControl>("SocialDetailsAvatar").Content)&&componentRows.SequenceEqual(components.Children.Cast<object>()),"preview rebuilds underlying profile");
            Check(!SystemParameters.ClientAreaAnimation||C<Border>("AvatarPreviewCard").RenderTransform is TranslateTransform{HasAnimatedProperties:true},"missing launcher entrance motion");
            Check(Focused(C<Button>("AvatarPreviewClose")),"opening did not focus close button");
            await Task.Delay(260);w.UpdateLayout();
            Check(C<Border>("AvatarPreviewCard").ActualWidth==298&&C<Rectangle>("AvatarPreviewPhoto").ActualWidth==256&&C<Rectangle>("AvatarPreviewPhoto").ActualHeight==256,"viewer/photo not compact 256 px layout");
            Check(C<TextBlock>("AvatarPreviewName").Text==friend.Name&&C<TextBlock>("AvatarPreviewUsername").Text=="@player","wrong player identity");
            Check(C<Border>("SocialDetailsOverlay").Opacity>.99&&C<Border>("SocialDetailsCard").Opacity>.99,"opening flickers existing profile");
            var backdrop=C<Border>("AvatarPreviewOverlay");
            Check(ReferenceEquals(w.InputHitTest(backdrop.TranslatePoint(new Point(4,4),w)),backdrop),"backdrop permits clickthrough");
            Check(!Press(C<Rectangle>("AvatarPreviewPhoto")).Handled&&Visible("AvatarPreviewOverlay"),"inside click closes viewer");
            Check(KeyPress(C<Button>("AvatarPreviewClose"),Key.Tab).Handled&&Focused(C<Button>("AvatarPreviewClose")),"Tab escapes viewer");
            Capture("avatar-preview");
            C<Button>("AvatarPreviewClose").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(280);
            Check(!Visible("AvatarPreviewOverlay")&&Visible("SocialDetailsOverlay")&&Field<Guid?>("_socialDetailsPeer")==friend.Id,"close X loses profile");
            Check(C<Rectangle>("AvatarPreviewPhoto").Fill is null&&C<TextBlock>("AvatarPreviewName").Text.Length==0,"dismissed viewer retains image/identity");
            Check(Focused(C<Button>("SocialDetailsAvatarButton")),"dismissal did not restore focus to avatar");
            Open();await Task.Delay(240);var outside=Press(backdrop);await Task.Delay(280);
            Check(outside.Handled&&!Visible("AvatarPreviewOverlay")&&Visible("SocialDetailsOverlay"),"outside press is not consumed or closes more than viewer");
            Open();await Task.Delay(240);var escape=KeyPress(C<Button>("AvatarPreviewClose"),Key.Escape);await Task.Delay(280);
            Check(escape.Handled&&!Visible("AvatarPreviewOverlay")&&Visible("SocialDetailsOverlay"),"Esc does not close only viewer");
            KeyPress(C<Button>("SocialDetailsClose"),Key.Escape);await Task.Delay(280);
            Check(!Visible("SocialDetailsOverlay"),"normal profile Esc regressed");
            Call("ShowSocialDetails",friend);Open();await Task.Delay(260);
            generation=Field<int>("_avatarPreviewGeneration");
            var renamed=friend with{DisplayName=language=="ru"?"Новое имя":"Updated name",Nickname="updated_player"};
            Players(renamed,missing);Call("RenderSocialDetails",renamed);
            Check(C<TextBlock>("AvatarPreviewName").Text==renamed.Name&&C<TextBlock>("AvatarPreviewUsername").Text=="@updated_player"&&generation==Field<int>("_avatarPreviewGeneration")&&backdrop.Opacity>.99,"profile refresh fails to update identity or replays entrance");
            foreach(var selectedLanguage in new[]{"ru","en",language})
            {
                Field<PawsPatchLauncher.Localization>("_text").SetLanguage(selectedLanguage);Call("ApplySocialLanguage");
                Check(Visible("AvatarPreviewOverlay")&&AutomationProperties.GetName(C<Button>("AvatarPreviewClose"))==(selectedLanguage=="ru"?"Закрыть просмотр аватарки":"Close avatar preview"),"language switch loses viewer/localized close");
            }
            await Dismiss();
            // A recognized player who is not a friend uses the existing profile-avatar cache too.
            Avatars("_gameParticipantAvatars")[guest.Id]=(revision,photo);Set("_activityViewedPlayer",guest);Call("ShowSocialDetails",guest);Open();
            Check(Visible("AvatarPreviewOverlay")&&Field<Guid?>("_avatarPreviewPeer")==guest.Id&&avatarCalls==0,"nonfriend profile avatar cannot be previewed from cache");
            Call("CloseSocialDetails");
            Check(!Visible("AvatarPreviewOverlay")&&C<Rectangle>("AvatarPreviewPhoto").Fill is null,"closing parent leaves viewer/image");
            Call("ShowSocialDetails",missing);Open();
            Check(!C<Button>("SocialDetailsAvatarButton").IsEnabled&&!Visible("AvatarPreviewOverlay"),"missing avatar opens empty viewer");
            var deleted=friend with{DeletedAt=DateTimeOffset.UtcNow};Players(deleted,missing);Set("_socialDetailsPeer",deleted.Id);Call("RenderSocialDetails",deleted);Open();
            Check(!C<Button>("SocialDetailsAvatarButton").IsEnabled&&!Visible("AvatarPreviewOverlay"),"deleted profile exposes cached avatar");
            Players(friend,missing);Call("CloseSocialDetails");Call("ShowSocialDetails",friend);Open();
            var removed=friend with{AvatarRevision=null};Players(removed,missing);Call("RenderSocialDetails",removed);
            Check(!Visible("AvatarPreviewOverlay")&&C<Rectangle>("AvatarPreviewPhoto").Fill is null&&!C<Button>("SocialDetailsAvatarButton").IsEnabled,"removed avatar stays visible from stale cache");
            Check(Focused(C<Button>("SocialDetailsClose")),"removed avatar strands focus in hidden viewer");
            // Existing profile transport can complete after opening; preview never starts another read.
            var delayed=friend with{AvatarRevision=revision.AddMinutes(1)};Players(delayed,missing);Call("CloseSocialDetails");
            var pendingPhoto=new TaskCompletionSource<byte[]?>();
            Set("_gameAvatarReadOverride",(Func<Guid,CancellationToken,Task<byte[]?>>)((_,_)=>{avatarCalls++;return pendingPhoto.Task;}));
            Call("ShowSocialDetails",delayed);
            Check(!C<Button>("SocialDetailsAvatarButton").IsEnabled&&avatarCalls==1,"loading photo allows stale preview or reads twice");
            pendingPhoto.SetResult(jpeg);await Task.Delay(260);Open();
            Check(C<Button>("SocialDetailsAvatarButton").IsEnabled&&Visible("AvatarPreviewOverlay")&&avatarCalls==1,"completed profile download does not enable viewer");
            var closing=Dismiss();Call("CloseSocialDetails");Call("ShowSocialDetails",delayed);Open();await closing;await Task.Delay(280);
            Check(Visible("AvatarPreviewOverlay")&&Field<Guid?>("_avatarPreviewPeer")==delayed.Id,"old dismissal tears down reopened preview");
            // Identity changes use normal social teardown, including while a hide animation is pending.
            pendingPhoto=new TaskCompletionSource<byte[]?>();
            var latePhoto=(Task)Call("RefreshShownProfileAvatarAsync",delayed with{AvatarRevision=revision.AddMinutes(2)},Field<int>("_socialDetailsGeneration"))!;
            closing=Dismiss();
            var guestAccount=new AccountService(new AccountSessionStore(System.IO.Path.Combine(ActivityStore.Root,"avatar-preview-new-owner")),
                new AccountChecks.Handler(_=>throw new InvalidOperationException("Unexpected request after account switch")));
            Set("_account",guestAccount);Call("RenderSocialIdentity");pendingPhoto.SetResult(jpeg);await Task.WhenAll(closing,latePhoto);
            Check(!Visible("AvatarPreviewOverlay")&&!Visible("SocialDetailsOverlay")&&Field<Guid?>("_avatarPreviewPeer") is null&&Field<string?>("_avatarPreviewOwner") is null&&C<Rectangle>("AvatarPreviewPhoto").Fill is null,"account change retains profile/viewer identity");
            Check(Avatars("_gameParticipantAvatars").Count==0&&Avatars("_socialAvatars").Count==0&&!C<Button>("SocialDetailsAvatarButton").IsEnabled,"late photo restores previous account cache/trigger");
            Console.WriteLine($"AVATAR PREVIEW UI PASS {checks} {language}: cached 256 px photo, stable profile, X/outside/Esc, focus, language, missing/deleted/replaced avatar, delayed photo, nonfriend, reopen and account cleanup.");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();
            var timer=new DispatcherTimer{Interval=interactive?TimeSpan.FromMinutes(15):TimeSpan.FromSeconds(30)};timer.Tick+=(_,_)=>frame.Continue=false;
            task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start();try{Dispatcher.PushFrame(frame);}finally{timer.Stop();}
            if(!task.IsCompleted)throw new TimeoutException();task.GetAwaiter().GetResult();
        }
        finally{Set("_busy",false);w.Close();}
    }
}
