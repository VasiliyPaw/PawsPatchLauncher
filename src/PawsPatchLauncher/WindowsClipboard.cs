using System.ComponentModel;
using System.Runtime.InteropServices;

namespace PawsPatchLauncher;

// Eager Unicode data avoids WPF's OleFlushClipboard round trip. All native work
// stays off the UI thread; one writer at a time prevents late writes overtaking new ones.
internal static class WindowsClipboard
{
    private static readonly SemaphoreSlim Writer = new(1, 1);
    internal static async Task<bool> WriteTextAsync(nint owner, string text, CancellationToken token,
        Action<nint, string, CancellationToken>? write = null)
    {
        await Writer.WaitAsync(token).ConfigureAwait(false);
        try
        {
            return await Task.Run(() => ClipboardRetry.RunAsync(() =>
            {
                token.ThrowIfCancellationRequested();
                (write ?? WriteText)(owner, text, token);
                return true;
            }, token), token).ConfigureAwait(false);
        }
        finally { Writer.Release(); }
    }

    private static void WriteText(nint owner, string text, CancellationToken token)
    {
        if (owner == 0 || !IsWindow(owner)) throw new OperationCanceledException("Clipboard owner closed.", token);
        // Prepare the entire payload before opening or clearing the user's clipboard.
        var chars = (text + '\0').ToCharArray();
        var memory = GlobalAlloc(0x0002, checked((nuint)chars.Length * 2)); // GMEM_MOVEABLE
        if (memory == 0) throw new Win32Exception(Marshal.GetLastWin32Error());
        var opened = false;
        try
        {
            var pointer = GlobalLock(memory);
            if (pointer == 0) throw new Win32Exception(Marshal.GetLastWin32Error());
            try { Marshal.Copy(chars, 0, pointer, chars.Length); }
            finally { GlobalUnlock(memory); }
            token.ThrowIfCancellationRequested();
            if (!OpenClipboard(owner)) throw new ExternalException("Clipboard is occupied.", unchecked((int)0x800401D0));
            opened = true;
            token.ThrowIfCancellationRequested();
            if (!EmptyClipboard()) throw new Win32Exception(Marshal.GetLastWin32Error());
            // Once emptied, finish this transaction even if a new request cancels it.
            if (SetClipboardData(13, memory) == 0) throw new Win32Exception(Marshal.GetLastWin32Error()); // CF_UNICODETEXT
            memory = 0; // Ownership belongs to Windows, including after the launcher exits.
        }
        finally
        {
            if (opened) CloseClipboard();
            if (memory != 0) GlobalFree(memory);
        }
    }

    [DllImport("user32.dll")] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool IsWindow(nint window);
    [DllImport("user32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool OpenClipboard(nint owner);
    [DllImport("user32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool EmptyClipboard();
    [DllImport("user32.dll", SetLastError = true)] private static extern nint SetClipboardData(uint format, nint data);
    [DllImport("user32.dll")] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool CloseClipboard();
    [DllImport("kernel32.dll", SetLastError = true)] private static extern nint GlobalAlloc(uint flags, nuint bytes);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern nint GlobalLock(nint memory);
    [DllImport("kernel32.dll")] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool GlobalUnlock(nint memory);
    [DllImport("kernel32.dll")] private static extern nint GlobalFree(nint memory);
}
