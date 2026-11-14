using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class DiagnosticOptionsChecks
{
    internal static void Run(string language,string output)
    {
        if(!ActivityStore.IsSmokeTest||!ActivityStore.Root.StartsWith("G:"))throw new Exception("Isolated G: fixture required");
        Directory.CreateDirectory(output);new SettingsStore().Save(new UserSettings {Language=language,ModNoticeSeen=true});
        var w=new MainWindow(new LauncherConfiguration {FeedUrls=[],BetaFeedUrls=[],CacheRoot=Path.Combine(ActivityStore.Root,"cache")},null)
            {Width=1600,Height=1000,Left=-30000,Top=-30000,WindowStartupLocation=WindowStartupLocation.Manual,ShowActivated=false,ShowInTaskbar=false};
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        object? Call(string method,params object?[] args)=>typeof(MainWindow).GetMethod(method,flags)!.Invoke(w,args);
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        IEnumerable<T> Desc<T>(DependencyObject root)where T:DependencyObject
        {if(root is T match)yield return match;for(var i=0;i<VisualTreeHelper.GetChildrenCount(root);i++)foreach(var item in Desc<T>(VisualTreeHelper.GetChild(root,i)))yield return item;}
        T Named<T>(Window window,string name)where T:FrameworkElement=>Desc<T>(window).Single(c=>c.Name==name);
        var checks=0;void Check(bool ok,string why){if(!ok)throw new Exception("Diagnostic options UI: "+why);checks++;}
        void Snap(Window window,string name)
        {
            window.UpdateLayout();var root=(FrameworkElement)window.Content;var bmp=new RenderTargetBitmap((int)root.ActualWidth,(int)root.ActualHeight,96,96,PixelFormats.Pbgra32);bmp.Render(root);
            var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(bmp));using var file=File.Create(Path.Combine(output,name+"-"+language+".png"));png.Save(file);
        }
        async Task Ready(Window dialog)
        {
            for(var i=0;i<200&&!Named<Button>(dialog,"DiagnosticCreate").IsEnabled;i++)await Task.Delay(25);
            Check(Named<Button>(dialog,"DiagnosticCreate").IsEnabled,"preview does not complete");await Task.Delay(220);dialog.UpdateLayout();
        }
        Window Open(Action<DiagnosticOptions> select,DiagnosticLocations? locations)
        {
            var dialog=(Window)Call("CreateDiagnosticsOptionsDialog",select,locations)!;
            dialog.WindowStartupLocation=WindowStartupLocation.Manual;dialog.Left=dialog.Top=-30000;dialog.ShowActivated=false;dialog.Show();return dialog;
        }
        async Task Scenario()
        {
            var root=Path.Combine(ActivityStore.Root,"game");Directory.CreateDirectory(root);
            for(var i=1;i<=12;i++)foreach(var prefix in new[]{"","ART_"})
            {var file=Path.Combine(root,prefix+"log-"+i+".log");await File.WriteAllTextAsync(file,new string('x',80000)+i);File.SetLastWriteTimeUtc(file,DateTime.UtcNow.AddMinutes(i));}
            var dump=new byte[2*1024*1024];new Random(1).NextBytes(dump);await File.WriteAllBytesAsync(Path.Combine(root,"log-4.dmp"),dump);
            var locations=new DiagnosticLocations(root,Path.Combine(ActivityStore.Root,"documents"),Path.Combine(ActivityStore.Root,"local"),Path.Combine(ActivityStore.Root,"system"),[]);
            Set("_game",new GameInstallation(root,Path.Combine(root,"k2.exe"),null,null));
            DiagnosticOptions? accepted=null;var dialog=Open(value=>accepted=value,locations);await Ready(dialog);
            Check(Named<TextBlock>(dialog,"DiagnosticSizeEstimate").Text.Contains("≈"),"no approximate size preview");
            Snap(dialog,"diagnostic-options");
            var count=Named<ComboBox>(dialog,"DiagnosticLogCount");var dumps=Named<CheckBox>(dialog,"DiagnosticIncludeDumps");
            count.SelectedIndex=1;await Ready(dialog);var withDumps=Named<TextBlock>(dialog,"DiagnosticSizeEstimate").Text;
            dumps.IsChecked=false;await Ready(dialog);
            Check(Named<TextBlock>(dialog,"DiagnosticSizeEstimate").Text!=withDumps,"dump toggle does not update size");
            dumps.IsChecked=true;count.SelectedIndex=0;await Ready(dialog);Check(!dumps.IsEnabled&&dumps.IsChecked==false,"No logs does not disable and uncheck dumps");
            Check(Named<TextBlock>(dialog,"DiagnosticSelectionDetails").Text.Contains("0"),"empty selection has no count preview");
            count.SelectedIndex=8;await Ready(dialog);Named<Button>(dialog,"DiagnosticCreate").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(accepted is {RecentCount:int.MaxValue,IncludeCrashDumps:false},"Create ignores selected options");
            var cancel=Open(_=>throw new Exception("Cancel accepted options"),locations);Named<Button>(cancel,"DiagnosticCancel").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(50);
            Check(!cancel.IsVisible,"Cancel does not close preview");
            Set("_game",null);var launcherOnly=Open(_=>{},null);await Ready(launcherOnly);
            Check(!Named<ComboBox>(launcherOnly,"DiagnosticLogCount").IsEnabled&&!Named<CheckBox>(launcherOnly,"DiagnosticIncludeDumps").IsEnabled&&Named<CheckBox>(launcherOnly,"DiagnosticIncludeDumps").IsChecked==false,"launcher-only dialog offers game files");launcherOnly.Close();
            Call("HistoryButton_Click",null,new RoutedEventArgs());
            var history=(Window)typeof(MainWindow).GetField("_historyWindow",flags)!.GetValue(w)!;history.Left=history.Top=-30000;await Task.Delay(100);
            var badge=(Border)w.FindName("HistoryUnreadBadge");badge.Visibility=Visibility.Visible;history.UpdateLayout();
            Check(!badge.IsVisible&&((Grid)w.FindName("NewsHeaderGrid")).Visibility==Visibility.Collapsed,"orphan unread dot still visible in history window");
            Snap(history,"history-without-floating-dot");history.Close();
            Check(((Grid)w.FindName("NewsHeaderGrid")).Visibility==Visibility.Visible,"closing history does not restore shared header");
            Console.WriteLine($"DIAGNOSTIC OPTIONS UI PASS {checks} {language}: selection, estimates, dumps, cancel, launcher-only, history indicator");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();_=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false));
            var timer=new DispatcherTimer {Interval=TimeSpan.FromSeconds(30)};timer.Tick+=(_,_)=>frame.Continue=false;timer.Start();Dispatcher.PushFrame(frame);timer.Stop();
            if(!task.IsCompleted)throw new TimeoutException("Diagnostic UI");task.GetAwaiter().GetResult();
        }
        finally{foreach(Window dialog in Application.Current.Windows.Cast<Window>().Where(d=>d.Owner==w).ToArray())dialog.Close();w.Close();}
    }
}
