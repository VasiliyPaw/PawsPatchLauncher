using PawsPatchLauncher;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Input;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Navigation;
using System.Windows.Threading;

namespace PreviewRenderer;

internal static class ModNoticeChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest || ActivityStore.LocalTestProfile is not null) throw new Exception("Disposable smoke profile required");
        var path = Path.Combine(ActivityStore.Root, "settings.json");
        var original = File.Exists(path) ? File.ReadAllText(path) : null;
        Directory.CreateDirectory(ActivityStore.Root);
        var store = new SettingsStore();
        var checks = 0;
        void Check(bool ok, string why) { checks++; if (!ok) throw new Exception(why); }
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        var previousContext = SynchronizationContext.Current;
        SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(Dispatcher.CurrentDispatcher));
        object? Call(MainWindow w, string method, params object[] args) => typeof(MainWindow).GetMethod(method, flags)!.Invoke(w, args);
        UserSettings Settings(MainWindow w) => (UserSettings)typeof(MainWindow).GetField("_settings", flags)!.GetValue(w)!;
        MainWindow Window()
        {
            var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [] }, null)
            { Left = -32000, Top = -32000, ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
            ((PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text", flags)!.GetValue(w)!).SetLanguage(language);
            Call(w, "ApplyLanguage");
            w.Show(); w.UpdateLayout();
            return w;
        }
        void Complete(Task task)
        {
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(10) };
            var deadline = DateTime.UtcNow.AddSeconds(5);
            timer.Tick += (_, _) => { if (task.IsCompleted || DateTime.UtcNow > deadline) frame.Continue = false; };
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("Notice animation timed out");
            task.GetAwaiter().GetResult();
        }
        try
        {
            File.Delete(path);
            Check(store.Load().Mod == GameMod.Vanilla && !store.Load().ModNoticeSeen, "Fresh profile does not start Vanilla/unread");
            using (var lifetime = new WindowLifetime(Window()))
            {
                var w = lifetime.Window;
                T Control<T>(string name) => (T)w.FindName(name);
                var settings = Settings(w);
                var before = ConfigurationCode.Create(settings);
                Check(Control<Border>("ModulesNavBadge").Visibility == Visibility.Visible, "Missing unread badge");
                Check(Control<Border>("ModNoticeOverlay").Visibility == Visibility.Collapsed, "Notice opened before visiting Components");
                Call(w, "SetActivePage", "mods");
                Check(!settings.ModNoticeSeen, "About mods consumed Components notice");
                Call(w, "SetActivePage", "modules");
                Check(Control<Border>("ModNoticeOverlay").Visibility == Visibility.Visible, "First visit did not open notice");
                Check(settings.ModNoticeSeen && store.Load().ModNoticeSeen, "Read state not persisted immediately");
                Check(Control<Border>("ModulesNavBadge").Visibility == Visibility.Collapsed, "Badge not cleared");
                Check(Control<Grid>("MainBody").IsEnabled && KeyboardNavigation.GetTabNavigation(Control<Border>("ModNoticeCard")) == KeyboardNavigationMode.Cycle,
                    "Notice disables the background or loses its keyboard focus boundary");
                Check((string)Control<RadioButton>("ImmortalsModRadio").Content == "Immortals", "Translated Immortals name");
                Check(Control<TextBlock>("ImmortalsAuthorText").Text.EndsWith("MartialDoctor") && Control<TextBlock>("ModNoticeArcaneAuthorText").Text.EndsWith("Darquan Mortis"), "Wrong credits");
                var link = Control<Hyperlink>("ModsDiscordLink");
                const string invite = "https://discord.gg/krCK7DDwyz";
                Check(link.NavigateUri.AbsoluteUri == invite, "Wrong invite");
                var opened = new List<string>();
                typeof(MainWindow).GetField("_openHelpLink", flags)!.SetValue(w, (Func<string, Task>)(url => { opened.Add(url); return Task.CompletedTask; }));
                link.RaiseEvent(new RequestNavigateEventArgs(link.NavigateUri, "") { RoutedEvent = Hyperlink.RequestNavigateEvent });
                Complete(Task.Delay(260));
                Check(opened.Count == 0 && Control<Border>("ConfirmationOverlay").Visibility == Visibility.Visible, "External invite bypasses confirmation");
                Control<Button>("ConfirmationDeleteButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Complete(Task.Delay(260));
                Check(opened.SequenceEqual(new[] { invite }), "Invite click failed");
                Call(w, "ShowModNotice");
                foreach (var size in new[] { new Size(1050,680), new Size(1280,800), new Size(1600,1000) })
                {
                    var content = (FrameworkElement)w.Content;
                    content.Measure(size); content.Arrange(new Rect(size)); content.UpdateLayout();
                    var card = Control<Border>("ModNoticeCard");
                    var bounds = card.TransformToAncestor(content).TransformBounds(new Rect(card.RenderSize));
                    Check(bounds.Left >= 20 && bounds.Right <= size.Width - 20 && bounds.Top >= 20 && bounds.Bottom <= size.Height - 20, "Notice clipped at " + size);
                    var nav = Control<Button>("AboutModsNav");
                    var footer = Control<Button>("PrivacyPolicyButton");
                    Check(nav.TranslatePoint(new Point(0, nav.ActualHeight), content).Y <= footer.TranslatePoint(new Point(), content).Y, "Sidebar overlaps footer at " + size);
                }
                Complete((Task)Call(w, "CloseModNoticeAsync")!);
                Check(Control<Grid>("MainBody").IsEnabled, "Notice left background disabled");
                Call(w, "SetActivePage", "home"); Call(w, "SetActivePage", "modules");
                Check(Control<Border>("ModNoticeOverlay").Visibility == Visibility.Collapsed, "Notice repeated within session");
                Check(w.FindName("ModNoticeButton") is null, "Removed authors button remains");
                Call(w, "ShowModNotice");
                Check(Control<Border>("ModNoticeOverlay").Visibility == Visibility.Visible, "Onboarding notice failed");
                Complete((Task)Call(w, "CloseModNoticeAsync")!);
                Call(w, "SetActivePage", "mods");
                foreach (var name in new[] { "GuideImmortalsTab", "GuideArcaneTab", "GuideImmortalsTab" })
                    Control<Button>(name).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Check((string)typeof(MainWindow).GetField("_guideSubject", flags)!.GetValue(w)! == GameMod.Immortals,
                    "Unified guide mod tabs failed");
                Check(ConfigurationCode.Create(settings) == before, "Reading mod information changed game settings");
                ConfigurationCode.Apply(new UserSettings(), settings);
                Check(settings.ModNoticeSeen, "Config import reset onboarding");
                var help = (string)Call(w, "CoreHelpText")!;
                Check(!help.Contains("стартового рассинхрона") && !help.Contains("startup desync"), "Desync bullet remains");
                Check(help.Contains(language == "ru" ? "Исправлено отображение цветов на значках рот." : "Fixed color display on company badges."), "Badge wording not updated");
            }
            using (var lifetime = new WindowLifetime(Window()))
            {
                var w = lifetime.Window;
                Call(w, "SetActivePage", "modules");
                Check(((Border)w.FindName("ModNoticeOverlay")).Visibility == Visibility.Collapsed && ((Border)w.FindName("ModulesNavBadge")).Visibility == Visibility.Collapsed, "Read notice returned after restart");
                Check(Settings(w).Mod == GameMod.Vanilla, "Notice unexpectedly changed persisted mod");
            }
            File.WriteAllText(path, "{\"language\":\"ru\",\"russianLocalization\":false}");
            Check(store.Load().Mod == GameMod.ArcaneWars && !store.Load().RussianLocalization && !store.Load().ModNoticeSeen, "Legacy profile migration changed choices");
            store.Save(new UserSettings { Mod = GameMod.ArcaneWars, PawPatchEnabled = false, ModNoticeSeen = true });
            Check(store.Load().Mod == GameMod.ArcaneWars && !store.Load().PawPatchEnabled && store.Load().ModNoticeSeen, "Existing profile choices lost");
            Console.WriteLine($"MOD NOTICE PASS {checks} {language}: fresh/legacy profiles, first visit, persistence, manual reopen, credits/link, layout, independent About tabs, tooltip.");
        }
        finally { SynchronizationContext.SetSynchronizationContext(previousContext); if (original is null) File.Delete(path); else File.WriteAllText(path, original); }
    }

    private sealed class WindowLifetime(MainWindow window) : IDisposable
    {
        public MainWindow Window { get; } = window;
        public void Dispose() => Window.Close();
    }
}
