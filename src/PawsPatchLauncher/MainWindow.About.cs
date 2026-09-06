using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private string _aboutCategory = "always";
    private int _aboutTransitionVersion;

    private void AboutNav_Click(object sender, RoutedEventArgs e) => SetActivePage("about");
    private async void AboutCategory_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string category }) await SwitchAboutCategoryAsync(category);
    }

    private void SyncAboutTabs()
    {
            foreach (var tab in new[] { AboutAlwaysTab, AboutOptionalTab, AboutBetaTab })
            {
                var category = (string)tab.Tag;
                tab.Content = PatchGuide.CategoryName(category, _text.Language);
                SetChangelogTabState(tab, category == _aboutCategory);
                System.Windows.Automation.AutomationProperties.SetName(tab, (string)tab.Content);
            }
    }

    private void CancelAboutTransition()
    {
        _aboutTransitionVersion++;
        AboutEntriesPanel.BeginAnimation(UIElement.OpacityProperty, null);
        AboutEntriesPanel.Opacity = 1;
    }

    private void RefreshAboutPage()
    {
        CancelAboutTransition();
        SyncAboutTabs();
        AboutTitleText.Text = _text["nav.about"];
        AboutIntroText.Text = T("Что добавляет и меняет Paw's Patch поверх Arcane Wars. Выберите раздел, чтобы посмотреть подробности.",
            "What Paw's Patch adds and changes on top of Arcane Wars. Choose a section to read the details.");
        AboutCategoryText.Text = PatchGuide.CategoryDescription(_aboutCategory, _text.Language);
        AboutEntriesPanel.Children.Clear();
        foreach (var entry in PatchGuide.Entries.Where(x => x.Category == _aboutCategory))
        {
            var panel = new StackPanel();
            var badge = new TextBlock { Text = PatchGuide.CategoryName(entry.Category, _text.Language),
                Style = (Style)FindResource("SmallMetadataText"), Foreground = (Brush)FindResource("GoldBrightBrush"), Margin = new Thickness(0, 0, 0, 6) };
            var title = new TextBlock { Text = entry.Title(_text.Language), Style = (Style)FindResource("CardTitle"), TextWrapping = TextWrapping.Wrap };
            var body = new TextBlock { Text = entry.Body(_text.Language), Style = (Style)FindResource("CardDescription") };
            panel.Children.Add(badge); panel.Children.Add(title); panel.Children.Add(body);
            var card = new Border { Name = "AboutEntry_" + entry.Id.Replace('-', '_'), Tag = entry.Id,
                Style = (Style)FindResource("Card"), Margin = new Thickness(0, 0, 0, 14), Child = panel };
            System.Windows.Automation.AutomationProperties.SetName(card, entry.Title(_text.Language));
            AboutEntriesPanel.Children.Add(card);
        }
    }

    private async Task SwitchAboutCategoryAsync(string category)
    {
        var target = category is "optional" or "beta" ? category : "always";
        if (target == _aboutCategory) return;
        _aboutCategory = target;
        SyncAboutTabs();
        var revision = ++_aboutTransitionVersion;
        var animate = _activePage == "about" && AboutEntriesPanel.IsVisible && SystemParameters.ClientAreaAnimation;
        if (animate)
        {
            AboutEntriesPanel.BeginAnimation(UIElement.OpacityProperty,
                new DoubleAnimation(AboutEntriesPanel.Opacity, 0, TimeSpan.FromMilliseconds(80))
                { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }, FillBehavior = FillBehavior.HoldEnd },
                HandoffBehavior.SnapshotAndReplace);
            await Task.Delay(90);
        }
        if (revision != _aboutTransitionVersion) return;
        RefreshAboutPage();
        MainOptionsScroll.ScrollToTop();
        if (animate) { AboutEntriesPanel.Opacity = 0; Motion.Reveal(AboutEntriesPanel); }
    }
}
