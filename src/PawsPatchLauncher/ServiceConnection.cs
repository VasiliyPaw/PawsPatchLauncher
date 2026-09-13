namespace PawsPatchLauncher;

// Shared by account/chat requests. Canceled view reads never report a connection failure.
internal sealed class ServiceConnection
{
    private readonly object _sync = new();
    private long _started, _completed;
    private bool? _available;
    private DateTimeOffset _checkedAt;
    internal bool? Available { get { lock (_sync) return _available; } }
    internal DateTimeOffset CheckedAt { get { lock (_sync) return _checkedAt; } }
    internal event Action? Changed;
    internal long Begin() => Interlocked.Increment(ref _started);
    internal void Complete(long request, bool available)
    {
        bool changed;
        lock (_sync)
        {
            if (request < _completed) return;
            _completed = request; _checkedAt = DateTimeOffset.UtcNow;
            changed = _available != available; _available = available;
        }
        if (changed) Changed?.Invoke();
    }
}
