using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;
using XamlAnimatedGif;
namespace PreviewRenderer;
internal static class IdentityMediaUiChecks
{
 const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
 internal static void Run(string language)
 {
  var w=new MainWindow();int checks=0;
  object? Invoke(string n,params object?[] a)=>typeof(MainWindow).GetMethod(n,Flags)!.Invoke(w,a);
  T Field<T>(string n)=>(T)typeof(MainWindow).GetField(n,Flags)!.GetValue(w)!;
  void Set(string n,object v)=>typeof(MainWindow).GetField(n,Flags)!.SetValue(w,v);
  T Control<T>(string n)=>(T)w.FindName(n);
  void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Identity/media UI: "+why);}
  try{
   Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Invoke("ApplyLanguage");Invoke("ShowAccountForm",true);
   Check(Control<TextBox>("AccountDisplayNameInput").IsVisible==Control<TextBox>("AccountNicknameInput").IsVisible,"registration display field");
   Check(Control<TextBox>("AccountDisplayNameInput").MaxLength==32,"display input bound");
   Invoke("ShowAccountForm",false);Check(Control<TextBlock>("AccountEmailLabel").Text.Contains("username",StringComparison.OrdinalIgnoreCase),"login username label");
   SocialChecks.Populate(w,"chat");
   var peer=Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p=>p.Relation=="friend") with{DisplayName="A shared display name"};
   Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)new[]{peer});Invoke("RenderSocialRows");Invoke("RenderSocialMessages");
   Check(Control<System.Windows.Documents.Run>("FriendsChatName").Text==peer.Name&&Control<System.Windows.Documents.Run>("FriendsChatUsername").Text=="@"+peer.Nickname
      &&Control<TextBlock>("FriendsChatTitle").Inlines.OfType<System.Windows.Documents.Run>().Any(r=>r.Text==" · "),"compact chat identity line");
   var name=(StackPanel)Invoke("SocialNameLabel",peer)!;
   Check(((TextBlock)name.Children[0]).Text==peer.Name&&((TextBlock)name.Children[1]).Text=="@"+peer.Nickname,"row identity");
   var avatar=(Grid)Invoke("SocialAvatar",peer.Id,30d,false)!;
   avatar.RaiseEvent(new System.Windows.Input.MouseButtonEventArgs(System.Windows.Input.Mouse.PrimaryDevice,0,System.Windows.Input.MouseButton.Left){RoutedEvent=UIElement.MouseLeftButtonUpEvent});
   Check(Control<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible&&Control<TextBlock>("SocialDetailsUsername").Text=="@"+peer.Nickname,"avatar opens profile");
   Invoke("CloseSocialDetails");Check(Control<TextBlock>("SocialDetailsUsername").Text=="","profile identity cleared");
   var menu=(ContextMenu)Invoke("CreateSocialMenu",new Button(),peer)!;
   Check(((MenuItem)menu.Items[0]).Header.ToString()==(language=="ru"?"Профиль":"Profile"),"profile menu label");
   Invoke("ApplyNotificationSoundLanguage");Control<Slider>("NotificationVolumeSlider").Value=37;
   Check(Field<UserSettings>("_settings").NotificationVolume==37&&Control<TextBlock>("NotificationVolumeValue").Text=="37%","volume preference");
   var gif=Convert.FromBase64String("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==");int requests=0;
   Invoke("ResetChatMedia",true);
   Set("_chatMedia",new ChatMedia(new Fixture(req=>{requests++;return new HttpResponseMessage(HttpStatusCode.OK){Content=new ByteArrayContent(gif)};})));
   var panel=new StackPanel();Invoke("AddChatMedia",panel,"https://media.discordapp.net/example.gif?signature=fixture");
   Check(panel.Children.Count==1&&requests==0,"smoke preview performed automatic network");
   using var surface=new System.Windows.Interop.HwndSource(new System.Windows.Interop.HwndSourceParameters("Hidden media fixture"){Width=16,Height=16,WindowStyle=unchecked((int)0x80000000)});
   surface.RootVisual=panel;Pump(); // Hidden native render target gives the GIF player a genuine Loaded lifecycle.
   var host=(Border)panel.Children[0];((Button)host.Child).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
   Pump();Check(host.Child is Image,"inline GIF not an image");
   var image=(Image)host.Child;
   image.RaiseEvent(new RoutedEventArgs(FrameworkElement.LoadedEvent));Pump();
   Check(image.Source is not null&&image.Source.Width==1,"GIF first frame decoded");
   Check(AnimationBehavior.GetSourceStream(image) is MemoryStream,"GIF stream / no disk URL");
   Check(AnimationBehavior.GetRepeatBehavior(image)==System.Windows.Media.Animation.RepeatBehavior.Forever,"GIF does not repeat");
   Invoke("ResetChatMedia",true);
   Check(AnimationBehavior.GetSourceStream(image) is null&&image.Source is null,"media retained across identity reset");
   Check(requests==1,"duplicate media download");
   Console.WriteLine($"IDENTITY + MEDIA UI PASS {checks} {language}: separate name lines, avatar profile, popup label, volume, inline GIF stream/repeat/cleanup; detached UI, mocked media");
  }finally{w.Close();}
 }
 private static void Pump(){
  var frame=new DispatcherFrame();var timer=new DispatcherTimer{Interval=TimeSpan.FromMilliseconds(80)};
  timer.Tick+=(_,_)=>{timer.Stop();frame.Continue=false;};timer.Start();Dispatcher.PushFrame(frame);
 }
 private sealed class Fixture(Func<HttpRequestMessage,HttpResponseMessage> handler):HttpMessageHandler{
  protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>Task.FromResult(handler(request));
 }
}
