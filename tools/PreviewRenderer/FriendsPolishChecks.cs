using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class FriendsPolishChecks
{
    internal static void Run(string language)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated fixture only");
        var w=new MainWindow {Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,
            WindowStartupLocation=WindowStartupLocation.Manual,Width=1050,Height=680};
        const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Invoke(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name)=>(T)w.FindName(name);
        int count=0;void Check(bool ok,string why){count++;if(!ok)throw new Exception("Friends polish: "+why);}
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Invoke("ApplyLanguage");
            var players=SocialHubChecks.Populate(w);Invoke("ResetBroadcast");
            var input=C<TextBox>("FriendsSearchInput");var rows=C<StackPanel>("FriendsRowsPanel");
            var initial=rows.Children.Count;Check(initial==9,"fixture friends missing");
            Invoke("FriendsSearch_Click",C<Button>("FriendsSearchButton"),new RoutedEventArgs());
            Check(C<Border>("FriendsSearchPanel").Visibility==Visibility.Visible,"search toggle did not reveal field");
            input.Text="@FRIEND0";Check(rows.Children.Count==1,"case-insensitive @username search");
            input.Text="ЛЕСНОЙ";Check(rows.Children.Count==1,"case-insensitive display name search");
            Set("_socialPeer",players[0].Id);C<TextBox>("FriendsMessageInput").Text="draft";
            input.Text="__absent__";
            Check(rows.Children.Count==0&&C<TextBlock>("FriendsListEmptyText").Text==(language=="ru"?"Никого не найдено":"No matches"),"empty search result");
            Check(Field<Guid?>("_socialPeer")==players[0].Id&&C<TextBox>("FriendsMessageInput").Text=="draft","filter destroyed selected chat/draft");
            input.Text="friend0";var row=rows.Children[0];Invoke("RenderSocialRows");
            Check(ReferenceEquals(row,rows.Children[0]),"identical poll rebuilt filtered row");
            Invoke("FriendsClearSearch_Click",C<Button>("FriendsClearSearchButton"),new RoutedEventArgs());
            Check(rows.Children.Count==initial&&input.Text=="","clear search");
            Invoke("FriendsShowAdd_Click",C<Button>("FriendsShowAddButton"),new RoutedEventArgs());w.UpdateLayout();
            Check(C<Border>("FriendsAddPanel").ActualHeight is >40 and <90,"add friend form is not compact");
            Check(C<Button>("FriendsAddButton").Content is LauncherIcon&&C<TextBox>("FriendsNicknameInput").ActualWidth>80,"compact form lost icon/input space");
            var extra=players.Concat(Enumerable.Range(0,4).Select(i=>players[0] with {Id=Guid.NewGuid(),Nickname="more"+i,DisplayName="Extra "+i})).ToArray();
            Invoke("OpenBroadcast",Field<AccountService>("_account").UserId,extra);
            Invoke("BroadcastKind_Click",C<Button>("BroadcastSaveTab"),new RoutedEventArgs());
            Set("_broadcastSave",new SaveTransferDescriptor("fixture.rsg",16,new string('a',64)));Set("_broadcastBytes",new byte[16]);Invoke("RefreshBroadcastKind");
            var boxes=C<StackPanel>("BroadcastRows").Children.OfType<CheckBox>().ToArray();
            foreach(var box in boxes.Take(10))box.IsChecked=true;
            Check(boxes.Count(b=>b.IsChecked==true)==10&&!boxes[10].IsEnabled&&C<Button>("BroadcastSendButton").IsEnabled,"ten save recipients/cap");
            Check(C<TextBlock>("BroadcastSummary").Text.Contains("10 / 10"),"save batch summary");
            boxes[9].IsChecked=false;Check(boxes[10].IsEnabled,"save capacity did not recover");
            Invoke("BroadcastKind_Click",C<Button>("BroadcastConfigTab"),new RoutedEventArgs());
            foreach(var box in boxes.Where(b=>b.IsEnabled).Take(5))box.IsChecked=true;
            Check(boxes.Count(b=>b.IsChecked==true)==5&&boxes.Count(b=>b.IsEnabled)==5,"config cap changed from five");
            Invoke("ResetBroadcast");Invoke("ClearToastStack");
            var state=Field<OperationFeedback>("_toast");var stack=C<StackPanel>("ToastStack");
            state.Show(()=>"first",duration:TimeSpan.FromMilliseconds(950));Invoke("RefreshToast");await Task.Delay(250);
            var oldRemaining=state.Remaining;Invoke("ShowToast",(Func<string>)(()=>"second"),false);
            await Task.Delay(260);
            Check(stack.Children.Count==2&&stack.Children[1]==C<Border>("ToastPanel"),"new toast not below old one");
            var first=(Border)stack.Children[0];var last=C<Border>("ToastPanel");
            Check(first.TranslatePoint(new Point(),w).Y+first.ActualHeight<=last.TranslatePoint(new Point(),w).Y+1,"stack overlaps after entrance");
            var snapshots=(System.Collections.IEnumerable)Field<object>("_archivedToasts");var snapshot=snapshots.Cast<object>().First();
            var archived=(OperationFeedback)snapshot.GetType().GetField("State")!.GetValue(snapshot)!;
            Check(archived.Message=="first"&&archived.Remaining<oldRemaining&&state.Message=="second","new toast replaced/renewed old lifetime");
            await Task.Delay(850);
            Check(stack.Children.Count==1&&last.Visibility==Visibility.Visible&&state.Message=="second","independent expiry removed wrong notification");
            Invoke("ShowToast",(Func<string>)(()=>"third"),true);await Task.Delay(260);
            var old=(Border)stack.Children[0];
            var close=((Grid)((Grid)old.Child).Children[0]).Children.OfType<Button>().Single();close.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            await Task.Delay(320);
            Check(stack.Children.Count==1&&state.Message=="third"&&state.Failed,"dismiss older toast removed newest");
            for(int i=0;i<4;i++)Invoke("ShowToast",(Func<string>)(()=>"burst"),false);
            Check(stack.Children.Count==5,"burst notices overwritten");Invoke("ClearToastStack");
            Check(stack.Children.Count==1&&last.Visibility==Visibility.Collapsed&&!Field<DispatcherTimer>("_toastTimer").IsEnabled,"stack clear leaked entries/timer");
            input.Text="private search";Set("_socialIdentity","different-owner");Invoke("RenderSocialIdentity");
            Check(input.Text==""&&C<Border>("FriendsSearchPanel").Visibility==Visibility.Collapsed,"account switch retained search");
            AccountChecks.Populate(w,"nickname");Invoke("RenderAccountCooldown");
            Check(C<TextBlock>("AccountCooldownText").Text.Contains("23:")&&!C<Button>("AccountEditorSubmitButton").IsEnabled,"daily cooldown lost hours or enabled rename");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();
            var timer=new DispatcherTimer {Interval=TimeSpan.FromSeconds(30)};timer.Tick+=(_,_)=>frame.Continue=false;
            task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start();Dispatcher.PushFrame(frame);timer.Stop();if(!task.IsCompleted)throw new TimeoutException("Friends polish checks timed out");
            task.GetAwaiter().GetResult();Console.WriteLine($"FRIENDS POLISH PASS {count} {language}: local search, compact add, per-kind caps, independent stacked toast expiry/dismiss/reflow/cleanup");
        }
        finally {w.Close();}
    }
}
