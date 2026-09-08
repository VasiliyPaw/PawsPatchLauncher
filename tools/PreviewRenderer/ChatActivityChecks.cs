using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class ChatActivityChecks
{
    internal static void Run(string language,string output)
    {
        if(!ActivityStore.IsSmokeTest)throw new Exception("Fixture only");
        var w=new MainWindow {Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual};
        const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name)=>(T)w.FindName(name);
        int n=0;void Check(bool ok,string why){n++;if(!ok)throw new Exception("Chat activity UI: "+why);}
        void Frame(string stage)
        {
            var content=(FrameworkElement)w.Content;content.UpdateLayout();
            var bitmap=new RenderTargetBitmap((int)content.ActualWidth,(int)content.ActualHeight,96,96,PixelFormats.Pbgra32);
            bitmap.Render(content);
            var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(bitmap));
            var path=Path.GetFullPath(output)+"."+stage+".png";Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            using var stream=File.Create(path);png.Save(stream);
        }
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Call("ApplyLanguage");
            var players=SocialHubChecks.Populate(w).ToArray();Call("ResetBroadcast");
            var owner=Field<AccountService>("_account").UserId;
            var stamp=DateTimeOffset.UtcNow.AddHours(1);
            for(var i=0;i<players.Length;i++)players[i]=players[i] with {LastMessageAt=stamp.AddSeconds(-i),LastMessageOrdinal=100-i};
            Set("_socialPlayers",players); Set("_socialMessages",Array.Empty<SocialMessage>());Set("_socialPending",Array.Empty<PendingSocialMessage>());
            Set("_socialPeer",(Guid?)players[0].Id);Call("RenderSocialRows");Call("RenderSocialMessages");w.UpdateLayout();await Task.Delay(420);
            var panel=C<StackPanel>("FriendsRowsPanel");
            var rows=panel.Children.OfType<FrameworkElement>().ToDictionary(v=>(Guid)v.Tag);
            var buttons=rows.ToDictionary(p=>p.Key,p=>(Button)((Grid)((StackPanel)p.Value).Children[0]).Children[0]);
            C<TextBox>("FriendsMessageInput").Text="unchanged draft";
            Check(panel.Children.OfType<FrameworkElement>().Select(v=>(Guid)v.Tag).SequenceEqual(players.Select(p=>p.Id)),"initial order");
            var selected=Field<Guid?>("_socialPeer");
            Frame("before");
            for(var i=0;i<24;i++)
            {
                var index=(i*5+4)%players.Length;
                var moving=rows[players[index].Id];var before=moving.TranslatePoint(new Point(),panel);
                players[index]=players[index] with{LastMessageAt=stamp.AddSeconds(i+1),LastMessageOrdinal=200+i,Unread=i+1};
                Set("_socialPlayers",players.ToArray());Call("RenderSocialRows");
                var after=moving.TranslatePoint(new Point(),panel);
                Check(((FrameworkElement)panel.Children[0]).Tag.Equals(players[index].Id),"burst latest not first");
                if(SystemParameters.ClientAreaAnimation)
                    Check(Math.Abs(before.Y-after.Y)<5,$"interruption jumped instead of retargeting: step={i}, {before.Y} -> {after.Y}, animated={Field<ChatListMotion>("_chatListMotion").IsAnimating}, visible={panel.IsVisible}, received={Field<DateTimeOffset>("_socialListReceived")}");
                Check(panel.Children.Count==players.Length && panel.Children.OfType<FrameworkElement>().Distinct().Count()==players.Length,"duplicate/dropped chat");
                await Task.Delay(25);
                if(i==0){await Task.Delay(65);Frame("moving");}
            }
            await Task.Delay(450);
            Frame("settled");
            Check(!Field<ChatListMotion>("_chatListMotion").IsAnimating,"animation clocks never stop");
            Check(panel.Children.OfType<FrameworkElement>().All(row=>ReferenceEquals(rows[(Guid)row.Tag],row)&&row.RenderTransform.Value.IsIdentity),"cards replaced or stale transforms");
            Check(Field<Guid?>("_socialPeer")==selected&&C<TextBox>("FriendsMessageInput").Text=="unchanged draft","order changed selection/draft");
            foreach(var p in buttons)Check(ReferenceEquals(p.Value,((Grid)((StackPanel)rows[p.Key]).Children[0]).Children[0]),"button recreated");
            Call("RenderSocialRows");Check(!Field<ChatListMotion>("_chatListMotion").IsAnimating,"identical poll restarted animation");
            var pendingPeer=players.First(p=>p.Id!=(Guid)((FrameworkElement)panel.Children[0]).Tag).Id;
            Set("_socialPending",new[]{new PendingSocialMessage(Guid.Parse(owner),pendingPeer,Guid.NewGuid(),"outgoing","text"){CreatedAt=stamp.AddDays(1)}});
            Call("RenderSocialRows");Check(((FrameworkElement)panel.Children[0]).Tag.Equals(pendingPeer),"optimistic outgoing did not promote");
            C<TextBox>("FriendsSearchInput").Text="friend0";
            Check(!Field<ChatListMotion>("_chatListMotion").IsAnimating&&panel.Children.Count==1,"search left stale motion/rows");
            C<TextBox>("FriendsSearchInput").Clear();
            for(var i=0;i<3;i++)players[i]=players[i] with{LastMessageAt=stamp.AddDays(2),LastMessageOrdinal=1000+i};
            Set("_socialPending",Array.Empty<PendingSocialMessage>());Set("_socialPlayers",players);Call("RenderSocialRows");
            Check(panel.Children.OfType<FrameworkElement>().Take(3).Select(v=>(Guid)v.Tag).SequenceEqual(players.Take(3).Reverse().Select(p=>p.Id)),"same-poll/same-time messages not stable");
            await Task.Delay(420);

            // Quick game-folder send: choose file before friend lookup; full success closes.
            var trace=new List<string>();var fixture=Path.Combine(ActivityStore.Root,"quick-send-"+Guid.NewGuid()+".rsg");
            var data=new byte[32];"TGCK"u8.CopyTo(data);File.WriteAllBytes(fixture,data);
            Set("_broadcastPickPathOverride",(Func<Task<string?>>)(()=>{trace.Add("picker");return Task.FromResult<string?>(fixture);}));
            Set("_friendSettingsReadOverride",(Func<Task<IReadOnlyList<SocialPlayer>>>)(()=>{trace.Add("friends");return Task.FromResult<IReadOnlyList<SocialPlayer>>(players);}));
            var attempts=0;var failSecond=false;
            Set("_broadcastSendOverride",(Func<Guid,Guid,string?,SaveTransferDescriptor?,byte[]?,CancellationToken,Task>)((actor,peer,code,save,bytes,ct)=>
            {
                attempts++;Check(actor.ToString()==owner&&code is null&&save?.FileName==Path.GetFileName(fixture)&&bytes?.Length==32,"quick save payload");
                if(failSecond&&attempts==2)throw new IOException("fixture failure");
                return Task.CompletedTask;
            }));
            await (Task)Call("OpenBroadcastFlowAsync",true)!;
            Check(trace.SequenceEqual(new[]{"picker","friends"})&&Field<bool>("_broadcastCloseAfterSend"),"quick route order/source flag");
            Check(!Field<bool>("_broadcastConfig")&&C<TextBlock>("BroadcastPayloadText").Text.Contains(Path.GetFileName(fixture)),"selected save absent");
            C<StackPanel>("BroadcastRows").Children.OfType<CheckBox>().First().IsChecked=true;
            await (Task)Call("SendBroadcastAsync")!;
            Check(attempts==1&&C<Border>("BroadcastOverlay").Visibility==Visibility.Collapsed,"quick success did not close");
            trace.Clear();await (Task)Call("OpenBroadcastFlowAsync",false)!;
            Check(trace.SequenceEqual(new[]{"friends"})&&!Field<bool>("_broadcastCloseAfterSend"),"friends route auto-picked/retained quick flag");
            Set("_broadcastSave",SaveTransferGuard.Describe(Path.GetFileName(fixture),data));Set("_broadcastBytes",data);Call("RefreshBroadcastKind");
            C<StackPanel>("BroadcastRows").Children.OfType<CheckBox>().First().IsChecked=true;
            await (Task)Call("SendBroadcastAsync")!;
            Check(C<Border>("BroadcastOverlay").Visibility==Visibility.Visible,"normal broadcast auto-closed");
            Call("ResetBroadcast");attempts=0;failSecond=true;await (Task)Call("OpenBroadcastFlowAsync",true)!;
            foreach(var box in C<StackPanel>("BroadcastRows").Children.OfType<CheckBox>().Take(2))box.IsChecked=true;
            await (Task)Call("SendBroadcastAsync")!;
            Check(attempts==2&&C<Border>("BroadcastOverlay").Visibility==Visibility.Visible,"partial failure lost retry window");
            failSecond=false;await (Task)Call("SendBroadcastAsync")!;
            Check(attempts==3&&C<Border>("BroadcastOverlay").Visibility==Visibility.Collapsed,"retry resent success or did not close");
            trace.Clear();Set("_broadcastPickPathOverride",(Func<Task<string?>>)(()=>{trace.Add("picker");return Task.FromResult<string?>(null);}));
            await (Task)Call("OpenBroadcastFlowAsync",true)!;
            Check(trace.SequenceEqual(new[]{"picker"})&&C<Border>("BroadcastOverlay").Visibility==Visibility.Collapsed,"cancel picker opened broadcast/loaded friends");
            var delayedPick=new TaskCompletionSource<string?>();
            Set("_broadcastPickPathOverride",(Func<Task<string?>>)(()=>delayedPick.Task));
            trace.Clear();var pendingPick=(Task)Call("OpenBroadcastFlowAsync",true)!;
            // Simultaneous account change must remove all cached rows/motion.
            typeof(AccountService).GetMethod("SetGuest",flags)!.Invoke(Field<AccountService>("_account"),null);Call("RenderAccount");
            delayedPick.SetResult(fixture);await pendingPick;
            Check(trace.Count==0&&C<Border>("BroadcastOverlay").Visibility==Visibility.Collapsed&&!Field<bool>("_offerSending"),"stale picker opened broadcast for another account");
            Check(panel.Children.Count==0&&!Field<ChatListMotion>("_chatListMotion").IsAnimating,"logout retained private rows/motion");
            Console.WriteLine($"CHAT ACTIVITY UI PASS {n} {language}: 24 overlapping retargets, identity/draft, search/cleanup, quick picker, source-specific close, partial retry and cancellation");
        }
        try
        {
            w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame=new DispatcherFrame();var timeout=new DispatcherTimer{Interval=TimeSpan.FromSeconds(35)};
            timeout.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timeout.Start();Dispatcher.PushFrame(frame);timeout.Stop();
            if(!task.IsCompleted)throw new TimeoutException("chat activity checks");
            task.GetAwaiter().GetResult();
        }
        finally {w.Close();}
    }
}
