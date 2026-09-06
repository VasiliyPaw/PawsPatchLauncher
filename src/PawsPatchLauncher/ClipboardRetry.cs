using System.Runtime.InteropServices;

namespace PawsPatchLauncher;

public static class ClipboardRetry
{
    private static readonly int[] Delays = [40, 70, 110, 160, 220];

    public static bool IsBusy(Exception error) => error is ExternalException && error.HResult == unchecked((int)0x800401D0);

    // Await on the caller's context: Windows clipboard calls must stay on the UI's STA thread.
    // No forced unlock, background clipboard reads, or retry of unrelated errors.
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
