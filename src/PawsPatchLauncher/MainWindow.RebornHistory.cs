using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private IReadOnlyList<RebornBuild> _rebornHistory = [];
    private bool _rebornHistoryLoading, _rebornHistoryLoaded, _rebornHistoryError, _rebornHistoryAllowed;
    private string _rebornHistoryOwner = "";
    private int _rebornHistoryRequest;
    private Func<CancellationToken,Task<IReadOnlyList<RebornBuild>>>? _rebornHistoryOverride = null;

    private void RefreshRebornHistoryAccess()
    {
        if (_rebornHistoryOwner == _account.UserId && _rebornHistoryAllowed == RebornAccess) return;
        _rebornHistoryOwner = _account.UserId; _rebornHistoryAllowed = RebornAccess;
        _rebornHistoryRequest++; _rebornHistory = []; _rebornHistoryLoading = _rebornHistoryLoaded = _rebornHistoryError = false;
        if (!RebornAccess && _historySubject == "reborn") { _historySubject = "launcher"; _historySource = "all"; }
        if (!_initializing) RefreshNews();
    }
    private async Task LoadRebornHistoryAsync(bool force = false)
    {
        if (!RebornAccess || _rebornHistoryLoading || !force && _rebornHistoryLoaded) return;
        var owner = _account.UserId; var request = ++_rebornHistoryRequest;
        _rebornHistoryLoading = true; _rebornHistoryError = false; RefreshNews();
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token); timeout.CancelAfter(TimeSpan.FromSeconds(12));
            var history = await (ActivityStore.IsSmokeTest
                ? _rebornHistoryOverride?.Invoke(timeout.Token) ?? Task.FromResult<IReadOnlyList<RebornBuild>>([])
                : _account.GetRebornHistoryAsync(timeout.Token));
            if (owner != _account.UserId || request != _rebornHistoryRequest || !RebornAccess) return;
            if (history.Count > RebornHistory.Limit || history.Select(b => b.Id).Distinct().Count() != history.Count) throw new InvalidDataException("Invalid Reborn history.");
            foreach (var build in history) RebornBuild.Validate(build);
            _rebornHistory = history; _rebornHistoryLoaded = true;
        }
        catch (AccountException error) when (error.Code == "reborn_access_denied")
        { if (owner == _account.UserId && request == _rebornHistoryRequest) { _rebornDenied = true; RefreshRebornAccess(); } }
        catch (Exception error) when (error is AccountException or IOException or InvalidDataException or OperationCanceledException or System.Net.Http.HttpRequestException)
        { if (owner == _account.UserId && request == _rebornHistoryRequest) { _rebornHistoryError = true; _rebornHistoryLoaded = false; } }
        finally
        {
            if (owner == _account.UserId && request == _rebornHistoryRequest)
            { _rebornHistoryLoading = false; RefreshNews(); }
        }
    }
    private void AddRebornHistoryStatus()
    {
        var text = _rebornHistoryLoading ? T("Проверяем сборки…","Checking builds…") : _rebornHistoryError
            ? T("Каталог сборок пока недоступен. Проверьте подключение и повторите попытку.","The build catalog is unavailable. Check your connection and try again.")
            : T("Сборка ещё не опубликована","No build published yet");
        NewsEntriesPanel.Children.Add(new TextBlock { Text = text, Style = (Style)FindResource("CardDescription") });
        if (_rebornHistoryError)
        {
            var retry = new Button { Content = T("Повторить","Retry"), Style = (Style)FindResource("GhostButton"), HorizontalAlignment = HorizontalAlignment.Left, Margin = new Thickness(0,10,0,0) };
            LauncherIcon.SetKind(retry,IconKind.Sync); retry.Click += async (_,_) => await LoadRebornHistoryAsync(force:true);
            NewsEntriesPanel.Children.Add(retry);
        }
    }
}
