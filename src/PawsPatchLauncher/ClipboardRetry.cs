using System.Runtime.InteropServices;

namespace PawsPatchLauncher;

public static class ClipboardRetry
{
    private static readonly int[] Delays = [40, 70, 110, 160, 220];

    public static bool IsBusy(Exception error) => error is ExternalException && error.HResult == unchecked((int)0x800401D0);

    // Preserve the caller's context: WPF paste/test delegates use STA, native Unicode
    // writes use their serialized background worker. Never force-unlock another owner.
    public static async Task<T> RunAsync<T>(Func<T> operation, CancellationToken cancellationToken = default,
        Func<TimeSpan, CancellationToken, Task>? delay = null)
    {
        delay ??= Task.Delay;
        for (var attempt = 0; ; attempt++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try { return operation(); }
            catch (Exception error) when (IsBusy(error) && attempt < Delays.Length)
            {
                await delay(TimeSpan.FromMilliseconds(Delays[attempt]), cancellationToken);
            }
        }
    }
}
