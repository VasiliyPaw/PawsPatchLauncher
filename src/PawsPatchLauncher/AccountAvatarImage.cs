using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
namespace PawsPatchLauncher;

// Decoding is bounded before pixels are materialized. Only normalized pixels leave the PC.
public static class AccountAvatarImage
{
    public const int MaxInputBytes = 10 * 1024 * 1024;
    public static BitmapSource Decode(byte[] bytes, bool normalized = false)
    {
        if (bytes.Length == 0 || bytes.Length > (normalized ? 204800 : MaxInputBytes)) throw new AccountException("avatar_too_large");
        try
        {
            using var stream = new MemoryStream(bytes, writable: false);
            var decoder = BitmapDecoder.Create(stream, BitmapCreateOptions.DelayCreation, BitmapCacheOption.None);
            if (decoder is not (JpegBitmapDecoder or PngBitmapDecoder) || decoder.Frames.Count != 1) throw new AccountException("invalid_avatar");
            var frame = decoder.Frames[0];
            var width = frame.PixelWidth; var height = frame.PixelHeight;
            if (width < 1 || height < 1 || width > 8192 || height > 8192 || (long)width * height > 32000000
                || normalized && (decoder is not JpegBitmapDecoder || width != 256 || height != 256)) throw new AccountException("invalid_avatar");
            stream.Position = 0;
            var bitmap = new BitmapImage();
            bitmap.BeginInit(); bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.StreamSource = stream;
            if (width >= height) bitmap.DecodePixelWidth = Math.Min(width, 512); else bitmap.DecodePixelHeight = Math.Min(height, 512);
            bitmap.EndInit(); bitmap.Freeze();
            return bitmap;
        }
        catch (AccountException) { throw; }
        catch (Exception error) when (error is NotSupportedException or FileFormatException or ArgumentException or IOException or System.Runtime.InteropServices.COMException)
        { throw new AccountException("invalid_avatar"); }
    }

    public static byte[] Normalize(byte[] bytes)
    {
        var bitmap = Decode(bytes);
        var side = Math.Min(bitmap.PixelWidth, bitmap.PixelHeight);
        var square = new CroppedBitmap(bitmap, new Int32Rect((bitmap.PixelWidth-side)/2, (bitmap.PixelHeight-side)/2, side, side));
        var visual = new DrawingVisual();
        using (var drawing = visual.RenderOpen())
        {
            drawing.DrawRectangle(new SolidColorBrush(Color.FromRgb(16,34,58)), null, new Rect(0,0,256,256));
            drawing.DrawImage(square, new Rect(0,0,256,256));
        }
        var target = new RenderTargetBitmap(256,256,96,96,PixelFormats.Pbgra32); target.Render(visual);
        var encoder = new JpegBitmapEncoder { QualityLevel = 88 };
        encoder.Frames.Add(BitmapFrame.Create(target)); // No original EXIF, comments or geolocation.
        using var output = new MemoryStream(); encoder.Save(output);
        if (output.Length > 204800) throw new AccountException("avatar_too_large");
        return output.ToArray();
    }
}
