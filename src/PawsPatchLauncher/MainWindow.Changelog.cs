using System.Windows;
using System.Windows.Media.Animation;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private int _changelogTransitionVersion;
    private bool _changelogTransitionPending;

    private void CancelChangelogTransition()
    {
        _changelogTransitionVersion++;
        _changelogTransitionPending = false;
        NewsScrollViewer.BeginAnimation(UIElement.OpacityProperty, null);
        NewsScrollViewer.Opacity = 1;
    }

    private async Task SwitchChangelogAsync(string category)
    {
        var target = category.Equals("launcher", StringComparison.OrdinalIgnoreCase) ? "launcher" : "patch";
        // A second click on the current tab must not flash or reset the reading position.
        if (_changelogCategory == target) return;
        _changelogCategory = target;
        var version = ++_changelogTransitionVersion;
        _changelogTransitionPending = true;
        RefreshChangelogTabState();
        var animate = SystemParameters.ClientAreaAnimation && NewsScrollViewer.IsVisible
            && NewsScrollViewer.ActualWidth > 0 && NewsScrollViewer.ActualHeight > 0;
        if (animate)
        {
            NewsScrollViewer.BeginAnimation(UIElement.OpacityProperty,
                new DoubleAnimation(NewsScrollViewer.Opacity, 0, TimeSpan.FromMilliseconds(80))
                {
                    EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut },
                    FillBehavior = FillBehavior.HoldEnd
                }, HandoffBehavior.SnapshotAndReplace);
            await Task.Delay(90);
        }
        // A newer click, language/feed refresh or closing the window invalidates this swap.
        if (version != _changelogTransitionVersion) return;
        RefreshNews();
        NewsScrollViewer.ScrollToTop();
        NewsScrollViewer.UpdateLayout();
        if (animate)
        {
            NewsScrollViewer.Opacity = 0;
            Motion.Reveal(NewsScrollViewer);
        }
    }
}
