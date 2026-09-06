using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class AboutChecks
{
    internal static void Layout(MainWindow window, FrameworkElement content)
    {
        T Named<T>(string name) => (T)window.FindName(name);
        void Require(bool valid, string message) { if (!valid) throw new InvalidOperationException(message); }
        var nav = Named<Button>("AboutNav");
        var settings = Named<Button>("SettingsNav");
        var footer = Named<TextBlock>("LauncherVersionLabel");
        Require(nav.Parent == settings.Parent && ((Panel)nav.Parent).Children[^1] == nav,
            "About must be the final navigation item, after Settings.");
        Require(nav.TranslatePoint(new Point(), content).Y >= settings.TranslatePoint(new Point(0, settings.ActualHeight), content).Y + 7
            && nav.TranslatePoint(new Point(0, nav.ActualHeight), content).Y < footer.TranslatePoint(new Point(), content).Y - 10,
            "About navigation overlaps Settings or the launcher footer.");
        if (Named<StackPanel>("AboutPatchPanel").Visibility != Visibility.Visible) return;
        var tabs = Named<WrapPanel>("AboutTabsPanel");
        Require(tabs.Children.Count == 3 && tabs.Children.OfType<Button>().Count() == 3, "Guide must use three history-style buttons, not setting radios.");
        foreach (var tab in tabs.Children.OfType<Button>())
        {
            var position = tab.TranslatePoint(new Point(), tabs);
            Require(position.X >= 0 && position.X + tab.ActualWidth <= tabs.ActualWidth + 1
                && position.Y + tab.ActualHeight <= tabs.ActualHeight + 1, "About category tabs overflow instead of wrapping.");
        }
        var intro = Named<TextBlock>("AboutTitleText");
        Require(intro.FontSize == 18 && intro.FontWeight == FontWeights.Bold, "About page title lost standard typography.");
        foreach (var card in Named<StackPanel>("AboutEntriesPanel").Children.OfType<Border>())
        {
            var text = ((StackPanel)card.Child).Children.OfType<TextBlock>().ToArray();
            Require(text.Length == 3 && text[0].FontSize == 11 && text[1].FontSize == 18
                && text[1].FontWeight == FontWeights.Bold && text[2].FontSize == 13 && text[2].LineHeight == 19,
                "About feature typography differs from the shared styles.");
            Require(text[1].TextWrapping == TextWrapping.Wrap && text[2].TextWrapping == TextWrapping.Wrap
                && text.All(t => t.ActualWidth <= card.ActualWidth), "About text is clipped horizontally.");
        }
        Console.WriteLine("ABOUT LAYOUT PASS: final navigation, footer clearance, wrapped tabs and consistent feature typography");
    }

    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("About checks require --smoke-test.");
        var window = new MainWindow { Left = -32000, Top = -32000, Width = 1050, Height = 680,
            ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Invoke(string name, params object?[] values) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(window, values);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(window)!;
        T Named<T>(string name) => (T)window.FindName(name);
        Task Switch(string category) => (Task)Invoke("SwitchAboutCategoryAsync", category)!;
        var entries = Named<StackPanel>("AboutEntriesPanel");
        var scroll = Named<ScrollViewer>("MainOptionsScroll");
        string FirstId() => (string)((Border)entries.Children[0]).Tag;
        var checks = 0;
        void Check(bool valid, string message) { if (!valid) throw new InvalidOperationException(message); checks++; }
        async Task Scenario()
        {
            var localization = Field<PawsPatchLauncher.Localization>("_text");
            localization.SetLanguage(language); Invoke("ApplyLanguage");
            Invoke("ShowWorking", (Func<string>)(() => "isolated operation"));
            var settingsBefore = JsonSerializer.Serialize(Field<UserSettings>("_settings"));
            var channelBefore = Field<ChannelManifest?>("_channel");
            var operationBefore = Named<TextBlock>("OperationText").Text;
            Check(PatchGuide.Entries.Count == 13 && PatchGuide.Entries.Select(e => e.Id).Distinct().Count() == 13,
                "Guide entries are missing or have duplicate IDs.");
            Check(PatchGuide.Entries.All(e => e.Category is "always" or "optional" or "beta"), "Unknown guide category.");
            foreach (var entry in PatchGuide.Entries)
            {
                Check(new[] { entry.TitleRu, entry.TitleEn, entry.BodyRu, entry.BodyEn }.All(t => !string.IsNullOrWhiteSpace(t)
                    && !t.Contains('\u2014') && !t.Contains('\u2013') && !t.Contains("F9", StringComparison.OrdinalIgnoreCase)
                    && !t.Contains("PawQuickSave", StringComparison.OrdinalIgnoreCase)), "Guide contains missing, long-dash or deferred quick-save text: " + entry.Id);
            }
            var controls = PatchGuide.Entries.Single(e => e.Id == "dvorak");
            Check(controls.Body(language).Contains("WASD") && controls.Body(language).Contains("Dvorak")
                && controls.Body(language).Contains("F "), "WASD/F description or its profile qualification is missing.");
            var colorText = localization["modules.colors.desc"] + localization["modules.colors.help"]
                + PatchGuide.Entries.Single(e => e.Id == "colors").Body(language);
            Check(PatchGuide.PlayerColorCount == 49 && colorText.Split("49").Length == 4 && !colorText.Contains("51"), "Color count differs across UI/help/guide.");
            var desyncText = localization["modules.oos.continue"] + localization["modules.oos.help"]
                + PatchGuide.Entries.Single(e => e.Id == "desync").Body(language);
            Check(!desyncText.Contains("experiment", StringComparison.OrdinalIgnoreCase)
                && !desyncText.Contains("эксперимент", StringComparison.OrdinalIgnoreCase), "Desync bypass still marked experimental.");
            Check(desyncText.Contains(language == "ru" ? "все обнаруженные" : "all detected")
                && desyncText.Contains(language == "ru" ? "не исправляет" : "does not repair")
                && desyncText.Contains(language == "ru" ? "серьёзные" : "serious"), "Desync warning lost scope, severity or divergent-state warning.");
            Named<Button>("AboutNav").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            await Task.Delay(230); window.UpdateLayout();
            Check(Field<string>("_activePage") == "about" && entries.Children.Count == 4 && FirstId() == "base", "About navigation does not open Always included.");
            foreach (var name in new[] { "SettingsPanel", "GameInfoCard", "ConfigurationCodeCard", "DiagnosticsCard", "ColorsModuleCard", "RemovalCard" })
                Check(Named<FrameworkElement>(name).Visibility == Visibility.Collapsed, "Unrelated block remains visible in About: " + name);
            Layout(window, (FrameworkElement)window.Content);
            var moving = SystemParameters.ClientAreaAnimation;
            var switching = Switch("optional");
            if (moving)
            {
                Check(FirstId() == "base", "About text changed before fading out.");
                await Task.Delay(35);
                Check(entries.Opacity is > 0 and < 1, "About has no intermediate fade-out frame.");
            }
            await switching;
            Check(entries.Children.Count == 7 && FirstId() == "powers-shards", "Configurable entries are wrong.");
            if (moving)
            {
                // Hidden WPF windows can delay the first animation tick during layout.
                // Require an actual intermediate frame, not an assumed wall-clock tick.
                var wait = System.Diagnostics.Stopwatch.StartNew();
                while (entries.Opacity == 0 && wait.ElapsedMilliseconds < 500) await Task.Delay(16);
                Check(entries.Opacity is > 0 and < 1,
                    $"About has no intermediate fade-in frame: opacity={entries.Opacity}, animated={entries.HasAnimatedProperties}, waited={wait.ElapsedMilliseconds}ms.");
            }
            await Task.Delay(220); window.UpdateLayout();
            Check(entries.Opacity == 1, "About did not settle after fading.");
            scroll.ScrollToVerticalOffset(120); window.UpdateLayout(); var offset = scroll.VerticalOffset;
            Check(offset > 0, "Long guide cannot be scrolled.");
            await Switch("optional");
            Check(scroll.VerticalOffset == offset && entries.Opacity == 1, "Selected-tab click resets scroll or flashes.");
            var first = Switch("beta"); await Task.Delay(20);
            var second = Switch("always"); await Task.Delay(20);
            var third = Switch("beta"); await Task.WhenAll(first, second, third); await Task.Delay(230); window.UpdateLayout();
            Check(FirstId() == "colors" && entries.Children.Count == 2 && entries.Opacity == 1 && scroll.VerticalOffset == 0,
                "Rapid category changes show stale contents or scroll.");
            var betaTab = Named<Button>("AboutBetaTab");
            Check(betaTab.Style == Named<Button>("PatchChangelogButton").Style, "Guide tab differs from the history tab style.");
            var selectedSurface = (Border)betaTab.Template.FindName("Border", betaTab);
            Check(((SolidColorBrush)selectedSurface.Background).Color == (Color)ColorConverter.ConvertFromString("#5B451D"),
                "Selected guide tab has no settled gold highlight.");
            Check(Named<RadioButton>("HeaderReleaseRadio").IsChecked == (Field<UserSettings>("_settings").Channel == "stable")
                && Named<RadioButton>("HeaderBetaRadio").IsChecked == (Field<UserSettings>("_settings").Channel == "beta"),
                "Guide tab selection changed the patch-channel selector.");
            Named<Button>("AboutAlwaysTab").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            await Task.Delay(340);
            Check(FirstId() == "base" && Field<string>("_aboutCategory") == "always", "Real category Click handler is not wired.");
            switching = Switch("optional");
            localization.SetLanguage(language == "ru" ? "en" : "ru"); Invoke("ApplyLanguage");
            await switching; await Task.Delay(220);
            var title = ((StackPanel)((Border)entries.Children[0]).Child).Children.OfType<TextBlock>().ElementAt(1).Text;
            Check(title == PatchGuide.Entries.Single(e => e.Id == "powers-shards").Title(localization.Language)
                && entries.Opacity == 1, "Language refresh was overwritten by a stale animation.");
            switching = Switch("beta"); Invoke("SetActivePage", "home"); await switching; await Task.Delay(220);
            Check(entries.Opacity == 1 && Named<StackPanel>("AboutPatchPanel").Visibility == Visibility.Collapsed,
                "Leaving About keeps a stale transition active.");
            Invoke("SetActivePage", "about"); await Task.Delay(220);
            Check(FirstId() == "colors", "Returning to About lost the selected category.");
            Check(JsonSerializer.Serialize(Field<UserSettings>("_settings")) == settingsBefore, "Reading About changed patch configuration.");
            Check(ReferenceEquals(Field<ChannelManifest?>("_channel"), channelBefore), "Reading About changed the patch channel.");
            Check(Named<TextBlock>("OperationText").Text == operationBefore, "Reading About changed independent operation status.");
            foreach (var available in new[] { true, false, true })
            {
                var channel = new ChannelManifest { Channel = available ? "beta" : "stable" };
                if (available) channel.Packages.Add(new PackageRelease { Id = "player-colors" });
                typeof(MainWindow).GetField("_channel", flags)!.SetValue(window, channel);
                Invoke("RefreshModuleAvailability");
                var description = Named<TextBlock>("ColorsDescriptionText").Text;
                Check(available ? description == localization["modules.colors.desc"] : !description.Contains("49"),
                    "Color description retained stale availability or palette size when returning to Beta.");
            }
            switching = Switch("always"); window.Close(); await switching;
            Check(entries.Opacity == 1, "Closing About left a pending animation.");
            Console.WriteLine($"ABOUT PASS {checks} {language}: catalog, read-only navigation, 49 colors, desync warning, deferred hotkey, typography, smooth/rapid tabs and cancellation");
        }
        try
        {
            window.Show();
            var task = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(20) };
            timer.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => window.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("About checks did not complete.");
            task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}
