namespace PawsPatchLauncher;

/// <summary>Keep the latest progress sample and at most one pending context callback.
/// Filtering inside Progress&lt;T&gt;'s callback still queues every chunk on the UI thread.</summary>
public sealed class CoalescingProgress<T>(Action<T> handler, TimeSpan? minimumInterval = null) : IProgress<T>
{
    private readonly SynchronizationContext _context = SynchronizationContext.Current ?? new SynchronizationContext();
    private readonly object _gate = new();
    private T _latest = default!;
    private bool _queued;
    private readonly System.Diagnostics.Stopwatch _clock = System.Diagnostics.Stopwatch.StartNew();
    private long _lastDispatch = -100000;

    public void Report(T value)
    {
        lock (_gate)
        {
            _latest = value;
            if (_queued) return;
            _queued = true;
        }
        var delay = Math.Max(0, (minimumInterval?.TotalMilliseconds ?? 0) - (_clock.ElapsedMilliseconds - Interlocked.Read(ref _lastDispatch)));
        if (delay == 0) _context.Post(_ => Drain(), null);
        else _ = PostDelayedAsync((int)Math.Ceiling(delay));
    }

    private async Task PostDelayedAsync(int delay)
    {
        await Task.Delay(delay).ConfigureAwait(false);
        _context.Post(_ => Drain(), null);
    }

    private void Drain()
    {
        T value;
        lock (_gate) { value = _latest; Interlocked.Exchange(ref _lastDispatch, _clock.ElapsedMilliseconds); _queued = false; }
        handler(value);
    }
}
