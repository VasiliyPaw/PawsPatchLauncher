using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class FriendConfigurationCardChecks
{
    internal static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated fixture required");
        var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [] }, null);
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        T C<T>(string name) => (T)w.FindName(name);
        var checks = 0;
        void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
        try
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Call("ApplyLanguage");
            SocialChecks.Populate(w, "details");
            var peer = Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p => p.Relation == "friend");
            Set("_gameRunningProbe", (Func<bool>)(() => false));
            Set("_game", new GameInstallation(Path.Combine(ActivityStore.Root, "card-fixture"), "k2.exe", null, null));
            foreach (var mod in new[] { "vanilla", "immortals" })
            {
                Field<Dictionary<string, FriendVersionCatalog>>("_friendVersionCatalogs")["beta"] = new(SelfUpdater.CurrentVersion.ToString(), "beta",
                    new Dictionary<string, string> { [mod] = new('A', 64) }, new Dictionary<string, string?> { [mod] = "0.3.0-beta.1" }, DateTimeOffset.UtcNow);
                var player = peer with { Presence = "online", Channel = "beta", Configuration = "PAW-BETA-" + mod.ToUpperInvariant() + "-PP1-CL1-OOS1",
                    Versions = new(SelfUpdater.CurrentVersion.ToString(), mod, "beta", new('A', 64), "0.3.0-beta.1") };
                Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)[player]); Call("RenderSocialDetails", player);
                Check(C<TextBlock>("SocialDetailsChannel").Text.StartsWith(GameMod.Name(mod)), "Mod name missing");
                Check(C<StackPanel>("SocialDetailsComponents").Children.Count == 3, "Wrong component rows");
                Check(C<TextBlock>("SocialDetailsCopyHint").Text.Length == 0, "Valid current configuration blocked");
                Check(C<Button>("SocialDetailsCopyButton").IsEnabled, "Copy button blocked");
                if (mod == "vanilla") Save("ready");
                player = player with { Configuration = null, Versions = null, Components = "{\"core\":true,\"colors\":true,\"desync\":true}" };
                Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)[player]); Call("RenderSocialDetails", player);
                Check(!C<Button>("SocialDetailsCopyButton").IsEnabled, "Unknown configuration can be copied");
                Check(C<TextBlock>("SocialDetailsChannel").Text.Contains(" · ") && !C<TextBlock>("SocialDetailsChannel").Text.StartsWith(GameMod.Name(mod)), "Missing mod silently inferred");
                Check(C<TextBlock>("SocialDetailsCopyHint").Text.Length > 20, "Missing explanation");
                if (language is not ("ru" or "en")) Check(!C<TextBlock>("SocialDetailsCopyHint").Text.StartsWith("The player's"), "Missing translation");
                if (mod == "vanilla") Save("unknown");
            }
            void Save(string state)
            {
                var root = (FrameworkElement)w.Content;
                root.Measure(new Size(1440, 1000)); root.Arrange(new Rect(0, 0, 1440, 1000)); root.UpdateLayout();
                var card = C<Border>("SocialDetailsCard");
                var drawing = new DrawingVisual();
                using (var dc = drawing.RenderOpen()) dc.DrawRectangle(new VisualBrush(card), null, new Rect(0, 0, card.ActualWidth, card.ActualHeight));
                var bitmap = new RenderTargetBitmap((int)Math.Ceiling(card.ActualWidth), (int)Math.Ceiling(card.ActualHeight), 96, 96, PixelFormats.Pbgra32);
                bitmap.Render(drawing); var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(bitmap));
                Directory.CreateDirectory(output); using var stream = File.Create(Path.Combine(output, state + "-" + language + ".png")); png.Save(stream);
            }
            Console.WriteLine($"FRIEND CONFIGURATION CARD {language}: {checks} PASS");
        }
        finally { w.Close(); }
    }
}
