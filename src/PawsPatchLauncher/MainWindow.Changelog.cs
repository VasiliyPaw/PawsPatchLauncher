using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Animation;
namespace PawsPatchLauncher;
public partial class MainWindow
{
    public sealed record TimelineChoice(string Id, string Label, bool Unread = false)
    { public Visibility UnreadVisibility => Unread ? Visibility.Visible : Visibility.Collapsed; }
    private int _changelogTransitionVersion;
    private bool _changelogTransitionPending, _syncingTimeline;
    private string? _renderedNewsIdentity;
    private string? _renderedHistorySelection;
    private readonly HashSet<string> _expandedHistoryEntries = [];
    private string _historySubject = "", _historySource = "all", _historyBranch = "stable", _historyActiveSelection = "";
    private IReadOnlyList<TimelineEntry> _renderedHistory = [];
    private ChannelManifest?[] HistoryManifests() => [ChannelForMod("stable"), ChannelForMod("beta"), _latestChannel, _channel];
    private IReadOnlyList<TimelineEntry> HistoryRows(string subject, string source, string branch)
        => subject == "reborn" ? RebornAccess ? RebornHistory.Entries(_rebornHistory,branch,_text.Language) : [] : ChangelogTimeline.Entries(HistoryManifests(), subject, source, branch);
    private string HistoryBranchFor(string mod) => mod == "reborn" ? RebornChannel : mod == _settings.Mod ? _settings.Channel : _settings.ModChannels?.GetValueOrDefault(mod)?.Channel ?? "stable";
    private void SyncHistorySelection()
    {
        var subject = _activePage == "reborn" && RebornAccess ? "reborn" : _settings.Mod;
        var branch = HistoryBranchFor(subject);
        var active = subject + ":" + branch;
        if (_historyActiveSelection == active) return;
        _historyActiveSelection = active; _historySubject = subject; _historySource = "all"; _historyBranch = branch;
    }
    private void SyncHistoryFilters()
    {
        SyncHistorySelection();
        _syncingTimeline = true;
        try
        {
            bool Unread(string subject, string source, string branch) => HistoryRows(subject, source, branch).Any(r => ChangelogTimeline.IsUnread(_settings, r));
            var subjects = new[] { "launcher", GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars }.Concat(RebornAccess ? ["reborn"] : Array.Empty<string>());
            SetChoices(HistorySubjectCombo, subjects.Select(id => new TimelineChoice(id, id == "reborn" ? "Kohan Reborn" : id == "launcher" ? T("Лаунчер", "Launcher") : GameMod.Name(id, _text.Language == "ru"), Unread(id, "all", id == "reborn" ? "all" : HistoryBranchFor(id)))).ToArray(), _historySubject);
            SetChoices(HistorySourceCombo, [new("all", T("Все изменения", "All changes")),
                new("mod", _historySubject == GameMod.Vanilla ? T("Игра", "Game") : T("Мод", "Mod"), Unread(_historySubject, "mod", "all")),
                new("patch", "Paw's Patch", Unread(_historySubject, "patch", _historyBranch))], _historySource);
            SetChoices(HistoryBranchCombo, [new("all", T("Все ветки", "All branches")),
                new("stable", T("Релиз", "Release"), Unread(_historySubject, "patch", "stable")),
                new("beta", T("Бета", "Beta"), Unread(_historySubject, "patch", "beta"))], _historyBranch);
            var reborn = _historySubject == "reborn";
            HistorySourceCombo.Visibility = _historySubject == "launcher" || reborn ? Visibility.Collapsed : Visibility.Visible;
            HistoryBranchCombo.Visibility = _historySubject == "launcher" || _historySource == "mod" && !reborn ? Visibility.Collapsed : Visibility.Visible;
            Grid.SetColumn(HistoryBranchCombo,reborn ? 0 : 1); Grid.SetColumnSpan(HistoryBranchCombo,reborn ? 2 : 1);
            HistoryBranchCombo.Margin = reborn ? new Thickness(0) : new Thickness(6,0,0,0);
            System.Windows.Automation.AutomationProperties.SetName(HistorySubjectCombo, T("История: игра или лаунчер", "History: game or launcher"));
            System.Windows.Automation.AutomationProperties.SetName(HistorySourceCombo, T("История: мод или патч", "History: mod or patch"));
            System.Windows.Automation.AutomationProperties.SetName(HistoryBranchCombo, reborn ? "Kohan Reborn: " + T("Канал", "Channel") : T("Канал истории патча", "Patch history channel"));
        }
        finally { _syncingTimeline = false; }
    }
    private static void SetChoices(ComboBox combo, TimelineChoice[] choices, string selected)
    {
        if (combo.ItemsSource is not TimelineChoice[] old || !old.SequenceEqual(choices)) combo.ItemsSource = choices;
        combo.SelectedItem = ((TimelineChoice[])combo.ItemsSource).FirstOrDefault(c => c.Id == selected);
    }
    private async void HistoryFilter_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (_initializing || _syncingTimeline || sender is not ComboBox { SelectedItem: TimelineChoice choice } combo) return;
        var subject = combo == HistorySubjectCombo ? choice.Id : _historySubject;
        var source = combo == HistorySourceCombo ? choice.Id : _historySource;
        var branch = combo == HistoryBranchCombo ? choice.Id : _historyBranch;
        if (combo == HistorySubjectCombo) { source = "all"; branch = HistoryBranchFor(subject); }
        await SwitchHistoryAsync(subject, source, branch);
    }
    private void CancelChangelogTransition()
    {
        _changelogTransitionVersion++; _changelogTransitionPending = false;
        NewsScrollViewer.BeginAnimation(UIElement.OpacityProperty, null); NewsScrollViewer.Opacity = 1;
    }
    private async Task SwitchHistoryAsync(string subject, string source, string branch)
    {
        if (subject == "reborn")
        {
            if (!RebornAccess) subject = "launcher";
            source = "all";
        }
        if ((_historySubject, _historySource, _historyBranch) == (subject, source, branch)) return;
        (_historySubject, _historySource, _historyBranch) = (subject, source, branch);
        var version = ++_changelogTransitionVersion; _changelogTransitionPending = true; SyncHistoryFilters();
        var animate = SystemParameters.ClientAreaAnimation && NewsScrollViewer.IsVisible && NewsScrollViewer.ActualHeight > 0;
        if (animate)
        {
            NewsScrollViewer.BeginAnimation(UIElement.OpacityProperty, new DoubleAnimation(NewsScrollViewer.Opacity, 0, TimeSpan.FromMilliseconds(80))
            { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }, FillBehavior = FillBehavior.HoldEnd });
            await Task.Delay(90);
        }
        if (version != _changelogTransitionVersion) return;
        RefreshNews(); NewsScrollViewer.ScrollToTop();
        if (animate) { NewsScrollViewer.Opacity = 0; Motion.Reveal(NewsScrollViewer); }
        if (subject == "reborn") _ = LoadRebornHistoryAsync();
    }
    private void RefreshNews()
    {
        if (NewsEntriesPanel is null) return;
        SyncHistorySelection(); NewsTitleText.Text = _text["news.title"]; SyncHistoryFilters();
        var entries = HistoryRows(_historySubject, _historySource, _historyBranch);
        var selection = _historySubject + ":" + _historySource + ":" + _historyBranch;
        var status = _historySubject == "reborn" && (entries.Count == 0 || _rebornHistoryError) ? $":{_rebornHistoryLoading}:{_rebornHistoryError}" : "";
        var identity = _text.Language + ":" + selection + status + string.Join('|', entries.Select(e => e.ReadKey + e.ContentId + e.Overview));
        if (identity == _renderedNewsIdentity) { MarkVisibleChangelogRead(); return; }
        var preserveScroll = selection == _renderedHistorySelection && NewsScrollViewer.ActualHeight > 0;
        var previousOffset = NewsScrollViewer.VerticalOffset;
        var anchor = preserveScroll ? NewsEntriesPanel.Children.OfType<Border>().FirstOrDefault(card => card.Tag is string[]
            && card.TranslatePoint(new Point(),NewsScrollViewer).Y + card.ActualHeight > 0) : null;
        var anchorKeys = anchor?.Tag as string[];
        var anchorY = anchor?.TranslatePoint(new Point(),NewsScrollViewer).Y ?? 0;
        _renderedHistorySelection = selection;
        _renderedNewsIdentity = identity; _renderedHistory = entries; CancelChangelogTransition(); NewsEntriesPanel.Children.Clear();
        if (_historySubject == "reborn" && (entries.Count == 0 || _rebornHistoryError)) AddRebornHistoryStatus();
        else if (entries.Count == 0) NewsEntriesPanel.Children.Add(new TextBlock { Text = _historySource == "mod"
            ? T("История выпусков оригинальной игры пока не добавлена.", "Release notes for the original game have not been added yet.") : _text["news.empty"], Style = (Style)FindResource("CardDescription") });
        foreach (var group in entries.GroupBy(e => e.Subject + ":" + e.Source + ":" + e.ContentId + ":" + e.Overview)) NewsEntriesPanel.Children.Add(HistoryCard(group.ToArray()));
        if (preserveScroll)
        {
            NewsScrollViewer.UpdateLayout();
            var current = anchorKeys is null ? null : NewsEntriesPanel.Children.OfType<Border>().FirstOrDefault(card => card.Tag is string[] keys && keys.Intersect(anchorKeys).Any());
            NewsScrollViewer.ScrollToVerticalOffset(current is null ? previousOffset
                : NewsScrollViewer.VerticalOffset + current.TranslatePoint(new Point(),NewsScrollViewer).Y - anchorY);
        }
        MarkVisibleChangelogRead();
    }
    private Border HistoryCard(TimelineEntry[] rows)
    {
        var row = rows[0]; var entry = row.Entry; var item = new StackPanel();
        var owner = row.Source == "reborn" ? "Kohan Reborn" : row.Source == "patch" ? "Paw's Patch" : row.Source == "launcher" ? T("Лаунчер", "Launcher") : T("Авторский мод", "Original mod");
        var branch = row.Source is "patch" or "reborn" ? " · " + string.Join(" / ", rows.Select(r => ChannelPresentation.Name(r.Branch, _text.Language)).Distinct()) : "";
        item.Children.Add(new TextBlock { Text = owner + branch + (row.Overview ? T(" · обзор версии", " · version overview") : ""), Style = (Style)FindResource("MetadataText"), Foreground = SocialBrush(row.Source == "mod" ? "#92CBBE" : "#D9BD78") });
        item.Children.Add(new TextBlock { Text = row.Source == "patch" ? ChannelPresentation.ChangelogText(entry.Title.Get(_text.Language), _text.Language) : entry.Title.Get(_text.Language), Style = (Style)FindResource("CardSubtitle"), Margin = new Thickness(0, 7, 0, 0) });
        var metadata = row.Source == "patch" ? PawPatchVersions.Display(row.Subject, entry.Version)! : entry.Version;
        if (DateTimeOffset.TryParse(entry.PublishedAt, out var date)) metadata += " · " + date.ToString(UiLanguages.DatePattern(_text.Language) + "");
        else if (!row.Overview) metadata += T(" · дата не указана", " · date not specified");
        item.Children.Add(new TextBlock { Text = metadata, Style = (Style)FindResource("SmallMetadataText"), Margin = new Thickness(0, 4, 0, 0) });
        var body = row.LocalizedBody ?? (row.Source == "patch" ? ChannelPresentation.ChangelogText(entry.Body.Get(_text.Language), _text.Language) : entry.Body.Get(_text.Language));
        var content = new StackPanel { Margin = new Thickness(0, 9, 0, 0), Tag = "changelog-body" }; item.Children.Add(content);
        void RenderBody(string text) => RenderChangelogBody(content, text);
        RenderBody(body);
        if (body.Length > 420 || body.Count(c => c == '\n') > 5)
        {
            var preview = ChangelogTextLayout.Preview(body);
            var keys = rows.Select(r => r.ReadKey).ToArray();
            var expanded = keys.Any(_expandedHistoryEntries.Contains);
            RenderBody(expanded ? body : preview);
            string Caption() => expanded ? T("Свернуть ▴", "Collapse ▴") : T("Показать полностью ▾", "Show all ▾");
            var button = new Button { Content = Caption(), Style = (Style)FindResource("GhostButton"), HorizontalAlignment = HorizontalAlignment.Left, Margin = new Thickness(0, 10, 0, 0), Padding = new Thickness(9, 5, 9, 5) };
            button.Click += (_, _) =>
            {
                expanded = !expanded;
                foreach (var key in keys) { if (expanded) _expandedHistoryEntries.Add(key); else _expandedHistoryEntries.Remove(key); }
                RenderBody(expanded ? body : preview); button.Content = Caption(); Motion.Reveal(content);
            }; item.Children.Add(button);
        }
        return new Border { Child = item, Tag = rows.Select(r => r.ReadKey).ToArray(), Background = SocialBrush("#132840"), BorderBrush = SocialBrush("#40536E"), BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(7), Padding = new Thickness(12), Margin = new Thickness(0, 0, 0, 10) };
    }

    // Share the same typography between release history and the Reborn build page.
    private void RenderChangelogBody(StackPanel content, string text)
    {
        content.Children.Clear();
        foreach (var line in ChangelogTextLayout.Parse(text))
        {
            var block = new TextBlock { Text = line.Kind == ChangelogTextKind.Bullet ? "• " + line.Text : line.Text,
                TextWrapping = TextWrapping.Wrap, Foreground = SocialBrush(line.Kind == ChangelogTextKind.Heading ? "#E7D099" : "#CDD5E1") };
            if (line.Kind == ChangelogTextKind.Heading)
            { block.FontSize = 15; block.FontWeight = FontWeights.SemiBold; block.Margin = new Thickness(0, content.Children.Count == 0 ? 0 : 10, 0, 3); }
            else { block.Style = (Style)FindResource("CardDescription"); block.Margin = new Thickness(line.Kind == ChangelogTextKind.Bullet ? 9 : 0, 0, 0, 5); }
            content.Children.Add(block);
        }
    }
}
