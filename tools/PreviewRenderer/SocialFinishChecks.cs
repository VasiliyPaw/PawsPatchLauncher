using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class SocialFinishChecks
{
    const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
    internal static void Run(string language)
    {
        var w=new MainWindow();int checks=0;
        object? Invoke(string n,params object?[] a)=>typeof(MainWindow).GetMethod(n,Flags)!.Invoke(w,a);
        T Field<T>(string n)=>(T)typeof(MainWindow).GetField(n,Flags)!.GetValue(w)!;
        void Set(string n,object value)=>typeof(MainWindow).GetField(n,Flags)!.SetValue(w,value);
        T Control<T>(string n)=>(T)w.FindName(n);
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Social finish UI: "+why);}
        MouseButtonEventArgs Press(UIElement element,bool right=false)
        {
            var e=new MouseButtonEventArgs(Mouse.PrimaryDevice,0,right?MouseButton.Right:MouseButton.Left){RoutedEvent=right?Mouse.MouseUpEvent:UIElement.PreviewMouseDownEvent};
            element.RaiseEvent(e);return e;
        }
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Invoke("ApplyLanguage");SocialChecks.Populate(w,"chat");
            int menus=0;Set("_socialMenuOpenOverride",(Action<ContextMenu>)(_=>menus++));
            var friend=Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p=>p.Relation=="friend");
            var line=(Grid)((StackPanel)Control<StackPanel>("FriendsRowsPanel").Children[0]).Children[0];
            Check(line.Children.Count==1,"trailing chat action button remains");
            Press((Button)line.Children[0],true);
            Check(menus==1&&Field<ContextMenu>("_socialMenu").Items.Count==3,"friend-row right-click lost actions");Invoke("CloseSocialMenu");
            var message=(Grid)Control<StackPanel>("FriendsMessagesPanel").Children[0];
            var bubble=message.Children.OfType<Border>().Single();var textPanel=(StackPanel)bubble.Child;
            Press(message,true);Press(textPanel,true);Press(textPanel.Children.OfType<TextBlock>().Last(),true);
            Check(menus==1,"ordinary message/background opens player menu");
            Check(textPanel.Children.OfType<TextBlock>().First().Text.EndsWith(Field<IReadOnlyList<SocialMessage>>("_socialMessages")[0].CreatedAt.ToLocalTime().ToString("HH:mm:ss")),"message seconds missing");

            Invoke("ShowSocialDetails",friend);
            var headerAvatar=Control<ContentControl>("FriendsChatHeaderAvatar").Content;
            Check(headerAvatar is Grid {Width:38},"chat header avatar missing");
            Invoke("RenderSocialMessages");Check(ReferenceEquals(headerAvatar,Control<ContentControl>("FriendsChatHeaderAvatar").Content),"unchanged header avatar rebuilt");
            Check(Control<System.Windows.Documents.Run>("FriendsChatUsername").BaselineAlignment==BaselineAlignment.Center,"username baseline not raised");
            Invoke("CloseSocialDetails");Control<Button>("FriendsChatProfileButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(Control<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible,"chat header does not open profile");
            var offline=friend with{Presence="offline",LastSeen=new DateTimeOffset(2026,9,8,4,23,47,TimeSpan.Zero)};
            Invoke("RenderSocialDetails",offline);
            Check(Control<TextBlock>("SocialDetailsActivity").Text.EndsWith(offline.LastSeen!.Value.ToLocalTime().ToString("HH:mm:ss")),"last seen seconds missing");
            Invoke("RenderSocialDetails",friend);
            Press(Control<TextBlock>("SocialDetailsName"));Check(Control<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible,"inside click closes profile");
            foreach(var action in new[]{"Remove","Block"})
            {
                var button=Control<Button>("SocialDetails"+action+"Button");
                Check(button.Background.ToString()=="#FF653A38"&&button.IsEnabled,"profile action style/availability");
                button.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Check(Control<Border>("ConfirmationOverlay").Visibility==Visibility.Visible,"dangerous action has no confirmation");
                Press(Control<Border>("ConfirmationCard"));Check(Control<Border>("ConfirmationOverlay").Visibility==Visibility.Visible,"card padding counted as outside");
                var e=Press(Control<Border>("ConfirmationOverlay"));await Task.Delay(40);
                Check(e.Handled&&Control<Border>("ConfirmationOverlay").Visibility==Visibility.Collapsed,"outside confirmation not consumed/cancelled");
                Check(Control<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible&&Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").Any(p=>p.Id==friend.Id),"cancel closed profile or mutated friendship");
            }
            Press(Control<Border>("SocialDetailsOverlay"));Check(Control<Border>("SocialDetailsOverlay").Visibility==Visibility.Collapsed,"outside profile stays open");
            Control<Border>("HelpOverlay").Visibility=Visibility.Visible;
            Press(Control<TextBlock>("HelpBodyText"));Check(Control<Border>("HelpOverlay").Visibility==Visibility.Visible,"inside help closes");
            Press(Control<Border>("HelpOverlay"));Check(Control<Border>("HelpOverlay").Visibility==Visibility.Collapsed,"outside help stays open");

            string copied="";Set("_clipboardWrite",(Action<string>)(s=>copied=s));
            Invoke("ShowSocialDetails",friend);
            var friendCopy=Control<ClipboardButton>("SocialDetailsCopyUsernameButton");
            friendCopy.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(40);
            Check(copied==friend.Nickname&&ClipboardButton.GetIsCopySuccessful(friendCopy)&&!friendCopy.IsEnabled,"friend username checkmark/cooldown");
            friendCopy.IsEnabled=true;Check(!friendCopy.IsEnabled,"render overrode copy cooldown");
            Invoke("CloseSocialDetails");Invoke("ShowSocialDetails",friend);
            Check(!ClipboardButton.GetIsCopySuccessful(friendCopy)&&friendCopy.IsEnabled,"profile reset kept stale feedback");
            Invoke("CloseSocialDetails");
            Control<Button>("AccountCopyUsernameButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(40);
            Check(copied==Field<AccountService>("_account").Nickname,"own username clipboard payload");
            Check(Control<TextBlock>("ToastText").Text.Contains(language=="ru"?"скопирован":"copied"),"username copy feedback");
            Check(ClipboardButton.GetIsCopySuccessful(Control<Button>("AccountCopyUsernameButton"))&&!Control<Button>("AccountCopyUsernameButton").IsEnabled,"own username cooldown");
            Check(Control<TextBlock>("AccountProfileCreatedText").Text.Count(c=>c==':')==3,"account creation time seconds");
            var configCopy=Control<ClipboardButton>("CopyConfigurationButton");
            configCopy.IsEnabled=true;configCopy.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(30);
            Check(ConfigurationCode.Parse(copied) is not null&&ClipboardButton.GetIsCopySuccessful(configCopy)&&!configCopy.IsEnabled,"configuration checkmark/cooldown");
            configCopy.ApplyTemplate();
            Check(configCopy.Template.FindName("CopySuccessIcon",configCopy) is LauncherIcon {Visibility:Visibility.Visible},"copy success template missing");
            configCopy.ResetFeedback();
            var completion=new TaskCompletionSource<bool>();int clicks=0;
            var copyTask=configCopy.CopyAsync(()=>{clicks++;return completion.Task;});
            await configCopy.CopyAsync(()=>{clicks++;return Task.FromResult(true);});
            Check(!configCopy.IsEnabled&&!ClipboardButton.GetIsCopySuccessful(configCopy)&&clicks==1,"pending copy repeated or reported success");
            completion.SetResult(false);await copyTask;
            Check(configCopy.IsEnabled&&!ClipboardButton.GetIsCopySuccessful(configCopy),"failed copy has checkmark or cooldown");
            copyTask=configCopy.CopyAsync(()=>Task.FromResult(true));
            configCopy.Content="Localized while waiting";configCopy.IsEnabled=false;
            await Task.Delay(4600);Check(!configCopy.IsEnabled&&ClipboardButton.GetIsCopySuccessful(configCopy),"cooldown ended before five seconds");
            await copyTask;Check(!configCopy.IsEnabled&&!ClipboardButton.GetIsCopySuccessful(configCopy)&&configCopy.Content.ToString()=="Localized while waiting","cooldown lost external disable or changed label");
            configCopy.IsEnabled=true;Check(configCopy.IsEnabled,"cooldown did not unlock after five seconds");
            var before=new UserSettings();var after=ConfigurationCode.Parse(friend.Configuration!);
            var confirmation=(Task<bool>)Invoke("ConfirmActionAsync","fixture","body","changes","path","copy")!;
            Invoke("RenderConfigurationChanges",before,after,null);
            var entries=Control<StackPanel>("ConfirmationChangesPanel").Children.OfType<Border>().Select(b=>b.Child).OfType<Grid>().ToArray();
            Check(entries.Length==ConfigurationChanges.Compare(before,after,language=="ru").Count&&entries.Length>1,"structured diff row count");
            Check(entries.All(g=>g.Tag is ConfigurationChange c&&g.Children.OfType<Border>().Count()==2&&c.Before!=c.After),"structured before/after values");
            var content=(FrameworkElement)w.Content;
            foreach(var size in new[]{new Size(1440,900),new Size(1050,680)})
            {
                content.Measure(size);content.Arrange(new Rect(size));content.UpdateLayout();
                var bounds=Control<Border>("ConfirmationCard").TransformToAncestor(content).TransformBounds(new Rect(Control<Border>("ConfirmationCard").RenderSize));
                Check(bounds.Top>=0&&bounds.Bottom<=size.Height,"configuration preview clips compact window");
            }
            Press(Control<Border>("ConfirmationOverlay"));Check(!await confirmation,"outside click accepted configuration");
            confirmation=(Task<bool>)Invoke("ConfirmActionAsync","plain","body","label","plain value","delete")!;
            Check(Control<StackPanel>("ConfirmationChangesPanel").Visibility==Visibility.Collapsed&&Control<TextBlock>("ConfirmationPathText").Visibility==Visibility.Visible,"pretty preview leaks into other confirmations");
            Press(Control<Border>("ConfirmationOverlay"));await confirmation;
            OfferUiChecks.Populate(w);
            foreach(Border offer in Control<StackPanel>("FriendsMessagesPanel").Children)
            {
                var header=((StackPanel)offer.Child).Children.OfType<DockPanel>().Single();
                Check(header.Children.OfType<TextBlock>().Any(t=>t.Tag as string=="offer-time"&&t.Text.Count(c=>c==':')==2),"offer time missing");
            }

            Invoke("ResetChatMedia",true);
            const string gifUrl="https://media.discordapp.net/first.gif?signature=exact";
            const string pngUrl="https://example.com/second.png";
            var gif=Convert.FromBase64String("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==");
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(BitmapSource.Create(2,2,96,96,PixelFormats.Bgra32,null,new byte[16],8)));
            using var bytes=new MemoryStream();encoder.Save(bytes);bool failPng=true;
            Set("_chatMedia",new ChatMedia(new Fixture(req=>req.RequestUri!.AbsolutePath.EndsWith(".png")
                ?new HttpResponseMessage(failPng?HttpStatusCode.ServiceUnavailable:HttpStatusCode.OK){Content=new ByteArrayContent(bytes.ToArray())}
                :new HttpResponseMessage(HttpStatusCode.OK){Content=new ByteArrayContent(gif)})));
            var panel=new StackPanel();var body=new TextBlock {Tag="message-body",Text="Caption\n"+gifUrl+"\n"+pngUrl};panel.Children.Add(body);
            Invoke("AddChatMedia",panel,body.Text);
            var hosts=panel.Children.OfType<Border>().ToArray();
            Check(body.Text.Contains(gifUrl)&&body.Text.Contains(pngUrl),"links hidden before loading");
            using var surface=new HwndSource(new HwndSourceParameters("Hidden chat media finish fixture"){Width=500,Height=600,WindowStyle=unchecked((int)0x80000000)});
            surface.RootVisual=panel;await Task.Delay(80);
            ((Button)hosts[0].Child).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(150);
            Check(hosts[0].Child is Image {Source:not null}&&!body.Text.Contains(gifUrl)&&body.Text.Contains(pngUrl)&&body.Text.Contains("Caption"),"GIF success did not selectively hide URL");
            copied="";Press((Image)hosts[0].Child,true);
            var menu=Field<ContextMenu>("_socialMenu");
            Check(menu.Items.Count==1&&((MenuItem)menu.Items[0]).Tag as string=="copy_media_link","media opens player menu");
            ((MenuItem)menu.Items[0]).RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));await Task.Delay(40);
            Check(copied==gifUrl,"image copy lost original signed URL");
            ((Button)hosts[1].Child).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(80);
            Check(hosts[1].Child is Button&&body.Text.Contains(pngUrl)&&!body.Text.Contains(gifUrl),"failed image did not retain its link");
            failPng=false;((Button)hosts[1].Child).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(100);
            Check(hosts[1].Child is Image {Source:not null}&&body.Text=="Caption","PNG retry link/caption handling");
            ((Image)hosts[0].Child).Source=null;
            Check(body.Text.Contains(gifUrl),"lost GIF preview did not restore fallback link");
            Invoke("ResetChatMedia",true);
            Check(((Image)hosts[1].Child).Source is null,"media teardown retained bitmap");
            Console.WriteLine($"SOCIAL FINISH UI PASS {checks} {language}: outside cancellation/layers, row-only menus, red profile actions, username/link clipboard, media success/failure/retry, seconds and structured diff; mocked network/clipboard, hidden image surface");
        }
        try
        {
            SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(w.Dispatcher));
            var task=Scenario();var frame=new DispatcherFrame();var timer=new DispatcherTimer {Interval=TimeSpan.FromSeconds(30)};
            timer.Tick+=(_,_)=>frame.Continue=false;timer.Start();_=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(new Action(()=>frame.Continue=false)));
            if(!task.IsCompleted)Dispatcher.PushFrame(frame);timer.Stop();
            if(!task.IsCompleted)throw new TimeoutException("Social finish checks");task.GetAwaiter().GetResult();
        }
        finally {Invoke("CloseSocialMenu");w.Close();SynchronizationContext.SetSynchronizationContext(null);}
    }
    private sealed class Fixture(Func<HttpRequestMessage,HttpResponseMessage> handler):HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>Task.FromResult(handler(request));
    }
}
