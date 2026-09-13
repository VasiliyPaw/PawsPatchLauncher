using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net;
using System.Security.Cryptography;
using System.Text.Json;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class StartupChecks
{
    internal static void RenderChecking(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Fixture only");
        var feed = new FeedClient(new() { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(ActivityStore.Root, "startup-preview") });
        var window = new StartupWindow(feed, language) { Left = -30000, Top = -30000, WindowStartupLocation = WindowStartupLocation.Manual, ShowActivated = false, ShowInTaskbar = false };
        typeof(StartupWindow).GetField("_started", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(window, true);
        try
        {
            window.Show(); window.UpdateLayout();
            void CheckLayout()
            {
                window.UpdateLayout();
                FrameworkElement C(string name)=>(FrameworkElement)window.FindName(name);
                double Top(string name)=>C(name).TranslatePoint(new(),window).Y;
                double Bottom(string name)=>Top(name)+C(name).ActualHeight;
                if(window.ActualHeight>320||Bottom("StagePanel")>Top("TransferPanel")||Bottom("TransferPanel")>Top("FooterPanel")||Bottom("FooterPanel")>window.ActualHeight-18)
                    throw new Exception("Compact startup content overlaps or exceeds window.");
            }
            CheckLayout();Save(window,output);
            foreach(var stage in new[]{"offline","download","install"})
            {
                ((TextBlock)window.FindName("StageText")).Text=stage=="install"?(language=="ru"?"Устанавливаем обновление":"Installing update")
                    :stage=="download"?(language=="ru"?"Загружаем обновление":"Downloading update"):(language=="ru"?"Проверяем обновления":"Checking for updates");
                ((TextBlock)window.FindName("DetailText")).Text=stage=="install"?(language=="ru"?"Лаунчер откроется автоматически. Предыдущая версия сохранена для восстановления.":"The launcher will open automatically. The previous version is retained for recovery.")
                    :stage=="download"?(language=="ru"?"Новая версия · 0.7.3":"New version · 0.7.3"):(language=="ru"?"Сервер пока недоступен. Повторяем попытку · до 30 с":"Server unavailable. Retrying · up to 30 s");
                ((Button)window.FindName("ContinueButton")).Visibility=stage=="offline"?Visibility.Visible:Visibility.Hidden;
                ((Button)window.FindName("CancelUpdateButton")).Visibility=stage=="download"?Visibility.Visible:Visibility.Collapsed;
                ((Button)window.FindName("CancelUpdateButton")).IsEnabled=stage=="download";
                ((TextBlock)window.FindName("FooterText")).Text=stage=="download"?(language=="ru"?"При отмене откроется текущая версия":"Cancel to open the installed version")
                    :(language=="ru"?"Лаунчер откроется после установки":"The launcher will open after installation");
                ((TextBlock)window.FindName("SizeText")).Text="42.5 MB / 68.9 MB";
                ((TextBlock)window.FindName("PercentText")).Text="62%";
                ((ProgressBar)window.FindName("DownloadProgress")).IsIndeterminate=false;
                ((ProgressBar)window.FindName("DownloadProgress")).Value=62;
                ((TextBlock)window.FindName("SpeedText")).Text=language=="ru"?"8.2 MB/с · осталось 00:03":"8.2 MB/s · remaining 00:03";
                CheckLayout();if(stage=="download")Save(window,Path.ChangeExtension(output,".download.png"));
            }
        }
        finally { typeof(StartupWindow).GetField("_finished", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(window, true); window.Close(); }
        Console.WriteLine("STARTUP PREVIEW PASS: initial/offline/download/install layouts fit at 570x320; actual WPF window, no download or installation.");
    }
    internal static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Fixture only");
        using var http = new HttpClient(new Offline());
        var feed = new FeedClient(new() { FeedUrls = ["https://offline.invalid/stable"], BetaFeedUrls = [], CacheRoot = Path.Combine(ActivityStore.Root, "startup") }, http);
        var w = new StartupWindow(feed, language) { Left = -30000, Top = -30000, WindowStartupLocation = WindowStartupLocation.Manual, ShowActivated = false, ShowInTaskbar = false };
        typeof(StartupWindow).GetField("_started", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(w, true);
        async Task Test()
        {
            int n = 0; void Check(bool ok, string why) { n++; if (!ok) throw new Exception("Startup UI: " + why); }
            T C<T>(string name) => (T)w.FindName(name);
            Check(C<TextBlock>("VersionText").Text.Contains(SelfUpdater.CurrentVersion.ToString(3)), "Installed launcher version missing");
            Check(C<Button>("ContinueButton").Visibility==Visibility.Hidden&&!C<Button>("ContinueButton").IsEnabled, "Manual opening initially visible");
            Check(C<Button>("CancelUpdateButton").Visibility==Visibility.Collapsed&&!C<Button>("CancelUpdateButton").IsEnabled, "Cancel update initially visible");
            var watch = Stopwatch.StartNew();
            var run = (Task)typeof(StartupWindow).GetMethod("RunAsync", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(w, null)!;
            await Task.Delay(1300);
            Check(!w.Completion.IsCompleted && C<TextBlock>("DetailText").Text.Contains(language == "ru" ? "Повторяем" : "Retrying"), "Offline retry not shown");
            await Task.Delay(8000);
            Check(C<Button>("ContinueButton").Visibility!=Visibility.Visible, "Manual opening visible before 10 seconds");
            await Task.Delay(1200);
            Check(C<Button>("ContinueButton").Visibility==Visibility.Visible&&C<Button>("ContinueButton").IsEnabled, "Manual opening missing after 10 seconds");
            Save(w, Path.ChangeExtension(output, ".offline.png"));
            await run;
            Check(!await w.Completion && watch.Elapsed.TotalSeconds >= 29.5 && watch.Elapsed.TotalSeconds < 35, "Offline fallback not bounded to 30 seconds");
            // Inspect the download layout at the smallest supported size using explicit sample values.
            C<TextBlock>("StageText").Text = language == "ru" ? "Загружаем обновление" : "Downloading update";
            C<TextBlock>("DetailText").Text = language == "ru" ? "Новая версия · 0.6.5" : "New version · 0.6.5";
            C<TextBlock>("SizeText").Text = "42.5 MB / 68.9 MB"; C<TextBlock>("PercentText").Text = "62%";
            C<ProgressBar>("DownloadProgress").IsIndeterminate = false; C<ProgressBar>("DownloadProgress").Value = 62;
            C<TextBlock>("SpeedText").Text = language == "ru" ? "8.2 MB/с · осталось 00:03" : "8.2 MB/s · remaining 00:03";
            Save(w, output);
            Check(C<Button>("ContinueButton").ActualWidth > 90 && C<TextBlock>("SpeedText").ActualHeight >= 15, "Transfer layout clipped");
            using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
            var payload = JsonSerializer.SerializeToUtf8Bytes(new ChannelManifest { Launcher = new() { Version = "99.0.0", Size = 123, Sha256 = new('A',64), Urls = ["https://stall.invalid/update.exe"] } }, LauncherJsonContext.Default.ChannelManifest);
            var signed = JsonSerializer.SerializeToUtf8Bytes(new SignedFeedEnvelope { Payload = Convert.ToBase64String(payload), Signature = Convert.ToBase64String(key.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation)) }, LauncherJsonContext.Default.SignedFeedEnvelope);
            async Task StallCase(bool skip)
            {
                using var stallHttp = new HttpClient(new Stall(signed, skip));
                var cache = Path.Combine(ActivityStore.Root, "startup-stall-" + skip);
                var stallFeed = new FeedClient(new() { FeedUrls = ["https://stall.invalid/feed.json"], BetaFeedUrls = [], PublicKeyPem = key.ExportSubjectPublicKeyInfoPem(), CacheRoot = cache }, stallHttp);
                var stalled = new StartupWindow(stallFeed, language);
                try
                {
                    var elapsed = Stopwatch.StartNew();
                    var pending = (Task)typeof(StartupWindow).GetMethod("RunAsync", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(stalled, null)!;
                    await Task.Delay(200);
                    if (!skip)
                    {
                        Check(((TextBlock)stalled.FindName("StageText")).Text.Contains(language == "ru" ? "Загружаем" : "Downloading"), "Valid signed update did not reach download");
                        Check(((TextBlock)stalled.FindName("PercentText")).Text=="0%","Download percentage missing before first bytes");
                    }
                    else
                    {
                        Check(((Button)stalled.FindName("ContinueButton")).Visibility!=Visibility.Visible&&!((Button)stalled.FindName("ContinueButton")).IsEnabled,"Manual opening remained during download");
                        Check(((TextBlock)stalled.FindName("PercentText")).Text=="33%","The first partial chunk did not update percentage before stalling");
                        ((Button)stalled.FindName("ContinueButton")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                        await Task.Delay(200);Check(!pending.IsCompleted,"Hidden button interrupted a download");
                        var cancel = (Button)stalled.FindName("CancelUpdateButton");
                        Check(cancel.Visibility == Visibility.Visible && cancel.IsEnabled && cancel.Background is SolidColorBrush brush && brush.Color.R < 100,
                            "Download cancellation is missing or uses a bright background");
                        cancel.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                    }
                    await pending;
                    Check(!await stalled.Completion && (skip ? elapsed.Elapsed.TotalSeconds < 2 : elapsed.Elapsed.TotalSeconds is >= 29.5 and < 35), skip ? "Fixture cancellation failed" : "Stalled download did not fall back after 30 seconds");
                    if (skip) Check(Directory.GetFiles(cache,"*.download",SearchOption.AllDirectories).SingleOrDefault() is { } partial
                        && new FileInfo(partial).Length==41 && Directory.GetFiles(cache,"*.exe",SearchOption.AllDirectories).Length==0,
                        "Cancelling the window lost partial bytes or accepted an incomplete executable");
                }
                finally { stalled.Close(); }
            }
            await StallCase(false); await StallCase(true);
            Console.WriteLine($"STARTUP UI PASS {n} {language}: actual 30-second offline/stalled fallback, Continue hidden until 10 seconds/during downloads, dark Cancel button opens installed version, percentage and layout");
        }
        try
        {
            w.Show(); var task = w.Dispatcher.InvokeAsync(Test).Task.Unwrap(); var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(85) }; timer.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start(); Dispatcher.PushFrame(frame); timer.Stop(); if (!task.IsCompleted) throw new TimeoutException(); task.GetAwaiter().GetResult();
        }
        finally { w.Close(); }
    }
    private static void Save(Window w, string path)
    {
        w.UpdateLayout(); var view = (FrameworkElement)w.Content;
        var bitmap = new RenderTargetBitmap((int)w.Width, (int)w.Height, 96, 96, PixelFormats.Pbgra32); bitmap.Render(view);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!); using var file = File.Create(path); encoder.Save(file);
    }
    private sealed class Offline : HttpMessageHandler
    { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token) => throw new HttpRequestException("Simulated offline connection."); }
    private sealed class Stall(byte[] signed, bool partial) : HttpMessageHandler
    {
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            if (request.RequestUri!.AbsolutePath.EndsWith(".exe"))
            {
                if (partial) return new(HttpStatusCode.OK) { Content = new StreamContent(new PartialStream()) };
                await Task.Delay(100000, token);
            }
            return new(HttpStatusCode.OK) { Content = new ByteArrayContent(signed) };
        }
    }
    private sealed class PartialStream() : MemoryStream(new byte[123], false)
    {
        public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken token = default)
        {
            if (Position > 0) await Task.Delay(100000, token);
            return await base.ReadAsync(buffer[..Math.Min(41,buffer.Length)], token);
        }
    }
}
