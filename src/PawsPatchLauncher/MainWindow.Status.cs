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
        ActionJournal.Record("operation.result", failure ? "failure" : "success");
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
        if (ArcaneAccessBlocked) return ArcaneAccessReason;
        if (_installationFailure is not null) return T("Не удалось прочитать состояние установки: ", "Cannot read the installation state: ") + _installationFailure;
        if (_fileCheckFailed) return T("Найдены ошибки файлов. Откройте проверку файлов в настройках.", "File errors found. Open file verification in Settings.");
        if (_selectionRequiresUpdate) return SelectionUpdateText;
        if (_game is not null && !_patchInstalled) return T("Установите выбранный мод с языками и компонентами для работы без интернета.", "Install the selected mod with its languages and components for offline use.");
        if (CompatibilityRelevant && CompatibilityProblem)
            return _compatiblePatchUpdate is not null ? T("Доступен совместимый патч. Нажмите красный значок у версии игры.", "A compatible patch is available. Open the red icon beside the game version.")
                : _settingsPending || _installedRuntimeMismatch ? T("Примените настройки, чтобы играть с доступными файловыми изменениями.", "Apply settings to play with available file changes.")
                : T("Файловые изменения применены. Игра готова к запуску.", "File changes applied. Ready to play.");
        if (!GameMod.IsArcaneWars(_settings) && _game is not null)
            return _settingsPending ? T("Нажмите «Применить настройки», чтобы переключить мод и язык. Повторная загрузка не нужна.", "Use Apply settings to switch the mod and language. No download is needed.")
                : _patchUpdateAvailable ? T("Доступно обновление: ", "Update available: ") + GameMod.Name(_settings.Mod, _text.Language == "ru")
                : GameMod.Name(_settings.Mod, _text.Language == "ru") + T(" · Готово к запуску.", " · Ready to play.");
        if (_feedFailure is not null && !_patchInstalled) return _feedFailure();
        if (_game is null) return _text["status.notfound"];
        if (!_patchInstalled) return _text["status.notinstalled"];
        if (_pendingLauncherUpdate is not null) return string.Format(_text["update.launcher.ready"], _pendingLauncherUpdate.Version);
        if (_patchUpdateAvailable) return string.Format(_text["update.patch.title"], CurrentChannelName());
        if (FrequencyUnavailable) return FrequencyUnavailableText;
        if (_settingsPending) return T("Перед запуском нажмите «Применить настройки».", "Use Apply settings before launching the game.");
        if (_feedFailure is not null) return T("Установленный мод доступен без интернета. Обновления пока не проверены.", "The installed mod is available offline. Updates have not been checked.");
        if (_launcherCheckFailed) return T("Не удалось проверить обновления лаунчера. Повторите проверку.", "Could not check launcher updates. Try again.");
        if (_channel is null || _lastChecked is null) return T("Обновления ещё не проверены.", "Updates have not been checked yet.");
        return string.Format(_text["patch.ready"], CurrentChannelName());
    }

    private void RefreshOperationStatus()
    {
        var message = _feedback.Message;
        SetOperationCaption(message ?? (FeedBlocksActions ? _text["progress.checking"] : IdleStatus()));
        OperationText.Foreground = (Brush)FindResource(_feedback.Failed || message is null && (_feedFailure is not null || _installationFailure is not null || _fileCheckFailed)
            ? "DangerBrush" : "TextMainBrush");
        var progressVisible = _busy && _feedback.Working || FeedBlocksActions && message is null;
        // One compact title/measurement row stays fixed through every phase.
        // Detailed transfer statistics and cancellation are expanded on demand.
        OperationText.Height = progressVisible ? 18 : double.NaN;
        OperationText.TextWrapping = progressVisible ? TextWrapping.NoWrap : TextWrapping.Wrap;
        OperationText.ToolTip = progressVisible ? OperationText.Text : null;
        OperationWorkDetails.Visibility = progressVisible ? Visibility.Visible : Visibility.Collapsed;
        OperationProgress.Visibility = progressVisible ? Visibility.Visible : Visibility.Collapsed;
        RefreshOperationDetails(progressVisible);
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
        OperationStatusPanel.Visibility = home || _busy || _selectionRequiresUpdate || _presentedError is not null && (!_errorFromFeed || !_silentFeedFailure)
            ? Visibility.Visible : Visibility.Collapsed;
    }
}
