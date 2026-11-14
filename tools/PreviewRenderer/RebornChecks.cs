using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class RebornChecks
{
    internal static void Run(string language,string output)
    {
        if (!ActivityStore.IsSmokeTest || !ActivityStore.Root.StartsWith("G:")) throw new InvalidOperationException("Isolated G: fixture required");
        Directory.CreateDirectory(output); new SettingsStore().Save(new UserSettings { Language=language, ModNoticeSeen=true });
        var w = new MainWindow(new LauncherConfiguration { FeedUrls=[],BetaFeedUrls=[],CacheRoot=Path.Combine(ActivityStore.Root,"cache") },null)
            { Width=1600,Height=1000,Left=-30000,Top=-30000,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual };
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        void Set(string name,object value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        T C<T>(string name)=>(T)w.FindName(name);
        var checks=0;void Check(bool ok,string why){if(!ok)throw new Exception("Reborn UI: "+why);checks++;}
        IEnumerable<T> Desc<T>(DependencyObject root) where T:DependencyObject
        { if(root is T found)yield return found;for(var i=0;i<VisualTreeHelper.GetChildrenCount(root);i++)foreach(var item in Desc<T>(VisualTreeHelper.GetChild(root,i)))yield return item; }
        Button Choice(string name)=>Desc<Button>(C<StackPanel>("RebornBody")).Single(b=>b.Name==name);
        void Snap(string name)
        {
            w.UpdateLayout();var root=(FrameworkElement)w.Content;var visual=new DrawingVisual();
            using(var dc=visual.RenderOpen())dc.DrawRectangle(new VisualBrush(root),null,new Rect(root.RenderSize));
            var bmp=new RenderTargetBitmap((int)root.ActualWidth,(int)root.ActualHeight,96,96,PixelFormats.Pbgra32);bmp.Render(visual);
            var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(bmp));using var file=File.Create(Path.Combine(output,name+"-"+language+".png"));png.Save(file);
        }
        async Task Scenario()
        {
            Set("_gameRunningProbe",(Func<bool>)(()=>false));
            Check(C<Button>("RebornNav").Visibility==Visibility.Collapsed,"guest sees private navigation");
            var account=Field<AccountService>("_account");var session=new AccountSession { UserId=Guid.NewGuid().ToString(),Nickname="paw",DisplayName="Paw",Email="fixture@example.invalid",AdminLevel=2 };
            typeof(AccountService).GetField("_session",flags)!.SetValue(account,session);
            typeof(AccountService).GetProperty("State")!.SetValue(account,AccountState.SignedIn);
            Set("_rebornCatalogOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>Task.FromResult<IReadOnlyList<RebornBuild>>([])));
            Call("RenderAccount");Check(C<Button>("RebornNav").Visibility==Visibility.Visible,"admin role without team cannot see Reborn");
            Call("SetActivePage","reborn");Check(C<ScrollViewer>("RebornPage").Visibility==Visibility.Visible,"admin without team cannot open Reborn");
            session.AdminLevel=0;Call("RenderAccount");Check(C<Button>("RebornNav").Visibility==Visibility.Collapsed&&Field<string>("_activePage")=="home","withdrawn admin access leaves Reborn visible");
            session.AdminLevel=0;session.PawsTeam=true;
            Set("_rebornCatalogOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>Task.FromResult<IReadOnlyList<RebornBuild>>([])));
            Call("RenderAccount");Check(C<Button>("RebornNav").Visibility==Visibility.Visible,"team member cannot see Reborn navigation");
            Call("SetActivePage","reborn");await Task.Delay(200);w.UpdateLayout();
            Check(C<ScrollViewer>("RebornPage").IsVisible&&!C<StackPanel>("KohanActionsFooter").IsVisible&&!C<Grid>("MainOptionsHost").IsVisible,"Reborn shares original game actions/content");
            Check(!Choice("RebornPrimaryAction").IsEnabled&&Field<IReadOnlyList<RebornBuild>>("_rebornBuilds").Count==0,"empty channel offers a download or invented build");
            Check(Field<UserSettings>("_settings").RebornChannel=="stable","initial channel is not Release");
            Check(Desc<TextBlock>(C<StackPanel>("RebornBody")).Any(t=>t.Text==UiLanguages.Text(language,"Сборка ещё не опубликована","No build published yet")),"missing honest empty-channel state");
            session.AdminLevel=1;Call("RenderAccount");Snap("reborn-release");
            Choice("RebornBetaChoice").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(60);
            Check(Field<UserSettings>("_settings").RebornChannel=="beta"&&new SettingsStore().Load().RebornChannel=="beta","Beta preference not saved");
            Check(!Choice("RebornPrimaryAction").IsEnabled,"empty Beta offers a download");Snap("reborn-beta");
            Set("_rebornBusy",true);Set("_pendingLauncherUpdate",new LauncherRelease{Version="99.0.0",Size=1,Sha256=new string('A',64),Urls=["https://fixture.invalid/never.exe"]});
            var restart=false;Set("_restartLauncher",(Func<Task>)(()=>{restart=true;return Task.CompletedTask;}));Set("_finishLauncherRestart",(Action)(()=>{}));
            Check(!await (Task<bool>)Call("InstallPendingLauncherUpdateAsync",false)!&&!restart,"launcher restarts during a Reborn operation");Set("_rebornBusy",false);
            session.AdminLevel=1;w.Width=1050;w.Height=680;Call("RenderAccount");await Task.Delay(80);w.UpdateLayout();
            var root=(FrameworkElement)w.Content;
            Check(C<Button>("AboutNav").TranslatePoint(new Point(0,C<Button>("AboutNav").ActualHeight),root).Y<=C<Button>("PrivacyPolicyButton").TranslatePoint(new Point(),root).Y,
                "extra Reborn navigation overlaps sidebar footer in a compact admin window");Snap("reborn-beta-compact");
            w.Width=1600;w.Height=1000;session.AdminLevel=0;Call("RenderAccount");
            var chosen=Field<UserSettings>("_settings").GamePath;Call("SetActivePage","home");
            Check(C<StackPanel>("KohanActionsFooter").IsVisible&&C<ScrollViewer>("MainOptionsScroll").IsVisible,"original game controls not restored");
            var gate=new TaskCompletionSource<IReadOnlyList<RebornBuild>>(TaskCreationOptions.RunContinuationsAsynchronously);
            Set("_rebornCatalogOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>gate.Task));Call("SetActivePage","reborn");
            session.PawsTeam=false;Call("RenderAccount");
            gate.SetResult([new RebornBuild(Guid.NewGuid(),"beta","0.1.0-test",100,new string('A',64),"KohanReborn.exe",DateTimeOffset.UtcNow,new())]);await Task.Delay(50);
            Check(C<Button>("RebornNav").Visibility==Visibility.Collapsed&&Field<string>("_activePage")=="home"&&Field<IReadOnlyList<RebornBuild>>("_rebornBuilds").Count==0,"revoked role/stale response leaks private page");
            Check(Field<UserSettings>("_settings").GamePath==chosen,"Reborn navigation changed Kohan II installation");
            Console.WriteLine($"REBORN UI PASS {checks} {language}: team/admin access, honest empty Release/Beta, channel persistence, separate controls, role revocation and no game mutations");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();
            _=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false));var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(25)};timer.Tick+=(_,_)=>frame.Continue=false;
            timer.Start();Dispatcher.PushFrame(frame);timer.Stop();if(!task.IsCompleted)throw new TimeoutException("Reborn UI");task.GetAwaiter().GetResult();
        }
        finally{w.Close();}
    }
}
