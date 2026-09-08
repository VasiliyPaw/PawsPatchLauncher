using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class HistoryResourceChecks
{
    private const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
    private static object? Call(MainWindow w,string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,Flags)!.Invoke(w,args);
    private static T Field<T>(MainWindow w,string name)=>(T)typeof(MainWindow).GetField(name,Flags)!.GetValue(w)!;
    private static void Set(MainWindow w,string name,object? value)=>typeof(MainWindow).GetField(name,Flags)!.SetValue(w,value);
    private static IEnumerable<T> Desc<T>(DependencyObject node) where T:DependencyObject
    {if(node is T t)yield return t;for(var i=0;i<VisualTreeHelper.GetChildrenCount(node);i++)foreach(var child in Desc<T>(VisualTreeHelper.GetChild(node,i)))yield return child;}
    internal static void PopulateResources(MainWindow w)
    {
        AdminChecks.Populate(w,"status");Set(w,"_adminSection","resources");Call(w,"BuildAdminLayout");
        using var data=JsonDocument.Parse(JsonSerializer.Serialize(new{checked_at=DateTimeOffset.UtcNow,database_bytes=13000000,messages_count=5000,messages_bytes=1300000,offers_bytes=81920,
            storage_bytes=1500000,saves_bytes=1400000,avatars_bytes=100000,removed_messages=5000,database_reference_limit=524288000,storage_reference_limit=1073741824,provider_metrics=Array.Empty<object>()}));
        Call(w,"RenderAdminResources",data.RootElement);
    }
    internal static void PopulateHistory(MainWindow w)
    {
        var peer=SocialHubChecks.Populate(w)[0].Id;Call(w,"ResetBroadcast");
        var owner=Guid.Parse(Field<AccountService>(w,"_account").UserId);
        Set(w,"_socialPeer",peer);Set(w,"_socialMessages",(IReadOnlyList<SocialMessage>)Array.Empty<SocialMessage>());
        Set(w,"_socialOffers",(IReadOnlyList<SocialOffer>)Array.Empty<SocialOffer>());
        Set(w,"_socialPending",(IReadOnlyList<PendingSocialMessage>)Array.Empty<PendingSocialMessage>());
        Call(w,"ResetSocialHistory");Call(w,"EnsureHistoryScope");
        var ru=Field<PawsPatchLauncher.Localization>(w,"_text").Language=="ru";
        var time=DateTimeOffset.UtcNow.AddMinutes(-30);
        var messages=Enumerable.Range(1,50).Select(i=>new SocialMessage(i%2==0?owner:peer,Guid.NewGuid(),i%2==0?peer:owner,
            ru?(i%2==0?"Хорошо, проверю конфигурацию и отправлю сейв.":"Давай попробуем вместе — я уже подготовил игру."):(i%2==0?"Okay, I will check the configuration and send a save.":"Let us try it together — my game is ready."),
            "text",time.AddSeconds(i*30),i)).ToArray();
        Call(w,"MergeHistoryPage",new SocialMessagePage(messages,[],true,0,false),false);Call(w,"RenderSocialMessages");
    }
    internal static void Run(string language)
    {
        var w=new MainWindow{Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,Width=1050,Height=680,WindowStartupLocation=WindowStartupLocation.Manual};
        int n=0;void Check(bool ok,string message){n++;if(!ok)throw new Exception("History/resources UI: "+message);}
        T C<T>(string name)=>(T)w.FindName(name);
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>(w,"_text").SetLanguage(language);Call(w,"ApplyLanguage");
            PopulateResources(w);w.UpdateLayout();
            var tabs=Desc<Button>(C<StackPanel>("AdminPanel")).Where(b=>b.Tag is string).Select(b=>b.Tag).ToArray();
            Check(tabs.SequenceEqual(new[]{"status","resources","users","bans","deleted"}),"resource tab not second");
            Check(Field<TextBox>(w,"_adminSearch").Visibility==Visibility.Collapsed,"resources has irrelevant search");
            Check(Field<StackPanel>(w,"_adminRows").Children.Count==7,"resource card count");
            Check(Desc<ProgressBar>(Field<StackPanel>(w,"_adminRows")).Count()==2,"unavailable provider usage has fabricated progress");
            Check(Desc<TextBlock>(Field<StackPanel>(w,"_adminRows")).Count(t=>t.Text==(language=="ru"?"Нет данных":"No data"))==3,"provider missing state");
            using(var stale=JsonDocument.Parse(JsonSerializer.Serialize(new{checked_at=DateTimeOffset.UtcNow,provider_metrics=new[]{new{metric="emails_daily",used=95,quota=100,checked_at=DateTimeOffset.UtcNow.AddHours(-2)}}})))Call(w,"RenderAdminResources",stale.RootElement);
            Check(Desc<TextBlock>(Field<StackPanel>(w,"_adminRows")).Any(t=>t.Text.Contains(language=="ru"?"устарели":"Stale")),"old usage shown as current");
            Call(w,"RenderAdminStatusFailure");Check(Field<StackPanel>(w,"_adminRows").Children.Count==1,"failed resource request retains old green cards");
            MonitorChecks.Run(w,language,Check);
            var friends=SocialHubChecks.Populate(w);Call(w,"ResetBroadcast");var peer=friends[0].Id;
            var owner=Guid.Parse(Field<AccountService>(w,"_account").UserId);
            Set(w,"_socialPeer",peer);Set(w,"_socialMessages",(IReadOnlyList<SocialMessage>)Array.Empty<SocialMessage>());
            Set(w,"_socialPending",(IReadOnlyList<PendingSocialMessage>)Array.Empty<PendingSocialMessage>());
            Set(w,"_socialOffers",(IReadOnlyList<SocialOffer>)Array.Empty<SocialOffer>());
            Call(w,"SetActivePage","friends");Call(w,"ResetSocialHistory");Call(w,"EnsureHistoryScope");
            var time=DateTimeOffset.UtcNow.AddDays(-1);
            SocialMessage Message(int ordinal)=>new(owner,Guid.Parse($"50000000-0000-0000-0000-{ordinal:000000000000}"),peer,"Message "+ordinal,"text",time,ordinal);
            SocialMessagePage Page(int start,long revision=0)=>new(Enumerable.Range(start,50).Select(Message).ToArray(),[],start>1,revision,revision>0);
            Set(w,"_historyReadOverride",(Func<Guid,SocialMessage?,Task<SocialMessagePage>>)((_,before)=>Task.FromResult(before is null?Page(951):Page((int)before.Ordinal-50))));
            Check((bool)Call(w,"MergeHistoryPage",Page(951),false)!,"first page rejected");Call(w,"RenderSocialMessages");w.UpdateLayout();
            C<ScrollViewer>("FriendsChatScroll").ScrollToVerticalOffset(150);w.UpdateLayout();
            var anchor=Message(953).MessageId;
            var row=C<StackPanel>("FriendsMessagesPanel").Children.OfType<FrameworkElement>().Single(e=>Equals(e.Tag,anchor));
            var beforeY=row.TranslatePoint(new Point(),C<ScrollViewer>("FriendsChatScroll")).Y;
            await (Task)Call(w,"NavigateHistoryAsync",true)!;w.UpdateLayout();
            Check(Field<IReadOnlyList<SocialMessage>>(w,"_socialMessages").Count==100,"older page replaced existing messages");
            row=C<StackPanel>("FriendsMessagesPanel").Children.OfType<FrameworkElement>().Single(e=>Equals(e.Tag,anchor));
            Check(Math.Abs(row.TranslatePoint(new Point(),C<ScrollViewer>("FriendsChatScroll")).Y-beforeY)<3,"prepend changed visible anchor");
            for(var i=0;i<5;i++)await (Task)Call(w,"NavigateHistoryAsync",true)!;
            Check(Field<IReadOnlyList<SocialMessage>>(w,"_socialMessages").Count==350,"history cache lost pages");
            Check(C<StackPanel>("FriendsMessagesPanel").Children.Count<=200,"unbounded WPF message elements");
            Check(C<Button>("FriendsHistoryNewer").Visibility==Visibility.Visible,"no route back through cached pages");
            Check(!(bool)typeof(MainWindow).GetProperty("HistoryAtNewest",Flags)!.GetValue(w)!,"old window eligible for read acknowledgement");
            C<ScrollViewer>("FriendsChatScroll").ScrollToTop();w.UpdateLayout();Call(w,"RefreshHistoryJump");
            Check(C<Button>("FriendsChatJumpBottom").Visibility==Visibility.Visible&&C<Button>("FriendsChatJumpBottom").HorizontalAlignment==HorizontalAlignment.Center,"floating bottom action missing / alignment");
            Set(w,"_historyReadOverride",(Func<Guid,SocialMessage?,Task<SocialMessagePage>>)((_,_)=>throw new Exception("Jump must work offline without a request")));
            await (Task)Call(w,"JumpToLatestHistoryAsync")!;await Task.Delay(450);w.UpdateLayout();
            Check(Field<int>(w,"_historyViewStart")==150,"jump does not show latest bounded window");
            Check(C<ScrollViewer>("FriendsChatScroll").ScrollableHeight-C<ScrollViewer>("FriendsChatScroll").VerticalOffset<2,"jump did not reach bottom");
            // Exercise the actual XAML event rather than calling its helper; emulate late media layout.
            var chat=C<ScrollViewer>("FriendsChatScroll");chat.ScrollToVerticalOffset(150);w.UpdateLayout();Call(w,"RefreshHistoryJump");
            var jump=C<Button>("FriendsChatJumpBottom");Check(jump.IsEnabled,"visible jump button disabled");
            var unchangedRow=C<StackPanel>("FriendsMessagesPanel").Children[0];
            Check(jump.Margin.Bottom==20,"jump button position was changed instead of appearance threshold");
            jump.RaiseEvent(new RoutedEventArgs(Button.ClickEvent,jump));
            Check(ReferenceEquals(unchangedRow,C<StackPanel>("FriendsMessagesPanel").Children[0]),"jump recreates unchanged chat/media");
            await Task.Delay(45);
            C<StackPanel>("FriendsMessagesPanel").Children.OfType<FrameworkElement>().Last().Height=400;
            w.UpdateLayout();await Task.Delay(700);w.UpdateLayout();
            Check(chat.ScrollableHeight-chat.VerticalOffset<2,"button animation aborted by delayed image layout");
            chat.ScrollToVerticalOffset(150);w.UpdateLayout();Call(w,"RefreshHistoryJump");
            jump.Focus();jump.RaiseEvent(new RoutedEventArgs(Button.ClickEvent,jump));
            await Task.Delay(40);
            chat.RaiseEvent(new System.Windows.Input.KeyEventArgs(System.Windows.Input.Keyboard.PrimaryDevice,
                PresentationSource.FromVisual(chat)!,Environment.TickCount,System.Windows.Input.Key.Home){RoutedEvent=System.Windows.Input.Keyboard.PreviewKeyDownEvent});
            chat.ScrollToVerticalOffset(100);w.UpdateLayout();await Task.Delay(430);w.UpdateLayout();
            Check(!SmoothScroll.IsAnimating(chat)&&Math.Abs(chat.VerticalOffset-100)<2,"user input cannot cancel jump");
            jump.RaiseEvent(new RoutedEventArgs(Button.ClickEvent,jump));await Task.Delay(450);w.UpdateLayout();
            Check(chat.ScrollableHeight-chat.VerticalOffset<2,"second button click after cancellation fails");
            chat.ScrollToVerticalOffset(chat.ScrollableHeight-150);w.UpdateLayout();Call(w,"RefreshHistoryJump");await Task.Delay(280);
            Check(jump.Visibility==Visibility.Collapsed,"jump appears too near the bottom");
            chat.ScrollToVerticalOffset(chat.ScrollableHeight-240);w.UpdateLayout();Call(w,"RefreshHistoryJump");
            Check(jump.Visibility==Visibility.Visible,"jump does not appear above threshold");
            jump.RaiseEvent(new RoutedEventArgs(Button.ClickEvent,jump));await Task.Delay(450);w.UpdateLayout();
            Call(w,"AppendSentHistoryMessage",Message(1001));Call(w,"RenderSocialMessages");w.UpdateLayout();
            Check(Field<int>(w,"_historyViewStart")==151&&C<StackPanel>("FriendsMessagesPanel").Children.OfType<FrameworkElement>().Any(e=>Equals(e.Tag,Message(1001).MessageId)),"send ACK disappears at 200-message boundary");
            Check(!(bool)Call(w,"MergeHistoryPage",Page(551,1),true)!,"stale older page survives retention revision");
            Call(w,"MergeHistoryPage",Page(951,1),false);Check(Field<IReadOnlyList<SocialMessage>>(w,"_socialMessages").Count==50,"trim leaves deleted cached messages");
            Check(!(bool)Call(w,"MergeHistoryPage",Page(951),false)!&&Field<long>(w,"_historyRevision")==1,"delayed old response rolls back retention");
            Call(w,"MergeHistoryPage",new SocialMessagePage([],[],false,1,true),true);Call(w,"RenderSocialMessages");
            Check(C<TextBlock>("FriendsHistoryNotice").Visibility==Visibility.Visible,"trimmed-history explanation missing");
            Call(w,"ResetSocialHistory");Check(Field<string?>(w,"_historyScope")==null&&Field<int>(w,"_historyViewStart")==0,"history owner reset");
        }
        try{w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();var timeout=new DispatcherTimer{Interval=TimeSpan.FromSeconds(45)};
            timeout.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);timeout.Start();Dispatcher.PushFrame(frame);timeout.Stop();if(!task.IsCompleted)throw new TimeoutException();task.GetAwaiter().GetResult();Console.WriteLine($"HISTORY / RESOURCES UI PASS {n} {language}: mock pages, retention, viewport anchor, bounded controls, animated bottom, quota states");}
        finally{w.Close();}
    }
}
