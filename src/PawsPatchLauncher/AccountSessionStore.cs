using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;

namespace PawsPatchLauncher;

// Kept out of UserSettings, installation backups and diagnostic archives.
public sealed class AccountSession
{
    public Guid LauncherId { get; set; }
    public Guid LoginId { get; set; }
    public DateTimeOffset? CreatedAt { get; set; }
    public DateTimeOffset? NicknameChangedAt { get; set; }
    public DateTimeOffset? EmailChangedAt { get; set; }
    public DateTimeOffset? PasswordChangedAt { get; set; }
    public DateTimeOffset? AvatarChangedAt { get; set; }
    public bool DeletionPending { get; set; }
    public int AdminLevel { get; set; }
    public bool ProtectedAdmin { get; set; }
    public DateTimeOffset? BannedAt { get; set; }
    public DateTimeOffset? BanUntil { get; set; }
    public string BanReason { get; set; } = "";
    public DateTimeOffset? DeletedAt { get; set; }
    public string AccessToken { get; set; } = "";
    public string RefreshToken { get; set; } = "";
    public long ExpiresAt { get; set; }
    public string UserId { get; set; } = "";
    public string Email { get; set; } = "";
    public string Nickname { get; set; } = "";
    public string DisplayName { get; set; } = "";
    public DateTimeOffset? DisplayNameChangedAt { get; set; }
    public override string ToString() => "AccountSession [redacted]";
}

public sealed class AccountSessionStore
{
    private readonly string _directory;
    public string SessionPath => Path.Combine(_directory, "session.dat");
    public AccountSessionStore(string root) => _directory = Path.Combine(root, "account");

    // File locks survive awaits, unlike thread-affine named mutexes. Also serializes
    // refresh-token rotation between two launcher instances and logout vs. refresh.
    public async Task<IDisposable> LockAsync(CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(_directory);
        for (var attempt = 0; ; attempt++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try { return new FileStream(Path.Combine(_directory, "session.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
            catch (IOException) when (attempt < 100) { await Task.Delay(100, cancellationToken).ConfigureAwait(false); }
        }
    }

    public AccountSession? Read()
    {
        if (!File.Exists(SessionPath)) return null;
        if (new FileInfo(SessionPath).Length > 64 * 1024) throw new InvalidDataException("Invalid account session.");
        var plaintext = WindowsUserProtection.Transform(File.ReadAllBytes(SessionPath), protect: false);
        try
        {
            var session = JsonSerializer.Deserialize<AccountSession>(plaintext);
            if (session is null || !Guid.TryParse(session.UserId, out _) || session.AccessToken.Length is < 1 or > 16384 || session.RefreshToken.Length is < 1 or > 16384)
                throw new InvalidDataException("Invalid account session.");
            return session;
        }
        finally { CryptographicOperations.ZeroMemory(plaintext); }
    }

    public void Save(AccountSession session)
    {
        Directory.CreateDirectory(_directory);
        var plaintext = JsonSerializer.SerializeToUtf8Bytes(session);
        byte[] encrypted;
        try { encrypted = WindowsUserProtection.Transform(plaintext, protect: true); }
        finally { CryptographicOperations.ZeroMemory(plaintext); }
        var temporary = Path.Combine(_directory, "session-" + Guid.NewGuid().ToString("N") + ".tmp");
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            { stream.Write(encrypted); stream.Flush(flushToDisk: true); }
            File.Move(temporary, SessionPath, overwrite: true);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    public void Clear() { if (File.Exists(SessionPath)) File.Delete(SessionPath); }
}

internal static class WindowsUserProtection
{
    [StructLayout(LayoutKind.Sequential)]
    private struct Blob { public int Length; public IntPtr Data; }
    [DllImport("crypt32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptProtectData(ref Blob input, string description, IntPtr entropy, IntPtr reserved, IntPtr prompt, int flags, out Blob output);
    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptUnprotectData(ref Blob input, IntPtr description, IntPtr entropy, IntPtr reserved, IntPtr prompt, int flags, out Blob output);
    [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr memory);

    internal static byte[] Transform(byte[] bytes, bool protect)
    {
        var input = new Blob { Length = bytes.Length, Data = Marshal.AllocHGlobal(bytes.Length) };
        var output = new Blob();
        try
        {
            Marshal.Copy(bytes, 0, input.Data, bytes.Length);
            // UI_FORBIDDEN, current Windows user only; never LOCAL_MACHINE.
            var ok = protect
                ? CryptProtectData(ref input, "PawsPatchLauncher account", IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 1, out output)
                : CryptUnprotectData(ref input, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 1, out output);
            if (!ok) throw new CryptographicException("Windows could not protect or read the account session.");
            var result = new byte[output.Length];
            Marshal.Copy(output.Data, result, 0, result.Length);
            return result;
        }
        finally
        {
            for (var i = 0; i < input.Length; i++) Marshal.WriteByte(input.Data, i, 0);
            Marshal.FreeHGlobal(input.Data);
            if (output.Data != IntPtr.Zero)
            {
                for (var i = 0; i < output.Length; i++) Marshal.WriteByte(output.Data, i, 0);
                LocalFree(output.Data);
            }
        }
    }
}
