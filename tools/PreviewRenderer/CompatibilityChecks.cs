using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class CompatibilityChecks
{
    const BindingFlags F=BindingFlags.Instance|BindingFlags.NonPublic;
    static object? Call(MainWindow w,string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,F)!.Invoke(w,args);
    static void Set(MainWindow w,string name,object? value)=>typeof(MainWindow).GetField(name,F)!.SetValue(w,value);
    static T Field<T>(MainWindow w,string name)=>(T)typeof(MainWindow).GetField(name,F)!.GetValue(w)!;
    internal static void Populate(MainWindow w)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Fixture only");
        Set(w,"_channel",new ChannelManifest{Game=new GameRequirement{Version="1.3.72",SteamBuild="25068126",K2ExeSha256=new(){new string('0',64)}}});
        Set(w,"_compatibilityState",GameCompatibilityState.Unsupported);Set(w,"_compatibilityKey","preview-mismatch");
        Call(w,"RefreshGameLaunchState");
    }
    internal static void Run(string language)
    {
        var w=new MainWindow{Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual,Width=1050,Height=680};
        var path=Path.Combine(Path.GetTempPath(),"paw-compatibility-"+Guid.NewGuid()+".fixture");
        int n=0;void Check(bool ok,string message){n++;if(!ok)throw new Exception("Compatibility UI: "+message);}
        T C<T>(string name)=>(T)w.FindName(name);
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>(w,"_text").SetLanguage(language);Call(w,"ApplyLanguage");
            Set(w,"_gameRunningProbe",(Func<bool>)(()=>false));
            var bytes=new byte[]{2,4,6,8};await File.WriteAllBytesAsync(path,bytes);
            var hash=Convert.ToHexString(SHA256.HashData(bytes));
            Set(w,"_game",new GameInstallation(Path.GetDirectoryName(path)!,path,"different-metadata","beta"));
            var channel=new ChannelManifest{Game=new GameRequirement{Version="1.3.72",SteamBuild="25068126",K2ExeSha256=new(){hash}}};Set(w,"_channel",channel);
            Check(await (Task<bool>)Call(w,"CheckGameCompatibilityAsync",true)!,"supported hash / changed metadata");
            Check(C<Button>("LaunchButton").IsEnabled&&C<TextBlock>("GameCompatibilityHint").Visibility==Visibility.Collapsed,"valid game blocked");
            await File.WriteAllBytesAsync(path,new byte[]{1,2,3,4,5});
            Check(!await (Task<bool>)Call(w,"CheckGameCompatibilityAsync",true)!,"unsupported file accepted");
            var popup=Field<Border>(w,"_compatibilityPopup");
            Check(popup is not null&&!C<Button>("LaunchButton").IsEnabled&&C<TextBlock>("GameCompatibilityHint").Visibility==Visibility.Visible,"warning / launch gate absent");
            Check(C<TextBlock>("ReadyStatusText").Text==(language=="ru"?"Версия игры не подходит":"Unsupported game version"),"header still claims game ready");
            Check(((StackPanel)popup!.Child).Children.OfType<TextBlock>().Any(t=>t.Text.Contains("1.3.72")&&t.Text.Contains("25068126")),"warning missing supported version");
            Check((string)C<TextBlock>("GameCompatibilityHint").ToolTip== (language=="ru"?"Поддерживается Kohan II ":"Supported Kohan II version: ")+"1.3.72 · Steam build 25068126","supported version missing");
            for(var i=0;i<5;i++)Call(w,"RefreshGameLaunchState");
            Check(ReferenceEquals(popup,Field<Border>(w,"_compatibilityPopup")),"warning rebuilt every tick");
            ((DockPanel)((StackPanel)popup!.Child).Children[0]).Children.OfType<Button>().Single().RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            await Task.Delay(260);Call(w,"RefreshGameLaunchState");
            Check(Field<Border?>(w,"_compatibilityPopup")==null&&!C<Button>("LaunchButton").IsEnabled,"dismissal enabled launch or popup respawned");
            // Direct invocation is rejected too, before any process or installer can run.
            await (Task)Call(w,"LaunchGameAsync")!;
            Check(Field<GameCompatibilityState>(w,"_compatibilityState")==GameCompatibilityState.Unsupported&&!Field<bool>(w,"_launchStarting"),"direct launch did not release/reject");
            Check(!C<Button>("LaunchButton").IsEnabled&&C<Button>("CheckUpdatesButton").IsEnabled,"local incompatibility disabled update checks");
            await File.WriteAllBytesAsync(path,bytes);
            Check(await (Task<bool>)Call(w,"CheckGameCompatibilityAsync",true)!,"restored supported binary not accepted");
            Check(C<Button>("LaunchButton").IsEnabled&&C<TextBlock>("GameCompatibilityHint").Visibility==Visibility.Collapsed,"restored game warning remains");
            channel.Game.K2ExeSha256=new(){new string('0',64)};
            Check(!await (Task<bool>)Call(w,"CheckGameCompatibilityAsync",true)!,"new feed rule not applied");
            channel.Game.K2ExeSha256=new(){hash};
            Check(await (Task<bool>)Call(w,"CheckGameCompatibilityAsync",true)!,"compatible patch update did not unlock");
            Set(w,"_game",new GameInstallation(Path.GetDirectoryName(path)!,path+".missing",null,null));
            Check(!await (Task<bool>)Call(w,"CheckGameCompatibilityAsync",true)!,"missing binary accepted");
            Check(Field<GameCompatibilityState>(w,"_compatibilityState")==GameCompatibilityState.Unavailable&&Field<Border?>(w,"_compatibilityPopup")==null&&!C<Button>("LaunchButton").IsEnabled,"unreadable mislabeled wrong version");
            Set(w,"_game",new GameInstallation(Path.GetDirectoryName(path)!,path,null,null));
            channel.Game.K2ExeSha256=new(){new string('0',64)};var old=(Task<bool>)Call(w,"CheckGameCompatibilityAsync",true)!;
            channel.Game.K2ExeSha256=new(){hash};var latest=(Task<bool>)Call(w,"CheckGameCompatibilityAsync",true)!;
            await Task.WhenAll(old,latest);
            Check(Field<GameCompatibilityState>(w,"_compatibilityState")==GameCompatibilityState.Supported,"stale check overrode current requirement");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();
            var timeout=new DispatcherTimer{Interval=TimeSpan.FromSeconds(30)};timeout.Tick+=(_,_)=>frame.Continue=false;
            task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timeout.Start();Dispatcher.PushFrame(frame);timeout.Stop();if(!task.IsCompleted)throw new TimeoutException();task.GetAwaiter().GetResult();
            Console.WriteLine($"COMPATIBILITY UI PASS {n} {language}: synthetic files; game never launched");
        }
        finally{w.Close();if(File.Exists(path))File.Delete(path);}
    }
}
