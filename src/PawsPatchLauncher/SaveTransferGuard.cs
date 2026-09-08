using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public sealed record SaveTransferDescriptor(string FileName, long Size, string Sha256);
public sealed record SaveInstallResult(string Path, string? BackupPath);

// Staging foundation, not an enabled network transport. Never opens a save in the game,
// extracts an archive, or treats the header/hash as a malware scan.
public static partial class SaveTransferGuard
{
    public const int MaximumBytes = 20 * 1024 * 1024;
    public static void ValidateDescriptor(SaveTransferDescriptor file)
    {
        var name = file.FileName;
        if (string.IsNullOrWhiteSpace(name) || name.Length > 128 || Path.GetFileName(name) != name
            || name.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || name.EndsWith(' ') || name.EndsWith('.')
            || name.StartsWith('.') || !name.EndsWith(".rsg", StringComparison.OrdinalIgnoreCase)
            || name.Any(c=>char.GetUnicodeCategory(c)==System.Globalization.UnicodeCategory.Format)
            || ReservedName().IsMatch(name.Split('.')[0].TrimEnd(' ')) || file.Size is < 16 or > MaximumBytes
            || !HashPattern().IsMatch(file.Sha256)) throw new InvalidDataException("Invalid save descriptor.");
    }
    public static void ValidateBytes(SaveTransferDescriptor file, ReadOnlySpan<byte> bytes)
    {
        ValidateDescriptor(file);
        if (bytes.Length != file.Size || !bytes[..4].SequenceEqual("TGCK"u8)
            || !CryptographicOperations.FixedTimeEquals(SHA256.HashData(bytes), Convert.FromHexString(file.Sha256)))
            throw new InvalidDataException("Save integrity check failed.");
    }
    public static SaveTransferDescriptor Describe(string name, ReadOnlySpan<byte> bytes)
    {
        var file = new SaveTransferDescriptor(name, bytes.Length, Convert.ToHexString(SHA256.HashData(bytes)));
        ValidateBytes(file, bytes); return file;
    }
    // A caller must explicitly confirm an existing file and pass its pre-confirmation hash.
    // A mismatched hash means the file changed while the question was open: ask again.
    public static async Task<SaveInstallResult> InstallAsync(string saveDirectory, SaveTransferDescriptor file,
        byte[] bytes, string? approvedExistingHash, Func<bool> gameRunning, CancellationToken ct = default,bool allowWhileRunning=false)
    {
        ValidateDescriptor(file);
        if (bytes.Length != file.Size) throw new InvalidDataException("Save size mismatch.");
        var snapshot = (byte[])bytes.Clone();
        ValidateBytes(file, snapshot);
        var root = Path.GetFullPath(saveDirectory);
        CheckAncestors(root);
        if (!allowWhileRunning&&gameRunning()) throw new InvalidOperationException("Game is running.");
        Directory.CreateDirectory(root);
        CheckAncestors(root);
        var destination = Path.Combine(root, file.FileName);
        var staging = Path.Combine(root, ".paw-transfer-" + Guid.NewGuid().ToString("N") + ".tmp");
        var gatePath = Path.Combine(root, ".paw-transfer.lock");
        CheckAncestors(gatePath);
        using var gate = new FileStream(gatePath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        try
        {
            await using (var stream = new FileStream(staging, FileMode.CreateNew, FileAccess.Write, FileShare.None, 65536, true))
            {
                await stream.WriteAsync(snapshot, ct); await stream.FlushAsync(ct); stream.Flush(true);
            }
            ct.ThrowIfCancellationRequested();
            CheckAncestors(root);
            if (!allowWhileRunning&&gameRunning()) throw new InvalidOperationException("Game is running.");
            string? backup = null;
            if (File.Exists(destination))
            {
                CheckAncestors(destination);
                if (approvedExistingHash is null || !HashPattern().IsMatch(approvedExistingHash))
                    throw new InvalidOperationException("Overwrite confirmation required.");
                // Hold a deny-write handle through the atomic replace. A game currently writing
                // this file makes the open fail; never overwrite a save in flight.
                using var existing = new FileStream(destination, FileMode.Open, FileAccess.Read, FileShare.Read|FileShare.Delete);
                    if (!CryptographicOperations.FixedTimeEquals(SHA256.HashData(existing), Convert.FromHexString(approvedExistingHash)))
                        throw new InvalidOperationException("Existing save changed. Confirm overwrite again.");
                var backups = Path.Combine(root, ".paw-backups");
                CheckAncestors(backups); Directory.CreateDirectory(backups); CheckAncestors(backups);
                backup = Path.Combine(backups, file.FileName + "." + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "." + Guid.NewGuid().ToString("N") + ".bak");
                // One atomic replace preserves the exact file being replaced, including a
                // concurrent last-second game write. A failed backup must abort replacement.
                File.Replace(staging, destination, backup);
            }
            else
            {
                if (approvedExistingHash is not null) throw new InvalidOperationException("Existing save disappeared. Confirm again.");
                File.Move(staging, destination, false);
            }
            return new SaveInstallResult(destination, backup);
        }
        finally { if (File.Exists(staging)) File.Delete(staging); }
    }
    private static void CheckAncestors(string path)
    {
        for (var item = Path.GetFullPath(path); !string.IsNullOrEmpty(item); item = Path.GetDirectoryName(item))
            if ((File.Exists(item) || Directory.Exists(item)) && (File.GetAttributes(item) & FileAttributes.ReparsePoint) != 0)
                throw new InvalidDataException("Save paths must not contain links.");
    }
    [GeneratedRegex("^(CON|PRN|AUX|NUL|COM[0-9¹²³]|LPT[0-9¹²³])(?:\\.|$)", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex ReservedName();
    [GeneratedRegex("\\A[0-9a-fA-F]{64}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex HashPattern();
}
