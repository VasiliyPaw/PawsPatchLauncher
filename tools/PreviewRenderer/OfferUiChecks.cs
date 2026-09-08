using System.IO;
using Path=System.IO.Path;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Shapes;
using PawsPatchLauncher;
namespace PreviewRenderer;
internal static class OfferUiChecks
{
 const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
 internal static void PopulateConfirmation(MainWindow w)
 {
  Populate(w);
  var settings=(UserSettings)typeof(MainWindow).GetField("_settings",Flags)!.GetValue(w)!;
  ConfigurationCode.Apply(ConfigurationCode.Parse("PAW-STABLE-IW1-SP4-RM0-SG0-LM1-RU0-CL1-OOS0"),settings);
  var game=new GameInstallation(ActivityStore.Root,Path.Combine(ActivityStore.Root,"k2.exe"),null,null);
  typeof(MainWindow).GetField("_game",Flags)!.SetValue(w,game);
  typeof(MainWindow).GetField("_gameRunningProbe",Flags)!.SetValue(w,(Func<bool>)(()=>false));
  var friend=((IReadOnlyList<SocialPlayer>)typeof(MainWindow).GetField("_socialPlayers",Flags)!.GetValue(w)!).First(p=>p.Relation=="friend");
  typeof(MainWindow).GetMethod("ShowSocialDetails",Flags)!.Invoke(w,new object[]{friend});
  _=(Task)typeof(MainWindow).GetMethod("CopyFriendSettingsAsync",Flags)!.Invoke(w,null)!;
 }
 internal static void Populate(MainWindow w)
 {
  if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException();
  SocialChecks.Populate(w,"chat");
  T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,Flags)!.GetValue(w)!;
  void Set(string name,object value)=>typeof(MainWindow).GetField(name,Flags)!.SetValue(w,value);
  var peer=Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p=>p.Relation=="friend");
  var owner=Guid.Parse(Field<AccountService>("_account").UserId);var now=DateTimeOffset.UtcNow;
  var config=new SocialOffer(Guid.NewGuid(),peer.Id,owner,"config",peer.Configuration,null,null,null,"pending",now,now.AddMinutes(10),null,null);
  var save=config with{Id=Guid.NewGuid(),Kind="save",Configuration=null,FileName="Великая война.rsg",FileSize=102400,Sha256=new string('a',64)};
  var sent=config with{Id=Guid.NewGuid(),Sender=owner,Recipient=peer.Id,State="accepted"};
  Set("_socialOffers",(IReadOnlyList<SocialOffer>)new[]{config,save,sent});
  Set("_socialMessages",(IReadOnlyList<SocialMessage>)new[]{config,save,sent}.Select(o=>new SocialMessage(o.Sender,o.Id,o.Recipient,"fallback","config",now)).ToArray());
  Set("_socialPending",(IReadOnlyList<PendingSocialMessage>)Array.Empty<PendingSocialMessage>());
  typeof(MainWindow).GetMethod("RenderSocialMessages",Flags)!.Invoke(w,null);
 }
 internal static void Run(string language)
 {
  var w=new MainWindow();var checks=0;
  object? Invoke(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,Flags)!.Invoke(w,args);
  T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,Flags)!.GetValue(w)!;
  void Set(string name,object value)=>typeof(MainWindow).GetField(name,Flags)!.SetValue(w,value);
  T Control<T>(string name)=>(T)w.FindName(name);
  void Check(bool value,string why){checks++;if(!value)throw new Exception("Offer UI: "+why);}
  try {
   Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Invoke("ApplyLanguage");Populate(w);
   var rows=Control<StackPanel>("FriendsMessagesPanel");
   Check(rows.Children.Count==3 && rows.Children.OfType<Border>().Count()==3,"offers not distinct inline cards");
   var first=(Border)rows.Children[0];var peer=Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p=>p.Relation=="friend");
   ((Task)Invoke("OpenSocialChatAsync",peer)!).GetAwaiter().GetResult();
   Check(Control<Border>("FriendsChatCard").Visibility==Visibility.Collapsed&&!Field<bool>("_socialBusy"),"active chat click did not close chat");
   Populate(w); first=(Border)rows.Children[0];
   var accept=((StackPanel)first.Child).Children.OfType<WrapPanel>().Single().Children.OfType<Button>().First();
   Set("_busy",true);Invoke("RenderSocialMessages");Check(!accept.IsEnabled&&ReferenceEquals(first,rows.Children[0]),"busy action refresh rebuilds cards");
   Set("_busy",false);Invoke("RenderSocialMessages");
   Check(accept.IsEnabled==!(bool)Invoke("ConfigurationMatches",peer.Configuration)!&&ReferenceEquals(first,rows.Children[0]),"identical configuration / action refresh");
   Check(Control<Button>("FriendsComposerMoreButton").Content is LauncherIcon{Kind:IconKind.More},"composer menu icon");
   var sample=Field<IReadOnlyList<SocialOffer>>("_socialOffers")[0];
   foreach(var own in new[]{false,true})foreach(var kind in new[]{"config","save"})foreach(var state in new[]{"pending","applying","accepted","declined","failed","expired","cancelled","sending"})
   {
    var offer=sample with{Sender=own?sample.Recipient:sample.Sender,Recipient=own?sample.Sender:sample.Recipient,Kind=kind,State=state,FileName=kind=="save"?"test.rsg":null,FileSize=16};
    var row=(Border)Invoke("RenderOfferCard",offer)!;var panel=(StackPanel)row.Child;
    Check(panel.Children.OfType<WrapPanel>().Count()==(state=="pending"?1:0),"wrong sender cancel / receiver action visibility");
    Check(row.Opacity==(state=="sending"?.55:1),"optimistic card opacity");
    Check(panel.Children.OfType<TextBlock>().First().Text.Length>5,"empty status");
   }
   foreach(var presence in new[]{"online","playing","offline"}) {
    Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)new[]{peer with{Presence=presence}});
    var avatar=(Grid)Invoke("SocialAvatar",peer.Id,40d,true)!;
    var dot=avatar.Children.OfType<Ellipse>().Last();
    Check(dot.Width==16&&dot.Fill.ToString()==(presence=="online"?"#FF72ACFF":presence=="playing"?"#FF5CE5A1":"#FF718095"),"presence dot");
    var profile=(Grid)Invoke("SocialAvatar",peer.Id,68d,true)!;
    Check(profile.Children.OfType<Ellipse>().Last().Width==20,"large profile dot");
   }
   foreach(var size in new[]{new Size(1440,900),new Size(1050,680)}) {
    var content=(FrameworkElement)w.Content;content.Measure(size);content.Arrange(new Rect(size));content.UpdateLayout();
    var button=Control<Button>("FriendsComposerMoreButton");
    Check(button.ActualWidth==34&&button.TranslatePoint(new Point(button.ActualWidth,0),content).X<=size.Width,"composer clipped");
    Check(first.ActualWidth>240&&first.ActualWidth<Control<Border>("FriendsChatCard").ActualWidth,"offer card clipped");
   }
   Check(Control<CheckBox>("NotificationSoundToggle").IsChecked==true,"sound default not enabled");
   Console.WriteLine($"OFFER UI PASS {checks} {language}: distinct status cards, recipient-only actions, active-chat toggle, presence, composer layout, sound preference");
  }finally{w.Close();}
 }
}
