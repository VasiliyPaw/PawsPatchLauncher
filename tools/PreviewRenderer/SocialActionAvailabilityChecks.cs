using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class SocialActionAvailabilityChecks
{
    internal static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated fixture required.");
        new SettingsStore().Save(new UserSettings { ModNoticeSeen = true, Language = language });
        var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [] }, null);
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T C<T>(string name) => (T)w.FindName(name);
        var checks = 0;
        void Check(bool ok, string reason) { checks++; if (!ok) throw new Exception("Social action eligibility: " + reason); }
        void Click(string name) => C<Button>(name).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        var owner = Guid.NewGuid(); var peer = Guid.NewGuid();
        var removalCalls = 0; var accountMutations = 0;
        HttpResponseMessage Json(object body) => new(HttpStatusCode.OK) { Content = new StringContent(JsonSerializer.Serialize(body)) };
        var handler = new AccountChecks.Handler(request =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (path.EndsWith("/token")) return Task.FromResult(Json(new { access_token = "fixture-access", refresh_token = "fixture-refresh", expires_in = 3600,
                user = new { id = owner, email = "fixture@example.invalid" } }));
            if (path.EndsWith("/paw_profiles")) return Task.FromResult(Json(new[] { new { id = owner, nickname = "fixture" } }));
            if (path.EndsWith("/paw_friend_action")) { removalCalls++; return Task.FromResult(Json(new { status = "ok" })); }
            if (path.EndsWith("/paw_social_list")) return Task.FromResult(Json(new { status = "ok", players = Array.Empty<object>() }));
            if (path.EndsWith("/account-actions")) accountMutations++;
            throw new InvalidOperationException("Unexpected mocked route: " + path);
        });
        using var service = new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root, "social-eligibility-" + Guid.NewGuid())), handler);
        var friend = new SocialPlayer(peer, "friend", "friend", DisplayName: "Fixture player");
        void ShowPlayer(SocialPlayer player)
        {
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { player }); Set("_socialListReceived", DateTimeOffset.UtcNow);
            Call("SetActivePage", "friends"); Call("RenderSocialRows"); Call("RenderSocialIdentity"); Call("ShowSocialDetails", player);
        }
        void Preview(string name, FrameworkElement element)
        {
            var root = (FrameworkElement)w.Content;
            root.Measure(new Size(1440, 900)); root.Arrange(new Rect(0, 0, 1440, 900)); root.UpdateLayout();
            var drawing = new DrawingVisual();
            using (var dc = drawing.RenderOpen()) dc.DrawRectangle(new VisualBrush(element), null, new Rect(0, 0, element.ActualWidth, element.ActualHeight));
            var bitmap = new RenderTargetBitmap(Math.Max(1, (int)Math.Ceiling(element.ActualWidth)), Math.Max(1, (int)Math.Ceiling(element.ActualHeight)), 96, 96, PixelFormats.Pbgra32);
            bitmap.Render(drawing);
            var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(bitmap));
            Directory.CreateDirectory(output); using var file = File.Create(Path.Combine(output, name + "-" + language + ".png")); png.Save(file);
        }
        async Task Scenario()
        {
            await service.SignInAsync("fixture@example.invalid", "fixture-password", remember: false);
            Field<AccountService>("_account").Dispose(); Set("_account", service); Call("RenderAccount");
            ShowPlayer(friend);
            Check(C<Button>("SocialDetailsRemoveButton").IsEnabled, "real friend cannot be removed in smoke fixtures");
            var removing = (Task)Call("SocialFriendActionAsync", friend, "remove")!;
            Check(!removing.IsCompleted && Field<TaskCompletionSource<bool>?>("_confirmation") is not null && removalCalls == 0, "friend removal skips confirmation");
            Click("ConfirmationCancelButton"); await removing;
            Check(removalCalls == 0 && Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").Count == 1, "cancelled removal mutated friendship");
            removing = (Task)Call("SocialFriendActionAsync", friend, "remove")!;
            Click("ConfirmationDeleteButton"); await removing;
            Check(removalCalls == 1 && Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").Count == 0, "approved removal did not reach mocked RPC exactly once");
            Check(C<Border>("SocialDetailsOverlay").Visibility == Visibility.Collapsed, "removed friend profile remains active");

            ShowPlayer(friend with { IsFriend = false });
            StackPanel ChatRow(SocialPlayer player) => (StackPanel)Call("RenderSocialFriend", player)!;
            StackPanel ChatIdentity(StackPanel row) => (StackPanel)((Grid)((Button)((Grid)row.Children[0]).Children[0]).Content).Children[1];
            var officialRow=ChatRow(friend with { IsFriend=false });
            Check(ChatIdentity(officialRow).Children.Count==2 && ChatIdentity(officialRow).Children[0] is SocialIdentityLine {AllowWrap:false}, "nonfriend badge is not beside display name");
            Preview("official-chat-row", officialRow);
            var officialHeight=officialRow.ActualHeight;
            var normalRow=ChatRow(friend);
            Check(ReferenceEquals(officialRow,normalRow) && ChatIdentity(normalRow).Children[0] is TextBlock, "cached row retains nonfriend badge after friendship change");
            Preview("friend-chat-row", normalRow);
            Check(Math.Abs(normalRow.ActualHeight-officialHeight)<.1,"nonfriend badge changes row height");
            var longRow=ChatRow(friend with {IsFriend=false,DisplayName=new string('W',32),Unread=4});
            Preview("nonfriend-long-name",longRow);
            Check(Math.Abs(longRow.ActualHeight-officialHeight)<.1,"long name/unread wraps nonfriend badge");
            ChatRow(friend with { IsFriend=false });
            Check(C<Button>("SocialDetailsRemoveButton").IsEnabled && C<TextBlock>("SocialDetailsRelationshipText").Visibility == Visibility.Visible, "official conversation cannot add a friend");
            Check(Equals(C<Button>("SocialDetailsRemoveButton").Tag,"request") && C<Button>("SocialDetailsRemoveButton").Content.ToString()==(language=="ru"?"Добавить в друзья":"Add friend"), "nonfriend action still removes or labels a friendship");
            Preview("official-chat", C<Border>("SocialDetailsCard"));
            Call("CloseSocialDetails");
            var session = (AccountSession)typeof(AccountService).GetField("_session", flags)!.GetValue(service)!;
            session.AdminLevel = 2; session.ProtectedAdmin = true; Call("RenderAccount");
            Check(!C<Button>("AccountDeleteButton").IsEnabled && !service.CanDeleteAccount, "protected administrator exposes deletion");
            Check(ToolTipService.GetShowOnDisabled(C<Button>("AccountDeleteButton")) && C<Button>("AccountDeleteButton").ToolTip is string { Length: > 30 }, "protected administrator lacks explanation");
            Call("ShowAccountEditor", "delete");
            Check(Field<string>("_accountEditor") == "" && accountMutations == 0, "protected account entered deletion");

            session.ProtectedAdmin = false; session.AdminLevel = 0; Call("RenderAccount");
            Check(C<Button>("AccountDeleteButton").IsEnabled && C<Button>("AccountDeleteButton").ToolTip is null, "ordinary account retains protected state");
            Call("ShowAccountEditor", "delete"); C<PasswordBox>("AccountCurrentPasswordInput").Password = "fixture-password";
            var deleting = (Task)Call("SubmitAccountEditorAsync")!;
            Check(!deleting.IsCompleted && Field<TaskCompletionSource<bool>?>("_confirmation") is not null && accountMutations == 0, "ordinary account cannot reach confirmation");
            Click("ConfirmationCancelButton"); await deleting;
            Check(accountMutations == 0 && service.State == AccountState.SignedIn && C<PasswordBox>("AccountCurrentPasswordInput").Password == "", "cancelled deletion sent a request or retained password");
            session.BannedAt = DateTimeOffset.UtcNow; session.BanUntil = DateTimeOffset.UtcNow.AddHours(1); Call("RenderAccount");
            Check(!C<Button>("AccountDeleteButton").IsEnabled && C<Button>("AccountDeleteButton").ToolTip is string { Length: > 20 }, "ban deletion guard or explanation lost");
            session.BanUntil = DateTimeOffset.UtcNow.AddMinutes(-1); Call("RenderAccount");
            Check(C<Button>("AccountDeleteButton").IsEnabled && C<Button>("AccountDeleteButton").ToolTip is null, "expired ban leaves stale deletion restriction");

            // Unshown layout previews for inspection, without operating the user's desktop.
            session.BannedAt = session.BanUntil = null; session.AdminLevel = 2; Call("RenderAccount");
            foreach (var section in new[] { "users", "bans", "deleted" })
            {
                Set("_adminSection", section); Call("BuildAdminLayout"); Call("SetActivePage", "admin");
                Preview("admin-" + section, C<StackPanel>("AdminHeaderPanel"));
            }
            Call("SetActivePage", "home"); Call("SetBusy", true, "Downloading fixture / Загрузка");
            Set("_transferReceived", (long?)52428800L); Set("_transferTotal", (long?)104857600L);
            Call("RefreshOperationDetails", true);
            Preview("download-compact", C<Border>("OperationStatusPanel"));
            Call("OperationDetails_Click", C<Button>("OperationDetailsButton"), new RoutedEventArgs());
            Preview("download-expanded", C<Border>("OperationStatusPanel")); Call("SetBusy", false, null);
            Console.WriteLine($"SOCIAL ACTION ELIGIBILITY PASS {checks} {language}: real friendship confirmation/cancellation and mocked removal, official conversation, protected/ordinary/banned accounts; isolated profile and fake mutations only");
        }
        try
        {
            var task = w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(25) }; timer.Tick += (_, _) => frame.Continue = false;
            _ = task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false));
            timer.Start(); Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Social action eligibility checks timed out.");
            task.GetAwaiter().GetResult();
        }
        finally { Set("_busy", false); w.Close(); }
    }
}
