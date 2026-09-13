using System.Diagnostics;

namespace PawsPatchLauncher;

public sealed record StartupCheckResult(LauncherRelease? Release, bool Online, int Attempts, Exception? Error = null);

public static class StartupUpdateCheck
{
    public static readonly TimeSpan OfflineBudget = TimeSpan.FromSeconds(30);
    public static readonly TimeSpan ContinueDelay = TimeSpan.FromSeconds(10);
    public static bool CanOpenInstalled(TimeSpan elapsed, bool connectionFailed, bool checking)
        => checking && connectionFailed && elapsed >= ContinueDelay;
    public static async Task<StartupCheckResult> RunAsync(
        Func<CancellationToken, Task<LauncherRelease?>> read,
        IProgress<(int Attempt, TimeSpan Remaining)>? progress = null,
        CancellationToken cancellationToken = default,
        TimeSpan? budget = null, TimeSpan? attemptLimit = null, TimeSpan? retryInterval = null)
    {
        var limit = budget ?? OfflineBudget;
        var attemptTimeout = attemptLimit ?? TimeSpan.FromSeconds(3);
        var interval = retryInterval ?? TimeSpan.FromSeconds(1);
        var watch = Stopwatch.StartNew();
        Exception? lastError = null;
        var attempts = 0;
        while (watch.Elapsed < limit)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var remaining = limit - watch.Elapsed;
            attempts++;
            progress?.Report((attempts, remaining));
            using var attempt = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            attempt.CancelAfter(remaining < attemptTimeout ? remaining : attemptTimeout);
            try
            {
                // Bound even an unresponsive provider; normal HTTP reads also receive cancellation.
                var release = await read(attempt.Token).WaitAsync(attempt.Token);
                cancellationToken.ThrowIfCancellationRequested();
                return new(release, true, attempts);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
            catch (Exception error) { lastError = error; }
            remaining = limit - watch.Elapsed;
            if (remaining > TimeSpan.Zero)
                await Task.Delay(remaining < interval ? remaining : interval, cancellationToken);
        }
        return new(null, false, attempts, lastError);
    }
}
