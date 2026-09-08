using System.IO;
using System.Net;
using System.Net.Http;
using System.Text.Json;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class LayoutRefreshChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Fixture only");
        var w = new MainWindow { Left=-32000, Top=-32000, ShowActivated=false, ShowInTaskbar=false, WindowStartupLocation=WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name) => (T)w.FindName(name);
        int checks=0; void Check(bool value,string why) { if(!value) throw new Exception(why); checks++; }
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Call("ApplyLanguage");
            Check(Field<string>("_changelogCategory")=="launcher","startup history not launcher");
            Check(w.FindName("FriendsChatsTab") is null && w.FindName("FriendsSearchButton") is null && w.FindName("FriendsClearSearchButton") is null,"obsolete navigation remains");
            Check(C<StackPanel>("FriendsToolbar").Children.OfType<Button>().Select(b=>b.Name).SequenceEqual(
                new[]{"FriendsShowAddButton","FriendsRequestsTab","FriendsBroadcastButton","FriendsBlockedTab"}),"toolbar action order");
            Check(C<Button>("FriendsBlockedTab").Content is LauncherIcon { Kind:IconKind.BlockedUsers }, "blocked-users icon");
            SocialChecks.Populate(w,"chat");
            var rows=C<StackPanel>("FriendsRowsPanel"); var friendRow=rows.Children[0];
            var input=C<TextBox>("FriendsSearchInput"); input.Text="Huheru";
            Check(rows.Children.Count==1 && C<TextBlock>("FriendsSearchPlaceholder").Visibility==Visibility.Collapsed,"live search placeholder");
            input.Clear(); friendRow=rows.Children[0];
            var peer=Field<Guid?>("_socialPeer");
            C<TextBox>("FriendsMessageInput").Text="preserved draft";
            foreach(var size in new[]{new Size(1050,680),new Size(1600,1000)})
            {
                w.Width=size.Width; w.Height=size.Height; w.UpdateLayout();
                Check(C<TextBlock>("FriendsTitleText").ActualHeight < 28, "Friends title wraps at minimum width");
                foreach(var kind in new[]{"requests","add","blocked"})
                {
                    Call("OpenFriendsDialog",kind); w.UpdateLayout(); await Task.Delay(210);
                    Check(Field<string>("_socialSection")=="chats" && Field<Guid?>("_socialPeer")==peer,"dialog replaced chat selection");
                    Check(ReferenceEquals(friendRow,rows.Children[0]) && C<TextBox>("FriendsMessageInput").Text=="preserved draft","dialog rebuilt chat/draft");
                    var card=C<Border>("FriendsDialogCard"); var content=(FrameworkElement)w.Content;
                    var rect=card.TransformToAncestor(content).TransformBounds(new Rect(card.RenderSize));
                    Check(rect.Left>=0 && rect.Right<=content.ActualWidth+1 && rect.Top>=0 && rect.Bottom<=content.ActualHeight+1,"dialog clips: "+kind);
                    Check(C<Button>("FriendsDialogClose").IsEnabled,"close unavailable");
                    if(kind=="requests")
                    {
                        Check(C<StackPanel>("FriendsDialogRows").Children.Count==1,"incoming request missing");
                        Call("SwitchSocialRequests","outgoing"); Check(C<StackPanel>("FriendsDialogRows").Children.Count==0,"outgoing filtering");
                        Call("SwitchSocialRequests","incoming");
                    }
                    if(kind=="add")Check(card.ActualWidth<=430 && card.ActualHeight<210,"add dialog not compact");
                    await (Task)Call("CloseFriendsDialogAsync")!;
                    Check(C<Border>("FriendsDialogOverlay").Visibility==Visibility.Collapsed,"dialog did not close");
                }
            }
            var friends=SocialHubChecks.Populate(w);
            // Both request directions share the same compact row layout and direct actions.
            var outgoing=new SocialPlayer(Guid.NewGuid(),"long_username_12345678901","outgoing");
            var outgoingCard=(Border)Call("RenderSocialRequest",outgoing)!;
            var outgoingGrid=(Grid)((StackPanel)outgoingCard.Child).Children[0];
            var outgoingActions=(StackPanel)outgoingGrid.Children[1];
            Check(outgoingActions.Children.Count==1 && outgoingActions.Children[0] is Button { Height:26, Tag:"cancel" },
                "outgoing request missing compact direct cancel");
            Check(!Field<bool>("_broadcastConfig") && C<Button>("BroadcastChooseFile").Visibility==Visibility.Visible,"save not default");
            var tabs=(Panel)C<Button>("BroadcastSaveTab").Parent;
            Check(ReferenceEquals(tabs.Children[0],C<Button>("BroadcastSaveTab")),"save is not first");
            Call("ResetBroadcast");
            var gameButtons=(Panel)C<Button>("OpenSavesFolderButton").Parent;
            Check(gameButtons.Children.IndexOf(C<Button>("SendSaveBroadcastButton"))==gameButtons.Children.IndexOf(C<Button>("OpenSavesFolderButton"))+1,"send save order");
            // Expired/missing code presentation, without any Auth/network calls.
            var service=Field<AccountService>("_account");
            typeof(AccountService).GetMethod("SetGuest",flags)!.Invoke(service,null);
            Call("RenderAccount"); Call("ShowAccountForm",true);
            C<CheckBox>("AccountRememberCheck").IsChecked=false;
            C<TextBox>("AccountEmailInput").Text="player@example.test";
            Call("BeginEmailConfirmation"); Call("RenderAccount");
            Check(!Field<bool>("_confirmationRemember"),"confirmation lost remember choice");
            Check(C<Border>("AccountFormCard").Visibility==Visibility.Collapsed && C<Border>("AccountConfirmationCard").Visibility==Visibility.Visible,"confirmation not separate");
            C<TextBox>("AccountConfirmationCodeInput").Text="00123"; Check(!C<Button>("AccountConfirmButton").IsEnabled,"short OTP enabled");
            C<TextBox>("AccountConfirmationCodeInput").Text="001234"; Check(C<Button>("AccountConfirmButton").IsEnabled,"six digits disabled");
            Call("AccountHeader_Click",C<Button>("AccountHeaderButton"),new RoutedEventArgs());
            Check(C<Border>("AccountFormCard").Visibility==Visibility.Collapsed,"header resurrects registration form over OTP");
            // Exercise actual UI -> OTP verification -> profile transition with delayed mocked Auth.
            var owner = Guid.NewGuid().ToString();
            var vault = new AccountSessionStore(Path.Combine(ActivityStore.Root, "otp-ui-" + Guid.NewGuid().ToString("N")));
            var reply = new TaskCompletionSource<HttpResponseMessage>();
            var verifyCalls = 0;
            var otpService = new AccountService(vault, new AccountChecks.Handler(request =>
            {
                var path = request.RequestUri!.AbsolutePath;
                if (path.EndsWith("/verify")) { verifyCalls++; return reply.Task; }
                var body = path.EndsWith("/user") ? JsonSerializer.Serialize(new { id=owner, email="player@example.test" }) :
                    path.EndsWith("/account-actions") ? "{\"status\":\"ok\",\"avatar\":null}" :
                    JsonSerializer.Serialize(new[] { new { id=owner, nickname="newplayer", display_name="New player" } });
                return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content=new StringContent(body) });
            }));
            service.Dispose(); Set("_account", otpService);
            C<TextBox>("AccountConfirmationCodeInput").Text="001234";
            var confirming = (Task)Call("ConfirmEmailAsync")!;
            Check(!C<Button>("AccountConfirmButton").IsEnabled && !C<TextBox>("AccountConfirmationCodeInput").IsEnabled, "OTP UI not locked");
            await (Task)Call("ConfirmEmailAsync")!;
            Check(verifyCalls==1, "double OTP submission");
            reply.SetResult(new HttpResponseMessage(HttpStatusCode.OK) { Content=new StringContent(JsonSerializer.Serialize(
                new { access_token="fixture-access", refresh_token="fixture-refresh", expires_in=3600,
                    user=new { id=owner, email="player@example.test" } })) });
            await confirming;
            Check(otpService.State==AccountState.SignedIn && C<Border>("AccountSignedInCard").Visibility==Visibility.Visible &&
                C<Border>("AccountConfirmationCard").Visibility==Visibility.Collapsed, "OTP did not sign in/show profile");
            Check(!File.Exists(vault.SessionPath) && C<TextBox>("AccountConfirmationCodeInput").Text=="", "OTP ignored remember choice or retained code");
            typeof(AccountService).GetMethod("SetGuest",flags)!.Invoke(otpService,null); Call("RenderAccount");
            Call("ShowAccountForm",false);
            Check(C<TextBox>("AccountConfirmationCodeInput").Text=="" && C<CheckBox>("AccountRememberCheck").Visibility==Visibility.Visible,"OTP retained / remember missing");
            var stable=new ChannelManifest{Channel="stable",PublishedAt="2026-09-09"};
            var beta=new ChannelManifest{Channel="beta",PublishedAt="2026-09-09"};
            stable.Changelog.Add(new ChangelogEntry{Category="patch",Version="stable-only",Title=new(){Ru="Release-only",En="Release-only"}});
            beta.Changelog.Add(new ChangelogEntry{Category="patch",Version="beta-only",Title=new(){Ru="Beta-only",En="Beta-only"}});
            var feed=Field<FeedClient>("_feedClient");
            var remember=typeof(FeedClient).GetMethod("RememberChannel",flags)!;
            remember.Invoke(feed,[stable]);remember.Invoke(feed,[beta]);
            foreach(var channel in new[]{stable,beta})
            {
                Set("_channel",channel);Set("_latestChannel",channel);
                foreach(var category in new[]{"patch","beta"})
                {
                    await (Task)Call("SwitchChangelogAsync",category)!;Call("RefreshNews");
                    var title=((StackPanel)C<StackPanel>("NewsEntriesPanel").Children[0]).Children.OfType<TextBlock>().First().Text;
                    Check(title==(category=="beta"?"Beta-only":"Release-only"),"history follows selected channel");
                }
            }
            Console.WriteLine($"LAYOUT REFRESH PASS {checks} {language}: permanent search, isolated dialogs, draft/selection, minimum/default geometry, save default, OTP UI and independent changelogs");
        }
        try
        {
            w.Show(); var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame=new DispatcherFrame();var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(35)};
            timer.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);
            timer.Start();try{Dispatcher.PushFrame(frame);}finally{timer.Stop();}
            if(!task.IsCompleted)throw new TimeoutException("layout checks");
            task.GetAwaiter().GetResult();
        }
        finally { w.Close(); }
    }
}
