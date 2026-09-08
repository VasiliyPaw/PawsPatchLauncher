using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class SocialRefinementChecks
{
    const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
    internal static void PopulateConfirmation(MainWindow w,bool matches)
    {
        SocialChecks.Populate(w,"chat");
        var peer=((IReadOnlyList<SocialPlayer>)typeof(MainWindow).GetField("_socialPlayers",Flags)!.GetValue(w)!).First(p=>p.Relation=="friend");
        var code=ConfigurationCode.Create(new UserSettings {Channel="beta",RoamingSpawnMode="x4",RussianLocalization=true});
        peer=peer with {DisplayName="Друг",Nickname="friend",Channel="beta",Configuration=matches?code:code.Replace("SP4","SP1")};
        _=typeof(MainWindow).GetMethod("ConfirmConfigurationOfferAsync",Flags)!.Invoke(w,new object[]{peer,code});
    }
    internal static void Run(string language)
    {
        var w=new MainWindow();int checks=0;
        object? Invoke(string n,params object?[] a)=>typeof(MainWindow).GetMethod(n,Flags)!.Invoke(w,a);
        T Field<T>(string n)=>(T)typeof(MainWindow).GetField(n,Flags)!.GetValue(w)!;
        T Control<T>(string n)=>(T)w.FindName(n);
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Social refinement UI: "+why);}
        void Finish(Task<bool> task,bool accept,bool expected)
        {
            var close=(Task)Invoke("CompleteConfirmationAsync",accept)!;
            PumpUntil(Task.WhenAll(close,task));
            Check(task.Result==expected,"confirmation result / disabled bypass");
            Check(Control<Border>("ConfirmationOverlay").Visibility==Visibility.Collapsed,"confirmation did not close");
        }
        try
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Invoke("ApplyLanguage");Invoke("ShowAccountForm",true);
            var names=(StackPanel)Control<TextBox>("AccountNicknameInput").Parent;
            Check(names.Children.IndexOf(Control<TextBox>("AccountDisplayNameInput"))<names.Children.IndexOf(Control<TextBox>("AccountNicknameInput")),"registration name before username");
            var edits=(Panel)Control<Button>("AccountEditNicknameButton").Parent;
            Check(edits.Children.IndexOf(Control<Button>("AccountEditDisplayNameButton"))<edits.Children.IndexOf(Control<Button>("AccountEditNicknameButton")),"edit name before username");
            Check(Control<Slider>("NotificationVolumeSlider") is DragAnywhereSlider,"volume track behavior not wired");
            SocialChecks.Populate(w,"chat");
            var peer=Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p=>p.Relation=="friend") with {Nickname="MixedUser",DisplayName="Mixed Display"};
            const string code="PAW-BETA-IW0-SP4-RM1-SG0-LM1-RU1-CL0-OOS1";
            foreach(var match in new[]{code,code+"-PS1"})
            {
                var task=(Task<bool>)Invoke("ConfirmConfigurationOfferAsync",peer with {Channel="beta",Configuration=match},code)!;
                Check(!task.IsCompleted&&Control<Border>("ConfirmationOverlay").Visibility==Visibility.Visible,"identical confirmation not shown");
                Check(!Control<Button>("ConfirmationDeleteButton").IsEnabled,"identical offer enabled");
                Check(Control<TextBlock>("ConfirmationPathText").Text.Contains(language=="ru"?"совпадают":"already match"),"identical explanation missing");
                Finish(task,true,false); // Even a programmatic click cannot bypass the disabled action.
            }
            var unknown=(Task<bool>)Invoke("ConfirmConfigurationOfferAsync",peer with {Configuration=null},code)!;
            Check(!Control<Button>("ConfirmationDeleteButton").IsEnabled,"unknown configuration guessed");
            Finish(unknown,false,false);
            foreach(var accept in new[]{false,true})
            {
                var task=(Task<bool>)Invoke("ConfirmConfigurationOfferAsync",peer with {Channel="beta",Configuration=code.Replace("SP4","SP1")},code)!;
                Check(!task.IsCompleted&&Control<Button>("ConfirmationDeleteButton").IsEnabled,"different config not confirmable");
                var text=Control<TextBlock>("ConfirmationPathText").Text;
                Check(text.Contains("Mixed Display · @mixeduser")&&text.Contains("×4"),"recipient/diff missing");
                Check(Control<CheckBox>("ConfirmationLocalizationToggle").Visibility==Visibility.Collapsed,"send confused with apply-localization choice");
                Finish(task,accept,accept);
            }
            Check(Field<IReadOnlyList<SocialOffer>>("_socialOffers").Count==0,"confirmation mutated conversation");
            Check(Field<Dictionary<Guid,SocialOffer>>("_sendingOffers").Count==0,"confirmation created optimistic offer early");

            // Hidden WPF surface: actual mouse capture, no cursor movement/click injection.
            using var surface=new HwndSource(new HwndSourceParameters("Hidden slider fixture") {Width=260,Height=50,WindowStyle=unchecked((int)0x80000000)});
            var slider=new DragAnywhereSlider {Width=220,Height=22,Minimum=0,Maximum=100,TickFrequency=1,IsSnapToTickEnabled=true,Style=(Style)w.FindResource("NotificationVolumeSliderStyle")};
            var root=new Grid();root.Children.Add(slider);surface.RootVisual=root;
            root.Measure(new Size(260,50));root.Arrange(new Rect(0,0,260,50));root.UpdateLayout();
            var track=(Track)slider.Template.FindName("PART_Track",slider);
            void Move(double ratio)
            {
                var x=track.Thumb.ActualWidth/2+ratio*(track.ActualWidth-track.Thumb.ActualWidth);
                typeof(DragAnywhereSlider).GetMethod("MoveTo",Flags)!.Invoke(slider,new object[]{new Point(x,11)});
            }
            slider.RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,0,MouseButton.Left){RoutedEvent=UIElement.PreviewMouseLeftButtonDownEvent});
            Check(slider.IsMouseCaptured&&(bool)typeof(DragAnywhereSlider).GetField("_trackDragging",Flags)!.GetValue(slider)!,"track press did not capture continuous drag");
            Move(.25);Check(slider.Value==25&&slider.IsMouseCaptured,"track drag to 25");
            Move(.73);Check(slider.Value==73&&slider.IsMouseCaptured,"drag required another click / stale layout");
            Move(1.5);Check(slider.Value==100,"right boundary");
            Move(-.5);Check(slider.Value==0,"left boundary");
            slider.RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,0,MouseButton.Left){RoutedEvent=UIElement.PreviewMouseLeftButtonUpEvent});
            Check(!slider.IsMouseCaptured&&!(bool)typeof(DragAnywhereSlider).GetField("_trackDragging",Flags)!.GetValue(slider)!,"drag release stuck");
            slider.RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,0,MouseButton.Left){RoutedEvent=UIElement.PreviewMouseLeftButtonDownEvent});
            slider.ReleaseMouseCapture();
            Check(!(bool)typeof(DragAnywhereSlider).GetField("_trackDragging",Flags)!.GetValue(slider)!,"lost capture stuck");
            Console.WriteLine($"SOCIAL REFINEMENT UI PASS {checks} {language}: name order, confirmation diff/equal/cancel/accept, actual hidden mouse capture and bounded drag; no real accounts or game");
        }
        finally {w.Close();}
    }
    private static void PumpUntil(Task task)
    {
        var frame=new DispatcherFrame();var started=DateTime.UtcNow;
        var timer=new DispatcherTimer {Interval=TimeSpan.FromMilliseconds(10)};
        timer.Tick+=(_,_)=>{if(task.IsCompleted||DateTime.UtcNow-started>TimeSpan.FromSeconds(5)){timer.Stop();frame.Continue=false;}};
        timer.Start();Dispatcher.PushFrame(frame);
        if(!task.IsCompleted)throw new TimeoutException("UI fixture");
        task.GetAwaiter().GetResult();
    }
}
