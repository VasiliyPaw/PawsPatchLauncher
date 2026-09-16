using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
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
        var activity=new GameActivity("match",true,3702,192,256,Players:[new("p1","Game nickname",false,profile,2,"#DDA443",Race:"human",Subrace:"royalist"),new("p2","Computer",true,Team:1,Color:"#478BDC",Race:"haroun",Subrace:"council"),new("p3","Guest",false,Team:2,Color:"#C45482")]);
        var friend=new SocialPlayer(peer,"fixture","friend",Presence:"playing",PlayingSince:DateTimeOffset.UtcNow.AddMinutes(-90),DisplayName:"Игрок / Player",Activity:activity.Summary());
        var response=new GameActivityDetails(activity,DateTimeOffset.UtcNow);
        var calls=0;
        IEnumerable<TextBlock> FactionLabels()=>C<StackPanel>("GameActivityBody").Children.OfType<StackPanel>()
            .SelectMany(g=>g.Children.OfType<Border>()).Select(b=>b.Child is Button button?(Grid)button.Content:(Grid)b.Child)
            .SelectMany(g=>g.Children.OfType<Grid>()).SelectMany(n=>n.Children.OfType<TextBlock>()).Where(t=>Equals(t.Tag,"factions"));
        IEnumerable<T> Visuals<T>(DependencyObject parent) where T:DependencyObject
        {
            for(var i=0;i<VisualTreeHelper.GetChildrenCount(parent);i++)
            {
                var child=VisualTreeHelper.GetChild(parent,i);if(child is T found)yield return found;
                foreach(var next in Visuals<T>(child))yield return next;
            }
        }
        void ReadWith(Func<Guid,CancellationToken,Task<GameActivityDetails?>> read)=>Set("_gameActivityReadOverride",read);
        void Capture(string name)
        {
            w.UpdateLayout();var view=(FrameworkElement)w.Content;var bitmap=new RenderTargetBitmap((int)view.ActualWidth,(int)view.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(view);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var stream=File.Create(Path.Combine(output,name+"-"+language+".png"));encoder.Save(stream);
            if(name=="game-details-roster")
            {
                var card=C<Border>("GameActivityCard");
                var drawing=new DrawingVisual();
                using(var dc=drawing.RenderOpen())dc.DrawRectangle(new VisualBrush(card),null,new Rect(0,0,card.ActualWidth,card.ActualHeight));
                var detail=new RenderTargetBitmap((int)Math.Ceiling(card.ActualWidth*1.5),(int)Math.Ceiling(card.ActualHeight*1.5),144,144,PixelFormats.Pbgra32);
                detail.Render(drawing);var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(detail));
                using var file=File.Create(Path.Combine(output,"match-card-"+language+".png"));png.Save(file);
                var heights=C<StackPanel>("GameActivityBody").Children.OfType<StackPanel>().SelectMany(g=>g.Children.OfType<Border>()).Select(b=>b.ActualHeight).Distinct();
                Console.WriteLine("PARTICIPANT CARD HEIGHT: "+string.Join(", ",heights));
            }
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
            var groups=C<StackPanel>("GameActivityBody").Children.OfType<StackPanel>().ToArray();
            Check(groups.Length==2&&Equals(groups[0].Tag,1)&&Equals(groups[1].Tag,2),"teams grouped in numeric order despite roster order");
            Check(groups[0].Children.OfType<Border>().Count()==1&&groups[1].Children.OfType<Border>().Count()==2,"all participants in their team");
            var labels=FactionLabels().ToArray();
            Check(labels.Length==3,"race/subrace line present for every participant");
            Check(labels.Any(t=>t.Text==(language=="ru"?"Люди · Роялисты":"Human · Royalist")),"native race/subrace names localized for viewer");
            Check(labels.Any(t=>t.Text==(language=="ru"?"Раса и фракция неизвестны":"Race and faction unknown")),"legacy missing values are not presented as random");
            var marker=(Grid)((Grid)((Button)groups[1].Children.OfType<Border>().First().Child).Content).Children[0];
            Check(((SolidColorBrush)((Border)marker.Children[1]).Background).Color==(Color)ColorConverter.ConvertFromString("#DDA443"),"player color preserved exactly");
            Check(C<Border>("GameActivityCard").ActualWidth<=570&&C<Border>("GameActivityCard").ActualHeight<=590,"compact card exceeds window");
            Check(Field<DispatcherTimer>("_gameActivityTimer").IsEnabled,"open details not refreshed");Capture("game-details");
            var rowHeights=groups.SelectMany(g=>g.Children.OfType<Border>()).Select(b=>b.ActualHeight).Distinct().ToArray();
            Check(rowHeights.Length==1,"participant cards differ in height");
            var beforeTick=Field<TextBlock>("_gameActivityElapsedText").Text;var beforeCalls=calls;
            var roster=groups[1].Children.OfType<Border>().First();
            await Task.Delay(1150);
            Check(Field<TextBlock>("_gameActivityElapsedText").Text!=beforeTick&&calls==beforeCalls,"local clock did not tick or performed network polling");
            Check(ReferenceEquals(roster,groups[1].Children.OfType<Border>().First()),"one-second clock rebuilt rows");
            var sameRow=C<StackPanel>("GameActivityBody").Children[5];await (Task)Call("RefreshGameActivityAsync")!;
            Check(ReferenceEquals(sameRow,C<StackPanel>("GameActivityBody").Children[5]),"unchanged poll rebuilt participant rows");
            Call("CloseGameActivity");Check(!Field<DispatcherTimer>("_gameActivityTimer").IsEnabled,"closed details kept polling");
            Check(!Field<DispatcherTimer>("_gameActivityClockTimer").IsEnabled,"closed details kept local clock running");
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
            var lobby=activity with{Phase="lobby",ElapsedSeconds=null,Players=[new("p1","Game nickname",false,profile,2,"#DDA443",Race:"random",Subrace:"random"),new("p2","Computer",true,Team:1,Race:"human",Subrace:"random")]};
            ReadWith((_,_)=>Task.FromResult<GameActivityDetails?>(response with{Activity=lobby}));
            await (Task)Call("RefreshGameActivityAsync")!;await Task.Delay(260);w.UpdateLayout();
            labels=FactionLabels().ToArray();
            Check(labels.Any(t=>t.Text==(language=="ru"?"Случайно · Случайно":"Random · Random")),"random race and subrace remain independent lobby choices");
            Check(labels.Any(t=>t.Text==(language=="ru"?"Люди · Случайно":"Human · Random")),"fixed race with random subrace is not replaced by match choice");
            Check(labels.All(t=>((string)t.ToolTip).Contains(language=="ru"?"Фракция: ":"Faction: ")),"race and subrace meanings exposed to hover and accessibility");
            Capture("game-details-lobby");
            var fullRoster=activity with{Players=Enumerable.Range(0,12).Select(i=>new GameParticipant("p"+i,i==0?"Game nickname":"Computer "+i,i!=0,i==0?profile:null,i/2+1,i%2==0?"#DDA443":"#478BDC",Race:new[]{"human","drauga","gauri","haroun","shadow","undead"}[i%6],Subrace:new[]{"royalist","nationalist","council","council","fallen","ceyah"}[i%6])).ToArray()};
            ReadWith((_,_)=>Task.FromResult<GameActivityDetails?>(response with{Activity=fullRoster}));
            await (Task)Call("RefreshGameActivityAsync")!;await Task.Delay(260);w.UpdateLayout();
            var scroll=C<ScrollViewer>("GameActivityScroll");var body=C<StackPanel>("GameActivityBody");
            Check(scroll.ComputedVerticalScrollBarVisibility==Visibility.Visible,"twelve players can scroll");
            Check(scroll.ViewportWidth-body.ActualWidth>=13.5,"participant cards leave readable gap before scrollbar");
            var bar=Visuals<ScrollBar>(scroll).Single(b=>b.Orientation==Orientation.Vertical);
            var right=bar.TranslatePoint(new Point(bar.ActualWidth,0),C<Border>("GameActivityCard")).X;
            Check(C<Border>("GameActivityCard").ActualWidth-right>=29,"scrollbar has room before right card edge");
            scroll.ScrollToBottom();w.UpdateLayout();Check(scroll.VerticalOffset>0,"last team is reachable");scroll.ScrollToTop();w.UpdateLayout();
            Capture("game-details-roster");
            ReadWith((_,_)=>Task.FromResult<GameActivityDetails?>(response with{Activity=activity with{Players=Enumerable.Range(0,64).Select(i=>new GameParticipant("p"+i,new string('W',80),i%2==0,Team:i%3==0?null:i%16+1,Color:i%2==0?"#000000":"#FFFFFF",Race:new string('r',80),Subrace:new string('s',80))).ToArray()}}));
            await (Task)Call("RefreshGameActivityAsync")!;await Task.Delay(260);w.UpdateLayout();
            Check(C<Border>("GameActivityCard").ActualHeight<=590&&C<Button>("GameActivityClose").IsVisible,"large roster exceeds card");
            Check(C<StackPanel>("GameActivityBody").Children.OfType<StackPanel>().Last().Tag is null,"unknown team kept together after numbered teams");
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
