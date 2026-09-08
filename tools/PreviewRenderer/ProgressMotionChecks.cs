using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class ProgressMotionChecks
{
    internal static void Run(string language)
    {
        var window=new MainWindow{Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,Width=1050,Height=680,WindowStartupLocation=WindowStartupLocation.Manual};
        const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(window,args);
        var bar=(ProgressBar)window.FindName("OperationProgress");
        var details=(TextBlock)window.FindName("TransferText");
        var count=0;
        void Check(bool ok,string reason){count++;if(!ok)throw new Exception("Progress motion: "+reason);}
        double Target()=>(double)typeof(MainWindow).GetField("_progressTarget",flags)!.GetValue(window)!;
        async Task Flush(){await window.Dispatcher.InvokeAsync(()=>{},DispatcherPriority.ContextIdle);window.UpdateLayout();}
        IProgress<(long Received,long? Total)> Begin(string name)=>(IProgress<(long,long?)>)Call("TransferProgress",name)!;
        async Task Scenario()
        {
            ((PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text",flags)!.GetValue(window)!).SetLanguage(language);Call("ApplyLanguage");
            foreach(var page in new[]{"home","settings"})
            foreach(var name in new[]{"Paw's Patch Launcher 0.6.3","Arcane Wars patch"})
            {
                Call("SetActivePage",page);Call("SetBusy",true,"Progress fixture");await Flush();
                var transfer=Begin(name);await Flush();
                Check(bar.IsVisible&&bar.IsIndeterminate&&bar.Value==0,"transfer reset / unknown-length state");
                transfer.Report((500,1000));await Flush();
                Check(Target()==50&&!bar.IsIndeterminate&&details.Visibility==Visibility.Visible,"real measurement lost");
                await Task.Delay(45);var first=bar.Value;
                if(SystemParameters.ClientAreaAnimation)
                    Check(first is >0 and <50&&bar.HasAnimatedProperties,"known-length progress jumped directly");
                else Check(first==50&&!bar.HasAnimatedProperties,"reduced motion not immediate");
                await Task.Delay(45);Check(bar.Value>=first&&bar.Value<=50,"progress reversed or exceeded actual bytes");
                var before=bar.Value;Call("SetOperationProgress",80d,true);
                Check((SystemParameters.ClientAreaAnimation?Math.Abs(bar.Value-before)<.01:bar.Value==80)&&Target()==80,"new report jumped instead of continuing visible position");
                await Task.Delay(40);
                var animation=typeof(MainWindow).GetField("_progressAnimation",flags)!.GetValue(window);
                Call("SetOperationProgress",80d,true);
                Check(ReferenceEquals(animation,typeof(MainWindow).GetField("_progressAnimation",flags)!.GetValue(window)),"duplicate report restarted animation");
                await Task.Delay(300);Check(bar.Value==80&&!bar.HasAnimatedProperties,"progress did not settle / animation clock leaked");
                Call("SetOperationProgress",10d,true);Check(bar.Value==10&&!bar.HasAnimatedProperties,"retry/reset animated backwards");
                Call("SetOperationProgress",90d,true);await Task.Delay(30);
                Call("SetOperationIndeterminate",true);
                Check(bar.IsIndeterminate&&!bar.HasAnimatedProperties&&bar.Value==90,"install phase retained numeric animation");
                Call("SetOperationIndeterminate",false);Call("SetOperationProgress",100d,true);
                await Task.Delay(280);Check(bar.Value==100&&!bar.HasAnimatedProperties,"completion failed to settle");
                var pending=Begin("old transfer");pending.Report((900,1000));
                var current=Begin("new transfer");current.Report((20,1000));await Flush();
                Check(Target()==2&&bar.Value<=2,"queued old transfer contaminated new progress");
                Call("FinishTransfer");pending.Report((1000,1000));current.Report((1000,1000));await Flush();
                Check(Target()==2&&!bar.HasAnimatedProperties&&details.Visibility==Visibility.Collapsed,"completion/cancel allowed late progress");
                Call("SetBusy",false,null);await Flush();
                Check(bar.Visibility==Visibility.Collapsed&&bar.Value==0&&!bar.HasAnimatedProperties,"idle status retained progress clock");
            }
            Call("SetBusy",true,"Progress fixture");Begin("test");Call("SetOperationIndeterminate",false);await Flush();
            Call("SetOperationProgress",55d,false);Check(bar.Value==55&&!bar.HasAnimatedProperties,"immediate update option ignored");
            Call("SetOperationProgress",85d,true);await Task.Delay(25);bar.Visibility=Visibility.Collapsed;
            Check(bar.Value==85&&!bar.HasAnimatedProperties,"hidden progress kept running");
            bar.Visibility=Visibility.Visible;Call("SetOperationProgress",95d,true);await Task.Delay(25);
            Call("SetBusy",false,null);window.Close();Check(!bar.HasAnimatedProperties,"closing left an animation clock");
            Console.WriteLine($"PROGRESS MOTION UI PASS {count} {language}: launcher/patch, Home/footer, real byte targets, continuous retarget, reset, install, completion, cancellation and stale callbacks");
        }
        try
        {
            window.Show();var task=window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame=new DispatcherFrame();var timeout=new DispatcherTimer{Interval=TimeSpan.FromSeconds(20)};
            timeout.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>window.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timeout.Start();Dispatcher.PushFrame(frame);timeout.Stop();if(!task.IsCompleted)throw new TimeoutException("Progress motion checks timed out");task.GetAwaiter().GetResult();
        }
        finally{window.Close();}
    }
}
