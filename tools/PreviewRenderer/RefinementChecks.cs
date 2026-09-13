using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Media3D;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

/// <summary>UI-only fixtures. No downloads, game writes, sign-in requests or uninstall scheduling.</summary>
internal static class RefinementChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest || ActivityStore.LocalTestProfile is not null)
            throw new InvalidOperationException("Refinement checks require a disposable smoke profile.");
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        var settingsPath = Path.Combine(ActivityStore.Root, "settings.json");
        var originalSettings = File.Exists(settingsPath) ? File.ReadAllText(settingsPath) : null;
        var fixtureRoot = Path.Combine(ActivityStore.Root, "refinement", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(fixtureRoot);
        var sentinel = Path.Combine(fixtureRoot, "keep-fixture.txt");
        File.WriteAllText(sentinel, "This file must not be removed by confirmation checks.");
        var store = new SettingsStore();
        store.Save(new UserSettings { Mod = GameMod.ArcaneWars, ModNoticeSeen = true, Language = language, RussianLocalization = true });
        var window = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(fixtureRoot, "cache") }, null)
        {
            Left = -32000, Top = -32000, Width = 1050, Height = 680,
            ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual
        };
        object? Call(string method, params object?[] arguments)
            => typeof(MainWindow).GetMethod(method, flags)!.Invoke(window, arguments);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(window)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(window, value);
        T Named<T>(string name) => (T)window.FindName(name);
        void Click(string name) => Named<Button>(name).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        var settings = Field<UserSettings>("_settings");
        FixtureAccess.AllowArcaneWars(window);
        var text = Field<PawsPatchLauncher.Localization>("_text");
        var count = 0;
        void Check(bool condition, string why)
        {
            if (!condition) throw new InvalidOperationException("Refinement UI: " + why);
            count++;
        }
        void Layout() { window.UpdateLayout(); }
        async Task Until(Func<bool> condition, string why)
        {
            var deadline = DateTime.UtcNow.AddSeconds(4);
            while (!condition() && DateTime.UtcNow < deadline) await Task.Delay(15);
            Check(condition(), why);
        }
        string SelectedCode(ComboBox combo) => (string)combo.SelectedItem.GetType().GetProperty("Code")!.GetValue(combo.SelectedItem)!;
        void SelectLanguage(ComboBox combo, string code)
            => combo.SelectedItem = combo.Items.Cast<object>().Single(item => (string)item.GetType().GetProperty("Code")!.GetValue(item)! == code);
        string ChoiceLabel(ComboBox combo, string code)
        {
            var choice = combo.Items.Cast<object>().Single(item => (string)item.GetType().GetProperty("Code")!.GetValue(item)! == code);
            return (string)choice.GetType().GetProperty("Label")!.GetValue(choice)!;
        }
        string GuideText() => string.Join("\n", Descendants(Named<StackPanel>("AboutEntriesPanel")).OfType<TextBlock>().Select(t => t.Text));
        Border[] UnreadDots(string name) => Named<Button>(name).Content is Panel panel ? panel.Children.OfType<Border>().ToArray() : [];
        void CheckAnimation(string cardName)
        {
            var card = Named<FrameworkElement>(cardName);
            Check(!SystemParameters.ClientAreaAnimation || card.RenderTransform is TranslateTransform { HasAnimatedProperties: true },
                cardName + " has no animated entry while Windows animations are enabled.");
        }
        void CheckModalSurface(string overlayName, string cardName)
        {
            var overlay = Named<FrameworkElement>(overlayName);
            var card = Named<FrameworkElement>(cardName);
            Check(Named<Grid>("MainBody").IsEnabled && Named<Grid>("TitleBar").IsEnabled,
                overlayName + " changes the enabled state of the launcher.");
            var hit = window.InputHitTest(overlay.TranslatePoint(new Point(3, 3), window)) as DependencyObject;
            Check(IsInside(hit, overlay) && !IsInside(hit, Named<Grid>("MainBody")),
                overlayName + " does not intercept backdrop hit testing.");
            var cycle = Ancestors(card).OfType<DependencyObject>().Any(node => IsInside(node, overlay)
                && KeyboardNavigation.GetTabNavigation(node) == KeyboardNavigationMode.Cycle
                && KeyboardNavigation.GetControlTabNavigation(node) == KeyboardNavigationMode.Cycle);
            Check(cycle, overlayName + " permits tab navigation to escape the dialog.");
            var focused = Keyboard.FocusedElement as DependencyObject ?? FocusManager.GetFocusedElement(window) as DependencyObject;
            // An inactive off-screen window may only have logical focus; inspect that scope as well.
            Check(IsInside(focused, card) || IsInside(FocusManager.GetFocusedElement(window) as DependencyObject, card),
                overlayName + " did not move focus into its card.");
        }
        MouseButtonEventArgs Press(FrameworkElement target)
        {
            var press = new MouseButtonEventArgs(Mouse.PrimaryDevice, Environment.TickCount, MouseButton.Left)
            { RoutedEvent = Mouse.PreviewMouseDownEvent, Source = target };
            target.RaiseEvent(press); return press;
        }
        KeyEventArgs Escape(UIElement target)
        {
            var key = new KeyEventArgs(Keyboard.PrimaryDevice, PresentationSource.FromVisual(window), Environment.TickCount, Key.Escape)
            { RoutedEvent = Keyboard.PreviewKeyDownEvent };
            target.RaiseEvent(key); return key;
        }

        async Task Scenario()
        {
            text.SetLanguage(language); Call("ApplyLanguage"); Call("SetActivePage", "modules");
            await Task.Delay(260); Layout();
            var gameLanguage = Named<ComboBox>("GameLanguageCombo");
            var launcherLanguage = Named<ComboBox>("LauncherLanguageCombo");
            Check(gameLanguage.Items.Count == 2 && ChoiceLabel(gameLanguage, "en").StartsWith("English")
                && ChoiceLabel(gameLanguage, "ru") == "Русский", "Game language choices do not use their native names.");
            Check(!Named<CheckBox>("RussianToggle").IsVisible,
                "Legacy localization toggle remains visible next to the language selector.");
            foreach (var size in new[] { new Size(1050, 680), new Size(1280, 800) })
            {
                window.Width = size.Width; window.Height = size.Height; Layout();
                var scroll = Named<ScrollViewer>("MainOptionsScroll");
                scroll.ScrollToTop(); Layout();
                var tabs = Named<Border>("ModSelectorCard"); var languageCard = Named<Border>("RussianModuleCard");
                Check(tabs.IsVisible && languageCard.IsVisible && !IsInside(tabs, scroll) && !IsInside(languageCard, scroll),
                    "Mode/language controls belong to the scrolling component body.");
                var tabsBefore = tabs.TranslatePoint(new Point(), window); var languageBefore = languageCard.TranslatePoint(new Point(), window);
                var componentBefore = Named<Border>("CoreModuleCard").TranslatePoint(new Point(), window).Y;
                Check(scroll.ScrollableHeight > 0 && gameLanguage.ActualWidth >= 110 && gameLanguage.ActualHeight >= 25,
                    "Fixture has no component scrolling or the game language selector is clipped.");
                scroll.ScrollToEnd(); Layout();
                Check(scroll.VerticalOffset > 0 && Named<Border>("CoreModuleCard").TranslatePoint(new Point(), window).Y < componentBefore,
                    "Component body did not scroll.");
                Check((tabs.TranslatePoint(new Point(), window) - tabsBefore).Length < .5
                    && (languageCard.TranslatePoint(new Point(), window) - languageBefore).Length < .5,
                    "Pinned mode/language controls moved with the component body.");
            }
            window.Width = 1050; window.Height = 680; Layout();
            var componentNames = new[] { "CoreModuleCard", "ColorsModuleCard", "OosModuleCard", "IndependentHostilityCard",
                "RoamingSpawnCard", "AdditionalRoamingCard", "SiegeBalanceCard", "PowersShardsCard" };
            foreach (var gameCode in new[] { "ru", "en", "ru" })
            {
                SelectLanguage(gameLanguage, gameCode);
                foreach (var (mod, radio) in new[] { (GameMod.Vanilla, "VanillaModRadio"), (GameMod.Immortals, "ImmortalsModRadio"), (GameMod.ArcaneWars, "ArcaneWarsModRadio") })
                {
                    Check(Named<RadioButton>(radio).IsEnabled, "A supported game mode is disabled: " + mod);
                    Named<RadioButton>(radio).IsChecked = true; Layout();
                    Check(settings.Mod == mod && SelectedCode(gameLanguage) == gameCode && settings.RussianLocalization == (gameCode == "ru")
                        && store.Load().RussianLocalization == (gameCode == "ru"), "Switching mode lost the common language: " + mod);
                    Check(gameLanguage.IsVisible && gameLanguage.IsEnabled, "Game language is unavailable in " + mod);
                    Check(componentNames.All(name => Named<Border>(name).Visibility == (mod == GameMod.ArcaneWars ? Visibility.Visible : Visibility.Collapsed)),
                        "Mode exposes an incorrect set of component cards: " + mod);
                    Check(Named<Border>("VanillaEmptyCard").Visibility == (mod == GameMod.ArcaneWars ? Visibility.Collapsed : Visibility.Visible),
                        "No-component mode lacks its explanatory empty state.");
                }
            }
            foreach (var beta in new[] { true, false })
            {
                await (Task)Call("ChangeChannelAsync", beta)!;
                Check(settings.Channel == "stable" && settings.RussianLocalization && SelectedCode(gameLanguage) == "ru",
                    "An unavailable Beta changed the patch channel or the shared game language.");
            }
            Call("SetActivePage", "settings"); Layout();
            Check(launcherLanguage.IsVisible && launcherLanguage.Items.Count == 2 && ChoiceLabel(launcherLanguage, "en") == "English"
                && ChoiceLabel(launcherLanguage, "ru") == "Русский", "Launcher language selector missing or translated language names.");
            foreach (var code in new[] { language == "ru" ? "en" : "ru", language })
            {
                SelectLanguage(launcherLanguage, code);
                Check(text.Language == code && settings.Language == code && store.Load().Language == code && settings.RussianLocalization,
                    "Launcher language did not persist independently of the game language.");
            }
            foreach (var name in new[] { "LanguageButton", "SettingsLanguageButton", "ConfigurationCodeCard", "ConfigurationImportHost", "RemovePatchButton", "RemovePatchDescriptionText", "AboutModsNav" })
                Check(Named<UIElement>(name).Visibility == Visibility.Collapsed, "Obsolete launcher UI remains visible: " + name);

            Call("SetActivePage", "modules"); Layout();
            var enabledChanges = 0;
            DependencyPropertyChangedEventHandler enabledChanged = (_, _) => enabledChanges++;
            Named<Grid>("MainBody").IsEnabledChanged += enabledChanged; Named<Grid>("TitleBar").IsEnabledChanged += enabledChanged;
            FocusManager.SetFocusedElement(window, Named<Button>("ModulesNav"));
            Call("ShowModNotice"); CheckAnimation("ModNoticeCard"); await Task.Delay(40); Layout();
            CheckModalSurface("ModNoticeOverlay", "ModNoticeCard");
            Press(Named<Border>("ModNoticeCard"));
            Check(Named<Border>("ModNoticeOverlay").Visibility == Visibility.Visible, "Clicking inside the authors card closes it.");
            var beforePage = Field<string>("_activePage");
            var outside = Press(Named<Border>("ModNoticeOverlay"));
            Check(outside.Handled, "Authors backdrop did not consume its click.");
            await Until(() => Named<Border>("ModNoticeOverlay").Visibility == Visibility.Collapsed, "Authors backdrop did not dismiss the dialog.");
            Check(Field<string>("_activePage") == beforePage && Named<Grid>("MainBody").IsHitTestVisible,
                "Authors dismissal activated background navigation or left input blocked.");
            Call("ShowModNotice"); await Task.Delay(30);
            Check(Escape(Named<Button>("ModNoticeCloseButton")).Handled, "Authors dialog did not consume Escape.");
            await Until(() => Named<Border>("ModNoticeOverlay").Visibility == Visibility.Collapsed, "Escape did not dismiss the authors dialog.");

            FocusManager.SetFocusedElement(window, Named<Button>("ModulesNav"));
            Call("HelpButton_Click", new Button { Tag = "modules.ru" }, new RoutedEventArgs());
            CheckAnimation("HelpCard"); await Task.Delay(30); Layout();
            CheckModalSurface("HelpOverlay", "HelpCard");
            Check(Escape(Named<Button>("HelpCloseButton")).Handled, "Help did not consume Escape.");
            await Until(() => Named<Border>("HelpOverlay").Visibility == Visibility.Collapsed, "Escape did not dismiss help.");
            Check(ReferenceEquals(FocusManager.GetFocusedElement(window), Named<Button>("ModulesNav")), "Help did not restore its previous focus.");
            Call("HelpButton_Click", new Button { Tag = "modules.ru" }, new RoutedEventArgs());
            await Task.Delay(30);
            Check(Press(Named<Border>("HelpOverlay")).Handled, "Help backdrop passed its click through.");
            await Until(() => Named<Border>("HelpOverlay").Visibility == Visibility.Collapsed, "Help backdrop did not dismiss it.");

            var scheduledRemovals = 0;
            Set("_scheduleLauncherRemoval", (Func<Task>)(() => { scheduledRemovals++; throw new InvalidOperationException("UI checks must not uninstall."); }));
            Call("SetActivePage", "settings"); Layout();
            Task<bool> OpenRemoval() => (Task<bool>)Call("ConfirmLauncherRemovalAsync", Path.Combine(fixtureRoot, "launcher-fixture.exe"))!;
            var removal = OpenRemoval(); CheckAnimation("ConfirmationCard"); await Task.Delay(30); Layout();
            CheckModalSurface("ConfirmationOverlay", "ConfirmationCard");
            var removeMods = Named<CheckBox>("ConfirmationRemoveModsToggle");
            Check(removeMods.Visibility == Visibility.Visible && removeMods.IsChecked == true && !removal.IsCompleted,
                "Uninstall confirmation did not default to removing patch and mods.");
            Press(Named<Border>("ConfirmationCard"));
            Check(!removal.IsCompleted, "Clicking inside confirmation accepted or cancelled it.");
            Check(Press(Named<Border>("ConfirmationOverlay")).Handled, "Confirmation backdrop passed its click through.");
            Check(!await removal && !Field<bool>("_removeModsWithLauncher"), "Backdrop dismissal accepted uninstall.");
            removal = OpenRemoval(); removeMods.IsChecked = false; Click("ConfirmationCancelButton");
            Check(!await removal && !Field<bool>("_removeModsWithLauncher"), "Cancel retained an uninstall action.");
            removal = OpenRemoval();
            Check(removeMods.IsChecked == true, "Reopening uninstall retained an unchecked default.");
            removeMods.IsChecked = false; Click("ConfirmationDeleteButton");
            Check(await removal && !Field<bool>("_removeModsWithLauncher"), "Launcher-only choice was not captured.");
            removal = OpenRemoval(); Click("ConfirmationDeleteButton");
            Check(await removal && Field<bool>("_removeModsWithLauncher"), "Default remove-mods choice was not captured.");
            removal = OpenRemoval();
            Check(Escape(Named<Button>("ConfirmationCancelButton")).Handled && !await removal,
                "Confirmation Escape did not cancel uninstall.");
            Check(enabledChanges == 0 && Named<Grid>("MainBody").IsEnabled && Named<Grid>("TitleBar").IsEnabled
                && Named<Grid>("MainBody").IsHitTestVisible && Named<Grid>("TitleBar").IsHitTestVisible,
                "Modal lifecycle toggled enabled state or left the launcher blocked.");
            Check(scheduledRemovals == 0 && File.ReadAllText(sentinel) == "This file must not be removed by confirmation checks.",
                "Dialog-only fixture invoked uninstall or touched its sentinel.");
            Named<Grid>("MainBody").IsEnabledChanged -= enabledChanged; Named<Grid>("TitleBar").IsEnabledChanged -= enabledChanged;

            typeof(AccountService).GetProperty("State")!.SetValue(Field<AccountService>("_account"), AccountState.Guest);
            Call("RenderAccount");
            foreach (var register in new[] { false, true })
            {
                Call("ShowAccountForm", register); Layout();
                foreach (var remember in new[] { false, true })
                {
                    Named<CheckBox>("AccountRememberCheck").IsChecked = remember; Call("RenderAccount");
                    Check(Named<TextBlock>("AccountFormHintText").Visibility == Visibility.Collapsed
                        && string.IsNullOrWhiteSpace(Named<TextBlock>("AccountFormHintText").Text), "Login/register helper text returned.");
                    Check(Named<TextBlock>("AccountRememberText").Visibility == Visibility.Collapsed
                        && string.IsNullOrWhiteSpace(Named<TextBlock>("AccountRememberText").Text), "Session-duration helper text returned.");
                }
                Check(Named<UIElement>("AccountEmailInput").IsVisible && Named<UIElement>("AccountPasswordInput").IsVisible,
                    "Removing hints hid required account inputs.");
            }

            Call("SetActivePage", "settings");
            var manifest = new ChannelManifest { Channel = "stable", Changelog = [
                new() { Category = "launcher", Version = "fixture-1", PublishedAt = "2026-09-10", Title = Both("Launcher fixture"), Body = Both("Launcher change") },
                new() { Category = "patch", Version = "fixture-1", PublishedAt = "2026-09-10", Title = Both("Patch fixture"), Body = Both("Patch change") }
            ] };
            Set("_channel", manifest); Set("_latestChannel", manifest); settings.ReadChangelogs.Clear(); Call("RefreshUnreadBadges");
            var dots = UnreadDots("HomeNav");
            Check(dots.Length == 1 && dots[0].Background is SolidColorBrush brush && brush.Color.R > brush.Color.G * 1.3,
                "Unread history lacks its compact red navigation dot.");
            bool LauncherUnread() => Named<ComboBox>("HistorySubjectCombo").Items.OfType<MainWindow.TimelineChoice>().Single(c => c.Id == "launcher").Unread;
            Check(LauncherUnread(), "Launcher item has no unread mark.");
            ChangelogTimeline.MarkViewed(settings, ChangelogTimeline.Entries([manifest], "launcher", "all", "all"), true); Call("RefreshUnreadBadges");
            Check(!LauncherUnread(), "Reading launcher history retained its mark.");
            manifest.Changelog[0].Version = "fixture-2"; Call("RefreshUnreadBadges");
            Check(LauncherUnread(), "New launcher history did not restore its unread notification.");

            manifest.PatchGuide = PatchDocument("patch-global-v1");
            manifest.ModGuides = [ModDocument(GameMod.Vanilla), ModDocument(GameMod.ArcaneWars), ModDocument(GameMod.Immortals)];
            manifest.ModGuides.Single(g => g.Id == GameMod.ArcaneWars).PatchGuide = PatchDocument("patch-aw-v1");
            Check(manifest.ModGuides.All(GuideCatalog.IsValid), "Fixture guide is invalid.");
            Call("SetActivePage", "about"); Click("GuideGeneralTab"); Layout();
            var beforeGuide = JsonSerializer.Serialize(settings);
            var beforeOperation = Named<TextBlock>("OperationText").Text;
            Check(Named<StackPanel>("AboutPatchPanel").IsVisible && Named<StackPanel>("AboutEntriesPanel").Children.Count > 0,
                "Unified guide lacks its overview.");
            foreach (var (mod, tab) in new[] { (GameMod.Vanilla, "GuideVanillaTab"), (GameMod.ArcaneWars, "GuideArcaneTab"), (GameMod.Immortals, "GuideImmortalsTab") })
            {
                Click(tab); Layout();
                Check(Named<TextBlock>("AboutIntroText").Text.Contains("description-" + mod) && GuideText().Contains("body-" + mod),
                    "Unified guide did not render the chosen mode description and changes: " + mod);
                Check(Named<WrapPanel>("GuideVariantTabs").Visibility == (mod == GameMod.ArcaneWars ? Visibility.Visible : Visibility.Collapsed),
                    "Guide exposed an incorrect set of patch subtabs: " + mod);
            }
            var immortal = manifest.ModGuides.Single(g => g.Id == GameMod.Immortals);
            immortal.Sections[0].Body = Both("live-immortals-guide-replacement");
            Call("RefreshAboutFeed");
            Check(GuideText().Contains("live-immortals-guide-replacement") && !GuideText().Contains("body-immortals"),
                "Same-version feed update did not replace the open mod guide.");
            Click("GuideArcaneTab"); Click("GuidePatchTab"); Layout();
            Check(GuideText().Contains("patch-aw-v1") && !GuideText().Contains("body-arcane-wars"),
                "Paw's Patch subtab did not use its mod-specific guide.");
            var patch = manifest.ModGuides.Single(g => g.Id == GameMod.ArcaneWars).PatchGuide!;
            patch.Entries[0] = patch.Entries[0] with { BodyRu = "live-patch-guide-replacement", BodyEn = "live-patch-guide-replacement" };
            Call("RefreshAboutFeed");
            Check(GuideText().Contains("live-patch-guide-replacement"), "Same-version patch guide update did not refresh the open subtab.");
            Click("GuideModTab");
            Check(GuideText().Contains("body-arcane-wars") && !GuideText().Contains("live-patch-guide-replacement"),
                "Returning to About the mod retained patch content.");
            Check(JsonSerializer.Serialize(settings) == beforeGuide && Named<TextBlock>("OperationText").Text == beforeOperation,
                "Reading or refreshing guide content changed game choices or operation feedback.");
            Console.WriteLine($"REFINEMENT UI PASS {count} {language}: pinned modes/languages, three modes and channel persistence, settings cleanup, animated input-blocking dialogs, uninstall choices without deletion, account hints, red history badges, unified/live guides");
        }

        try
        {
            window.Show();
            var scenario = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(40) };
            timer.Tick += (_, _) => frame.Continue = false;
            scenario.ContinueWith(_ => window.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start();
            try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!scenario.IsCompleted) throw new TimeoutException("Refinement UI checks timed out.");
            scenario.GetAwaiter().GetResult();
        }
        finally
        {
            Set("_busy", false);
            // Never continue an accepted removal path: the fixture only called the dialog method.
            Call("CloseCompatibilityPopup");
            var completion = typeof(MainWindow).GetField("_confirmation", flags)!.GetValue(window) as TaskCompletionSource<bool>;
            completion?.TrySetResult(false); Set("_confirmation", null);
            window.Close();
            if (originalSettings is null) File.Delete(settingsPath); else File.WriteAllText(settingsPath, originalSettings);
        }
    }

    private static LocalizedText Both(string text) => new() { Ru = text, En = text };
    private static ModGuideDocument ModDocument(string mod) => new()
    {
        Id = mod, Version = "fixture-1", Author = "fixture author", Description = Both("description-" + mod),
        Sections = [new() { Id = "fixture-section", Title = Both("section-" + mod), Body = Both("body-" + mod) }]
    };
    private static PatchGuideDocument PatchDocument(string marker) => new()
    {
        Version = "fixture-1", Entries = [new("fixture-always", "always", marker, marker, "body-" + marker, "body-" + marker)]
    };
    private static IEnumerable<DependencyObject> Ancestors(DependencyObject start)
    {
        DependencyObject? node = start;
        while (node is not null)
        {
            yield return node;
            node = node is Visual or Visual3D ? VisualTreeHelper.GetParent(node)
                : node is FrameworkContentElement content ? content.Parent : LogicalTreeHelper.GetParent(node);
        }
    }
    private static bool IsInside(DependencyObject? source, DependencyObject root)
        => source is not null && Ancestors(source).Any(node => ReferenceEquals(node, root));
    private static IEnumerable<DependencyObject> Descendants(DependencyObject root)
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i); yield return child;
            foreach (var descendant in Descendants(child)) yield return descendant;
        }
    }
}
