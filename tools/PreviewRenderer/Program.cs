using PawsPatchLauncher;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace PreviewRenderer;

public static class Program
{
    [STAThread]
    public static void Main(string[] args)
    {
        if (args.Length is < 1 or > 2) throw new ArgumentException("Pass the output PNG path and an optional page name.");
        var app = new App();
        app.InitializeComponent();
        var window = new MainWindow { Width = 1240, Height = 760 };
        if (args.Length == 2)
            typeof(MainWindow).GetMethod("SetActivePage", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, [args[1]]);
        var content = (FrameworkElement)window.Content;
        content.Measure(new Size(1240, 760));
        content.Arrange(new Rect(0, 0, 1240, 760));
        content.UpdateLayout();
        var bitmap = new RenderTargetBitmap(1240, 760, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(content);
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        var output = Path.GetFullPath(args[0]);
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        using var stream = File.Create(output);
        encoder.Save(stream);
    }
}
