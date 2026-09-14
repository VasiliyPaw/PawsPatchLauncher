using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class GameActivityChecks
{
    internal static void Run(string language,string output)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated profile required");
        Directory.CreateDirectory(output);new SettingsStore().Save(new UserSettings{Language=language,ModNoticeSeen=true});
        var w=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null){Left=-32000,Top=-32000,Width=1050,Height=680,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual};
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        object? Call(string name,params object?[] values)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,values);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name)=>(T)w.FindName(name);
        var checks=0;void Check(bool ok,string why){if(!ok)throw new Exception("Game activity UI: "+why);checks++;}
        var peer=Guid.NewGuid();var profile=new GameParticipantProfile(peer,"fixture","Игрок / Player");
        var activity=new GameActivity("match",true,3702,192,256,Players:[new("p1","Game nickname",false,profile),new("p2","Computer",true),new("p3","Guest",false)]);
        var friend=new SocialPlayer(peer,"fixture","friend",Presence:"playing",PlayingSince:DateTimeOffset.UtcNow.AddMinutes(-90),DisplayName:"Игрок / Player",Activity:activity.Summary());
        var response=new GameActivityDetails(activity,DateTimeOffset.UtcNow);
        var calls=0;
        void ReadWith(Func<Guid,CancellationToken,Task<GameActivityDetails?>> read)=>Set("_gameActivityReadOverride",read);
        void Capture(string name)
        {
            w.UpdateLayout();var view=(FrameworkElement)w.Content;var bitmap=new RenderTargetBitmap((int)view.ActualWidth,(int)view.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(view);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var stream=File.Create(Path.Combine(output,name+"-"+language+".png"));encoder.Save(stream);
        }
        async Task Scenario()
        {
            Call("SetActivePage","friends");Set("_socialPlayers",(IReadOnlyList<SocialPlayer>)new[]{friend});Call("ShowSocialDetails",friend);
            Check(C<DockPanel>("SocialDetailsGameActivityRow").Visibility==Visibility.Visible,"missing summary row");
            Check(C<TextBlock>("SocialDetailsActivity").Text.Length>0,"original Playing duration disappeared");
            Check(C<Button>("SocialDetailsGameActivityButton").IsEnabled,"details button disabled");
            await Task.Delay(240);Capture("game-profile");
            ReadWith((_,_)=>{calls++;return Task.FromResult<GameActivityDetails?>(response);});
            await (Task)Call("ShowGameActivityAsync",peer)!;await Task.Delay(260);w.UpdateLayout();
            Check(calls==1&&C<Border>("GameActivityOverlay").Visibility==Visibility.Visible,"details load");
            Check(C<StackPanel>("GameActivityBody").Children.Count==8,"mode/time/map and three participants rendered");
            Check(C<Border>("GameActivityCard").ActualWidth<=570&&C<Border>("GameActivityCard").ActualHeight<=590,"compact card exceeds window");
            Check(Field<DispatcherTimer>("_gameActivityTimer").IsEnabled,"open details not refreshed");Capture("game-details");
            var sameRow=C<StackPanel>("GameActivityBody").Children[5];await (Task)Call("RefreshGameActivityAsync")!;
            Check(ReferenceEquals(sameRow,C<StackPanel>("GameActivityBody").Children[5]),"unchanged poll rebuilt participant rows");
            Call("CloseGameActivity");Check(!Field<DispatcherTimer>("_gameActivityTimer").IsEnabled,"closed details kept polling");
            await (Task)Call("ShowGameActivityAsync",peer)!;Check(calls==2,"reopening fresh details downloaded again");
            var overlay=C<Border>("GameActivityOverlay");
            var outside=new MouseButtonEventArgs(Mouse.PrimaryDevice,Environment.TickCount,MouseButton.Left){RoutedEvent=Mouse.PreviewMouseDownEvent};
            overlay.RaiseEvent(outside);await Task.Delay(280);
            Check(outside.Handled&&overlay.Visibility==Visibility.Collapsed&&C<Border>("SocialDetailsOverlay").Visibility==Visibility.Visible,"outside click closes only top layer and is consumed");
            var cache=Field<System.Collections.IDictionary>("_gameActivityCache");cache.Clear();
            var pending=new TaskCompletionSource<GameActivityDetails?>();ReadWith((_,_)=>pending.Task);
            var waiting=(Task)Call("ShowGameActivityAsync",peer)!;Check(C<TextBlock>("GameActivityStatus").Text.Contains(language=="ru"?"Загружаю":"Loading"),"loading state");
            Call("CloseGameActivity");pending.SetResult(response);await waiting;
            Check(overlay.Visibility==Visibility.Collapsed&&C<StackPanel>("GameActivityBody").Children.Count==0&&cache.Count==0,"late response reopened or cached closed details");
            ReadWith((_,_)=>Task.FromResult<GameActivityDetails?>(null));await (Task)Call("ShowGameActivityAsync",peer)!;
            Check(C<StackPanel>("GameActivityBody").Children.Count==0&&C<TextBlock>("GameActivityStatus").Text.Contains(language=="ru"?"недоступны":"unavailable"),"game exit leaves stale details");
            ReadWith((_,_)=>throw new System.Net.Http.HttpRequestException("fixture"));await (Task)Call("RefreshGameActivityAsync")!;
            Check(C<TextBlock>("GameActivityStatus").Text.Contains(language=="ru"?"ещё раз":"try again"),"transient failure lost retry feedback");
            ReadWith((_,_)=>Task.FromResult<GameActivityDetails?>(response with{Activity=activity with{Players=Enumerable.Range(0,64).Select(i=>new GameParticipant("p"+i,new string('W',80),i%2==0)).ToArray()}}));
            await (Task)Call("RefreshGameActivityAsync")!;await Task.Delay(260);w.UpdateLayout();
            Check(C<Border>("GameActivityCard").ActualHeight<=590&&C<Button>("GameActivityClose").IsVisible,"large roster exceeds card");
            Capture("game-details-long");Call("CloseSocialDetails");Check(overlay.Visibility==Visibility.Collapsed&&!Field<DispatcherTimer>("_gameActivityTimer").IsEnabled,"parent close leaves child alive");
            C<CheckBox>("ShareGameActivityToggle").IsChecked=false;Call("ShareGameActivityToggle_Click",C<CheckBox>("ShareGameActivityToggle"),new RoutedEventArgs());
            Check(!new SettingsStore().Load().ShareGameActivity,"sharing preference not persisted");
            Call("RenderSocialDetails",friend with{Activity=null});Check(C<DockPanel>("SocialDetailsGameActivityRow").Visibility==Visibility.Collapsed,"unknown activity invents state");
            Console.WriteLine($"GAME ACTIVITY UI PASS {checks} {language}");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(30)};
            timer.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start();try{Dispatcher.PushFrame(frame);}finally{timer.Stop();}if(!task.IsCompleted)throw new TimeoutException();task.GetAwaiter().GetResult();
        }
        finally { Set("_busy",false);w.Close(); }
    }
}
