using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly DispatcherTimer _communityHistoryScrollTimer = new() { Interval = TimeSpan.FromMilliseconds(200) };
    private bool _communityNavigating;
    private bool _communityHistoryOlder;

    private void InitializeCommunityHistory()
    {
        _communityHistoryScrollTimer.Tick += async (_, _) =>
        { _communityHistoryScrollTimer.Stop(); await NavigateCommunityHistoryAsync(_communityHistoryOlder); };
        Closed += (_, _) => _communityHistoryScrollTimer.Stop();
    }

    private async Task<CommunityPage> ReadCommunityPageAsync(string channel, long? before = null)
    {
        if (_communityPageReadOverride is not null) return await _communityPageReadOverride(channel, before, _accountLifetime.Token);
        if (_communityReadOverride is not null) return new(await _communityReadOverride(channel, _accountLifetime.Token), false, 0, false);
        return await _account.ReadCommunityPageAsync(channel, before, _accountLifetime.Token);
    }

    private void ScheduleCommunityHistory(ScrollChangedEventArgs e)
    {
        if (_communityNavigating || _communityRendering || e.ExtentHeightChange != 0 || Math.Abs(e.VerticalChange) < .1) return;
        var view = _communityViews[_communityChannel];
        var older = e.VerticalChange < 0 && CommunityScroll.VerticalOffset < 80 && (view.More || view.ViewStart > 0);
        var newer = e.VerticalChange > 0 && CommunityAtBottom() && !view.AtNewest;
        _communityHistoryScrollTimer.Stop();
        if (older || newer) { _communityHistoryOlder = older; _communityHistoryScrollTimer.Start(); }
    }

    private void RefreshCommunityHistoryControls()
    {
        var view = _communityViews[_communityChannel];
        CommunityOlder.Content = _communityNavigating ? T("Загрузка…", "Loading…") : T("Предыдущие сообщения", "Earlier messages");
        CommunityOlder.Visibility = view.More || view.ViewStart > 0 ? Visibility.Visible : Visibility.Collapsed;
        CommunityNewer.Content = T("Следующие сообщения", "Later messages");
        CommunityNewer.Visibility = !view.AtNewest ? Visibility.Visible : Visibility.Collapsed;
        CommunityOlder.IsEnabled = CommunityNewer.IsEnabled = !_communityNavigating && !_communitySending;
        CommunityHistoryNotice.Text = T("Старые сообщения удалены автоматически. При 10 000 сообщений в этом канале удаляются 5 000 самых старых.",
            "Older messages were removed automatically. At 10,000 messages in this channel, the oldest 5,000 are removed.");
        CommunityHistoryNotice.Visibility = view.Trimmed && !view.More && view.ViewStart == 0 ? Visibility.Visible : Visibility.Collapsed;
    }

    private async void CommunityOlder_Click(object sender, RoutedEventArgs e) => await NavigateCommunityHistoryAsync(true);
    private async void CommunityNewer_Click(object sender, RoutedEventArgs e) => await NavigateCommunityHistoryAsync(false);

    private async Task NavigateCommunityHistoryAsync(bool older)
    {
        if (_communityNavigating || _communitySending || ConfirmationActive || _accountLifetime.IsCancellationRequested) return;
        var channel = _communityChannel; var view = _communityViews[channel]; var mutation = _communityMutationVersion;
        if (!view.Loaded || (older ? !view.More && view.ViewStart == 0 : view.AtNewest)) return;
        _communityNavigating = true; view.Bottom = false; RefreshCommunityHistoryControls();
        try
        {
            if (older && view.ViewStart == 0)
            {
                if (view.Messages.FirstOrDefault() is not { } first) return;
                var page = await ReadCommunityPageAsync(channel, first.Ordinal);
                if (_accountLifetime.IsCancellationRequested || mutation != _communityMutationVersion) return;
                if (!view.Merge(page, true, false))
                {
                    // A retention/moderation change happened while navigating.
                    var latest = await ReadCommunityPageAsync(channel);
                    if (_accountLifetime.IsCancellationRequested || mutation != _communityMutationVersion) return;
                    view.Merge(latest, false, true); view.Bottom = true;
                }
            }
            else view.ViewStart = Math.Clamp(view.ViewStart + (older ? -CommunityHistory.PageSize : CommunityHistory.PageSize),
                0, Math.Max(0, view.Messages.Count - CommunityHistory.VisibleLimit));
            _communityError = "";
            if (channel == _communityChannel) { RenderCommunityMessages(); MarkCommunityRead(); }
        }
        catch (OperationCanceledException) when (_accountLifetime.IsCancellationRequested) { }
        catch (Exception ex) { _communityError = ex is AccountException a ? a.Code : "network"; }
        finally { _communityNavigating = false; if (!_accountLifetime.IsCancellationRequested) RefreshCommunityStatus(); }
    }
}
