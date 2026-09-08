using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class SocialHubChecks
{
    private const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
    private static object? Invoke(MainWindow w,string method,params object?[] args)=>typeof(MainWindow).GetMethod(method,Flags)!.Invoke(w,args);
    private static T Field<T>(MainWindow w,string name)=>(T)typeof(MainWindow).GetField(name,Flags)!.GetValue(w)!;
    private static void Set(MainWindow w,string name,object? value)=>typeof(MainWindow).GetField(name,Flags)!.SetValue(w,value);

    internal static IReadOnlyList<SocialPlayer> Populate(MainWindow w)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Fixture only");
        SocialChecks.Populate(w,"chat");
        var sample=Field<IReadOnlyList<SocialPlayer>>(w,"_socialPlayers")[0];
        var ours=new UserSettings { Channel="stable",RoamingSpawnMode="x4" };
        var folder=Path.Combine(ActivityStore.Root,"hub-fixture-"+Guid.NewGuid());
        Directory.CreateDirectory(Path.Combine(folder,".pawpatch"));
        var state=new InstallState {AppliedSettings=ours,Modules=new() {["pawpatch-core"]=new InstalledModule {
            Enabled=true,Version="0.5.9-fixture",DownloadedAt=new DateTimeOffset(2026,9,8,10,11,12,TimeSpan.Zero)}}};
        File.WriteAllText(Path.Combine(folder,".pawpatch","state.json"),JsonSerializer.Serialize(state,LauncherJsonContext.Default.InstallState));
        Set(w,"_game",new GameInstallation(folder,Path.Combine(folder,"k2.exe"),null,null));
        Set(w,"_gameRunningProbe",(Func<bool>)(()=>false));
        var names=new[]{"Huheru","Лесной страж","Союзник","Nightwatch","PawTwo","Knight","Beta tester"};
        var players=names.Select((name,i)=>sample with {Id=Guid.NewGuid(),Nickname="friend"+i,DisplayName=name}).ToList();
        players.Add(sample with {Id=Guid.NewGuid(),Nickname="same",DisplayName="Та же конфигурация",Configuration=ConfigurationCode.Create(ours),Channel="stable"});
        players.Add(sample with {Id=Guid.NewGuid(),Nickname="unknown",DisplayName="Нет данных",Configuration=null});
        Set(w,"_socialPlayers",(IReadOnlyList<SocialPlayer>)players);
        Invoke(w,"RenderSocialRows"); Invoke(w,"RefreshStatus");
        Invoke(w,"OpenBroadcast",Field<AccountService>(w,"_account").UserId,players);
        return players;
    }

    internal static void Run(string language)
    {
        var w=new MainWindow {Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,
            WindowStartupLocation=WindowStartupLocation.Manual,Width=1050,Height=680};var checks=0;
        T Control<T>(string name)=>(T)w.FindName(name);
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Social hub UI: "+why);}
        void Layout(double width,double height)
        {
            w.Width=width;w.Height=height;w.UpdateLayout();
            var content=(FrameworkElement)w.Content;content.Measure(new Size(width,height));content.Arrange(new Rect(0,0,width,height));content.UpdateLayout();
        }
        CheckBox[] Boxes()=>Control<StackPanel>("BroadcastRows").Children.OfType<CheckBox>().ToArray();
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>(w,"_text").SetLanguage(language);Invoke(w,"ApplyLanguage");
            SocialChecks.Populate(w,"details");
            var friend=Field<IReadOnlyList<SocialPlayer>>(w,"_socialPlayers")[0];
            var titles=new[]{"CoreTitleText","RussianTitleText","ColorsTitleText","OosTitleText","IndependentTitleText","RoamingSpawnTitleText","AdditionalRoamingTitleText","SiegeBalanceTitleText","PowersShardsTitleText"}.Select(n=>Control<TextBlock>(n).Text);
            var displayed=Control<StackPanel>("SocialDetailsComponents").Children.OfType<Grid>().Select(g=>g.Children.OfType<TextBlock>().First().Text);
            Check(displayed.SequenceEqual(titles),"profile components names/order differ from tab");
            Field<PawsPatchLauncher.Localization>(w,"_text").SetLanguage(language=="ru"?"en":"ru");Invoke(w,"ApplyLanguage");
            titles=new[]{"CoreTitleText","RussianTitleText","ColorsTitleText","OosTitleText","IndependentTitleText","RoamingSpawnTitleText","AdditionalRoamingTitleText","SiegeBalanceTitleText","PowersShardsTitleText"}.Select(n=>Control<TextBlock>(n).Text);
            displayed=Control<StackPanel>("SocialDetailsComponents").Children.OfType<Grid>().Select(g=>g.Children.OfType<TextBlock>().First().Text);
            Check(displayed.SequenceEqual(titles),"open profile kept previous language labels");
            Field<PawsPatchLauncher.Localization>(w,"_text").SetLanguage(language);Invoke(w,"ApplyLanguage");
            Invoke(w,"CloseSocialDetails");
            await (Task)Invoke(w,"OpenSocialChatAsync",friend)!;
            Check(Field<Guid?>(w,"_socialPeer") is null&&Control<Border>("FriendsChatCard").Visibility==Visibility.Collapsed,"chat toggle");
            Check(Control<Border>("FriendsChatEmptyCard").Visibility==Visibility.Visible&&!Control<Button>("FriendsSendButton").IsEnabled,"closed chat empty/send state");
            Check(w.FindName("MultiplayerNav") is null,"old navigation remains");
            Check(w.FindName("AccountAvatarChooseButton") is null&&w.FindName("AccountAvatarRemoveButton") is null,"standalone avatar actions remain");
            Invoke(w,"SetActivePage","account");Layout(1050,680);
            var avatar=Control<Button>("AccountAvatarEditButton");
            Check(avatar.IsEnabled&&avatar.ActualWidth==86&&avatar.Template.FindName("AvatarEditVeil",avatar) is Border,"avatar editing affordance");
            avatar.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            var menu=Field<ContextMenu>(w,"_socialMenu");
            Check(menu.Items.Count==2&&menu.Items.Cast<MenuItem>().All(i=>i.IsEnabled),"avatar menu actions");
            Invoke(w,"CloseSocialMenu");
            var players=Populate(w);
            var owner=Guid.Parse(Field<AccountService>(w,"_account").UserId);
            Check(Boxes().Length==9&&Boxes().Count(b=>b.IsEnabled)==7,"matching/unknown configs allowed");
            var available=Boxes().Where(b=>b.IsEnabled).ToArray();
            Layout(1050,680);
            var recipient=available[0];
            var card=(Border)recipient.Template.FindName("RecipientCard",recipient);
            Check(recipient.Template.FindName("CheckMark",recipient) is null&&card is not null,"recipient retained checkbox glyph");
            Check(Math.Abs(card!.ActualWidth-recipient.ActualWidth)<1&&card.ActualHeight>=58,"recipient background does not fill row");
            Check(recipient.InputHitTest(new Point(recipient.ActualWidth-5,5)) is not null
                &&recipient.InputHitTest(new Point(5,recipient.ActualHeight-5)) is not null,"empty row area is not clickable");
            Check(recipient.Template.Triggers.OfType<Trigger>().Any(t=>t.Property==UIElement.IsMouseOverProperty
                &&t.Setters.OfType<Setter>().Any(s=>s.TargetName=="RecipientCard"&&s.Property==Motion.BackgroundProperty)),"hover only targets text");
            var peer=new System.Windows.Automation.Peers.CheckBoxAutomationPeer(recipient);
            ((System.Windows.Automation.Provider.IToggleProvider)peer.GetPattern(System.Windows.Automation.Peers.PatternInterface.Toggle)).Toggle();
            Check(recipient.IsChecked==true&&((SolidColorBrush)Motion.GetBorderBrush(card)!).Color==(Color)ColorConverter.ConvertFromString("#C6A457"),"accessible selection did not highlight row");
            Check(Motion.GetOpacity((Border)recipient.Template.FindName("SelectionAccent",recipient))==1,"selected accent absent");
            recipient.IsChecked=false;
            foreach(var checkbox in available.Take(5))checkbox.IsChecked=true;
            Check(!available[5].IsEnabled&&!available[6].IsEnabled&&Control<Button>("BroadcastSendButton").IsEnabled,"selection cap");
            available[4].IsChecked=false;Check(available[5].IsEnabled,"selection capacity did not recover");
            foreach(var checkbox in available)checkbox.IsChecked=false;
            Check(!Control<Button>("BroadcastSendButton").IsEnabled,"empty batch enabled");
            foreach(var size in new[]{new Size(1050,680),new Size(1440,900)})
            {
                Layout(size.Width,size.Height);
                var content=(FrameworkElement)w.Content;
                foreach(var name in new[]{"BroadcastCard","BroadcastSendButton","BroadcastConfigTab","BroadcastSaveTab"})
                {
                    var control=Control<FrameworkElement>(name);var bounds=control.TransformToAncestor(content).TransformBounds(new Rect(control.RenderSize));
                    Check(bounds.Width>20&&bounds.Height>20&&bounds.Left>=0&&bounds.Right<=size.Width&&bounds.Top>=0&&bounds.Bottom<=size.Height,"broadcast clips: "+name);
                }
                Invoke(w,"ShowToast",(Func<string>)(()=>language=="ru"?"Конфигурация отправлена.":"Configuration sent."),false);
                Layout(size.Width,size.Height);
                var toast=Control<Border>("ToastPanel");var toastBounds=toast.TransformToAncestor(content).TransformBounds(new Rect(toast.RenderSize));
                Check(Math.Abs(toastBounds.Left+toastBounds.Width/2-content.ActualWidth/2)<2,"toast not centered");
                var toastHost=Control<ScrollViewer>("ToastHost");
                Check(VisualTreeHelper.GetParent(toastHost)==VisualTreeHelper.GetParent(Control<Border>("ConfirmationOverlay"))
                    &&Panel.GetZIndex(toastHost)>Panel.GetZIndex(Control<Border>("ConfirmationOverlay")),"toast under modal");
                Check(Control<Border>("ToastProgress").ActualWidth>200,"no expiry progress area");
            }
            Check(Control<TextBlock>("InstalledPatchText").Text.Contains("0.5.9-fixture"),"installed sidebar version");
            Check(Control<TextBlock>("PatchDownloadedText").Text.Contains("08.09.2026")&&Control<TextBlock>("PatchDownloadedText").Text.EndsWith(":12"),"download date/time");
            Set(w,"_friendSettingsReadOverride",(Func<Task<IReadOnlyList<SocialPlayer>>>)(()=>Task.FromResult(players)));
            var attempts=new List<Guid>(); var reject=true;
            var first=available[0];var second=available[1];first.IsChecked=second.IsChecked=true;
            Set(w,"_broadcastSendOverride",(Func<Guid,Guid,string?,SaveTransferDescriptor?,byte[]?,CancellationToken,Task>)((sender,target,code,save,bytes,ct)=>
            {
                Check(sender==owner&&code is not null&&save is null&&bytes is null,"batch payload/owner");
                attempts.Add(target);
                if(reject&&attempts.Count==2)throw new IOException("fixture failure");
                return Task.CompletedTask;
            }));
            await (Task)Invoke(w,"SendBroadcastAsync")!;
            Check(attempts.Count==2&&!first.IsChecked!.Value&&!first.IsEnabled&&second.IsChecked==true,"partial completion selection");
            reject=false;await (Task)Invoke(w,"SendBroadcastAsync")!;
            Check(attempts.Count==3&&attempts[2]==attempts[1]&&!second.IsEnabled,"retry resent completed recipient");
            var still=Boxes().First(b=>b.IsEnabled);still.IsChecked=true;
            var interrupted=new TaskCompletionSource();
            Set(w,"_broadcastSendOverride",(Func<Guid,Guid,string?,SaveTransferDescriptor?,byte[]?,CancellationToken,Task>)(async (_,_,_,_,_,ct)=>{interrupted.SetResult();await Task.Delay(Timeout.Infinite,ct);}));
            var job=(Task)Invoke(w,"SendBroadcastAsync")!;
            await interrupted.Task;
            Check(!Control<Button>("BroadcastSendButton").IsEnabled,"running batch double send");
            await (Task)Invoke(w,"CloseBroadcastAsync")!;await job;
            Check(Control<Border>("BroadcastOverlay").Visibility==Visibility.Collapsed&&!Field<bool>(w,"_offerSending"),"cancelled batch stuck");
            players=Populate(w);
            Invoke(w,"BroadcastKind_Click",Control<Button>("BroadcastSaveTab"),new RoutedEventArgs());
            Check(Boxes().All(b=>!b.IsEnabled)&&!Control<Button>("BroadcastSendButton").IsEnabled,"save enabled without selection");
            Set(w,"_broadcastSave",new SaveTransferDescriptor("fixture.rsg",16,new string('a',64)));
            Set(w,"_broadcastBytes",new byte[16]);Invoke(w,"RefreshBroadcastKind");
            Set(w,"_gameRunningProbe",(Func<bool>)(()=>true));
            Check(Boxes().All(b=>b.IsEnabled),"save recipients disabled during game or by config equality");
            Invoke(w,"ResetBroadcast");
            Check(Field<byte[]?>(w,"_broadcastBytes") is null&&Boxes().Length==0,"private payload not cleared");
            players=Populate(w);
            Boxes().First(b=>b.IsEnabled).IsChecked=true;
            var invoked=0;
            Set(w,"_broadcastSendOverride",(Func<Guid,Guid,string?,SaveTransferDescriptor?,byte[]?,CancellationToken,Task>)((_,_,_,_,_,_)=>{invoked++;return Task.CompletedTask;}));
            Set(w,"_friendSettingsReadOverride",(Func<Task<IReadOnlyList<SocialPlayer>>>)(()=>Task.FromResult<IReadOnlyList<SocialPlayer>>([])));
            await (Task)Invoke(w,"SendBroadcastAsync")!;
            Check(invoked==0,"removed friend received an offer");
            Invoke(w,"ResetBroadcast");players=Populate(w);
            foreach(var checkbox in Boxes().Where(b=>b.IsEnabled).Take(2))checkbox.IsChecked=true;
            Set(w,"_friendSettingsReadOverride",(Func<Task<IReadOnlyList<SocialPlayer>>>)(()=>Task.FromResult(players)));
            Set(w,"_broadcastSendOverride",(Func<Guid,Guid,string?,SaveTransferDescriptor?,byte[]?,CancellationToken,Task>)((_,_,_,_,_,_)=>{invoked++;throw new AccountException("rate_limit");}));
            await (Task)Invoke(w,"SendBroadcastAsync")!;
            Check(invoked==1&&Boxes().Count(b=>b.IsChecked==true)==2,"rate limit ignored or unsent selection lost");
            var read=new TaskCompletionSource<IReadOnlyList<SocialPlayer>>();
            Set(w,"_friendSettingsReadOverride",(Func<Task<IReadOnlyList<SocialPlayer>>>)(()=>read.Task));
            job=(Task)Invoke(w,"SendBroadcastAsync")!;
            var previous=Field<AccountService>(w,"_account");
            Set(w,"_account",new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root,"batch-guest-"+Guid.NewGuid()))));
            Invoke(w,"RenderAccount");previous.Dispose();
            read.SetResult(players);await job;
            Check(invoked==1&&Control<Border>("BroadcastOverlay").Visibility==Visibility.Collapsed&&Boxes().Length==0,"account switch leaked/sent stale batch");
        }
        try
        {
            w.Show();
            var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame=new DispatcherFrame();var timer=new DispatcherTimer {Interval=TimeSpan.FromSeconds(25)};
            timer.Tick+=(_,_)=>frame.Continue=false;
            task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start();Dispatcher.PushFrame(frame);timer.Stop();
            if(!task.IsCompleted)throw new TimeoutException("Social hub checks timed out");
            task.GetAwaiter().GetResult();
            Console.WriteLine($"SOCIAL HUB UI PASS {checks} {language}: profile, avatar menu, toast layers, chat toggle, batch limits/partial retry/cancellation; isolated mock transport");
        }
        finally {w.Close();}
    }
}
