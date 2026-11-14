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
        void Snap(string name,FrameworkElement? target=null)
        {
            w.UpdateLayout();var root=target??(FrameworkElement)w.Content;var visual=new DrawingVisual();
            using(var dc=visual.RenderOpen())dc.DrawRectangle(new VisualBrush(root),null,new Rect(root.RenderSize));
            var bmp=new RenderTargetBitmap((int)root.ActualWidth,(int)root.ActualHeight,96,96,PixelFormats.Pbgra32);bmp.Render(visual);
            var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(bmp));using var file=File.Create(Path.Combine(output,name+"-"+language+".png"));png.Save(file);
        }
        async Task Scenario()
        {
            Set("_gameRunningProbe",(Func<bool>)(()=>false));
            Check(C<Button>("RebornNav").Visibility==Visibility.Collapsed,"guest sees private navigation");
            bool HistoryChoice()=>((MainWindow.TimelineChoice[])C<ComboBox>("HistorySubjectCombo").ItemsSource).Any(c=>c.Id=="reborn");
            Call("SyncHistoryFilters");Check(!HistoryChoice(),"guest sees private history subject");
            var account=Field<AccountService>("_account");var session=new AccountSession { UserId=Guid.NewGuid().ToString(),Nickname="paw",DisplayName="Paw",Email="fixture@example.invalid",AdminLevel=2 };
            typeof(AccountService).GetField("_session",flags)!.SetValue(account,session);
            typeof(AccountService).GetProperty("State")!.SetValue(account,AccountState.SignedIn);
            Set("_rebornCatalogOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>Task.FromResult<IReadOnlyList<RebornBuild>>([])));
            Call("RenderAccount");Check(C<Button>("RebornNav").Visibility==Visibility.Visible,"admin role without team cannot see Reborn");
            Check(HistoryChoice(),"admin without team cannot see Reborn history");
            Call("SetActivePage","reborn");Check(C<ScrollViewer>("RebornPage").Visibility==Visibility.Visible,"admin without team cannot open Reborn");
            session.AdminLevel=0;Call("RenderAccount");Check(C<Button>("RebornNav").Visibility==Visibility.Collapsed&&Field<string>("_activePage")=="home","withdrawn admin access leaves Reborn visible");
            session.AdminLevel=0;session.PawsTeam=true;
            Set("_rebornCatalogOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>Task.FromResult<IReadOnlyList<RebornBuild>>([])));
            Call("RenderAccount");Check(C<Button>("RebornNav").Visibility==Visibility.Visible,"team member cannot see Reborn navigation");
            Call("SetActivePage","reborn");await Task.Delay(200);w.UpdateLayout();
            Check(C<ScrollViewer>("RebornPage").IsVisible&&!C<StackPanel>("KohanActionsFooter").IsVisible&&C<StackPanel>("RebornActionsFooter").IsVisible&&!C<Grid>("MainOptionsHost").IsVisible,"Reborn shares original game actions/content");
            Check(!C<Button>("RebornInstallButton").IsEnabled&&!C<Button>("RebornLaunchButton").IsEnabled&&Field<IReadOnlyList<RebornBuild>>("_rebornBuilds").Count==0,"empty channel offers a download or invented build");
            Check(Field<UserSettings>("_settings").RebornChannel=="stable","initial channel is not Release");
            Check(Desc<TextBlock>(C<StackPanel>("RebornBody")).Any(t=>t.Text==UiLanguages.Text(language,"Сборка ещё не опубликована","No build published yet")),"missing honest empty-channel state");
            session.AdminLevel=1;Call("RenderAccount");w.UpdateLayout();
            var bottomNav=(StackPanel)C<Button>("AdminNav").Parent;
            Check(C<Button>("RebornNav").Parent==bottomNav&&bottomNav.Children.IndexOf(C<Button>("RebornNav"))+1==bottomNav.Children.IndexOf(C<Button>("AdminNav")),"Reborn must sit immediately above admin navigation");
            Check(LauncherIcon.GetKind(C<Button>("RebornNav"))==IconKind.Reborn,"Reborn does not use its own K icon");
            Check(!Desc<Button>(C<StackPanel>("RebornBody")).Any()||Desc<Button>(C<StackPanel>("RebornBody")).All(b=>b.Name is "RebornReleaseChoice" or "RebornBetaChoice"),"folder chooser or install action remains in page cards");
            await (Task)Call("RebornActionAsync",false)!;
            Check(Field<UserSettings>("_settings").RebornPath is null,"empty-channel action prompts for or saves a folder");
            Snap("reborn-release");
            Choice("RebornBetaChoice").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(60);
            Check(Field<UserSettings>("_settings").RebornChannel=="beta"&&new SettingsStore().Load().RebornChannel=="beta","Beta preference not saved");
            Check(!C<Button>("RebornInstallButton").IsEnabled&&!C<Button>("RebornLaunchButton").IsEnabled,"empty Beta offers a download");Snap("reborn-beta");
            Set("_rebornBusy",true);Set("_pendingLauncherUpdate",new LauncherRelease{Version="99.0.0",Size=1,Sha256=new string('A',64),Urls=["https://fixture.invalid/never.exe"]});
            var restart=false;Set("_restartLauncher",(Func<Task>)(()=>{restart=true;return Task.CompletedTask;}));Set("_finishLauncherRestart",(Action)(()=>{}));
            Check(!await (Task<bool>)Call("InstallPendingLauncherUpdateAsync",false)!&&!restart,"launcher restarts during a Reborn operation");Set("_rebornBusy",false);
            session.AdminLevel=1;w.Width=1050;w.Height=680;Call("RenderAccount");await Task.Delay(80);w.UpdateLayout();
            var root=(FrameworkElement)w.Content;
            Check(C<Button>("AboutNav").TranslatePoint(new Point(0,C<Button>("AboutNav").ActualHeight),root).Y<=C<Button>("PrivacyPolicyButton").TranslatePoint(new Point(),root).Y,
                "extra Reborn navigation overlaps sidebar footer in a compact admin window");Snap("reborn-beta-compact");
            Check(C<Button>("RebornLaunchButton").TranslatePoint(new Point(),C<Grid>("RebornActionBar")).Y>=C<Button>("RebornInstallButton").TranslatePoint(new Point(),C<Grid>("RebornActionBar")).Y+C<Button>("RebornInstallButton").ActualHeight,"compact launch button overlaps installation actions");
            w.Width=1600;w.Height=1000;session.AdminLevel=0;Call("RenderAccount");
            var rootPath=Path.Combine(ActivityStore.Root,"reborn-installed-fixture");
            var archivePath=Path.Combine(ActivityStore.Root,Guid.NewGuid()+".zip");
            using(var zip=System.IO.Compression.ZipFile.Open(archivePath,System.IO.Compression.ZipArchiveMode.Create))
            { var entry=zip.CreateEntry("Reborn.exe");using var writer=new StreamWriter(entry.Open());writer.Write("fixture only; never execute"); }
            var fixtureBuild=new RebornBuild(Guid.NewGuid(),"beta","0.1.0-test",new FileInfo(archivePath).Length,await CryptoAndIO.Sha256Async(archivePath),"Reborn.exe",DateTimeOffset.UtcNow,new());
            await RebornInstall.InstallAsync(rootPath,fixtureBuild,archivePath,()=>Task.CompletedTask,CancellationToken.None);
            var settings=Field<UserSettings>("_settings");settings.RebornPath=rootPath;
            Set("_rebornBuilds",new RebornBuild[]{fixtureBuild});Call("RenderReborn");w.UpdateLayout();
            Check(!C<Button>("RebornInstallButton").IsEnabled&&C<Button>("RebornLaunchButton").IsEnabled,"installed build cannot launch or offers reinstall");
            Set("_rebornBuilds",new RebornBuild[]{fixtureBuild with { Id=Guid.NewGuid(),Version="0.2.0-test" }});Call("RenderReborn");
            Check(C<Button>("RebornInstallButton").IsEnabled&&C<Button>("RebornLaunchButton").IsEnabled,"update must preserve Play for the installed build");
            Choice("RebornReleaseChoice").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(!C<Button>("RebornLaunchButton").IsEnabled&&settings.RebornPath==rootPath,"switching to empty Release reuses a Beta launch or changes the shared folder");
            Choice("RebornBetaChoice").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Set("_rebornBusy",true);Call("RenderReborn");
            Check(C<StackPanel>("RebornOperationPanel").IsVisible&&!C<Button>("RebornInstallButton").IsEnabled&&!C<Button>("RebornLaunchButton").IsEnabled&&!C<Button>("RebornCheckUpdatesButton").IsEnabled,"operation footer does not lock Reborn actions");
            Set("_rebornBusy",false);Call("RenderReborn");
            var chosen=Field<UserSettings>("_settings").GamePath;Call("SetActivePage","home");
            Check(C<StackPanel>("KohanActionsFooter").IsVisible&&!C<StackPanel>("RebornActionsFooter").IsVisible&&C<ScrollViewer>("MainOptionsScroll").IsVisible,"original game controls not restored");
            Call("SetActivePage","reborn");Choice("RebornReleaseChoice").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Call("HistoryButton_Click",null,new RoutedEventArgs());
            var historyWindow=Field<Window>("_historyWindow");historyWindow.Left=historyWindow.Top=-30000;historyWindow.ShowActivated=false;
            await Task.Delay(180);w.UpdateLayout();historyWindow.UpdateLayout();
            Check(HistoryChoice()&&Field<string>("_historySubject")=="reborn"&&C<ComboBox>("HistorySourceCombo").Visibility==Visibility.Collapsed&&C<ComboBox>("HistoryBranchCombo").IsVisible,"history opened from Reborn does not select its own two-channel history");
            Check(Field<IReadOnlyList<TimelineEntry>>("_renderedHistory").Count==0&&Desc<TextBlock>(C<StackPanel>("NewsEntriesPanel")).Any(t=>t.Text==UiLanguages.Text(language,"Сборка ещё не опубликована","No build published yet")),"empty history invents release notes");
            Snap("reborn-history-release",(FrameworkElement)historyWindow.Content);
            void Branch(string id)=>C<ComboBox>("HistoryBranchCombo").SelectedItem=((MainWindow.TimelineChoice[])C<ComboBox>("HistoryBranchCombo").ItemsSource).Single(c=>c.Id==id);
            Branch("beta");await Task.Delay(220);Snap("reborn-history-beta",(FrameworkElement)historyWindow.Content);
            var older=fixtureBuild with {Id=Guid.NewGuid(),Channel="stable",Version="0.0.9-test",PublishedAt=DateTimeOffset.UtcNow.AddDays(-2),Notes=new(){[language]="older fixture"}};
            var newer=older with {Id=Guid.NewGuid(),Version="0.1.0-test",PublishedAt=older.PublishedAt.AddDays(1),Notes=new(){[language]="newer fixture"}};
            var betaNotes=fixtureBuild with {Notes=new(){[language]="beta fixture"}};
            Set("_rebornHistoryOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>Task.FromResult<IReadOnlyList<RebornBuild>>([older,betaNotes,newer])));
            await (Task)Call("LoadRebornHistoryAsync",true)!;
            Check(Field<IReadOnlyList<TimelineEntry>>("_renderedHistory").Count==1&&Field<IReadOnlyList<TimelineEntry>>("_renderedHistory")[0].Branch=="beta","Beta history contains another channel");
            Check(Desc<TextBlock>(C<StackPanel>("NewsEntriesPanel")).Any(t=>t.Text=="beta fixture"),"translated history notes absent from real cards");
            Branch("stable");await Task.Delay(220);
            Check(Field<IReadOnlyList<TimelineEntry>>("_renderedHistory").Count==2&&Field<IReadOnlyList<TimelineEntry>>("_renderedHistory")[0].Entry.Version=="0.1.0-test","Release history loses older versions or sorts incorrectly");
            Branch("all");await Task.Delay(220);
            Check(Field<IReadOnlyList<TimelineEntry>>("_renderedHistory").Count==3,"all channels history loses a branch");
            Check(!C<Button>("RebornInstallButton").IsEnabled,"history rows incorrectly become downloadable catalog builds");
            Set("_rebornHistoryOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>Task.FromException<IReadOnlyList<RebornBuild>>(new IOException("fixture offline"))));
            await (Task)Call("LoadRebornHistoryAsync",true)!;
            Check(Field<bool>("_rebornHistoryError")&&Desc<Button>(C<StackPanel>("NewsEntriesPanel")).Any(),"history transport failure lacks a retry action");
            var historyGate=new TaskCompletionSource<IReadOnlyList<RebornBuild>>(TaskCreationOptions.RunContinuationsAsynchronously);
            Set("_rebornHistoryOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>historyGate.Task));
            var pendingHistory=(Task)Call("LoadRebornHistoryAsync",true)!;
            var gate=new TaskCompletionSource<IReadOnlyList<RebornBuild>>(TaskCreationOptions.RunContinuationsAsynchronously);
            Set("_rebornCatalogOverride",(Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>)(_=>gate.Task));Call("SetActivePage","reborn");
            session.PawsTeam=false;Call("RenderAccount");
            gate.SetResult([new RebornBuild(Guid.NewGuid(),"beta","0.1.0-test",100,new string('A',64),"KohanReborn.exe",DateTimeOffset.UtcNow,new())]);await Task.Delay(50);
            Check(C<Button>("RebornNav").Visibility==Visibility.Collapsed&&Field<string>("_activePage")=="home"&&Field<IReadOnlyList<RebornBuild>>("_rebornBuilds").Count==0,"revoked role/stale response leaks private page");
            historyGate.SetResult([older,betaNotes,newer]);await pendingHistory;
            Check(!HistoryChoice()&&Field<string>("_historySubject")!="reborn"&&Field<IReadOnlyList<RebornBuild>>("_rebornHistory").Count==0&&Field<IReadOnlyList<TimelineEntry>>("_renderedHistory").All(r=>r.Source!="reborn"),"revoked membership or stale response leaves private history visible");
            historyWindow.Close();
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
