using System.Text.Json;

namespace PawsPatchLauncher;

public sealed record PendingInstallation(string GameDirectory, string Configuration, string Channel, string ReleaseId, DateTimeOffset Started, string? PinnedRelease = null);
public sealed class PendingInstallationStore
{
    private readonly string _path;
    public PendingInstallationStore(string? root = null) => _path = Path.Combine(root ?? ActivityStore.Root, "pending-installation.json");
    public PendingInstallation? Load()
    {
        try
        {
            if (!File.Exists(_path) || new FileInfo(_path).Length > 8192) return null;
            var saved = JsonSerializer.Deserialize<PendingInstallation>(File.ReadAllText(_path));
            return saved is not null && saved.ReleaseId.Length == 64 && saved.ReleaseId.All(Uri.IsHexDigit)
                && Path.IsPathFullyQualified(saved.GameDirectory) && FriendConfiguration.TryParse(saved.Configuration, saved.Channel, out _) ? saved : null;
        }
        catch { return null; }
    }
    public void Save(PendingInstallation state)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_path)!);
        File.WriteAllText(_path + ".tmp", JsonSerializer.Serialize(state));
        File.Move(_path + ".tmp", _path, true);
    }
    public void Clear() { if (File.Exists(_path)) File.Delete(_path); }
}
