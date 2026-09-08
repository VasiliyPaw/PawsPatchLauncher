using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class ArrivalPolishChecks
{
    internal static void Run(string language)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Smoke fixtures only.");
        var w=new MainWindow {Left=-32000,Top=-32000,Width=1050,Height=680,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual};
        const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Invoke(string method,params object?[] args)=>typeof(MainWindow).GetMethod(method,flags)!.Invoke(w,args);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T Control<T>(string name)=>(T)w.FindName(name);
        int checks=0;
        void Check(bool value,string why){checks++;if(!value)throw new Exception("Arrival polish: "+why);}
        async Task Layout(){w.UpdateLayout();await w.Dispatcher.InvokeAsync(()=>{},DispatcherPriority.ContextIdle);}
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Invoke("ApplyLanguage");
            var snapshot=new ArrivalSnapshot<int>();
            Check(snapshot.Observe("chat-a",[],false).Count==0,"preload not quiet");
            Check(snapshot.Observe("chat-a",[1,2],true).Count==0,"history animated");
            Check(snapshot.Observe("chat-a",[1,2,3],true).SetEquals([3]),"new key not detected");
            Check(snapshot.Observe("chat-a",[1,2,3],true).Count==0,"ACK/retry replayed");
            Check(snapshot.Observe("chat-b",[4,5],true).Count==0,"other chat history animated");
            Check(snapshot.Observe("chat-b",[],true).Count==0,"removal counted as arrival");
            Check(snapshot.Observe("chat-b",[6],true).SetEquals([6]),"first message in empty chat lost");
            SocialChecks.Populate(w,"chat");w.Show();await Layout();await Task.Delay(250);
            var main=Control<Grid>("MainBody");var logo=Control<Image>("BrandMark");
            foreach(var width in new[]{1050d,1440d})
            {
                w.Width=width;
                foreach(var page in new[]{"home","modules","settings","about","account","friends"})
                {
                    Invoke("SetActivePage",page);await Layout();
                    var split=page is "home" or "friends";
                    Check(main.ColumnDefinitions[0].Width.Value==228&&logo.Width==108&&logo.Height==108,"sidebar/logo changed");
                    Check(Control<Border>("ChangelogCard").Visibility==(page=="home"?Visibility.Visible:Visibility.Collapsed),"history visible off Home: "+page);
                    Check(Grid.GetColumnSpan(Control<ScrollViewer>("MainOptionsScroll"))==(split?1:3),"content did not reclaim width: "+page);
                    if(!split)Check(Control<ScrollViewer>("MainOptionsScroll").ActualWidth>=Control<Grid>("WorkspaceBody").ActualWidth-1,"empty right column: "+page);
                }
            }
            Invoke("SetActivePage","home");Invoke("SetActivePage","account");await Task.Delay(220);
            Check(Control<Border>("ChangelogCard").Visibility==Visibility.Collapsed,"queued reveal resurrected history");
            Invoke("SetBusy",true,"Fixture work");await Layout();
            Check(Control<Border>("OperationStatusPanel").IsVisible&&Control<ProgressBar>("OperationProgress").IsVisible,"off-Home progress disappeared");
            Check(Control<ContentControl>("OperationFooterHost").Content==Control<Border>("OperationStatusPanel"),"active operation not moved to footer");
            Invoke("SetBusy",false,null);await Layout();
            Check(!Control<Border>("OperationStatusPanel").IsVisible,"idle footer wastes height");
            Invoke("SetActivePage","home");await Layout();
            Check(Control<Border>("OperationStatusPanel").Parent==Control<Grid>("ChangelogContentGrid"),"Home status not restored");

            Invoke("SetActivePage","friends");await Layout();await Task.Delay(250);
            var messages=Control<StackPanel>("FriendsMessagesPanel");
            Check(!messages.Children.OfType<FrameworkElement>().Any(ArrivalMotion.IsRunning),"existing history animates on navigation");
            var owner=Guid.Parse(Field<AccountService>("_account").UserId);var peer=Field<Guid?>("_socialPeer")!.Value;
            var old=Field<IReadOnlyList<SocialMessage>>("_socialMessages");
            var added=new SocialMessage(peer,Guid.NewGuid(),owner,"New arrival","text",DateTimeOffset.UtcNow);
            Set("_socialMessages",old.Append(added).ToArray());Invoke("RenderSocialMessages");await Layout();
            var newest=(FrameworkElement)messages.Children[^1];
            Check(ArrivalMotion.IsRunning(newest)==SystemParameters.ClientAreaAnimation,"new message missing entrance");
            Check(!messages.Children.OfType<FrameworkElement>().SkipLast(1).Any(ArrivalMotion.IsRunning),"old messages replay entrance");
            await Task.Delay(280);Check(!ArrivalMotion.IsRunning(newest)&&Math.Abs(newest.Opacity-1)<.001,"entrance did not settle");
            Invoke("RenderSocialMessages");await Layout();
            Check(ReferenceEquals(newest,messages.Children[^1])&&!ArrivalMotion.IsRunning(newest),"identical poll replay/rebuild");
            var pending=Field<IReadOnlyList<PendingSocialMessage>>("_socialPending")[0];
            Set("_socialPending",Array.Empty<PendingSocialMessage>());
            Set("_socialMessages",old.Append(added).Append(new SocialMessage(owner,pending.Id,peer,pending.Body,"text",pending.CreatedAt)).ToArray());
            Invoke("RenderSocialMessages");await Layout();
            Check(!messages.Children.OfType<FrameworkElement>().Any(ArrivalMotion.IsRunning),"pending-to-sent reanimated");
            Invoke("ApplyLanguage");await Layout();
            Check(!messages.Children.OfType<FrameworkElement>().Any(ArrivalMotion.IsRunning),"language refresh reanimated messages");

            // Empty loaded conversations establish a baseline before the first real arrival.
            Set("_socialLoadedChat",null);Set("_socialMessages",Array.Empty<SocialMessage>());Invoke("RenderSocialMessages");
            Set("_socialLoadedChat",owner+"|"+peer);Invoke("RenderSocialMessages");
            Set("_socialMessages",new[]{added});Invoke("RenderSocialMessages");await Layout();
            Check(ArrivalMotion.IsRunning((FrameworkElement)messages.Children[0])==SystemParameters.ClientAreaAnimation,"first live message in empty chat stayed quiet");
            await Task.Delay(280);
            Invoke("SwitchSocialSection","requests");await Layout();await Task.Delay(220);
            var rows=Control<StackPanel>("FriendsRowsPanel");
            var player=new SocialPlayer(Guid.NewGuid(),"new_request","incoming");
            var players=Field<IReadOnlyList<SocialPlayer>>("_socialPlayers");
            Set("_socialPlayers",players.Append(player).ToArray());Invoke("RenderSocialRows");Invoke("RenderSocialNotifications");await Layout();
            var request=(FrameworkElement)rows.Children[^1];
            Check(ArrivalMotion.IsRunning(request)==SystemParameters.ClientAreaAnimation,"new request missing entrance");
            Check(!ArrivalMotion.IsRunning((FrameworkElement)rows.Children[0]),"old request reanimated");
            Check(ArrivalMotion.IsRunning(Control<Border>("FriendsRequestsBadge"))==SystemParameters.ClientAreaAnimation,"request badge did not pulse");
            await Task.Delay(400);Invoke("RenderSocialNotifications");Invoke("RenderSocialRows");await Layout();
            Check(!ArrivalMotion.IsRunning(Control<Border>("FriendsRequestsBadge"))&&!ArrivalMotion.IsRunning(request),"identical counters replayed pulse");
            Invoke("SetActivePage","home");await Layout();await Task.Delay(220);
            Check(!ArrivalMotion.IsRunning(Control<Border>("FriendsNavBadge")),"navigation pulse without arrival");
            Set("_socialPlayers",players.Append(player).Append(new SocialPlayer(Guid.NewGuid(),"another","incoming")).ToArray());
            Invoke("RenderSocialRows");Invoke("RenderSocialNotifications");await Layout();
            Check(ArrivalMotion.IsRunning(Control<Border>("FriendsNavBadge"))==SystemParameters.ClientAreaAnimation,"hidden Friends badge did not pulse");
            Check(!rows.Children.OfType<FrameworkElement>().Any(ArrivalMotion.IsRunning),"hidden request cards animated");
            await Task.Delay(400);
            Set("_socialPlayers",players);Invoke("RenderSocialRows");Invoke("RenderSocialNotifications");await Layout();
            Check(!ArrivalMotion.IsRunning(Control<Border>("FriendsNavBadge")),"decreased counter pulsed");
            var brush=new SolidColorBrush(Colors.DarkRed);var badge=Control<Border>("FriendsNavBadge");badge.Background=brush;
            ArrivalMotion.Pulse(badge);Check(brush.Color==Colors.DarkRed,"shared source brush modified");
            await Task.Delay(400);Check(ReferenceEquals(badge.Background,brush)&&!ArrivalMotion.IsRunning(badge),"pulse failed to restore brush/stop");
            var faded=new Border {Width=20,Height=20,Opacity=.55};rows.Children.Add(faded);
            Invoke("SetActivePage","friends");await Layout();ArrivalMotion.Enter(faded);await Task.Delay(280);
            Check(Math.Abs(faded.Opacity-.55)<.001,"sending opacity lost");
            Console.WriteLine($"ARRIVAL POLISH PASS {checks} {language}: Home-only history/full-width pages; sidebar preserved; progress retained; arrivals/empty-history/ACKs/quiet polls; one-shot counters and cleanup; Windows animations={SystemParameters.ClientAreaAnimation}");
        }
        try
        {
            var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();var timer=new DispatcherTimer {Interval=TimeSpan.FromSeconds(25)};
            timer.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start();Dispatcher.PushFrame(frame);timer.Stop();if(!task.IsCompleted)throw new TimeoutException("Arrival polish timed out.");task.GetAwaiter().GetResult();
        }
        finally{w.Close();}
    }
}
