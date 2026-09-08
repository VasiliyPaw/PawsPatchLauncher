using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class UpdateRefreshChecks
{
    // Calls the real timer callback path with a held HTTP response, never a real server.
    private sealed class FeedHandler : HttpMessageHandler
    {
        internal TaskCompletionSource Gate = new(TaskCreationOptions.RunContinuationsAsynchronously);
        internal bool Fail;
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            await Gate.Task.WaitAsync(ct);
            return new HttpResponseMessage(Fail ? HttpStatusCode.ServiceUnavailable : HttpStatusCode.OK)
            { Content = new StringContent("{\"schemaVersion\":1,\"channel\":\"stable\"}") };
        }
    }

    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated smoke mode required.");
        var config = new LauncherConfiguration { FeedUrls = ["https://fixture.invalid/stable.json"], BetaFeedUrls = [],
            RequireSignedRemoteFeed = false, CacheRoot = Path.Combine(ActivityStore.Root, "refresh-fixture-" + Guid.NewGuid()) };
        using var handler = new FeedHandler(); using var http = new HttpClient(handler);
        var w = new MainWindow(config, new FeedClient(config, http)) { Left=-32000, Top=-32000,
            ShowActivated=false, ShowInTaskbar=false, Width=1050, Height=680, WindowStartupLocation=WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w,args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        T Control<T>(string name) => (T)w.FindName(name);
        int checks=0;
        void Check(bool value, string why) { checks++; if(!value)throw new Exception("Update refresh: "+why); }
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Invoke("ApplyLanguage");
            Field<UserSettings>("_settings").Channel="stable"; Field<UserSettings>("_settings").PinnedRelease=null;
            SocialChecks.Populate(w,"chat");
            w.Show(); w.UpdateLayout(); await Task.Delay(250);
            var rows=Control<StackPanel>("FriendsRowsPanel"); var messages=Control<StackPanel>("FriendsMessagesPanel");
            var row=rows.Children[0]; var message=messages.Children[0];
            var chat=Control<Border>("FriendsChatCard"); var height=chat.ActualHeight;
            var composer=Control<TextBox>("FriendsMessageInput"); composer.Text="draft stays"; composer.CaretIndex=5;
            var inputChanges=0; var socialChanges=0; var logoutChanges=0;
            composer.IsEnabledChanged+=(_,_)=>inputChanges++;
            Control<Button>("FriendsSendButton").IsEnabledChanged+=(_,_)=>socialChanges++;
            Control<Button>("AccountLogoutButton").IsEnabledChanged+=(_,_)=>logoutChanges++;
            for(var i=0;i<2;i++)
            {
                handler.Fail=i==1; handler.Gate=new(TaskCreationOptions.RunContinuationsAsynchronously);
                var task=(Task<bool>)Invoke("CheckFeedAsync",true)!;
                await Task.Delay(50); w.UpdateLayout();
                Check(!task.IsCompleted && Field<bool>("_checkingFeed"),"fake response was not held");
                Check(Math.Abs(chat.ActualHeight-height)<.1,"chat height changed while checking");
                handler.Gate.SetResult(); var success=await task; w.UpdateLayout();
                Check(success==(i==0),"unexpected feed outcome");
                Check(ReferenceEquals(row,rows.Children[0])&&ReferenceEquals(message,messages.Children[0]),"background update rebuilt chat");
                Check(Math.Abs(chat.ActualHeight-height)<.1,"chat resized after check");
                Check(composer.Text=="draft stays"&&composer.CaretIndex==5,"draft/caret lost");
            }
            Check(inputChanges==0&&socialChanges==0,"chat enabled state toggled");
            Check(logoutChanges==0,"background check dimmed sign-out");
            handler.Fail=false; handler.Gate=new(TaskCreationOptions.RunContinuationsAsynchronously);
            var superseded=(Task<bool>)Invoke("CheckFeedAsync",true)!;
            var confirmation=(Task<bool>)Invoke("ConfirmActionAsync","Fixture","body","details","details","Confirm")!;
            Check(!Field<bool>("_checkingFeed") && !confirmation.IsCompleted,"confirmation did not preempt background read");
            Check(!await superseded,"cancelled background check claimed success");
            await (Task)Invoke("CompleteConfirmationAsync",false)!;
            Check(!await confirmation,"fixture confirmation accepted");
            handler.Gate=new(TaskCreationOptions.RunContinuationsAsynchronously);
            var oldRead=(Task<bool>)Invoke("CheckFeedAsync",true)!;
            var manual=(Task<bool>)Invoke("CheckFeedAsync",false)!;
            Check(Field<bool>("_checkingFeed") && Field<bool>("_busy"),"manual check did not reserve UI");
            Check(!await oldRead && Field<bool>("_checkingFeed"),"old finally cleared new check's state");
            handler.Gate.SetResult(); Check(await manual && !Field<bool>("_checkingFeed") && !Field<bool>("_busy"),"manual completion failed");
            Check(ReferenceEquals(message,messages.Children[0]),"manual refresh rebuilt unchanged chat");
            Invoke("SetActivePage","home"); await Task.Delay(220); w.UpdateLayout();
            var news=Control<StackPanel>("NewsEntriesPanel").Children[0];
            var newsHeight=Control<ScrollViewer>("NewsScrollViewer").ActualHeight;
            handler.Gate=new(TaskCreationOptions.RunContinuationsAsynchronously);
            var homeRead=(Task<bool>)Invoke("CheckFeedAsync",true)!; await Task.Delay(35);w.UpdateLayout();
            Check(Control<ProgressBar>("OperationProgress").Visibility==Visibility.Collapsed,"background read shows progress");
            Check(Math.Abs(newsHeight-Control<ScrollViewer>("NewsScrollViewer").ActualHeight)<.1,"background read resizes history");
            handler.Gate.SetResult();Check(await homeRead,"Home feed check failed");w.UpdateLayout();
            Check(ReferenceEquals(news,Control<StackPanel>("NewsEntriesPanel").Children[0]),"unchanged history rebuilt");
            Console.WriteLine($"UPDATE REFRESH UI PASS {checks} {language}: background success/failure without dimming or chat changes; confirmation/manual preemption; stale callbacks discarded; no real network/account/game");
        }
        try
        {
            var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame=new DispatcherFrame(); var timer=new DispatcherTimer {Interval=TimeSpan.FromSeconds(20)};
            timer.Tick+=(_,_)=>frame.Continue=false;
            task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start(); Dispatcher.PushFrame(frame); timer.Stop();
            if(!task.IsCompleted)throw new TimeoutException("Update refresh test timed out.");
            task.GetAwaiter().GetResult();
        }
        finally {w.Close();}
    }
}
