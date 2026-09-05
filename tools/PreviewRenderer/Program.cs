using PawsPatchLauncher;
using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace PreviewRenderer;

public static class Program
{
    [STAThread]
    public static void Main(string[] args)
    {
        if (args.Length != 1) throw new ArgumentException("Pass the output PNG path.");
        var app = new App();
        app.InitializeComponent();
        var window = new MainWindow { Width = 1240, Height = 760 };
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
