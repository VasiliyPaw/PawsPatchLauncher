using System.Runtime.InteropServices;
using PawsPatchLauncher;

internal static class ClipboardRetryTests
{
    internal static async Task<int> RunAsync()
    {
        int checks = 0, attempts = 0;
        void Check(bool condition, string message) { if (!condition) throw new Exception(message); checks++; }
        ExternalException Busy() => new("Synthetic occupied clipboard", unchecked((int)0x800401D0));
        var pauses = new List<TimeSpan>();
        Task Delay(TimeSpan duration, CancellationToken token) { token.ThrowIfCancellationRequested(); pauses.Add(duration); return Task.CompletedTask; }
        var text = await ClipboardRetry.RunAsync(() => ++attempts <= 3 ? throw Busy() : "PAW-BETA-test", delay: Delay);
        Check(text == "PAW-BETA-test" && attempts == 4, "Transient clipboard lock was not retried.");
        Check(pauses.Count == 3 && pauses.All(x => x > TimeSpan.Zero), "Clipboard retries have no backoff.");
        attempts = 0; pauses.Clear();
        try { await ClipboardRetry.RunAsync<bool>(() => { attempts++; throw Busy(); }, delay: Delay); throw new Exception("Expected clipboard failure."); }
        catch (ExternalException error) { Check(ClipboardRetry.IsBusy(error), "Clipboard error identity was lost."); }
        Check(attempts == 6 && pauses.Count == 5 && pauses.Sum(x => x.TotalMilliseconds) == 600, "Clipboard retry is unbounded.");
        attempts = 0;
        try { await ClipboardRetry.RunAsync<bool>(() => { attempts++; throw new InvalidOperationException("unrelated"); }, delay: Delay); throw new Exception("Expected unrelated failure."); }
        catch (InvalidOperationException) { Check(attempts == 1, "Unrelated error was retried."); }
        using var cancelled = new CancellationTokenSource(); cancelled.Cancel(); attempts = 0;
        try { await ClipboardRetry.RunAsync(() => ++attempts, cancelled.Token, Delay); throw new Exception("Expected cancellation."); }
        catch (OperationCanceledException) { Check(attempts == 0, "Cancelled operation still accessed the clipboard."); }
        using var superseded = new CancellationTokenSource(); attempts = 0;
        try
        {
            await ClipboardRetry.RunAsync<bool>(() => { attempts++; throw Busy(); }, superseded.Token,
                (_, token) => { superseded.Cancel(); token.ThrowIfCancellationRequested(); return Task.CompletedTask; });
            throw new Exception("Expected cancellation during retry.");
        }
        catch (OperationCanceledException) { Check(attempts == 1, "Superseded request continued writing."); }
        Check(!ClipboardRetry.IsBusy(new ExternalException("Other COM failure", unchecked((int)0x80004005))), "Unknown COM error treated as clipboard contention.");
        Console.WriteLine($"CLIPBOARD POLICY PASS {checks}: bounded retries, success, failure, cancellation; no real clipboard access");
        return checks;
    }
}
