using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public sealed class ClipboardButton : Button
{
    private static readonly DependencyPropertyKey SuccessKey = DependencyProperty.RegisterAttachedReadOnly(
        "IsCopySuccessful", typeof(bool), typeof(ClipboardButton), new FrameworkPropertyMetadata(false));
    public static readonly DependencyProperty IsCopySuccessfulProperty = SuccessKey.DependencyProperty;
    public static bool GetIsCopySuccessful(DependencyObject button) => (bool)button.GetValue(IsCopySuccessfulProperty);
    private bool _pending;
    private string? _context;
    private CancellationTokenSource? _feedback;

    protected override bool IsEnabledCore => base.IsEnabledCore && !_pending && !GetIsCopySuccessful(this);

    public void SetContext(string context)
    {
        if (_context == context) return;
        _context = context; ResetFeedback();
    }
    public void ResetFeedback()
    {
        _feedback?.Cancel(); _feedback = null; _pending = false;
        SetValue(SuccessKey, false); CoerceValue(IsEnabledProperty);
    }
    public async Task CopyAsync(Func<Task<bool>> copy)
    {
        if (!IsEnabled || _feedback is not null) return;
        using var request = new CancellationTokenSource();
        _feedback = request; _pending = true; CoerceValue(IsEnabledProperty);
        try
        {
            if (!await copy() || request.IsCancellationRequested) return;
            _pending = false; SetValue(SuccessKey, true); CoerceValue(IsEnabledProperty);
            await Task.Delay(TimeSpan.FromSeconds(5), request.Token);
        }
        catch (OperationCanceledException) when (request.IsCancellationRequested) { }
        finally { if (ReferenceEquals(_feedback, request)) ResetFeedback(); }
    }
}
