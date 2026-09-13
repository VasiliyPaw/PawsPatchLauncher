using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;
namespace PreviewRenderer;
internal static class ChangelogChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Smoke test required.");
        var window = new MainWindow { Left=-32000,Top=-32000,Width=1050,Height=680,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual };
        const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(window,args);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(window)!;
        void Set(string name,object value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(window,value);
        T C<T>(string name)=>(T)window.FindName(name);
        int checks=0; void Check(bool value,string message){if(!value)throw new Exception(message);checks++;}
        Task Switch(string subject,string source,string branch)=>(Task)Call("SwitchHistoryAsync",subject,source,branch)!;
        string Heading()=>((StackPanel)((Border)C<StackPanel>("NewsEntriesPanel").Children[0]).Child).Children.OfType<TextBlock>().Skip(1).First().Text;
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);
            var settings=Field<UserSettings>("_settings");settings.Mod=GameMod.ArcaneWars;settings.Channel="stable";
            var stable=new ChannelManifest {Channel="stable",PublishedAt="2030-09-10"};
            var beta=new ChannelManifest {Channel="beta",PublishedAt="2030-09-10"};
            foreach(var feed in new[]{stable,beta}) foreach(var category in new[]{"patch","launcher","mod"})
                for(int i=0;i<8;i++)feed.Changelog.Add(new(){Category=category,Mods=[GameMod.ArcaneWars],Version=i.ToString(),PublishedAt="2026-09-10",Title=new(){Ru=category+" RU "+i,En=category+" EN "+i},Body=new(){Ru=string.Concat(Enumerable.Repeat("Длинные изменения. ",80)),En=string.Concat(Enumerable.Repeat("Long change details. ",80))}});
            Set("_channel",stable);Set("_latestChannel",stable);
            var remember=typeof(FeedClient).GetMethod("RememberChannel",flags)!;remember.Invoke(Field<FeedClient>("_feedClient"),[stable]);remember.Invoke(Field<FeedClient>("_feedClient"),[beta]);
            Call("ApplyLanguage");Call("SetActivePage","home");window.UpdateLayout();await Task.Delay(200);
            Check(Field<string>("_historySubject")==GameMod.ArcaneWars&&Field<string>("_historyBranch")=="stable","default is not selected mod/channel");
            Check(C<ComboBox>("HistorySubjectCombo").Items.Count==4&&C<ComboBox>("HistorySourceCombo").Items.Count==3,"missing filters");
            var scroll=C<ScrollViewer>("NewsScrollViewer");
            var before=Heading();var change=Switch("launcher","all","stable");
            if(SystemParameters.ClientAreaAnimation){Check(scroll.HasAnimatedProperties&&Field<bool>("_changelogTransitionPending"),"fade animation not attached");Check(Heading()==before,"content replaced before transition");}
            await change;await Task.Delay(220);
            Check(Heading().StartsWith("launcher"),"wrong source rendered");
            Check(C<ComboBox>("HistorySourceCombo").Visibility==Visibility.Collapsed&&C<ComboBox>("HistoryBranchCombo").Visibility==Visibility.Collapsed,"launcher has patch filters");
            scroll.ScrollToVerticalOffset(80);window.UpdateLayout();var offset=scroll.VerticalOffset;await Switch("launcher","all","stable");Check(scroll.VerticalOffset==offset&&scroll.Opacity==1,"same selection resets reading");
            await Switch(GameMod.ArcaneWars,"mod","beta");await Task.Delay(220);
            Check(Heading().StartsWith("mod")&&C<ComboBox>("HistoryBranchCombo").Visibility==Visibility.Collapsed,"author history depends on patch branch");
            var card=(StackPanel)((Border)C<StackPanel>("NewsEntriesPanel").Children[0]).Child;
            var body=card.Children.OfType<TextBlock>().Last();var button=card.Children.OfType<Button>().Single();var shortLength=body.Text.Length;
            button.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));Check(body.Text.Length>shortLength,"expand lost full release notes");
            button.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));Check(body.Text.Length==shortLength,"collapse failed");
            var a=Switch("launcher","all","stable");await Task.Delay(15);var b=Switch(GameMod.ArcaneWars,"patch","beta");await Task.WhenAll(a,b);await Task.Delay(220);
            Check(Field<string>("_historySource")=="patch"&&Heading().StartsWith("patch")&&scroll.Opacity==1,"rapid filters restored stale content");
            await Switch(GameMod.ArcaneWars,"patch","all");await Task.Delay(220);
            Check(C<StackPanel>("NewsEntriesPanel").Children.Count==8,"identical release notes duplicated across channels");
            settings.Mod=GameMod.Immortals;settings.Channel="stable";Call("RefreshNews");
            Check(Field<string>("_historySubject")==GameMod.Immortals,"changing active mod did not reset history");
            await Switch(GameMod.Immortals,"mod","all");await Task.Delay(220);
            Check(Heading().Contains("Immortals"),"offline overview missing");
            Check(settings.Mod==GameMod.Immortals&&settings.Channel=="stable","history changed game settings");
            await Switch(GameMod.Vanilla,"mod","all");await Task.Delay(220);
            Check(C<StackPanel>("NewsEntriesPanel").Children[0] is TextBlock,"missing history has no honest empty state");
            var pending=Switch("launcher","all","stable");Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language=="ru"?"en":"ru");Call("ApplyLanguage");await pending;await Task.Delay(220);
            Check(scroll.Opacity==1&&!Field<bool>("_changelogTransitionPending"),"language refresh left stale transition");
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Call("ApplyLanguage");window.UpdateLayout();
            foreach(var name in new[]{"HistorySubjectCombo","HistorySourceCombo","HistoryBranchCombo"}) {var c=C<ComboBox>(name);Check(c.Visibility==Visibility.Collapsed || c.ActualWidth>0,"visible filter has no width");}
            Console.WriteLine($"TIMELINE UI PASS {checks} {language}: default scope, filters, author notes, no duplicates, expand/collapse, animation, rapid selection, refresh and settings isolation");
        }
        try
        {
            window.Show();var task=window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(30)};
            timer.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>window.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);timer.Start();try{Dispatcher.PushFrame(frame);}finally{timer.Stop();}
            if(!task.IsCompleted)throw new TimeoutException("timeline UI");task.GetAwaiter().GetResult();
        }
        finally {window.Close();}
    }
}
