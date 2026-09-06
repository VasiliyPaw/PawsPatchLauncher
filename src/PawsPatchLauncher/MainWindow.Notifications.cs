using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    // Independent of install/download status: copying must not hide a failure or finish a transfer.
    private readonly OperationFeedback _toast = new();
    private readonly DispatcherTimer _toastTimer = new() { Interval = TimeSpan.FromMilliseconds(200) };
    private CancellationTokenSource? _clipboardRequest;
    private bool _notificationClosed;
    private Action<string> _clipboardWrite = Clipboard.SetText;
    private Func<string> _clipboardRead = () => Clipboard.GetText();

    private void InitializeNotifications()
    {
        _toastTimer.Tick += (_, _) =>
        {
            if (!ToastPanel.IsMouseOver && !ToastPanel.IsKeyboardFocusWithin) RefreshToast();
        };
        Closed += (_, _) =>
        {
            _notificationClosed = true;
            _toastTimer.Stop();
            _clipboardRequest?.Cancel();
        };
    }

    private void ShowToast(Func<string> message, bool failure = false)
    {
        if (_notificationClosed) return;
        _toast.Show(message, failure, TimeSpan.FromSeconds(5));
        RefreshToast();
        ToastPanel.UpdateLayout();
        Motion.Reveal(ToastPanel);
    }

    private void RefreshToast()
    {
        ToastCloseButton.ToolTip = T("Закрыть уведомление", "Dismiss notification");
        System.Windows.Automation.AutomationProperties.SetName(ToastCloseButton, (string)ToastCloseButton.ToolTip);
        var message = _toast.Message;
        if (message is null)
        {
            _toastTimer.Stop();
            if (ToastPanel.Visibility == Visibility.Visible) Motion.Hide(ToastPanel);
            return;
        }
        ToastText.Text = message;
        ToastIcon.Kind = _toast.Failed ? IconKind.Warning : IconKind.Check;
        ToastIcon.Foreground = (Brush)FindResource(_toast.Failed ? "DangerBrush" : "GoldBrightBrush");
        ToastPanel.BorderBrush = (Brush)FindResource(_toast.Failed ? "DangerBrush" : "GoldBrush");
        ToastPanel.Visibility = Visibility.Visible;
        if (_toast.HasExpiry) _toastTimer.Start(); else _toastTimer.Stop();
    }

    private void ToastCloseButton_Click(object sender, RoutedEventArgs e)
    {
        _toast.Clear();
        _toastTimer.Stop();
        Motion.Hide(ToastPanel);
    }

    private async Task<bool> ClipboardActionAsync<TResult>(Func<TResult> operation, Action<TResult> success,
        Action<Func<string>, bool>? notice = null)
    {
        if (_notificationClosed) return false;
        _clipboardRequest?.Cancel();
        using var request = new CancellationTokenSource();
        _clipboardRequest = request;
        notice ??= ShowToast;
        // Remove an old "copied" toast before trying again, including a retry that eventually fails.
        _toast.Clear(); RefreshToast();
        try
        {
            var result = await ClipboardRetry.RunAsync(() => { Dispatcher.VerifyAccess(); return operation(); }, request.Token);
            if (request.IsCancellationRequested || _notificationClosed) return false;
            success(result);
            return true;
        }
        catch (OperationCanceledException) when (request.IsCancellationRequested) { return false; }
        catch (Exception error)
        {
            if (!request.IsCancellationRequested && !_notificationClosed)
            {
                ActivityStore.Log(error);
                notice(() => ClipboardRetry.IsBusy(error)
                    ? T("Буфер обмена занят. Подождите немного и повторите действие.", "The clipboard is busy. Wait a moment and try again.")
                    : T("Не удалось обратиться к буферу обмена. Попробуйте ещё раз.", "Could not access the clipboard. Please try again."), true);
            }
            return false;
        }
        finally { if (ReferenceEquals(_clipboardRequest, request)) _clipboardRequest = null; }
    }

    private Task<bool> CopyTextAsync(string text, Func<string> copied, Action<Func<string>, bool>? notice = null)
    {
        notice ??= ShowToast;
        return ClipboardActionAsync(() => { _clipboardWrite(text); return true; }, _ => notice(copied, false), notice);
    }

    private Task<bool> PasteTextAsync(TextBox target)
    {
        var previous = target.Text;
        return ClipboardActionAsync(_clipboardRead, text =>
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                ShowToast(() => T("В буфере обмена нет текста.", "There is no text in the clipboard."));
                return;
            }
            if (target.Text != previous)
            {
                ShowToast(() => T("Поле уже изменено. Повторите вставку, если она всё ещё нужна.", "The field was edited. Paste again if you still need it."));
                return;
            }
            if (target.MaxLength > 0 && text.Length > target.MaxLength)
            {
                ShowToast(() => T("Текст слишком длинный. Скопируйте только код или отпечаток.", "The text is too long. Copy only the code or fingerprint."), true);
                return;
            }
            target.Text = text;
            ShowToast(() => T("Текст вставлен. Проверьте его перед применением.", "Text pasted. Review it before applying."));
        });
    }
}
