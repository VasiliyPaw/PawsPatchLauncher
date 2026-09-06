using PawsPatchLauncher;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Controls;

namespace PreviewRenderer;

public static class Program
{
    [STAThread]
    public static void Main(string[] args)
    {
        var language = args.FirstOrDefault(arg => arg.StartsWith("--language="))?.Split('=')[1] ?? "ru";
        var width = int.Parse(args.FirstOrDefault(arg => arg.StartsWith("--width="))?.Split('=')[1] ?? "1440");
        var height = int.Parse(args.FirstOrDefault(arg => arg.StartsWith("--height="))?.Split('=')[1] ?? "900");
        args = args.Where(arg => !arg.StartsWith("--")).ToArray();
        if (args.Length is < 1 or > 3) throw new ArgumentException("Pass the output PNG path, an optional page name, and an optional vertical offset.");
        var app = new App();
        app.InitializeComponent();
        var window = new MainWindow();
        if (window.Width > SystemParameters.WorkArea.Width || window.Height > SystemParameters.WorkArea.Height)
            throw new InvalidOperationException("Initial window exceeds the screen work area.");
        window.Width = width; window.Height = height;
        var localization = (PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(window)!;
        localization.SetLanguage(language);
        Invoke(window, "ApplyLanguage");
        CheckTransferLifecycle(window);
        if (args.Length >= 2)
            typeof(MainWindow).GetMethod("SetActivePage", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, [args[1]]);
        if (args.Length >= 2 && args[1] is "modules" or "multiplayer")
        {
            var code = (System.Windows.Controls.Border)window.FindName("ConfigurationCodeCard");
            var host = (System.Windows.Controls.StackPanel)window.FindName("ConfigurationImportHost");
            var parent = (System.Windows.Controls.StackPanel)code.Parent;
            if (host.Parent != parent || parent.Children.IndexOf(host) != parent.Children.IndexOf(code) + 1
                || code.Visibility != Visibility.Visible || host.Children.Count != 1
                || host.Children[0].Visibility != Visibility.Visible)
                throw new InvalidOperationException("Configuration import is not directly below the visible configuration code.");
            Console.WriteLine("LAYOUT PASS " + args[1] + ": configuration code followed by import");
        }
        var content = (FrameworkElement)window.Content;
        content.Measure(new Size(width, height));
        content.Arrange(new Rect(0, 0, width, height));
        content.UpdateLayout();
        CheckBrandAndFonts(window, content);
        if (args.Length >= 2)
        {
            typeof(MainWindow).GetMethod("SetActivePage", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, [args[1]]);
            content.UpdateLayout();
        }
        if (args.Length == 3 && double.TryParse(args[2], out var offset))
        {
            var scroll = (System.Windows.Controls.ScrollViewer)typeof(MainWindow)
                .GetField("MainOptionsScroll", BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public)!
                .GetValue(window)!;
            scroll.ScrollToVerticalOffset(offset);
            content.UpdateLayout();
        }
        foreach (var name in new[] { "HomeNav", "ModulesNav", "MultiplayerNav", "SettingsNav" })
        {
            var button = (Button)window.FindName(name);
            var label = new TextBlock { Text = button.Content.ToString(), FontFamily = button.FontFamily, FontSize = button.FontSize, FontWeight = button.FontWeight };
            label.Measure(new Size(double.PositiveInfinity, double.PositiveInfinity));
            var available = button.ActualWidth - button.Padding.Left - button.Padding.Right - button.BorderThickness.Left - button.BorderThickness.Right;
            if (label.DesiredSize.Width > available) throw new InvalidOperationException(name + " label is clipped.");
        }
        Console.WriteLine($"LAYOUT PASS {language} {width}x{height}: all navigation labels fit");
        if (args.Length >= 2 && args[1] == "settings")
        {
            foreach (var name in new[] { "RemovePatchButton", "RemoveLauncherButton" })
            {
                var button = (Button)window.FindName(name);
                if (button.Visibility != Visibility.Visible || button.ActualHeight < 30 || button.Content.ToString()!.Length < 5)
                    throw new InvalidOperationException(name + " is missing from settings.");
            }
            Console.WriteLine("LAYOUT PASS settings: both localized uninstall buttons present");
        }
        var bitmap = new RenderTargetBitmap(width, height, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(content);
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        var output = Path.GetFullPath(args[0]);
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        using var stream = File.Create(output);
        encoder.Save(stream);
    }

    private static object? Invoke(MainWindow window, string name, params object?[] values)
        => typeof(MainWindow).GetMethod(name, BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, values);

    private static void CheckBrandAndFonts(MainWindow window, DependencyObject root)
    {
        if (window.Icon is null || window.FontFamily.Source != "Arial" || ((Image)window.FindName("BrandMark")).Source is not DrawingImage)
            throw new InvalidOperationException("Window icon, shared brand or Arial default is missing.");
        int checkedElements = 0;
        void Visit(DependencyObject item)
        {
            FontFamily? family = item is TextBlock text ? text.FontFamily
                : item is Button or TextBox or ComboBox or CheckBox or RadioButton ? ((Control)item).FontFamily : null;
            if (family is not null)
            {
                if (family.Source != "Arial") throw new InvalidOperationException("Non-Arial UI font: " + item.GetType().Name + " " + family.Source);
                checkedElements++;
            }
            for (int i = 0; i < VisualTreeHelper.GetChildrenCount(item); i++) Visit(VisualTreeHelper.GetChild(item, i));
        }
        Visit(root);
        if (checkedElements < 15) throw new InvalidOperationException("Insufficient rendered font coverage.");
        var info = Application.GetResourceStream(new Uri("pack://application:,,,/PawsPatchLauncher;component/Assets/PawsPatch.ico"))!;
        using var iconStream = info.Stream;
        var decoder = new IconBitmapDecoder(iconStream, BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad);
        if (!decoder.Frames.Select(f => f.PixelWidth).SequenceEqual(new[] { 16, 20, 24, 32, 40, 48, 64, 128, 256 }))
            throw new InvalidOperationException("Embedded ICO resolutions changed.");
        Console.WriteLine($"BRAND/FONT PASS: icon resource, vector logo, 9 icon resolutions, {checkedElements} Arial elements");
    }

    private static void CheckTransferLifecycle(MainWindow window)
    {
        var previous = SynchronizationContext.Current;
        var queue = new QueuedContext();
        SynchronizationContext.SetSynchronizationContext(queue);
        var details = (TextBlock)window.FindName("TransferText");
        var operation = (TextBlock)window.FindName("OperationText");
        try
        {
            IProgress<(long Received, long? Total)> Begin(string name) => (IProgress<(long Received, long? Total)>)Invoke(window, "TransferProgress", name)!;
            void CheckHidden()
            {
                if (details.Text != "" || details.Visibility != Visibility.Collapsed || operation.Text != "READY")
                    throw new InvalidOperationException("Completed/cancelled download left stale progress.");
            }
            var active = Begin("active");
            active.Report((10, 100)); queue.Drain();
            if (details.Visibility != Visibility.Visible || details.Text.Length == 0)
                throw new InvalidOperationException("Live transfer details are hidden.");
            active.Report((100, 100));
            Invoke(window, "FinishTransfer"); operation.Text = "READY"; queue.Drain(); CheckHidden();
            var cancelled = Begin("cancelled"); cancelled.Report((30, null));
            Invoke(window, "SetBusy", false, null); operation.Text = "READY"; queue.Drain(); CheckHidden();
            var old = Begin("old"); old.Report((100, 100));
            var current = Begin("current"); current.Report((10, 100)); queue.Drain();
            if (!operation.Text.EndsWith(": current")) throw new InvalidOperationException("Old transfer overwrote the current transfer.");
            // Also handle a cached download with no progress reports.
            Begin("cached"); Invoke(window, "FinishTransfer"); operation.Text = "READY"; queue.Drain(); CheckHidden();
            operation.Text = "";
            ((ProgressBar)window.FindName("OperationProgress")).Value = 0;
            Console.WriteLine("UI TRANSFER PASS: live, completed, cancelled, replaced, cached; queued callbacks ignored");
        }
        finally { SynchronizationContext.SetSynchronizationContext(previous); }
    }

    private sealed class QueuedContext : SynchronizationContext
    {
        private readonly Queue<Action> _queue = new();
        public override void Post(SendOrPostCallback callback, object? state) => _queue.Enqueue(() => callback(state));
        public void Drain() { while (_queue.TryDequeue(out var action)) action(); }
    }
}
