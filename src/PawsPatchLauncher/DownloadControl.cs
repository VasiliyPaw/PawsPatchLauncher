using System.Diagnostics;

namespace PawsPatchLauncher;

/// <summary>Only the file transport waits here. Chat and installation commits use no gate.</summary>
public sealed class DownloadControl
{
    private readonly object _sync = new();
    private TaskCompletionSource<bool>? _resume;
    private long _nextByteTime;
    private int _limit;
    private int _revision;
    public int Revision { get { lock (_sync) return _revision; } }
    public bool IsPaused { get { lock (_sync) return _resume is not null; } }
    public int LimitKiB { get { lock (_sync) return _limit; } set { lock (_sync) { _limit = Math.Clamp(value, 0, 102400); _nextByteTime = 0; _revision++; } } }
    public void Pause() { lock (_sync) { _resume ??= new(TaskCreationOptions.RunContinuationsAsynchronously); _revision++; } }
    public void Resume()
    {
        TaskCompletionSource<bool>? wait;
        lock (_sync) { wait = _resume; _resume = null; _nextByteTime = 0; _revision++; }
        wait?.TrySetResult(true);
    }
    public async Task WaitAsync(CancellationToken ct)
    {
        while (true)
        {
            Task? wait; lock (_sync) wait = _resume?.Task;
            if (wait is null) { ct.ThrowIfCancellationRequested(); return; }
            await wait.WaitAsync(ct).ConfigureAwait(false);
        }
    }
    public async Task PaceAsync(int bytes, CancellationToken ct)
    {
        await WaitAsync(ct).ConfigureAwait(false);
        long due;
        lock (_sync)
        {
            if (_limit == 0) return;
            var now = Stopwatch.GetTimestamp();
            due = _nextByteTime = Math.Max(now, _nextByteTime) + (long)(bytes * (double)Stopwatch.Frequency / (_limit * 1024L));
        }
        while (true)
        {
            await WaitAsync(ct).ConfigureAwait(false);
            var remaining = (due - Stopwatch.GetTimestamp()) / (double)Stopwatch.Frequency;
            if (remaining <= 0) return;
            await Task.Delay(TimeSpan.FromSeconds(Math.Min(.1, remaining)), ct).ConfigureAwait(false);
            lock (_sync) if (_limit == 0 || _nextByteTime == 0) return;
        }
    }
}
