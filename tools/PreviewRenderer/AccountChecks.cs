using System.Net;
using System.IO;
using System.Net.Http;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Threading;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class AccountChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Account checks require --smoke-test.");
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        var window = new MainWindow();
        object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(window, args);
        T Control<T>(string name) => (T)window.FindName(name);
        var localization = (PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text", flags)!.GetValue(window)!;
        localization.SetLanguage(language); Invoke("ApplyLanguage");
        var checks = 0;
        void Check(bool ok, string why) { checks++; if (!ok) throw new InvalidOperationException("Account UI: " + why); }
        async Task Scenario()
        {
            Invoke("SetActivePage", "friends");
            Check(Control<StackPanel>("FriendsPanel").Visibility == Visibility.Visible, "friends not shown");
            Check(Control<StackPanel>("AccountPanel").Visibility == Visibility.Collapsed, "account form leaks into friends");
            Check(Control<StackPanel>("FriendsGuestPanel").Visibility == Visibility.Visible, "friends guest invitation missing");
            Invoke("AccountShowLogin_Click", Control<Button>("FriendsLoginButton"), new RoutedEventArgs());
            Check(Control<StackPanel>("AccountPanel").Visibility == Visibility.Visible && Control<StackPanel>("FriendsPanel").Visibility == Visibility.Collapsed, "friends login does not open separate page");
            Invoke("AccountHeader_Click", Control<Button>("AccountHeaderButton"), new RoutedEventArgs());
            Check(Control<Border>("AccountFormCard").Visibility == Visibility.Visible, "header does not open guest sign-in");
            Check(Control<Border>("AccountSignedInCard").Visibility == Visibility.Collapsed, "guest sees signed-in actions");
            Check(Control<Button>("AccountShowLoginButton").Content.ToString() == (language == "ru" ? "Вход" : "Sign in"), "login label");
            Check(Control<Button>("AccountShowRegisterButton").Content.ToString() == (language == "ru" ? "Регистрация" : "Register"), "registration label");
            Check(Control<Button>("AccountHeaderButton").BorderBrush.ToString() == "#FFB68D37", "account header selected border missing");
            Invoke("AccountShowRegister_Click", Control<Button>("AccountShowRegisterButton"), new RoutedEventArgs());
            Check(Control<StackPanel>("AccountNicknamePanel").Visibility == Visibility.Visible, "register tab cannot switch directly");
            Invoke("AccountShowLogin_Click", Control<Button>("AccountShowLoginButton"), new RoutedEventArgs());
            Check(Control<StackPanel>("AccountNicknamePanel").Visibility == Visibility.Collapsed, "login tab cannot switch directly");
            foreach (var page in new[] { "home", "modules", "settings", "about" })
            {
                Invoke("SetActivePage", page);
                Check(Control<StackPanel>("FriendsPanel").Visibility == Visibility.Collapsed, "account leaks into " + page);
                Check(Control<StackPanel>("AccountPanel").Visibility == Visibility.Collapsed, "account page leaks into " + page);
            }
            Invoke("SetActivePage", "friends"); Invoke("ShowAccountForm", true);
            Check(Control<Border>("AccountFormCard").Visibility == Visibility.Visible, "registration form visibility");
            Check(Control<StackPanel>("AccountNicknamePanel").Visibility == Visibility.Visible && Control<StackPanel>("AccountRepeatPanel").Visibility == Visibility.Visible, "registration fields missing");
            Check(Control<TextBox>("AccountNicknameInput").MaxLength == 24, "nickname bound missing");
            Check(Control<CheckBox>("AccountRememberCheck").IsChecked == true, "remember not on by default");
            Check(Control<TextBlock>("AccountHeaderNameText").Text == (language == "ru" ? "Гость" : "Guest"), "header guest missing");
            var contentForPassword = (FrameworkElement)window.Content;
            contentForPassword.Measure(new Size(1440, 900)); contentForPassword.Arrange(new Rect(0, 0, 1440, 900)); contentForPassword.UpdateLayout();
            var passwordBox = Control<PasswordBox>("AccountPasswordInput");
            byte[] Pixels()
            {
                window.Dispatcher.Invoke(() => { }, DispatcherPriority.ContextIdle);
                contentForPassword.Measure(new Size(1440, 900)); contentForPassword.Arrange(new Rect(0, 0, 1440, 900)); contentForPassword.UpdateLayout();
                var bmp = new RenderTargetBitmap(1440, 900, 96, 96, PixelFormats.Pbgra32);
                bmp.Render(contentForPassword);
                var box = passwordBox.TransformToAncestor(contentForPassword).TransformBounds(new Rect(passwordBox.RenderSize));
                var region = new Int32Rect((int)box.X + 2, (int)box.Y + 2, (int)box.Width - 4, (int)box.Height - 4);
                var pixels = new byte[region.Width * region.Height * 4]; bmp.CopyPixels(region, pixels, region.Width * 4, 0); return pixels;
            }
            var empty = Pixels(); passwordBox.Password = "fixture-private"; var filled = Pixels();
            var ink = 0;
            for (var i = 0; i < empty.Length; i += 4) if (filled[i] != empty[i] || filled[i + 1] != empty[i + 1] || filled[i + 2] != empty[i + 2]) ink++;
            Check(ink > 40, "filled password produces no visible dots (clipped content host)");
            var reveal = Control<CheckBox>("AccountShowPasswordCheck");
            var plain = Control<TextBox>("AccountPasswordInputVisible");
            Check(reveal.IsChecked == false && plain.Visibility == Visibility.Collapsed && plain.Text == "", "plaintext retained by default");
            reveal.IsChecked = true;
            Check(plain.Text == "fixture-private" && plain.Visibility == Visibility.Visible && passwordBox.Visibility == Visibility.Collapsed, "show password does not reveal text");
            plain.Text = "fixture-edited";
            Check(passwordBox.Password == "fixture-edited", "revealed edits lost");
            reveal.IsChecked = false;
            Check(plain.Text == "" && passwordBox.Password == "fixture-edited" && passwordBox.Visibility == Visibility.Visible, "hide lost password or retained plain text");
            Control<PasswordBox>("AccountPasswordInput").Password = "fixture-private";
            Control<PasswordBox>("AccountRepeatInput").Password = "fixture-private";
            Invoke("SetActivePage", "home");
            Check(Control<PasswordBox>("AccountPasswordInput").Password == "" && Control<PasswordBox>("AccountRepeatInput").Password == "", "password retained across navigation");
            Invoke("SetActivePage", "friends"); Invoke("ShowAccountForm", false);
            Check(Control<StackPanel>("AccountNicknamePanel").Visibility == Visibility.Collapsed && Control<StackPanel>("AccountRepeatPanel").Visibility == Visibility.Collapsed, "login shows registration-only fields");
            Control<TextBox>("AccountEmailInput").Text = "bad@ email";
            Control<PasswordBox>("AccountPasswordInput").Password = "fixture-private";
            await (Task)Invoke("SubmitAccountAsync")!;
            Check(Control<TextBlock>("AccountMessageText").Text.Contains(language == "ru" ? "корректный адрес" : "valid email"), "missing inline validation");
            Check(Control<PasswordBox>("AccountPasswordInput").Password == "fixture-private" && Control<TextBox>("AccountEmailInput").Text == "bad@ email", "failed login cleared fields");

            foreach (var errorCode in new[] { "invalid_credentials", "email_not_confirmed" })
            {
                ((AccountService)typeof(MainWindow).GetField("_account", flags)!.GetValue(window)!).Dispose();
                typeof(MainWindow).GetField("_account", flags)!.SetValue(window, new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root, "failure-ui-" + Guid.NewGuid().ToString("N"))),
                    new Handler(_ => Task.FromResult(new HttpResponseMessage(HttpStatusCode.BadRequest) { Content = new StringContent(JsonSerializer.Serialize(new { error_code = errorCode })) }))));
                Invoke("ShowAccountForm", false);
                Control<TextBox>("AccountEmailInput").Text = "fixture@example.invalid";
                passwordBox.Password = "fixture-private";
                reveal.IsChecked = true;
                await (Task)Invoke("SubmitAccountAsync")!;
                Check(passwordBox.Password == "fixture-private" && plain.Text == "fixture-private" && Control<TextBox>("AccountEmailInput").Text == "fixture@example.invalid", "server rejection cleared input: " + errorCode);
                Check(Control<Border>("AccountMessageCard").Visibility == Visibility.Visible && Control<TextBlock>("AccountMessageText").Text.Length > 0, "server rejection not visible");
                if (errorCode == "email_not_confirmed")
                {
                    Check(Control<Button>("AccountResendButton").Visibility == Visibility.Visible, "unconfirmed email has no next step");
                    Check(((SolidColorBrush)Control<LauncherIcon>("AccountMessageIcon").Foreground).Color == (Color)ColorConverter.ConvertFromString("#F0CC73"), "unconfirmed email not highlighted gold");
                }
            }
            Invoke("SetActivePage", "friends");
            Check(passwordBox.Password == "" && plain.Text == "" && reveal.IsChecked == false && plain.Visibility == Visibility.Collapsed, "plaintext survives leaving account");
            Invoke("ShowAccountForm", false);

            var waiting = new TaskCompletionSource<HttpResponseMessage>();
            var user = Guid.NewGuid().ToString();
            var requests = 0;
            var fake = new Handler(request =>
            {
                requests++;
                if (request.RequestUri!.AbsolutePath.EndsWith("/token")) return waiting.Task;
                if (request.RequestUri.AbsolutePath.EndsWith("/user")) return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(JsonSerializer.Serialize(new { id = user, email = "fixture@example.invalid" })) });
                if (request.RequestUri.AbsolutePath.EndsWith("/account-actions")) return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("{\"status\":\"ok\",\"avatar\":null}") });
                return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(JsonSerializer.Serialize(new[] { new { id = user, nickname = "FixturePaw" } })) });
            });
            var old = (AccountService)typeof(MainWindow).GetField("_account", flags)!.GetValue(window)!; old.Dispose();
            var vault = new AccountSessionStore(Path.Combine(ActivityStore.Root, "account-ui-" + Guid.NewGuid().ToString("N")));
            typeof(MainWindow).GetField("_account", flags)!.SetValue(window, new AccountService(vault, fake));
            Control<TextBox>("AccountEmailInput").Text = "fixture@example.invalid";
            Control<PasswordBox>("AccountPasswordInput").Password = "fixture-private";
            var pending = (Task)Invoke("SubmitAccountAsync")!;
            Check(!Control<Button>("AccountSubmitButton").IsEnabled && !Control<StackPanel>("AccountFieldsPanel").IsEnabled, "form not locked during sign-in");
            await (Task)Invoke("SubmitAccountAsync")!;
            Check(requests == 1, "double submission");
            Invoke("SetActivePage", "modules");
            Check(Control<Button>("ModulesNav").IsEnabled, "account request blocked patch navigation");
            waiting.SetResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(JsonSerializer.Serialize(new { access_token = "fixture-access", refresh_token = "fixture-refresh", expires_in = 3600, user = new { id = user, email = "fixture@example.invalid" } })) });
            await pending; Invoke("SetActivePage", "friends");
            Check(Control<Border>("AccountSignedInCard").Visibility == Visibility.Visible && Control<Border>("AccountFormCard").Visibility == Visibility.Collapsed, "successful sign-in did not change UI");
            Check(Control<TextBlock>("AccountProfileNameText").Text == "FixturePaw", "server nickname missing");
            Check(Control<PasswordBox>("AccountPasswordInput").Password == "", "successful sign-in retained password");
            foreach (var name in new[] { "AccountSocialPendingText", "AccountProfilePrivacyText", "AccountAvatarHintText", "AccountIntroText", "AccountStateText", "FriendsIntroText", "FriendsPendingText" })
                Check(window.FindName(name) is null, "redundant description remains: " + name);
            Check(Control<TextBlock>("AccountHeaderNameText").Text == "FixturePaw", "header nickname stale after login");
            var avatar = AvatarFixture();
            var normalized = AccountAvatarImage.Decode(avatar, normalized: true);
            Check(normalized.PixelWidth == 256 && normalized.PixelHeight == 256 && avatar.Length <= 204800, "avatar not normalized/bounded");
            using (var encoded = new MemoryStream(avatar))
            {
                var frame = BitmapDecoder.Create(encoded, BitmapCreateOptions.None, BitmapCacheOption.OnLoad).Frames[0];
                Check(frame.Metadata is not BitmapMetadata metadata || !metadata.ContainsQuery("/app1/ifd/gps"), "avatar retains location metadata");
            }
            Invoke("SetAccountAvatar", user, avatar);
            Check(Control<System.Windows.Shapes.Ellipse>("AccountAvatarPicture").Visibility == Visibility.Visible && Control<System.Windows.Shapes.Ellipse>("AccountProfileAvatarPicture").Visibility == Visibility.Visible, "avatar missing from header/profile");
            Check(Control<System.Windows.Shapes.Ellipse>("AccountAvatarPicture").Fill == Control<System.Windows.Shapes.Ellipse>("AccountProfileAvatarPicture").Fill, "avatar mismatch between surfaces");
            Invoke("SetAccountAvatar", "not-current-user", null);
            Check(Control<System.Windows.Shapes.Ellipse>("AccountAvatarPicture").Visibility == Visibility.Visible, "stale account response cleared current avatar");
            Invoke("SetAccountAvatar", user, null);
            Check(Control<System.Windows.Shapes.Ellipse>("AccountAvatarPicture").Visibility == Visibility.Collapsed, "removed avatar still visible");
            foreach (var invalid in new[] { new byte[0], new byte[100], new byte[AccountAvatarImage.MaxInputBytes + 1] })
            {
                try { AccountAvatarImage.Normalize(invalid); throw new Exception("Invalid image accepted"); }
                catch (AccountException error) { Check(error.Code is "invalid_avatar" or "avatar_too_large", "image error not sanitized"); }
            }
            Check(window.FindName("FriendsProfileButton") is null, "signed-in friends still links to profile");
            Check(Control<StackPanel>("FriendsSignedInPanel").Visibility == Visibility.Visible, "signed-in friends empty state absent");
            Check(Control<Button>("AccountHeaderButton").BorderBrush.ToString() == "#00000000", "account highlight remains on Friends page");
            Invoke("ShowAccountEditor", "delete");
            Check(Control<StackPanel>("AccountCurrentPasswordPanel").Visibility == Visibility.Visible && Control<StackPanel>("AccountNewPasswordPanel").Visibility == Visibility.Collapsed && Control<StackPanel>("AccountEditValuePanel").Visibility == Visibility.Collapsed, "delete must show current password only");
            Invoke("ShowAccountEditor", "nickname");
            Check(Control<Border>("AccountEditorCard").Visibility == Visibility.Visible && Control<StackPanel>("AccountCurrentPasswordPanel").Visibility == Visibility.Collapsed, "nickname editor fields");
            Invoke("ShowAccountEditor", "email");
            Check(Control<StackPanel>("AccountCurrentPasswordPanel").Visibility == Visibility.Visible && Control<StackPanel>("AccountNewPasswordPanel").Visibility == Visibility.Collapsed, "email editor fields");
            Invoke("ShowAccountEditor", "password");
            Check(Control<StackPanel>("AccountNewPasswordPanel").Visibility == Visibility.Visible && Control<StackPanel>("AccountEditValuePanel").Visibility == Visibility.Collapsed, "password editor fields");
            Control<PasswordBox>("AccountCurrentPasswordInput").Password = "fixture-old";
            Control<PasswordBox>("AccountNewPasswordInput").Password = "fixture-new";
            Invoke("SetActivePage", "settings");
            Check(Control<PasswordBox>("AccountCurrentPasswordInput").Password == "" && Control<PasswordBox>("AccountNewPasswordInput").Password == "", "editor retains password when leaving");
            Invoke("AccountHeader_Click", Control<Button>("AccountHeaderButton"), new RoutedEventArgs());
            Check(Control<StackPanel>("AccountPanel").Visibility == Visibility.Visible && Control<StackPanel>("FriendsPanel").Visibility == Visibility.Collapsed && Control<Border>("AccountEditorCard").Visibility == Visibility.Collapsed, "header does not open separate profile overview");
            Invoke("ShowAccountEditor", "delete");
            Control<PasswordBox>("AccountCurrentPasswordInput").Password = "fixture-delete-cancel";
            var beforeDeleteRequests = requests;
            var deletion = (Task)Invoke("SubmitAccountEditorAsync")!;
            Check(Control<FrameworkElement>("ConfirmationOverlay").Visibility == Visibility.Visible, "delete confirmation overlay missing");
            Check(!Control<FrameworkElement>("MainBody").IsEnabled && !Control<FrameworkElement>("TitleBar").IsEnabled, "delete confirmation did not reserve UI");
            await (Task)Invoke("CompleteConfirmationAsync", false)!; await deletion;
            Check(requests == beforeDeleteRequests, "cancelled deletion reached server");
            Check(Control<PasswordBox>("AccountCurrentPasswordInput").Password == "", "cancelled deletion retained password");
            Invoke("AccountHeader_Click", Control<Button>("AccountHeaderButton"), new RoutedEventArgs());

            // Diagnostic archive uses an explicit allowlist; verify it cannot collect our session.
            var defaultVault = new AccountSessionStore(ActivityStore.Root);
            using (await defaultVault.LockAsync(CancellationToken.None)) defaultVault.Save(vault.Read()!);
            var archive = Path.Combine(ActivityStore.Root, "account-privacy-check-"+Guid.NewGuid().ToString("N")+".zip");
            await DiagnosticsCollector.CreateLauncherOnlyAsync(archive);
            using (var zip = System.IO.Compression.ZipFile.OpenRead(archive))
                Check(!zip.Entries.Any(e => e.FullName.Contains("session", StringComparison.OrdinalIgnoreCase) || e.FullName.Contains("account", StringComparison.OrdinalIgnoreCase)), "session leaked into diagnostics");
            defaultVault.Clear();

            ((AccountService)typeof(MainWindow).GetField("_account", flags)!.GetValue(window)!).Dispose();
            var recoveryCalls = 0;
            typeof(MainWindow).GetField("_account", flags)!.SetValue(window, new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root, "recovery-ui-" + Guid.NewGuid().ToString("N"))),
                new Handler(_ => { recoveryCalls++; return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("{}") }); })));
            Invoke("RenderAccount"); Invoke("ShowAccountForm", false);
            Check(Control<Button>("AccountForgotButton").Visibility == Visibility.Visible, "forgot password absent from login");
            Control<CheckBox>("AccountRememberCheck").IsChecked = false;
            Check(Control<TextBlock>("AccountRememberText").Text.Contains(language == "ru" ? "на этот запуск" : "this launch only"), "remember explanation not switched");
            Invoke("ShowAccountForm", true);
            Check(Control<Button>("AccountForgotButton").Visibility == Visibility.Collapsed && Control<CheckBox>("AccountRememberCheck").Visibility == Visibility.Visible, "registration mode controls wrong");
            Invoke("ShowAccountForm", false);
            Invoke("AccountForgot_Click", Control<Button>("AccountForgotButton"), new RoutedEventArgs());
            Check(Control<Border>("AccountRecoveryCard").Visibility == Visibility.Visible && Control<Border>("AccountFormCard").Visibility == Visibility.Collapsed, "recovery form not isolated");
            await (Task)Invoke("SubmitRecoveryAsync")!;
            Check(recoveryCalls == 1 && Control<StackPanel>("AccountRecoveryProofPanel").Visibility == Visibility.Visible, "recovery email step failed");
            Check(!Control<TextBox>("AccountRecoveryEmailInput").IsEnabled, "recovery target can change after sending");
            var codeInput = Control<TextBox>("AccountRecoveryProofInput");
            Check(codeInput.MaxLength == 6 && codeInput.Width == 206 && !codeInput.IsUndoEnabled, "code input not compact/six-digit/private");
            Check(Control<TextBlock>("AccountRecoveryProofLabel").Text.Contains("6") && !Control<TextBlock>("AccountRecoveryHintText").Text.Contains(language == "ru" ? "ссылк" : "link"), "legacy link instructions retained");
            Check(!Control<Button>("AccountRecoverySubmitButton").IsEnabled, "empty code can submit");
            codeInput.Text = "00123";
            Check(!Control<Button>("AccountRecoverySubmitButton").IsEnabled, "partial code can submit");
            codeInput.Text = "001234";
            Check(Control<Button>("AccountRecoverySubmitButton").IsEnabled, "complete code cannot submit");
            foreach (var typed in new[] { "a", " ", "７", "12" })
            {
                codeInput.Select(5, 1);
                var textEvent = new TextCompositionEventArgs(InputManager.Current.PrimaryKeyboardDevice, new TextComposition(InputManager.Current, codeInput, typed)) { RoutedEvent = TextCompositionManager.PreviewTextInputEvent };
                Invoke("AccountRecoveryCode_PreviewTextInput", codeInput, textEvent);
                Check(textEvent.Handled, "invalid keyboard input accepted");
            }
            var digitEvent = new TextCompositionEventArgs(InputManager.Current.PrimaryKeyboardDevice, new TextComposition(InputManager.Current, codeInput, "0")) { RoutedEvent = TextCompositionManager.PreviewTextInputEvent };
            Invoke("AccountRecoveryCode_PreviewTextInput", codeInput, digitEvent);
            Check(!digitEvent.Handled, "valid replacement digit rejected");
            Check(!Control<Button>("AccountRecoveryResendButton").IsEnabled, "resend ignores cooldown");
            await (Task)Invoke("ResendRecoveryCodeAsync")!;
            Check(recoveryCalls == 1, "rapid resend reached network");
            codeInput.SelectAll();
            var paste = new DataObjectPastingEventArgs(new DataObject(DataFormats.UnicodeText, " 001 234\r\n"), false, DataFormats.UnicodeText);
            Invoke("AccountRecoveryCode_Pasting", codeInput, paste);
            Check(!paste.CommandCancelled && (string)paste.DataObject.GetData(DataFormats.UnicodeText) == "001234", "spaced code paste not normalized");
            foreach (var invalidPaste in new[] { "1234567", "12345678", "https://example.invalid/?token=123456", "１２３４５６", "Code: 123456" })
            {
                paste = new DataObjectPastingEventArgs(new DataObject(DataFormats.UnicodeText, invalidPaste), false, DataFormats.UnicodeText);
                Invoke("AccountRecoveryCode_Pasting", codeInput, paste);
                Check(paste.CommandCancelled, "invalid paste accepted/truncated");
            }
            typeof(MainWindow).GetField("_recoveryRequestAfter", flags)!.SetValue(window, DateTimeOffset.UtcNow.AddSeconds(-1));
            Invoke("RenderAccountCooldown");
            Check(Control<Button>("AccountRecoveryResendButton").IsEnabled, "resend did not unlock");
            await (Task)Invoke("ResendRecoveryCodeAsync")!;
            Check(recoveryCalls == 2 && codeInput.Text == "" && !Control<Button>("AccountRecoveryResendButton").IsEnabled, "resend failed to clear code/restart cooldown");
            codeInput.Text = "123456";
            Invoke("SetActivePage", "home");
            Check(codeInput.Text == "", "recovery proof retained outside account page");
            Invoke("AccountHeader_Click", Control<Button>("AccountHeaderButton"), new RoutedEventArgs());
            Check(Control<Border>("AccountFormCard").Visibility == Visibility.Visible, "header cannot return to sign-in tabs");

            foreach (var size in new[] { new Size(1050, 680), new Size(1440, 900) })
            {
                var content = (FrameworkElement)window.Content;
                content.Measure(size); content.Arrange(new Rect(size)); content.UpdateLayout();
                var button = Control<Button>("FriendsNav");
                var bounds = button.TransformToAncestor(content).TransformBounds(new Rect(button.RenderSize));
                Check(bounds.Left >= 0 && bounds.Right <= size.Width && bounds.Top >= 0 && bounds.Bottom <= size.Height, "navigation clipped");
                Check(Control<TextBlock>("FriendsTitleText").FontSize == 18, "title scale inconsistent");
                var header = Control<Button>("AccountHeaderButton");
                bounds = header.TransformToAncestor(content).TransformBounds(new Rect(header.RenderSize));
                var ready = Control<Border>("ReadyStatusBadge");
                var readyBounds = ready.TransformToAncestor(content).TransformBounds(new Rect(ready.RenderSize));
                Check(bounds.Left >= readyBounds.Right && bounds.Right <= size.Width && bounds.Bottom <= size.Height, "account header clipped/overlapping status");
                Check(header.Width <= 100 && Control<Border>("AccountAvatarBorder").Width >= 48, "compact header or larger avatar lost");
            }
            Console.WriteLine($"ACCOUNT UI PASS {checks} {language}: guest, registration/login, secure input, async guards, navigation, persisted profile and diagnostic exclusion; no real Auth requests");
        }
        try
        {
            var task = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(15) };
            var deadline = DateTime.UtcNow.AddSeconds(20);
            timer.Tick += (_, _) => { if (task.IsCompleted || DateTime.UtcNow > deadline) frame.Continue = false; };
            timer.Start(); Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Account UI checks timed out.");
            task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }

    internal static void Populate(MainWindow window, string mode)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Account fixtures require smoke mode.");
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        object? Invoke(string method, params object?[] args) => typeof(MainWindow).GetMethod(method, flags)!.Invoke(window, args);
        if (mode is "register" or "login" or "recovery" or "confirmation-error" or "password-visible")
        {
            Invoke("ShowAccountForm", mode == "register");
            ((TextBox)window.FindName("AccountEmailInput")).Text = "player@example.invalid";
            ((TextBox)window.FindName("AccountNicknameInput")).Text = "Paw";
            ((TextBox)window.FindName("AccountDisplayNameInput")).Text = "Paw";
            ((PasswordBox)window.FindName("AccountPasswordInput")).Password = "fixture-password";
            ((PasswordBox)window.FindName("AccountRepeatInput")).Password = "fixture-password";
            if (mode == "password-visible") ((CheckBox)window.FindName("AccountShowPasswordCheck")).IsChecked = true;
            if (mode == "confirmation-error")
            {
                typeof(MainWindow).GetField("_accountMessage", flags)!.SetValue(window, "email_not_confirmed");
                typeof(MainWindow).GetField("_accountConfirmation", flags)!.SetValue(window, true);
                Invoke("RenderAccount");
            }
            if (mode == "recovery")
            {
                Invoke("AccountForgot_Click", window, new RoutedEventArgs());
                typeof(MainWindow).GetField("_accountRecoverySent", flags)!.SetValue(window, true);
                Invoke("RenderAccount");
            }
            return;
        }
        var id = Guid.NewGuid().ToString();
        var handler = new Handler(r => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(r.RequestUri!.AbsolutePath.EndsWith("/token")
            ? JsonSerializer.Serialize(new { access_token = "fixture-access", refresh_token = "fixture-refresh", expires_in = 3600, user = new { id, email = "player@example.invalid" } })
            : JsonSerializer.Serialize(new[] { new { id, nickname = "Paw", created_at = "2026-09-07T12:00:00Z", nickname_changed_at = DateTimeOffset.UtcNow.AddMinutes(-2), email_changed_at = DateTimeOffset.UtcNow.AddMinutes(-1), password_changed_at = DateTimeOffset.UtcNow.AddMinutes(-3) } })) }));
        var service = new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root, "profile-preview-" + Guid.NewGuid().ToString("N"))), handler);
        service.SignInAsync("player@example.invalid", "fixture-password", remember: false).GetAwaiter().GetResult();
        ((AccountService)typeof(MainWindow).GetField("_account", flags)!.GetValue(window)!).Dispose();
        typeof(MainWindow).GetField("_account", flags)!.SetValue(window, service);
        Invoke("RenderAccount");
        if (mode == "avatar") Invoke("SetAccountAvatar", id, AvatarFixture());
        if (mode == "logout-confirmation") Invoke("ConfirmAccountLogoutAsync");
        if (mode is "nickname" or "email" or "password" or "delete") Invoke("ShowAccountEditor", mode);
        if (mode == "delete-confirmation")
        {
            Invoke("ShowAccountEditor", "delete");
            ((PasswordBox)window.FindName("AccountCurrentPasswordInput")).Password = "fixture-delete-cancel";
            Invoke("SubmitAccountEditorAsync"); // The preview only renders; Close resolves the confirmation as Cancel.
        }
    }
    internal static byte[] AvatarFixture()
    {
        var visual = new DrawingVisual();
        using (var drawing = visual.RenderOpen())
        {
            drawing.DrawRectangle(Brushes.SteelBlue, null, new Rect(0,0,512,256));
            drawing.DrawEllipse(Brushes.Goldenrod, null, new Point(256,128),90,90);
        }
        var bitmap = new RenderTargetBitmap(512,256,96,96,PixelFormats.Pbgra32); bitmap.Render(visual);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var output = new MemoryStream(); encoder.Save(output);
        return AccountAvatarImage.Normalize(output.ToArray());
    }
    private sealed class Handler(Func<HttpRequestMessage, Task<HttpResponseMessage>> response) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
            request.RequestUri!.AbsolutePath.EndsWith("/paw_launcher_session")
                ? Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("{\"status\":\"ok\"}") }) : response(request);
    }
}
