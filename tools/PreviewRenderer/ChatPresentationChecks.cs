using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class ChatPresentationChecks
{
    private const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
    internal static void Run(string language)
    {
        var w=new MainWindow();var checks=0;
        object? Invoke(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,Flags)!.Invoke(w,args);
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,Flags)!.SetValue(w,value);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,Flags)!.GetValue(w)!;
        T Control<T>(string name)=>(T)w.FindName(name);
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Chat presentation: "+why);}
        var content=(FrameworkElement)w.Content;
        void Layout(Size size){content.Measure(size);content.Arrange(new Rect(size));content.UpdateLayout();}
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Invoke("ApplyLanguage");SocialChecks.Populate(w,"chat");
            var input=Control<TextBox>("FriendsMessageInput");var send=Control<Button>("FriendsSendButton");
            Check(send.Content is LauncherIcon {Kind:IconKind.Send},"send is not an accessible vector icon");
            var keys=typeof(MainWindow).GetMethod("SendOnKey",BindingFlags.NonPublic|BindingFlags.Static)!;
            foreach(var pair in new[]{(ModifierKeys.None,true),(ModifierKeys.Shift,false),(ModifierKeys.Control,true),(ModifierKeys.Shift|ModifierKeys.Control,false)})
                Check((bool)keys.Invoke(null,[Key.Enter,pair.Item1])! == pair.Item2,"Enter/Shift+Enter policy");
            foreach(var size in new[]{new Size(1440,900),new Size(1050,680)})
            {
                input.Text="";Layout(size);var single=input.ActualHeight;
                Check(single>=36 && single<=42,"single-line composer not compact");
                var host=Control<Grid>("FriendsConversationScroll");var card=Control<Border>("FriendsChatCard");var scroll=Control<ScrollViewer>("FriendsChatScroll");
                Check(Math.Abs(host.ActualHeight-card.ActualHeight)<2 && scroll.ActualHeight>card.ActualHeight*.65,"chat does not consume available height");
                Check(Math.Abs(input.TranslatePoint(new Point(0,input.ActualHeight),content).Y-send.TranslatePoint(new Point(0,send.ActualHeight),content).Y)<2,"send not aligned to input bottom");
                input.Text="one\ntwo";Layout(size);Check(input.ActualHeight>single+5,"explicit newline does not grow input");
                input.Text=string.Join(" ",Enumerable.Repeat("wrapped",40));Layout(size);Check(input.ActualHeight>single+5,"automatic wrap does not grow input");
                input.Text=string.Join("\n",Enumerable.Repeat("line",30));Layout(size);Check(input.ActualHeight<=132 && input.ExtentHeight>input.ViewportHeight,"long composer has no height cap/scroll");
                input.Text="";Layout(size);Check(Math.Abs(input.ActualHeight-single)<1,"composer does not shrink");
            }
            var row=(StackPanel)Control<StackPanel>("FriendsRowsPanel").Children[0];var grid=(Grid)row.Children[0];
            var more=(Button)grid.Children[0];Check(grid.Children.Count==1,"chat row still has a separate more button");
            var friend=Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").Single(p=>p.Relation=="friend");
            var friendContent=(DockPanel)((Button)grid.Children[0]).Content;
            var friendAvatar=friendContent.Children.OfType<Grid>().Single();Check(friendAvatar.Children.Count==3,"friend avatar/status badge missing");
            var menu=(ContextMenu)Invoke("CreateSocialMenu",more,friend)!;
            menu.Visibility=Visibility.Visible;menu.ApplyTemplate();menu.Measure(new Size(240,300));menu.Arrange(new Rect(0,0,240,menu.DesiredSize.Height));menu.UpdateLayout();
            foreach(MenuItem item in menu.Items)
            {
                var surface=(Border)item.Template.FindName("Surface",item);
                Check(surface.ActualWidth>=220,"menu row does not stretch");
                Check(VisualTreeHelper.HitTest(surface,new Point(2,surface.ActualHeight/2))?.VisualHit is Border && VisualTreeHelper.HitTest(surface,new Point(surface.ActualWidth-2,surface.ActualHeight/2))?.VisualHit is Border,"menu padding has no hit-test surface");
                Check(surface.Background is SolidColorBrush {Color.A:255},"initial menu background transparent");
                Motion.SetBackground(surface,new SolidColorBrush(Color.FromRgb(35,60,92)));
                Check(((SolidColorBrush)surface.Background).Color.A==255,"first hover fades from transparent white");
            }
            foreach(Grid bubble in Control<StackPanel>("FriendsMessagesPanel").Children)
                Check(bubble.Children.OfType<Grid>().Single().Children.OfType<System.Windows.Shapes.Ellipse>().Any(),"message author avatar missing");
            var owner=Guid.Parse(Field<AccountService>("_account").UserId);
            var box=new SocialOutbox(Path.Combine(ActivityStore.Root,"chat-check-"+Guid.NewGuid()));Set("_socialOutbox",box);
            var expired=new PendingSocialMessage(owner,friend.Id,Guid.NewGuid(),"Timeout fixture","text"){CreatedAt=DateTimeOffset.UtcNow.AddMinutes(-2)};
            await box.AddAsync(expired);Set("_socialNextPoll",DateTimeOffset.UtcNow.AddHours(1));Set("_socialNextDelivery",DateTimeOffset.UtcNow.AddHours(1));
            await (Task)Invoke("SocialTickAsync")!;
            var failed=(await box.ReadAsync(owner)).Single();Check(failed.Error=="delivery_timeout","timer did not fail expired send");
            var failedRow=Control<StackPanel>("FriendsMessagesPanel").Children.OfType<Grid>().Single(r=>r.Tag is Guid id && id==expired.Id);
            var failedBody=(StackPanel)failedRow.Children.OfType<Border>().Single().Child;
            Check(failedBody.Children.OfType<WrapPanel>().Single().Children.Count==2,"failed message lacks retry/delete");
            var confirmed=new SocialMessage(owner,expired.Id,friend.Id,expired.Body,"text",DateTimeOffset.UtcNow,42);
            Set("_socialMessages",(IReadOnlyList<SocialMessage>)new[]{confirmed});Invoke("RenderSocialMessages");
            Check(Control<StackPanel>("FriendsMessagesPanel").Children.Count==1,"late server acknowledgement rendered duplicate");
            Set("_socialMessages",(IReadOnlyList<SocialMessage>)Array.Empty<SocialMessage>());Set("_socialDeliveryBusy",true);
            await (Task)Invoke("ChangePendingSocialAsync",failed,true)!;
            var retried=(await box.ReadAsync(owner)).Single();Check(retried.Id==expired.Id && retried.Error=="","UI retry changed UUID/did not reset failure");
            await (Task)Invoke("ChangePendingSocialAsync",retried,false)!;Check((await box.ReadAsync(owner)).Count==0,"UI delete failed");
            Invoke("ShowSocialDetails",friend);Check(Control<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible && Control<TextBlock>("SocialDetailsChannel").Text.Contains(language=="ru"?"Бета":"Beta"),"details missing channel");
            Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)Array.Empty<SocialPlayer>());Invoke("RenderSocialRows");
            Check(Control<Border>("SocialDetailsOverlay").Visibility==Visibility.Collapsed && Control<TextBlock>("SocialDetailsName").Text=="" && Control<StackPanel>("SocialDetailsComponents").Children.Count==0,"removed friend details retained");
            Console.WriteLine($"CHAT PRESENTATION PASS {checks} {language}: full-height, grow/shrink/wrap/cap, keys, icons, whole-row menu hit areas, no transparent hover, avatars, inline deadline/retry/delete/dedup, private details");
        }
        try
        {
            SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(w.Dispatcher));
            var task=Scenario();var frame=new DispatcherFrame();var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(20)};
            timer.Tick+=(_,_)=>frame.Continue=false;timer.Start();_=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(new Action(()=>frame.Continue=false)));
            if(!task.IsCompleted)Dispatcher.PushFrame(frame);timer.Stop();if(!task.IsCompleted)throw new TimeoutException("Chat checks");task.GetAwaiter().GetResult();
        }
        finally{w.Close();SynchronizationContext.SetSynchronizationContext(null);}
    }
}
