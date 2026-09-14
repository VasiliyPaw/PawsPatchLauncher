using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class Launcher080Checks
{
    internal static void Run(string output)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Smoke profile required");
        Directory.CreateDirectory(output);new SettingsStore().Save(new UserSettings{Language="en",ModNoticeSeen=true,RussianLocalization=true,GameVoiceLanguage="en"});
        var w=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null){Left=-32000,Top=-32000,Width=1600,Height=1000,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual};
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        object? Call(string name,params object?[] values)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,values);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name)=>(T)w.FindName(name);
        var checks=0;void Check(bool value,string why){checks++;if(!value)throw new Exception("Launcher 080 UI: "+why);}
        void Capture(string name)
        {
            w.UpdateLayout();var view=(FrameworkElement)w.Content;var bitmap=new RenderTargetBitmap((int)view.ActualWidth,(int)view.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(view);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var stream=File.Create(Path.Combine(output,name+".png"));encoder.Save(stream);
        }
        var owner=Guid.NewGuid();var revision=DateTimeOffset.UtcNow;var network=0;
        HttpResponseMessage Json(object value)=>new(HttpStatusCode.OK){Content=new System.Net.Http.StringContent(JsonSerializer.Serialize(value))};
        var handler=new AccountChecks.Handler(request=>
        {
            network++;
            return Task.FromResult(request.RequestUri!.AbsolutePath switch
            {
                var path when path.EndsWith("/token")=>Json(new{access_token="fixture",refresh_token="fixture",expires_in=3600,user=new{id=owner,email="fixture@example.invalid"}}),
                var path when path.EndsWith("/paw_profiles")=>Json(new[]{new{id=owner,nickname="fixture",display_name="Player",avatar_changed_at=revision}}),
                _=>throw new Exception("Unexpected request in own-card fixture")
            });
        });
        using var account=new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root,"own-card")),handler);
        async Task Scenario()
        {
            Call("SetActivePage","settings");
            if(ActivityStore.LocalTestProfile is not null)
                Check((string)Call("LatestFriendLauncherVersion","0.7.12")! == "0.7.12.0","unpublished preview requires friends to install the preview");
            var choices=C<ComboBox>("LauncherLanguageCombo");
            Check(choices.Items.Count==5,"five launcher languages");
            foreach(var language in UiLanguages.Choices)
            {
                choices.SelectedIndex=UiLanguages.Choices.ToList().IndexOf(language);await Task.Delay(100);w.UpdateLayout();
                Check(Field<PawsPatchLauncher.Localization>("_text").Language==language.Code,"language choice applies");
                Check(choices.Items.Cast<object>().Select(x=>x.ToString()).SequenceEqual(UiLanguages.Choices.Select(c=>c.Label)),"launcher autonyms changed");
                Check(C<ComboBox>("GameLanguageCombo").Items[0].ToString()==UiLanguages.GameLanguageName("en",language.Code),"game text name not localized");
                Check(C<ComboBox>("GameVoiceCombo").Items[1].ToString()==UiLanguages.GameLanguageName("ru",language.Code),"speech name not localized");
                Check(Field<UserSettings>("_settings").RussianLocalization&&GameLanguages.Voice(Field<UserSettings>("_settings"))=="en","UI language changed game configuration");
                var card=C<Border>("InterfaceLanguageCard");Check(card.ActualWidth<400,"language setting stretched across the window");
                Check(choices.TranslatePoint(new Point(0,0),card).Y-C<TextBlock>("SettingsLanguageTitleText").TranslatePoint(new Point(0,0),card).Y<45,"language label is far from selector");
                Capture("settings-080-"+language.Code);
            }
            w.Width=1050;w.Height=680;w.UpdateLayout();Capture("settings-080-compact-fr");
            await account.SignInAsync("fixture@example.invalid","fixture-password",remember:false);Field<AccountService>("_account").Dispose();Set("_account",account);Call("RenderAccount");
            var afterSignIn=network;
            var own=(SocialPlayer)Call("CreateOwnPlayerCard",owner,null,new SocialVersions("0.8.0"),false)!;
            Check(own.Configuration is null,"own card published unapplied settings");
            Call("SetActivePage","account");
            C<Button>("OwnProfileNameButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(300);
            Check(Field<Guid?>("_socialDetailsPeer")==owner&&C<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible,"profile name did not open own card");
            Check(C<Grid>("SocialDetailsFriendActions").Visibility==Visibility.Collapsed,"own friend/block actions visible");
            Check(C<Button>("SocialDetailsCopyButton").Visibility==Visibility.Collapsed,"own copy action visible");
            Check(network==afterSignIn,"own card unnecessarily requested server profile");Capture("own-card-080");
            Call("CloseSocialDetails");
            var avatar=(Grid)Call("SocialAvatar",owner,30d,false,true)!;
            avatar.RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,Environment.TickCount,MouseButton.Left){RoutedEvent=Mouse.MouseUpEvent});await Task.Delay(300);
            Check(Field<Guid?>("_socialDetailsPeer")==owner&&C<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible,"own chat avatar did not open card");
            var brush=new ImageBrush(new DrawingImage(new GeometryDrawing(Brushes.CadetBlue,null,new RectangleGeometry(new Rect(0,0,256,256)))));brush.Freeze();
            Set("_accountAvatar",brush);Set("_accountAvatarOwner",owner.ToString());Set("_accountAvatarRevision",account.AvatarChangedAt);
            own=(SocialPlayer)Call("CreateOwnPlayerCard",owner,null,new SocialVersions("0.8.0"),false)!;Set("_ownPlayerCard",own);Call("RenderSocialDetails",own);
            Check(C<Button>("SocialDetailsAvatarButton").IsEnabled,"own avatar preview missing");
            C<Button>("SocialDetailsAvatarButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));Check(C<Border>("AvatarPreviewOverlay").Visibility==Visibility.Visible,"own avatar preview not opened");Call("CloseAvatarPreview",false);
            var profile=new GameParticipantProfile(owner,"fixture","Player",account.AvatarChangedAt);
            var details=new GameActivityDetails(new GameActivity("match",true,3702,192,256,Self:"self",Players:[new("self","Game nickname",false,Team:1,Color:"#DDA443",Race:"human",Subrace:"royalist"),new("bot","Computer",true,Team:1,Color:"#478BDC",Race:"haroun",Subrace:"council")]),DateTimeOffset.UtcNow);
            Set("_ownActivity",details);await (Task)Call("ShowGameActivityAsync",owner)!;await Task.Delay(260);Capture("own-match-080");
            Check(Field<GameActivityDetails>("_gameActivityShown").Activity.Players![0].Profile?.Id==owner,"native self identity not enriched");
            await (Task)Call("OpenGameParticipantProfileAsync",profile)!;await Task.Delay(260);
            Check(Field<Guid?>("_socialDetailsPeer")==owner&&C<Border>("GameActivityOverlay").Visibility==Visibility.Collapsed,"own match participant did not open card");
            Check(network==afterSignIn,"own-card routes issued extra account requests");
            Call("ClearSocialProfiles");Check(Field<SocialPlayer?>("_ownPlayerCard") is null&&Field<GameActivityDetails?>("_ownActivity") is null,"account cleanup retained own private state");
            Console.WriteLine($"LAUNCHER 080 UI PASS {checks}");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(35)};
            timer.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start();try{Dispatcher.PushFrame(frame);}finally{timer.Stop();}if(!task.IsCompleted)throw new TimeoutException();task.GetAwaiter().GetResult();
        }
        finally{Set("_busy",false);w.Close();}
    }
}
