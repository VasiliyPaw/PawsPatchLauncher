using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class TypographyChecks
{
    private const BindingFlags Fields = BindingFlags.NonPublic | BindingFlags.Instance;
    private static T Field<T>(MainWindow window, string name) => (T)typeof(MainWindow).GetField(name, Fields)!.GetValue(window)!;
    private static T Named<T>(MainWindow window, string name) => (T)window.FindName(name);

    internal static void Layout(MainWindow window, FrameworkElement content, string page)
    {
        void Require(bool valid, string message) { if (!valid) throw new InvalidOperationException(message); }
        var titles = new List<TextBlock>();
        foreach (var name in new[] { "SettingsTitleText", "PatchUpdatesTitleText", "HomeWelcomeTitleText", "UpdateNoticeTitleText",
                     "ConfigurationTitleText", "DiagnosticsTitleText", "GamePathLabel", "RemovalTitleText", "NewsTitleText" })
            titles.Add(Named<TextBlock>(window, name));
        foreach (var field in new[] { "_incidentCard", "_recoveryCard", "_importCard", "_multiplayerCard", "_versionCard", "_storageCard" })
            titles.Add(((StackPanel)Field<Border>(window, field).Child).Children.OfType<TextBlock>().First());
        foreach (var title in titles)
            Require(title.FontSize == 18 && title.FontWeight == FontWeights.Bold, $"Inconsistent card heading: {title.Text}");
        var modulesTitle = Named<TextBlock>(window, "ModulesTitleText");
        Require(modulesTitle.FontSize == 18 && modulesTitle.FontWeight == FontWeights.Bold,
            "Components page heading must match the compact card title style.");

        foreach (var name in new[] { "SettingsLanguageTitleText", "SettingsRepairTitleText", "CoreTitleText", "RussianTitleText", "ColorsTitleText", "OosTitleText", "IndependentTitleText", "RoamingSpawnTitleText", "AdditionalRoamingTitleText", "SiegeBalanceTitleText" })
        {
            var fieldTitle = Named<TextBlock>(window, name);
            Require(fieldTitle.FontSize == 15 && fieldTitle.FontWeight == FontWeights.SemiBold,
                $"Mini-heading must stay larger than 13px explanations: {name}");
            if (fieldTitle.ActualHeight > 0 && fieldTitle.Parent is StackPanel { Orientation: Orientation.Horizontal } row)
                foreach (FrameworkElement child in row.Children)
                    Require(child.TranslatePoint(new Point(child.ActualWidth, 0), row).X <= row.ActualWidth + 0.5,
                        $"Mini-heading/help row overflows: {name}");
        }
        var descriptions = new List<TextBlock>();
        foreach (var name in new[] { "SettingsLanguageDescriptionText", "LauncherUpdatesDescriptionText", "PatchChannelDescriptionText",
                     "SettingsRepairDescriptionText", "SettingsUpdatesDescriptionText", "ConfigurationDescriptionText", "DiagnosticsDescriptionText",
                     "HomeWelcomeBodyText", "UpdateNoticeBodyText", "CoreDescriptionText", "RussianDescriptionText", "ColorsDescriptionText",
                     "IndependentDescriptionText", "AdditionalRoamingDescriptionText", "SiegeBalanceDescriptionText",
                     "RemovePatchDescriptionText", "RemoveLauncherDescriptionText", "MultiplayerNoteText" })
            descriptions.Add(Named<TextBlock>(window, name));
        foreach (var field in new[] { "_incidentCard", "_recoveryCard", "_importCard", "_multiplayerCard", "_versionCard", "_storageCard" })
            descriptions.AddRange(((StackPanel)Field<Border>(window, field).Child).Children.OfType<TextBlock>().Skip(1)
                .Where(t => t != Named<TextBlock>(window, "DetailedComparisonTitle")));
        var descriptionStyle = (Style)window.FindResource("CardDescription");
        foreach (var description in descriptions)
        {
            Require(description.Style == descriptionStyle && description.FontSize == 13 && description.LineHeight == 19
                && description.LineStackingStrategy == LineStackingStrategy.BlockLineHeight && description.TextWrapping == TextWrapping.Wrap,
                $"Inconsistent card description: {description.Text}");
            if (description.ActualHeight > 0)
                Require(Math.Abs(description.ActualHeight / 19 - Math.Round(description.ActualHeight / 19)) < 0.05,
                    $"Description line spacing is not 19px: {description.Text}");
        }
        foreach (var name in new[] { "DiagnosticsArchiveInfoText", "GameVersionLabel", "PatchVersionLabel", "TransferText", "PatchChannelLabel", "ConfirmationEyebrowText", "ConfirmationPathLabel" })
            Require(Named<TextBlock>(window, name).FontSize == 12, $"Metadata was not raised from 11 to 12px: {name}");
        foreach (var name in new[] { "LastCheckedText", "LauncherVersionLabel" })
            Require(Named<TextBlock>(window, name).FontSize == 11, $"Small metadata was not raised from 10 to 11px: {name}");
        foreach (var name in new[] { "LauncherVersionText", "GameVersionText", "PatchVersionText", "ConfirmationPathText" })
            Require(Named<TextBlock>(window, name).FontSize == 13, $"Version/path value was not raised from 12 to 13px: {name}");
        Require(Named<TextBlock>(window, "GamePathText").FontSize == 14, "Game path was not raised from 13 to 14px.");

        foreach (var title in titles.Where(t => t.Visibility == Visibility.Visible && t.ActualHeight > 0 && t.Parent is StackPanel))
        {
            var parent = (StackPanel)title.Parent;
            if (parent.Orientation == Orientation.Horizontal)
            {
                var help = parent.Children.OfType<Button>().Single();
                Require(help.Width == 22 && help.Height == 22, "Help icon was enlarged with the heading.");
                var delta = help.TranslatePoint(new Point(0, help.ActualHeight / 2), content).Y
                    - title.TranslatePoint(new Point(0, title.ActualHeight / 2), content).Y;
                Require(Math.Abs(delta) < 0.6, "Help icon is vertically misaligned.");
                var helpGap = help.TranslatePoint(new Point(), content).X - title.TranslatePoint(new Point(title.ActualWidth, 0), content).X;
                Require(Math.Abs(helpGap - 8) < 0.6, "Help icon spacing changed.");
                var outer = (StackPanel)parent.Parent;
                var next = (FrameworkElement)outer.Children[outer.Children.IndexOf(parent) + 1];
                var gap = next.TranslatePoint(new Point(), content).Y - parent.TranslatePoint(new Point(0, parent.ActualHeight), content).Y;
                Require(Math.Abs(gap - 8) < 0.6, "Heading/help row does not leave an 8px description gap.");
            }
            else
            {
                var index = parent.Children.IndexOf(title);
                if (index + 1 == parent.Children.Count) continue;
                var next = (FrameworkElement)parent.Children[index + 1];
                var gap = next.TranslatePoint(new Point(), content).Y - title.TranslatePoint(new Point(0, title.ActualHeight), content).Y;
                Require(Math.Abs(gap - 8) < 0.6, $"Heading does not leave an 8px gap: {title.Text}, {gap}");
            }
        }
        var subtitle = Named<TextBlock>(window, "DetailedComparisonTitle");
        var divider = Named<Border>(window, "DetailedComparisonDivider");
        Require(subtitle.FontSize == 15 && subtitle.FontWeight == FontWeights.Bold && divider.Height == 1,
            "Detailed comparison did not keep its subsection hierarchy.");
        var comparison = (StackPanel)subtitle.Parent;
        Require(comparison.Children.IndexOf(divider) + 1 == comparison.Children.IndexOf(subtitle), "Comparison divider is misplaced.");
        if (page == "multiplayer")
        {
            foreach (var name in new[] { "ImportActions", "PeerActions" })
            {
                var row = Named<WrapPanel>(window, name);
                var buttons = row.Children.OfType<Button>().ToArray();
                Require(buttons.Length == 2, "Action pair lost a button.");
                var sameLine = Math.Abs(buttons[0].TranslatePoint(new Point(), row).Y - buttons[1].TranslatePoint(new Point(), row).Y) < 0.6;
                var fits = buttons.Sum(b => b.ActualWidth + b.Margin.Left + b.Margin.Right) <= row.ActualWidth + 0.5;
                Require(sameLine == fits, "Action pair does not wrap according to available width.");
                Require(buttons.All(b => b.TranslatePoint(new Point(b.ActualWidth, 0), row).X <= row.ActualWidth + 0.5), "Action button is clipped.");
            }
            foreach (var field in new[] { "_importInput", "_peerInput" })
            {
                var input = Field<TextBox>(window, field);
                var border = (Border)input.Template.FindName("InputBorder", input);
                Require(border.CornerRadius == new CornerRadius(5) && input.ActualHeight is >= 30 and <= 40,
                    "Input lost its compact rounded shape (or has doubled padding).");
                Require(input.Template.FindName("PART_ContentHost", input) is ScrollViewer && input.MaxLength == 256,
                    "Native text editing host/limit lost.");
            }
        }
        Console.WriteLine($"TYPOGRAPHY LAYOUT PASS {page}: 18px main headings, 10 mini-headings and subsection at 15px, {descriptions.Count} shared 13px/19px descriptions, metadata +1px, 8px gaps, bounded help rows, rounded native inputs and responsive action pairs");
    }

    internal static void PopulatePreview(MainWindow window, string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Typography preview requires --smoke-test.");
        var manifest = new ChannelManifest();
        manifest.Changelog.Add(new ChangelogEntry
        {
            Category = "patch", Version = "0.0.0-test", PublishedAt = "2026-09-06",
            Title = new LocalizedText { Ru = "Пример оформления обновления", En = "Sample update typography" },
            Body = new LocalizedText
            {
                Ru = "Заголовки карточек: 18, подзаголовки: 15, пояснения: 13. Даты, версии и время последней проверки увеличены на один пункт. Это пример для проверки оформления, а не опубликованное обновление.",
                En = "Card headings use 18, subheadings 15, and explanations 13. Dates, versions and the last-check time are one point larger. This is a visual test fixture, not a published update."
            }
        });
        typeof(MainWindow).GetField("_channel", Fields)!.SetValue(window, manifest);
        typeof(MainWindow).GetMethod("RefreshNews", Fields)!.Invoke(window, null);
        Named<TextBlock>(window, "LastCheckedText").Text = language == "ru" ? "Последняя проверка: 22:45:00" : "Last checked: 22:45:00";
    }

    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Typography checks require --smoke-test.");
        var window = new MainWindow { Left = -30000, Top = -30000, Width = 1050, Height = 680,
            WindowStartupLocation = WindowStartupLocation.Manual, ShowActivated = false, ShowInTaskbar = false };
        void Pump(int milliseconds = 220)
        {
            var frame = new DispatcherFrame(); var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(milliseconds) };
            timer.Tick += (_, _) => frame.Continue = false; timer.Start();
            try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
        }
        int checks = 0;
        void Check(bool value, string message) { if (!value) throw new InvalidOperationException(message); checks++; }
        try
        {
            Field<PawsPatchLauncher.Localization>(window, "_text").SetLanguage(language);
            typeof(MainWindow).GetMethod("ApplyLanguage", Fields)!.Invoke(window, null);
            typeof(MainWindow).GetMethod("SetActivePage", Fields)!.Invoke(window, ["multiplayer"]);
            window.Show(); Pump(); window.UpdateLayout();
            foreach (var field in new[] { "_importInput", "_peerInput" })
            {
                var input = Field<TextBox>(window, field);
                Check(input.Template.FindName("PART_ContentHost", input) is ScrollViewer, "Text editor host missing.");
                Check(input.MaxLength == 256 && input.TextWrapping == TextWrapping.Wrap && input.IsUndoEnabled && !input.AcceptsReturn, "Editing behavior changed.");
                Check(System.Windows.Automation.AutomationProperties.GetName(input).Length > 8, "Accessible input name is missing.");
                input.Text = "PAW-TEST"; input.Select(4, 4);
                Check(input.SelectedText == "TEST", "Selection is broken.");
                input.SelectedText = "BETA";
                Check(input.Text == "PAW-BETA" && input.CanUndo, "Replacing selected text/undo is broken.");
                input.Undo(); Check(input.Text == "PAW-TEST", "Native undo did not restore the input.");
                input.Text = new string('W', 200); window.UpdateLayout();
                Check(input.GetLineIndexFromCharacterIndex(199) > 0, "Long code does not wrap.");
                input.Clear(); window.UpdateLayout();
                Check(input.ActualHeight is >= 30 and <= 40, "Empty text field retained excess height.");
                var focus = input.Template.Triggers.OfType<Trigger>().Single(t => t.Property == UIElement.IsKeyboardFocusWithinProperty);
                var hover = input.Template.Triggers.OfType<Trigger>().Single(t => t.Property == UIElement.IsMouseOverProperty);
                Check(focus.Setters.OfType<Setter>().Any(s => s.Property == Motion.BorderBrushProperty)
                    && hover.Setters.OfType<Setter>().Any(s => s.Property == Motion.BorderBrushProperty), "Focus/hover don't use smooth border transitions.");
                var border = (Border)input.Template.FindName("InputBorder", input);
                input.IsEnabled = false; Pump(); Check(Math.Abs(border.Opacity - 0.45) < 0.01, "Disabled input isn't visually disabled.");
                input.IsEnabled = true; Pump(); Check(Math.Abs(border.Opacity - 1) < 0.01, "Re-enabled input remains faded.");
            }
            foreach (var name in new[] { "ImportActions", "PeerActions" })
            {
                var row = Named<WrapPanel>(window, name); var buttons = row.Children.OfType<Button>().ToArray();
                row.Width = buttons.Max(b => b.ActualWidth + b.Margin.Right) + 1; window.UpdateLayout();
                Check(buttons[1].TranslatePoint(new Point(), row).Y >= buttons[0].ActualHeight + 7.5, "Narrow action pair did not wrap with spacing.");
                row.Width = double.NaN;
            }
            window.Width = 1440; window.UpdateLayout();
            foreach (var name in new[] { "ImportActions", "PeerActions" })
            {
                var row = Named<WrapPanel>(window, name); var buttons = row.Children.OfType<Button>().ToArray();
                Check(Math.Abs(buttons[1].TranslatePoint(new Point(), row).Y - buttons[0].TranslatePoint(new Point(), row).Y) < 0.5, "Wide action pair remained stacked.");
            }
            Console.WriteLine($"TYPOGRAPHY UI PASS {checks} {language}: native selection/edit/undo/wrapping, accessibility, compact height, focus/hover transition wiring, disabled states and action-row reflow; no keyboard focus or real clipboard used");
        }
        finally { window.Close(); }
    }
}
