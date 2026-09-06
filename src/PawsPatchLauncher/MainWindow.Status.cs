using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly OperationFeedback _feedback = new();
    private readonly DispatcherTimer _feedbackTimer = new() { Interval = TimeSpan.FromMilliseconds(250) };
    private Func<string>? _feedFailure;
    private string? _installationFailure;
    private bool _settingsPending;
    private bool _fileCheckFailed;
    private string? _feedbackContext;
    private long _operationRevision;
    private TimeSpan _feedTimeout = TimeSpan.FromSeconds(30);

    private void InitializeFeedback()
    {
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
    }

    private void ResetFeedbackContext()
    {
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
        if (_settingsPending) return T("Выбранные настройки будут применены перед запуском игры.", "Selected settings will be applied before launching the game.");
        if (_channel is null || _lastChecked is null) return T("Обновления ещё не проверены.", "Updates have not been checked yet.");
        return string.Format(_text["patch.ready"], CurrentChannelName());
    }

    private void RefreshOperationStatus()
    {
        var message = _feedback.Message;
        OperationText.Text = message ?? (_checkingFeed ? _text["progress.checking"] : IdleStatus());
        OperationText.Foreground = (Brush)FindResource(_feedback.Failed || message is null && (_feedFailure is not null || _installationFailure is not null || _fileCheckFailed)
            ? "DangerBrush" : "TextMainBrush");
        var progressVisible = _busy && _feedback.Working || _checkingFeed && message is null;
        OperationProgress.Visibility = progressVisible ? Visibility.Visible : Visibility.Collapsed;
        if (!progressVisible)
        {
            OperationProgress.IsIndeterminate = false;
            OperationProgress.Value = 0;
        }
        else if (!_busy) OperationProgress.IsIndeterminate = true;
        if (_feedback.HasExpiry) _feedbackTimer.Start();
        else _feedbackTimer.Stop();
        RefreshErrorActions();
    }
}
