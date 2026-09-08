using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly OperationFeedback _feedback = new();
    private readonly DispatcherTimer _feedbackTimer = new() { Interval = TimeSpan.FromMilliseconds(250) };
    private Func<string>? _feedFailure;
    private bool _silentFeedFailure;
    private string? _installationFailure;
    private bool _settingsPending;
    private bool _fileCheckFailed;
    private string? _feedbackContext;
    private long _operationRevision;
    private TimeSpan _feedTimeout = TimeSpan.FromSeconds(30);

    private void InitializeFeedback()
    {
        InitializeProgressMotion();
        _feedbackTimer.Tick += (_, _) => RefreshOperationStatus();
        Closed += (_, _) => _feedbackTimer.Stop();
    }

    private void ShowWorking(Func<string> message)
    {
        ClearFriendlyError();
        _feedback.Begin(message);
        RefreshOperationStatus();
    }

    private void ShowResult(Func<string> message, bool failure = false, TimeSpan? duration = null)
    {
        if (!failure) ClearFriendlyError();
        FinishTransfer();
        _feedback.Show(message, failure, duration);
        RefreshOperationStatus();
        ShowToast(message, failure);
    }

    private void ResetFeedbackContext()
    {
        CancelBackgroundFeed();
        ClearFriendlyError();
        _feedback.Clear();
        _feedFailure = null;
        _lastChecked = null;
        _fileCheckFailed = false;
    }

    private string IdleStatus()
    {
        if (_installationFailure is not null) return T("Не удалось прочитать состояние установки: ", "Cannot read the installation state: ") + _installationFailure;
        if (_fileCheckFailed) return T("Найдены ошибки файлов. Откройте проверку файлов в настройках.", "File errors found. Open file verification in Settings.");
        if (_feedFailure is not null) return _feedFailure();
        if (_game is null) return _text["status.notfound"];
        if (!_patchInstalled) return _text["status.notinstalled"];
        if (_pendingLauncherUpdate is not null) return string.Format(_text["update.launcher.ready"], _pendingLauncherUpdate.Version);
        if (_patchUpdateAvailable) return string.Format(_text["update.patch.title"], CurrentChannelName());
        if (FrequencyUnavailable) return FrequencyUnavailableText;
        if (_settingsPending) return T("Нажмите «Применить настройки» или запустите игру.", "Use Apply settings or launch the game.");
        if (_launcherCheckFailed) return T("Не удалось проверить обновления лаунчера. Повторите проверку.", "Could not check launcher updates. Try again.");
        if (_channel is null || _lastChecked is null) return T("Обновления ещё не проверены.", "Updates have not been checked yet.");
        return string.Format(_text["patch.ready"], CurrentChannelName());
    }

    private void RefreshOperationStatus()
    {
        var message = _feedback.Message;
        OperationText.Text = message ?? (FeedBlocksActions ? _text["progress.checking"] : IdleStatus());
        OperationText.Foreground = (Brush)FindResource(_feedback.Failed || message is null && (_feedFailure is not null || _installationFailure is not null || _fileCheckFailed)
            ? "DangerBrush" : "TextMainBrush");
        var progressVisible = _busy && _feedback.Working || FeedBlocksActions && message is null;
        OperationProgress.Visibility = progressVisible ? Visibility.Visible : Visibility.Collapsed;
        if (!progressVisible)
        {
            SetOperationIndeterminate(false);
            SetOperationProgress(0,animate:false);
        }
        else if (!_busy) SetOperationIndeterminate(true);
        if (_feedback.HasExpiry) _feedbackTimer.Start();
        else _feedbackTimer.Stop();
        RefreshErrorActions();
        RefreshOperationPlacement();
    }

    // History is Home-only, but active operations must retain progress/cancel/error actions.
    private void RefreshOperationPlacement()
    {
        if (OperationFooterHost is null) return;
        var home = _activePage == "home";
        if (home && OperationFooterHost.Content is not null)
        {
            OperationFooterHost.Content = null;
            ChangelogContentGrid.Children.Add(OperationStatusPanel);
        }
        else if (!home && OperationStatusPanel.Parent is Grid parent)
        {
            parent.Children.Remove(OperationStatusPanel);
            OperationFooterHost.Content = OperationStatusPanel;
        }
        OperationStatusPanel.Margin = home ? new Thickness(0,14,0,0) : new Thickness(0,0,0,10);
        OperationStatusPanel.Visibility = home || _busy || _presentedError is not null && (!_errorFromFeed || !_silentFeedFailure)
            ? Visibility.Visible : Visibility.Collapsed;
    }
}
