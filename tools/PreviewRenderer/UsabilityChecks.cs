using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class UsabilityChecks
{
    internal static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated profile required");
        Directory.CreateDirectory(output);
        new SettingsStore().Save(new UserSettings { Language = language, ModNoticeSeen = true });
        var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [] }, null)
        { Width = 1440, Height = 960, Left = -30000, Top = -30000, ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        T C<T>(string name) => (T)w.FindName(name);
        int checks = 0; void Check(bool value, string why) { checks++; if (!value) throw new Exception("Usability UI: " + why); }
        void Snap(string name, FrameworkElement element)
        {
            w.UpdateLayout(); element.UpdateLayout();
            if (element.ActualWidth < 1 || element.ActualHeight < 1) throw new Exception("Empty screenshot: " + name);
            if (element.Name == "SocialDetailsCard")
            {
                var root = (FrameworkElement)w.Content;
                var bounds = element.TransformToAncestor(root).TransformBounds(new Rect(element.RenderSize));
                var full = new RenderTargetBitmap((int)Math.Ceiling(root.ActualWidth), (int)Math.Ceiling(root.ActualHeight), 96, 96, PixelFormats.Pbgra32); full.Render(root);
                var crop = new CroppedBitmap(full, new Int32Rect((int)Math.Floor(bounds.X), (int)Math.Floor(bounds.Y), (int)Math.Ceiling(bounds.Width), (int)Math.Ceiling(bounds.Height)));
                var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(crop)); using var file = File.Create(Path.Combine(output, name + "-" + language + ".png")); encoder.Save(file); return;
            }
            var visual = new DrawingVisual(); using (var dc = visual.RenderOpen())
            {
                dc.DrawRectangle(new SolidColorBrush(Color.FromRgb(16, 34, 56)), null, new Rect(element.RenderSize));
                var brush = new VisualBrush(element);
                if (element.Parent is Window) { brush.ViewboxUnits = BrushMappingMode.Absolute; brush.Viewbox = new Rect(element.RenderSize); brush.Stretch = Stretch.Fill; }
                dc.DrawRectangle(brush, null, new Rect(element.RenderSize));
            }
            var bmp = new RenderTargetBitmap((int)Math.Ceiling(element.ActualWidth), (int)Math.Ceiling(element.ActualHeight), 96, 96, PixelFormats.Pbgra32); bmp.Render(visual);
            var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(bmp)); using var stream = File.Create(Path.Combine(output, name + "-" + language + ".png")); png.Save(stream);
        }
        async Task CaptureDialog(string name, Window dialog)
        {
            dialog.WindowStartupLocation = WindowStartupLocation.Manual; dialog.Left = -30000; dialog.Top = -30000; dialog.ShowActivated = false; dialog.ShowInTaskbar = false;
            dialog.Show(); await Task.Delay(150); dialog.UpdateLayout(); Snap(name, (FrameworkElement)dialog.Content); dialog.Close();
        }
        async Task Scenario()
        {
            AccountChecks.Populate(w, "avatar"); Call("SetActivePage", "account");
            Check(C<Border>("ProfileVisibilityCard").IsDescendantOf(C<Border>("AccountSignedInCard")) && C<Border>("ProfileVisibilityCard").IsVisible, "privacy lives in the signed-in profile tab");
            Call("SetActivePage", "settings"); Check(!C<Border>("ProfileVisibilityCard").IsVisible, "general launcher settings no longer display profile privacy");
            Call("SetActivePage", "account");
            var savedVisibility = new ProfileVisibility(); bool failSave = false, failRead = true; int saves = 0;
            Set("_visibilityOverride", new Func<ProfileVisibility?, CancellationToken, Task<ProfileVisibility>>((value, _) =>
            {
                if (value is null && failRead) throw new AccountException("network_error");
                if (value is not null) { if (failSave) throw new AccountException("network_error"); savedVisibility = value; saves++; }
                return Task.FromResult(savedVisibility);
            }));
            await (Task)Call("LoadProfileVisibilityAsync")!;
            var privacyOwner = Field<AccountService>("_account").UserId;
            Check(!(bool)Call("ShouldRefreshProfileVisibility", privacyOwner, DateTimeOffset.UtcNow)!, "failed initial load backs off instead of flooding requests");
            Check((bool)Call("ShouldRefreshProfileVisibility", privacyOwner, DateTimeOffset.UtcNow.AddSeconds(31))!, "failed initial load retries automatically without a reload button");
            Check((bool)Call("ShouldRefreshProfileVisibility", Guid.NewGuid().ToString(), DateTimeOffset.UtcNow)!, "new account is not delayed by another account's retry schedule");
            failRead = false; await (Task)Call("LoadProfileVisibilityAsync")!;
            Check(C<ComboBox>("ConfigurationVisibilityCombo").IsEnabled, "signed-in account loads server-authoritative preferences");
            Check(w.FindName("ReloadProfileVisibilityButton") is null, "manual reload button removed");
            Check(C<Button>("SaveProfileVisibilityButton").Content.ToString() == UiLanguages.Text(language, "Сохранить", "Save"), "save button uses the concise label");
            C<ComboBox>("ConfigurationVisibilityCombo").SelectedIndex = 1; C<ComboBox>("ActivityVisibilityCombo").SelectedIndex = 2;
            await (Task)Call("SaveProfileVisibilityAsync")!;
            Check(saves == 1 && savedVisibility == new ProfileVisibility("friends", "nobody"), "independent privacy selections save once to the account");
            await Task.Delay(100); Snap("privacy-settings", C<Border>("ProfileVisibilityCard"));
            Snap("privacy-in-profile", (FrameworkElement)w.Content);
            Set("_visibilityReadAt", DateTimeOffset.UtcNow.AddMinutes(-2));
            Check((bool)Call("ShouldRefreshProfileVisibility", privacyOwner, DateTimeOffset.UtcNow)!, "unchanged selections refresh after a minute");
            failSave = true; C<ComboBox>("ConfigurationVisibilityCombo").SelectedIndex = 0; await (Task)Call("SaveProfileVisibilityAsync")!;
            Check(!(bool)Call("ShouldRefreshProfileVisibility", privacyOwner, DateTimeOffset.UtcNow)!, "automatic refresh never overwrites an unsaved selection");
            Check(savedVisibility.Configuration == "friends" && C<TextBlock>("ProfileVisibilityStatus").Text == UiLanguages.Text(language, "Не удалось сохранить. Прежняя видимость остаётся в силе. Повторите попытку.", "Could not save. Your previous visibility remains in effect. Try again."), "failed privacy save never claims success or changes server policy");
            failSave = false; await (Task)Call("LoadProfileVisibilityAsync")!;
            Check(C<ComboBox>("ConfigurationVisibilityCombo").SelectedIndex == 1, "refresh restores the actual saved account policy");
            Call("SetActivePage", "settings");
            C<ComboBox>("DownloadLimitCombo").SelectedIndex = 2;
            Check(Field<FeedClient>("_feedClient").Downloads.LimitKiB == 1024 && new SettingsStore().Load().DownloadLimitKiB == 1024, "rate selection persists and reaches only file transport");
            Snap("download-settings", C<Border>("DownloadSettingsCard"));

            Call("SetActivePage", "home"); Call("SetBusy", true, "Download fixture");
            using var cancellation = new CancellationTokenSource(); Set("_downloadCancellation", cancellation);
            var progress = (IProgress<(long Received, long? Total)>)Call("TransferProgress", "Paw’s Patch")!;
            progress.Report((24 * 1024 * 1024L, 64 * 1024 * 1024L)); await Task.Delay(240); w.UpdateLayout();
            Check(C<StackPanel>("DownloadControls").IsVisible, "pause and stop remain visible without expanding statistics");
            Call("OperationDetails_Click", C<Button>("OperationDetailsButton"), new RoutedEventArgs()); await Task.Delay(250);
            Snap("download-active", C<Border>("OperationStatusPanel"));
            C<Button>("PauseDownloadButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(Field<FeedClient>("_feedClient").Downloads.IsPaused && Field<bool>("_busy"), "pause keeps the operation alive without blocking metadata UI");
            Snap("download-paused", C<Border>("OperationStatusPanel"));
            Call("SetActivePage", "account"); Check(C<Border>("ProfileVisibilityCard").IsVisible, "profile privacy remains accessible during paused transfer");
            C<Button>("CancelDownloadButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(cancellation.IsCancellationRequested && !Field<FeedClient>("_feedClient").Downloads.IsPaused, "stop cancels paused transport promptly");
            Set("_downloadCancellation", null); Call("SetBusy", false, null);

            var selection = Field<UserSettings>("_settings");
            var pending = new PendingInstallation(Path.Combine(ActivityStore.Root, "fixture-game"), ConfigurationCode.Create(selection), selection.Channel, new string('A', 64), DateTimeOffset.UtcNow);
            new PendingInstallationStore().Save(pending); Set("_pendingInstall", pending); Call("RefreshDownloadControls"); Call("SetActivePage", "home");
            Snap("resume-after-restart", C<Border>("PendingInstallationCard"));
            var reloaded = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [] }, null);
            Check(((Border)reloaded.FindName("PendingInstallationCard")).Visibility == Visibility.Visible
                && ((Border)reloaded.FindName("OperationStatusPanel")).Visibility == Visibility.Visible, "fresh launcher presents unfinished install even without active feedback"); reloaded.Close();
            Call("ShowError", new HttpRequestException("Fixture service unavailable", null, HttpStatusCode.ServiceUnavailable));
            Check(C<Button>("RetryInstallationButton").IsVisible && C<TextBlock>("ErrorRecoveryHint").Text.Length > 50, "error explains recovery and exposes retry for persisted installation");
            Snap("error-with-retry", C<StackPanel>("ErrorActionsPanel"));
            await CaptureDialog("error-explanation", (Window)Call("CreateFriendlyErrorDialog")!);
            Call("ForgetInstallation"); Call("ClearFriendlyError"); Call("ClearToastStack");

            var peerSettings = ConfigurationCode.Parse(FriendConfiguration.Create(selection)); peerSettings.RoamingSpawnMode = "x2"; peerSettings.IgnoreZeroMorale = true; peerSettings.CustomPlayerColors = !selection.CustomPlayerColors;
            var peer = new SocialPlayer(Guid.NewGuid(), "nightwatch", "friend", Presence: "playing", PlayingSince: DateTimeOffset.UtcNow.AddMinutes(-37), Channel: peerSettings.Channel,
                Configuration: FriendConfiguration.Create(peerSettings), DisplayName: "Nightwatch", Activity: new GameActivity("match", true, 540, 192, 256));
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { peer }); Call("ShowSocialDetails", peer);
            Check(C<Button>("CompareProfileButton").IsVisible, "full profile exposes a comparison without applying settings");
            await CaptureDialog("gameplay-comparison", (Window)Call("CreateGameplayComparisonDialog", peer)!);
            foreach (var (name, hideSettings, hideActivity) in new[] { ("profile-hidden-all", true, true), ("profile-hidden-settings", true, false), ("profile-hidden-activity", false, true) })
            {
                var hidden = peer with { Configuration = hideSettings ? null : peer.Configuration, Components = "{}", Activity = hideActivity ? null : peer.Activity,
                    ConfigurationHidden = hideSettings, ActivityHidden = hideActivity };
                Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { hidden }); Call("RenderSocialDetails", hidden); await Task.Delay(130);
                Check(C<Border>("SocialDetailsPrivacyNotice").IsVisible && C<TextBlock>("SocialDetailsPrivacyText").Text.Length > 10, "profile explicitly describes " + name);
                if (hideSettings && hideActivity) Check(C<TextBlock>("SocialDetailsPrivacyText").Text == UiLanguages.Text(language, "Игрок скрыл игровые настройки и активность.", "This player has hidden gameplay settings and activity."), "all-hidden explanation names both kinds of data");
                Check(C<Button>("CompareProfileButton").IsVisible == !hideSettings, "hidden settings cannot be compared or reconstructed");
                Snap(name, C<Border>("SocialDetailsCard"));
            }
            w.Width = 1050; w.Height = 680;
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { peer }); Call("RenderSocialDetails", peer); w.UpdateLayout(); await Task.Delay(120);
            var content = (FrameworkElement)w.Content;
            var cardBounds = C<Border>("SocialDetailsCard").TransformToAncestor(content).TransformBounds(new Rect(C<Border>("SocialDetailsCard").RenderSize));
            Check(cardBounds.Top >= 0 && cardBounds.Bottom <= content.ActualHeight + 1, "profile with comparison fits the minimum launcher height");
            Snap("profile-compare-entry", C<Border>("SocialDetailsCard"));
            w.Width = 1440; w.Height = 960;
            Call("CloseSocialDetails");
            var watch = Stopwatch.StartNew(); double longest = 0;
            for (int i = 0; i < 20; i++) { var before = watch.Elapsed.TotalMilliseconds; Call("SetActivePage", i % 2 == 0 ? "settings" : "modules"); w.UpdateLayout(); longest = Math.Max(longest, watch.Elapsed.TotalMilliseconds - before); }
            Check(longest < 2000, "page switching never performs a multi-second synchronous operation in the isolated fixture");
            File.WriteAllText(Path.Combine(output, "ui-responsiveness-" + language + ".txt"), $"20 page switches: {watch.Elapsed.TotalMilliseconds:0.0}ms; max {longest:0.0}ms. Mocked social transport; no game launched.");
            Console.WriteLine($"USABILITY UI PASS {checks} {language}; twenty page switches max {longest:0.0}ms; mocked account/mutations, no game launched");
        }
        try
        {
            w.Show(); var task = w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame = new DispatcherFrame();
            var deadline = new DispatcherTimer { Interval = TimeSpan.FromSeconds(55) }; deadline.Tick += (_, _) => frame.Continue = false;
            _ = task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false)); deadline.Start(); Dispatcher.PushFrame(frame); deadline.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Usability UI fixture"); task.GetAwaiter().GetResult();
        }
        finally { Set("_busy", false); w.Close(); }
    }
}
