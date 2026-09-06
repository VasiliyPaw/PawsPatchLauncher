using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class FeedbackChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Feedback checks require --smoke-test.");
        var window = new MainWindow
        {
            Left = -32000,
            Top = -32000,
            ShowActivated = false,
            ShowInTaskbar = false,
            WindowStartupLocation = WindowStartupLocation.Manual,
            Width = 1050,
            Height = 680
        };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Invoke(string name, params object?[] values) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(window, values);
        object Field(string name) => typeof(MainWindow).GetField(name, flags)!.GetValue(window)!;
        void Set(string name, object value) => typeof(MainWindow).GetField(name, flags)!.SetValue(window, value);
        Task<bool> Copy(string value) => (Task<bool>)Invoke("CopyTextAsync", value, (Func<string>)(() => value + " copied"), null)!;
        Task<bool> Paste(TextBox target) => (Task<bool>)Invoke("PasteTextAsync", target)!;
        ExternalException Busy() => new("Synthetic clipboard contention", unchecked((int)0x800401D0));
        var tests = 0;
        void Check(bool value, string message) { if (!value) throw new InvalidOperationException(message); tests++; }
        async Task Scenario()
        {
            ((PawsPatchLauncher.Localization)Field("_text")).SetLanguage(language); Invoke("ApplyLanguage");
            Invoke("SetActivePage", "multiplayer");
            var snapshot = JsonSerializer.Serialize(Field("_settings"));
            var toast = (OperationFeedback)Field("_toast");
            var toastPanel = (Border)window.FindName("ToastPanel");
            var operation = (TextBlock)window.FindName("OperationText");
            var feedback = (OperationFeedback)Field("_feedback");
            Invoke("ShowWorking", (Func<string>)(() => "unchanged download status"));
            int calls = 0;
            string? written = null;
            Set("_clipboardWrite", (Action<string>)(text =>
            {
                Check(window.Dispatcher.CheckAccess(), "Clipboard writer left the STA dispatcher.");
                if (++calls < 3) throw Busy();
                written = text;
            }));
            Check(await Copy("first") && written == "first" && calls == 3, "Retry did not eventually copy.");
            Check(toast.Message == "first copied" && !toast.Failed, "Successful copy did not notify.");
            calls = 0;
            Set("_clipboardWrite", (Action<string>)(_ => { calls++; throw Busy(); }));
            Check(!await Copy("never") && calls == 6 && written == "first", "Failed copy claimed success.");
            Check(toast.Failed && !toast.Message!.Contains("copied"), "Old success survived a failed retry.");
            Check(feedback.Working && operation.Text == "unchanged download status", "Clipboard feedback replaced download status.");
            Set("_clipboardWrite", (Action<string>)(text => { if (text == "old") throw Busy(); written = text; }));
            var oldRequest = Copy("old"); await Task.Delay(5);
            Check(await Copy("new") && !await oldRequest && written == "new", "Older copy overwrote a newer request.");
            Check(toast.Message == "new copied", "Superseded result changed the notification.");
            var input = (TextBox)Field("_importInput"); input.Text = "original";
            Set("_clipboardRead", (Func<string>)(() => "")); await Paste(input);
            Check(input.Text == "original", "Empty clipboard erased an input.");
            Set("_clipboardRead", (Func<string>)(() => new string('X', 500))); await Paste(input);
            Check(input.Text == "original" && toast.Failed, "Oversize clipboard text was silently truncated.");
            calls = 0;
            Set("_clipboardRead", (Func<string>)(() => ++calls < 3 ? throw Busy() : "delayed"));
            var pendingPaste = Paste(input); input.Text = "new user edit"; await pendingPaste;
            Check(input.Text == "new user edit", "Delayed paste overwrote typing.");
            Set("_clipboardRead", (Func<string>)(() => "PAW-BETA-code"));
            await Paste(input);
            Check(input.Text == "PAW-BETA-code", "Paste did not reach its destination.");
            Check(JsonSerializer.Serialize(Field("_settings")) == snapshot, "Clipboard action applied game settings.");
            Invoke("ToastCloseButton_Click", toastPanel, new RoutedEventArgs());
            Invoke("ShowToast", (Func<string>)(() => "new notification"), false);
            await Task.Delay(260);
            Check(toastPanel.Visibility == Visibility.Visible && toast.Message == "new notification", "Old close hid a newer toast.");
            // Test the normal expiry path without making the suite wait five seconds.
            toast.Show(() => "expires", duration: TimeSpan.FromMilliseconds(35)); Invoke("RefreshToast");
            await Task.Delay(500);
            Check(toastPanel.Visibility == Visibility.Collapsed, "Expired toast remained visible.");
            Check(operation.Text == "unchanged download status", "Toast expiry touched operation status.");
            Invoke("ShowToast", (Func<string>)(() => language == "ru"
                ? "Буфер обмена занят. Подождите немного и повторите действие."
                : "The clipboard is busy. Wait a moment and try again."), true);
            window.UpdateLayout();
            var content = (FrameworkElement)window.Content;
            var bounds = toastPanel.TransformToAncestor(content).TransformBounds(new Rect(toastPanel.RenderSize));
            var options = (ScrollViewer)window.FindName("MainOptionsScroll");
            var optionsRight = options.TranslatePoint(new Point(options.ActualWidth, 0), content).X;
            var launch = (Button)window.FindName("LaunchButton");
            Check(bounds.Right < optionsRight && bounds.Bottom < launch.TranslatePoint(new Point(), content).Y,
                "Toast covers the status column or launch controls.");
            Check(toastPanel.ActualHeight < 160 && toastPanel.ActualWidth > 180, "Toast is not compact.");
            Invoke("SetActivePage", "settings");
            if (SystemParameters.ClientAreaAnimation) Check(options.Opacity < 1, "Page switch did not fade.");
            Invoke("SetActivePage", "home"); await Task.Delay(230);
            Check((string)Field("_activePage") == "home" && Math.Abs(options.Opacity - 1) < 0.001, "Rapid navigation left stale/transparent content.");
            var helpButton = new Button { Tag = "modules.colors" };
            Invoke("HelpButton_Click", helpButton, new RoutedEventArgs());
            var help = (Border)window.FindName("HelpOverlay");
            if (SystemParameters.ClientAreaAnimation) Check(help.Opacity < 1, "Help did not fade in.");
            Invoke("HelpCloseButton_Click", helpButton, new RoutedEventArgs()); await Task.Delay(25);
            Invoke("HelpButton_Click", helpButton, new RoutedEventArgs()); await Task.Delay(250);
            Check(help.Visibility == Visibility.Visible && Math.Abs(help.Opacity - 1) < 0.001, "Old fade-out closed reopened help.");
            Invoke("HelpCloseButton_Click", helpButton, new RoutedEventArgs()); await Task.Delay(220);
            Check(help.Visibility == Visibility.Collapsed, "Help did not close after fading.");
            Set("_clipboardWrite", (Action<string>)(_ => throw Busy()));
            var closingCopy = Copy("closing"); window.Close();
            Check(!await closingCopy, "Closing the launcher did not cancel clipboard retries.");
            Console.WriteLine($"FEEDBACK UI PASS {tests} {language}: safe STA retries, truthful notifications, races, paste, status isolation, expiry, bounds, page/help fades; simulated clipboard only");
        }
        try
        {
            window.Show();
            var work = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var watchdog = new DispatcherTimer { Interval = TimeSpan.FromSeconds(20) };
            watchdog.Tick += (_, _) => frame.Continue = false;
            work.ContinueWith(_ => window.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            watchdog.Start();
            try { Dispatcher.PushFrame(frame); } finally { watchdog.Stop(); }
            if (!work.IsCompleted) throw new TimeoutException("Feedback UI checks did not finish.");
            work.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}
