namespace PawsPatchLauncher;

// A result belongs to an operation, not to the last control that happened to refresh.
// Only informational results expire; actionable failures survive until the next action.
public sealed class OperationFeedback(TimeProvider? clock = null)
{
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;
    private Func<string>? _message;
    private DateTimeOffset? _expires;
    public bool Working { get; private set; }
    public bool Failed { get; private set; }

    public void Begin(Func<string> message)
    {
        Clear();
        Working = true;
        _message = message;
    }

    public void Show(Func<string> message, bool failure = false, TimeSpan? duration = null)
    {
        Working = false;
        Failed = failure;
        _message = message;
        _expires = failure ? null : _clock.GetUtcNow() + (duration ?? TimeSpan.FromSeconds(6));
    }

    public void Finish() { if (Working) Clear(); }
    public void Clear()
    {
        _message = null;
        _expires = null;
        Working = Failed = false;
    }

    public string? Message
    {
        get
        {
            if (_expires is { } expiry && _clock.GetUtcNow() >= expiry) Clear();
            return _message?.Invoke();
        }
    }
    public bool HasExpiry => _expires is not null;
}
