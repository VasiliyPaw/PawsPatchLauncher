using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class SessionMenuChecks
{
    private const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
    internal static void Run(string language,string output)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated fixture only");
        var w=new MainWindow(); int checks=0;
        object? Invoke(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,Flags)!.Invoke(w,args);
        T Control<T>(string name)=>(T)w.FindName(name);
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Session/menu UI: "+why);}
        var localization=(PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text",Flags)!.GetValue(w)!;
        localization.SetLanguage(language);Invoke("ApplyLanguage");
        async Task Scenario()
        {
            Invoke("SetActivePage","friends"); SocialChecks.Populate(w,"requests");
            var content=(FrameworkElement)w.Content;
            content.Measure(new Size(1050,680));content.Arrange(new Rect(0,0,1050,680));content.UpdateLayout();
            var card=(Border)Control<StackPanel>("FriendsRowsPanel").Children[0];
            var body=(StackPanel)card.Child;var grid=(Grid)body.Children[0];
            var actions=(StackPanel)grid.Children[1];var anchor=(Button)actions.Children[1];
            double rowHeight=card.ActualHeight;
            var players=(IReadOnlyList<SocialPlayer>)typeof(MainWindow).GetField("_socialPlayers",Flags)!.GetValue(w)!;
            var incoming=players.Single(p=>p.Relation=="incoming");
            var menu=(ContextMenu)Invoke("CreateSocialMenu",anchor,incoming)!;
            Check(menu.PlacementTarget==anchor && !menu.StaysOpen,"popup anchoring/dismissal");
            Check(menu.Items.Count==2,"incoming menu actions");
            Check(((MenuItem)menu.Items[0]).Tag?.ToString()=="decline" && ((MenuItem)menu.Items[1]).Tag?.ToString()=="block","wrong request menu");
            Check(body.Children.Count==1 && card.ActualHeight==rowHeight,"menu expands row");
            Check(((MenuItem)menu.Items[1]).Foreground.ToString()=="#FFF07B72","danger action color");
            Check(ReferenceEquals(menu.Style,w.FindResource("SocialContextMenu")),"unthemed popup");
            // Render the exact popup template without opening a native desktop popup.
            menu.Visibility=Visibility.Visible;menu.ApplyTemplate();
            menu.Measure(new Size(240,200));menu.Arrange(new Rect(0,0,240,menu.DesiredSize.Height));menu.UpdateLayout();
            Check(menu.ActualHeight>=65 && menu.ActualHeight<130,"menu compact layout");
            var bitmap=new RenderTargetBitmap(240,(int)Math.Ceiling(menu.ActualHeight),96,96,PixelFormats.Pbgra32);bitmap.Render(menu);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
            using(var stream=File.Create(Path.ChangeExtension(output,"menu.png")))encoder.Save(stream);
            var friend=players.Single(p=>p.Relation=="friend");
            var friendMenu=(ContextMenu)Invoke("CreateSocialMenu",anchor,friend)!;
            Check(((MenuItem)friendMenu.Items[0]).Tag?.ToString()=="details","friend details menu");
            Check(((MenuItem)friendMenu.Items[1]).Tag?.ToString()=="remove","friend remove menu");
            typeof(MainWindow).GetField("_socialMenu",Flags)!.SetValue(w,menu);
            Invoke("SetActivePage","account");
            Check(typeof(MainWindow).GetField("_socialMenu",Flags)!.GetValue(w) is null,"page switch retains popup");

            var account=(AccountService)typeof(MainWindow).GetField("_account",Flags)!.GetValue(w)!;
            string owner=account.UserId;
            Check(Control<Button>("AccountLogoutButton").Background.ToString()=="#FF653A38","logout not red");
            var cancel=(Task)Invoke("ConfirmAccountLogoutAsync")!;
            Check(!cancel.IsCompleted && Control<FrameworkElement>("ConfirmationOverlay").Visibility==Visibility.Visible,"logout skips confirmation");
            Check(account.UserId==owner && account.State==AccountState.SignedIn,"logout before confirmation");
            Check(Control<TextBlock>("ConfirmationTitleText").Text==(language=="ru"?"Выйти из аккаунта?":"Sign out?"),"confirmation title");
            await (Task)Invoke("CompleteConfirmationAsync",false)!; await cancel;
            Check(account.UserId==owner && account.State==AccountState.SignedIn,"cancel logs out");
            var accept=(Task)Invoke("ConfirmAccountLogoutAsync")!;
            await (Task)Invoke("CompleteConfirmationAsync",true)!; await accept;
            Check(account.State==AccountState.Guest,"confirmed logout retained account");
            Check(Control<StackPanel>("FriendsRowsPanel").Children.Count==0,"logout retained private rows");
            // Forced exit clears inputs and shows the explicit notification even off profile page.
            Control<TextBox>("AccountEmailInput").Text="private@example.invalid";
            Control<PasswordBox>("AccountPasswordInput").Password="fixture";
            Invoke("SetActivePage","home");Invoke("HandleEndedAccount","session_replaced");
            Check(Control<TextBox>("AccountEmailInput").Text=="" && Control<PasswordBox>("AccountPasswordInput").Password=="","forced exit retained inputs");
            Check(Control<Border>("AccountMessageCard").Visibility==Visibility.Visible,"forced exit warning missing");
            Check(Control<TextBlock>("AccountMessageText").Text.Contains(language=="ru"?"другом лаунчере":"another launcher"),"forced exit wording");
            Console.WriteLine($"SESSION + MENU UI PASS {checks} {language}: popup template/layout, actions, safe logout confirmation/cancel, forced exit and private-state clearing; no real account requests");
        }
        try
        {
            SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(w.Dispatcher));
            var task=Scenario();var frame=new DispatcherFrame();
            var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(20)};
            timer.Tick+=(_,_)=>frame.Continue=false;timer.Start();
            _=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(new Action(()=>frame.Continue=false)));
            if(!task.IsCompleted)Dispatcher.PushFrame(frame);timer.Stop();
            if(!task.IsCompleted)throw new TimeoutException("Session/menu UI checks");task.GetAwaiter().GetResult();
        }
        finally{w.Close();SynchronizationContext.SetSynchronizationContext(null);}
    }
}
