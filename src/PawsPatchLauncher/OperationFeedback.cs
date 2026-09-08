namespace PawsPatchLauncher;

// A result belongs to an operation, not to the last control that happened to refresh.
// Actionable failures persist by default; the independent toast explicitly opts into expiry.
public sealed class OperationFeedback(TimeProvider? clock = null)
{
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;
    private Func<string>? _message;
    private DateTimeOffset? _expires;
    private DateTimeOffset _started;
    public long Version { get; private set; }
    public TimeSpan? Remaining => _expires is { } expiry ? TimeSpan.FromTicks(Math.Max(0, (expiry - _clock.GetUtcNow()).Ticks)) : null;
    public double Progress => _expires is { } expiry && expiry > _started
        ? Math.Clamp((_clock.GetUtcNow() - _started).TotalMilliseconds / (expiry - _started).TotalMilliseconds, 0, 1) : 0;
    public bool Working { get; private set; }
    public bool Failed { get; private set; }

    public void Begin(Func<string> message)
    {
        Clear();
        Working = true;
        _message = message;
    }

    public void Show(Func<string> message, bool failure = false, TimeSpan? duration = null, bool expireFailure = false)
    {
        Version++;
        Working = false;
        Failed = failure;
        _message = message;
        _started = _clock.GetUtcNow();
        _expires = failure && !expireFailure ? null : _started + (duration ?? TimeSpan.FromSeconds(6));
    }

    public void Finish() { if (Working) Clear(); }
    public void Clear()
    {
        Version++;
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

    // Preserve the original deadline/localization callback when a newer toast takes the primary slot.
    public OperationFeedback Snapshot() => new(_clock)
    { _message=_message, _expires=_expires, _started=_started, Version=Version, Working=Working, Failed=Failed };
}
