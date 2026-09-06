using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class ChangelogChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Changelog checks require --smoke-test.");
        var window = new MainWindow { Left = -32000, Top = -32000, Width = 1050, Height = 680,
            ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Invoke(string name, params object?[] values) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(window, values);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(window)!;
        void Set(string name, object value) => typeof(MainWindow).GetField(name, flags)!.SetValue(window, value);
        Task Switch(string category) => (Task)Invoke("SwitchChangelogAsync", category)!;
        var scroll = (ScrollViewer)window.FindName("NewsScrollViewer");
        var entries = (StackPanel)window.FindName("NewsEntriesPanel");
        string Heading() => entries.Children[0] is StackPanel p ? ((TextBlock)p.Children[0]).Text : ((TextBlock)entries.Children[0]).Text;
        var checks = 0;
        void Check(bool condition, string text) { if (!condition) throw new InvalidOperationException(text); checks++; }
        void CheckTypography()
        {
            var text = ((StackPanel)entries.Children[0]).Children.OfType<TextBlock>().ToArray();
            Check(text.Length == 3 && text[0].FontSize == 15 && text[0].FontWeight == FontWeights.Bold
                && text[2].FontSize == 13 && text[0].FontSize > text[2].FontSize, "Changelog mini-heading lost its hierarchy.");
            Check(text[1].FontSize == 11 && text[1].TextWrapping == TextWrapping.Wrap,
                "Changelog version/date did not increase one step or lost wrapping.");
            Check(text[2].Style == (Style)window.FindResource("CardDescription") && text[2].LineHeight == 19,
                "Changelog explanation differs from card explanations.");
        }
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);
            var manifest = new ChannelManifest { Channel = "beta" };
            foreach (var category in new[] { "patch", "launcher" })
                for (int i = 0; i < 8; i++) manifest.Changelog.Add(new ChangelogEntry
                {
                    Category = category, Version = i.ToString(), PublishedAt = "2026-09-06",
                    Title = new LocalizedText { Ru = category + " RU " + i, En = category + " EN " + i },
                    Body = new LocalizedText { Ru = string.Concat(Enumerable.Repeat("Подробности изменений. ", 18)), En = string.Concat(Enumerable.Repeat("Detailed release notes. ", 18)) }
                });
            Set("_channel", manifest); Set("_latestChannel", manifest); Invoke("ApplyLanguage");
            window.UpdateLayout(); await Task.Delay(230);
            CheckTypography();
            Invoke("ShowWorking", (Func<string>)(() => "independent operation"));
            var moving = SystemParameters.ClientAreaAnimation;
            var previousHeading = Heading();
            var switching = Switch("launcher");
            Check(Field<string>("_changelogCategory") == "launcher", "Tab selection did not change immediately.");
            if (moving)
            {
                Check(Field<bool>("_changelogTransitionPending") && Heading() == previousHeading, "Old text was replaced before fading.");
                await Task.Delay(35);
                Check(scroll.Opacity is > 0 and < 1, "History has no fade-out intermediate frame.");
                var tab = (Button)window.FindName("LauncherChangelogButton");
                var surface = (Border)tab.Template.FindName("Border", tab);
                var border = ((SolidColorBrush)surface.BorderBrush).Color;
                Check(border != (Color)ColorConverter.ConvertFromString("#D6AA45") && border != (Color)ColorConverter.ConvertFromString("#526984"), "Tab border snapped instead of interpolating.");
            }
            await switching;
            Check(Heading().StartsWith("launcher"), "New history was not rendered.");
            CheckTypography();
            if (moving) { await Task.Delay(40); Check(scroll.Opacity is > 0 and < 1, "History has no fade-in intermediate frame."); }
            await Task.Delay(220);
            Check(scroll.Opacity == 1 && !Field<bool>("_changelogTransitionPending"), "History did not settle.");
            Check(((TextBlock)window.FindName("OperationText")).Text == "independent operation" && Field<OperationFeedback>("_feedback").Working, "Tab switching changed operation status.");
            scroll.ScrollToVerticalOffset(120); window.UpdateLayout();
            var offset = scroll.VerticalOffset;
            Check(offset > 0, "Fixture did not scroll.");
            await Switch("launcher");
            Check(scroll.Opacity == 1 && scroll.VerticalOffset == offset, "Current-tab click flashed or reset scroll.");
            var first = Switch("patch"); await Task.Delay(20);
            var second = Switch("launcher"); await Task.Delay(20);
            var third = Switch("patch"); await Task.WhenAll(first, second, third); await Task.Delay(220);
            Check(Heading().StartsWith("patch") && Field<string>("_changelogCategory") == "patch" && scroll.Opacity == 1, "Rapid clicks restored stale history.");
            Check(scroll.VerticalOffset == 0, "New tab did not start at the top.");
            var interrupted = Switch("launcher");
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language == "ru" ? "en" : "ru");
            Invoke("ApplyLanguage"); var refreshedHeading = Heading();
            await interrupted; await Task.Delay(200);
            Check(Heading() == refreshedHeading && scroll.Opacity == 1, "Language refresh was overwritten by a stale transition.");
            interrupted = Switch("patch");
            manifest.Changelog[0].Title = new LocalizedText { Ru = "fresh patch", En = "fresh patch" };
            Invoke("RefreshNews"); await interrupted;
            Check(Heading() == "fresh patch" && scroll.Opacity == 1, "Feed refresh retained a stale animation.");
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);
            manifest.Changelog[0].Title = new LocalizedText { Ru = "Stable и Beta", En = "Stable and Beta" };
            manifest.Changelog[0].Body = new LocalizedText { Ru = "Stable. PAW-STABLE-IW1", En = "Stable. PAW-STABLE-IW1" };
            Invoke("RefreshNews");
            var releaseName = language == "ru" ? "Релиз" : "Release";
            Check(Heading().StartsWith(releaseName) && ((StackPanel)entries.Children[0]).Children.OfType<TextBlock>().Last().Text == releaseName + ". PAW-STABLE-IW1", "Legacy channel labels were not renamed, or sharing code was modified.");
            Check(manifest.Changelog[0].Title.En == "Stable and Beta" && manifest.Channel == "beta", "Display renaming mutated signed feed content.");
            foreach (var category in new[] { "patch", "launcher" })
            {
                var entry = manifest.Changelog.First(item => item.Category == category);
                entry.Title = new LocalizedText { Ru = "Обновление \u2014 исправления", En = "Update \u2014 fixes" };
                entry.Body = new LocalizedText { Ru = "Текст \u2013 пояснение. https://example.test/a\u2014b", En = "Text \u2013 explanation. https://example.test/a\u2014b" };
                var sourceBytes = System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(manifest);
                await Switch(category); Invoke("RefreshNews"); window.UpdateLayout();
                Check(Heading() == (language == "ru" ? "Обновление - исправления" : "Update - fixes"), "History title retains a long dash.");
                var body = ((StackPanel)entries.Children[0]).Children.OfType<TextBlock>().Last().Text;
                Check(body == (language == "ru" ? "Текст - пояснение. https://example.test/a\u2014b" : "Text - explanation. https://example.test/a\u2014b"),
                    "History punctuation was not normalized or a literal link was changed.");
                Check(sourceBytes.SequenceEqual(System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(manifest)), "Punctuation changed signed source bytes.");
            }
            manifest.Changelog.Clear(); Invoke("RefreshNews"); await Switch("launcher"); await Task.Delay(220);
            Check(entries.Children.Count == 1 && entries.Children[0] is TextBlock && scroll.Opacity == 1, "Empty history vanished during transition.");
            Check(((TextBlock)entries.Children[0]).FontSize == 13 && ((TextBlock)entries.Children[0]).LineHeight == 19,
                "Empty-history explanation uses a different scale.");
            interrupted = Switch("patch"); window.Close(); await interrupted;
            Check(!Field<bool>("_changelogTransitionPending") && scroll.Opacity == 1, "Closed window retained a pending transition.");
            Console.WriteLine($"CHANGELOG PASS {checks} {language}: fade-out/in, tab colors, no-op/rapid clicks, scroll, status isolation, legacy channel display, refresh and close; Windows animations={moving}");
        }
        try
        {
            window.Show();
            var task = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(15) };
            timer.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => window.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("Changelog checks did not complete.");
            task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}
