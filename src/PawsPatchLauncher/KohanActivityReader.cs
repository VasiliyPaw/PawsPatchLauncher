using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace PawsPatchLauncher;

/// <summary>Bounded read-only observation of the verified Steam 1.3.72 executable.</summary>
public sealed class KohanActivityReader
{
    public const string SupportedSha256 = "1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45";
    private (int pid, long started, string path, string hash)? _verified;
    public static IReadOnlyDictionary<string,string> SupportedExecutables(InstallState? state)
    {
        var files = new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase) { ["k2.exe"] = SupportedSha256 };
        if (state?.BaseGameSha256?.Equals(SupportedSha256,StringComparison.OrdinalIgnoreCase) != true) return files;
        foreach (var file in state.Modules.Values.Where(m=>m.Enabled).SelectMany(m=>m.Files))
            if (file.Path.StartsWith("k2_",StringComparison.OrdinalIgnoreCase) && file.Path.EndsWith(".exe",StringComparison.OrdinalIgnoreCase)
                && !file.Path.Contains('/') && !file.Path.Contains('\\') && file.Sha256.Length==64 && file.Sha256.All(Uri.IsHexDigit))
                files[file.Path]=file.Sha256;
        return files;
    }
    public GameActivity? Read(string? gameDirectory, InstallState? state = null)
    {
        if (string.IsNullOrEmpty(gameDirectory)) return null;
        var directory = Path.GetFullPath(gameDirectory);
        var allowed = SupportedExecutables(state);
        var games = Process.GetProcesses();
        try
        {
        foreach (var game in games)
        {
            try
            {
                if (!allowed.TryGetValue(game.ProcessName+".exe",out var expectedHash)) continue;
                var expectedPath = Path.Combine(directory,game.ProcessName+".exe");
                var module = game.MainModule;
                if (module is null || !Path.GetFullPath(module.FileName).Equals(expectedPath, StringComparison.OrdinalIgnoreCase)) continue;
                var identity = (game.Id, game.StartTime.ToUniversalTime().Ticks, expectedPath, expectedHash);
                if (_verified != identity)
                {
                    using var file = new FileStream(expectedPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                    if (!Convert.ToHexString(SHA256.HashData(file)).Equals(expectedHash, StringComparison.OrdinalIgnoreCase)) return null;
                    _verified = identity;
                }
                using var handle = OpenProcess(0x1010, false, game.Id); // QUERY_LIMITED_INFORMATION | VM_READ only
                if (handle.IsInvalid) return null;
                byte[] ReadBytes(uint address, int count)
                {
                    if (count is < 1 or > 16384 || address < 0x10000 || (ulong)address + (uint)count > uint.MaxValue) throw new InvalidDataException();
                    var bytes = new byte[count];
                    if (!ReadProcessMemory(handle, new IntPtr(address), bytes, (nuint)count, out var done) || done != (nuint)count) throw new IOException("Game activity is not available.");
                    return bytes;
                }
                return ReadSnapshot(checked((uint)module.BaseAddress.ToInt64()), ReadBytes);
            }
            catch (Exception error) when (error is InvalidOperationException or System.ComponentModel.Win32Exception or IOException or UnauthorizedAccessException or OverflowException or ArgumentException) { return null; }
        }
        _verified = null;
        return null;
        }
        finally { foreach (var game in games) game.Dispose(); }
    }

    public static GameActivity? ReadSnapshot(uint image, Func<uint, int, byte[]> read)
    {
        uint U32(uint address) => BitConverter.ToUInt32(read(address, 4));
        float F32(uint address) => BitConverter.ToSingle(read(address, 4));
        byte U8(uint address) => read(address, 1)[0];
        string Wide(uint address)
        {
            if (address < 0x10000) return "";
            var chars = new List<byte>();
            for (var i = 0; i < 80; i++)
            {
                var bytes = read(checked(address + (uint)(i * 2)), 2);
                if (bytes[0] == 0 && bytes[1] == 0) return new string(Encoding.Unicode.GetString(chars.ToArray()).Where(c => !char.IsControl(c)).ToArray()).Trim();
                chars.AddRange(bytes);
            }
            return new string(Encoding.Unicode.GetString(chars.ToArray()).Where(c => !char.IsControl(c)).ToArray()).Trim();
        }
        string Ascii(uint address, int size)
        {
            var bytes = read(address, size); var end = Array.IndexOf(bytes, (byte)0);
            return end < 0 ? "" : Encoding.ASCII.GetString(bytes, 0, end);
        }
        try
        {
            // Stable native routines outside all Paw patch sites; checked on every sample.
            if (!read(image + 0x1618a5, 6).SequenceEqual(new byte[] { 0x8b,0x41,0x04,0x83,0xe8,0x00 })
                || !read(image + 0x15d1e7, 4).SequenceEqual(new byte[] { 0x8b,0x41,0x04,0xc3 })) return null;
            var session = U32(image + 0x5f3fe4);
            if (session < 0x10000) return null;
            var state = U32(session + 0xf0);
            var appState = U32(image + 0x5f92f4);
            var world = U32(image + 0x5f3fb8);
            var phase = appState is 5 or 13 ? "editor" : state switch { 0 => "menu", 1 => "lobby", 2 when world >= 0x10000 => "match", 2 => "loading", _ => null };
            if (phase is null) return null;
            if (phase is "menu" or "loading" or "editor") return new GameActivity(phase);
            var multiplayer = U8(session + 0x100) != 0;
            var manager = U32(image + 0x5f3fec);
            var local = manager >= 0x10000 ? U32(manager + 0xc) : 0;
            var players = new List<GameParticipant>(); var visited = new HashSet<uint>();
            string? self = null;
            var head = U32(session + 0xc8); var node = head;
            while (node != 0 && visited.Count < 64)
            {
                if (!visited.Add(node)) return null;
                var player = U32(node);
                if (U32(player) != image + 0x4bd914) return null;
                var id = U32(player + 0x20); var bot = U8(player + 0xc) != 0;
                var name = Wide(U32(player + 8));
                var key = "p" + id.ToString(System.Globalization.CultureInfo.InvariantCulture);
                if (name.Length > 0)
                {
                    players.Add(new GameParticipant(key, name, bot));
                    if (!bot && local != 0 && U32(player + 4) == local) self = key;
                }
                node = U32(node + 4);
            }
            if (node != 0 || players.Select(p => p.Key).Distinct().Count() != players.Count) return null;
            string? room = null;
            if (multiplayer)
            {
                // Hash the native Steam lobby identity; do not transmit Steam IDs or join commands.
                var connect = Ascii(image + 0x5f21e0, 64);
                const string prefix = "+connect_lobby ";
                if (connect.StartsWith(prefix, StringComparison.Ordinal) && ulong.TryParse(connect[prefix.Length..], out var lobby) && lobby != 0)
                    room = Convert.ToHexString(SHA256.HashData(Encoding.ASCII.GetBytes("KohanII/SteamLobby/" + lobby.ToString(System.Globalization.CultureInfo.InvariantCulture))));
            }
            int? elapsed = null;
            if (phase == "match") { var seconds = F32(world + 0xe8); if (float.IsFinite(seconds) && seconds is >= 0 and <= 604800) elapsed = (int)seconds; }
            // Follow the same WorldCreator selection used by the native lobby map preview.
            var sourceKind = U32(session + 0x64);
            var sourceOffset = sourceKind switch { 0 => 0x80u, 2 => 0x7cu, 5 => 0x88u, _ => 0x78u };
            var creator = U32(session + sourceOffset);
            int? width = null, height = null;
            if (sourceKind <= 5 && creator >= 0x10000)
            {
                var x = F32(creator + 0x3c); var y = F32(creator + 0x40);
                if (float.IsFinite(x) && float.IsFinite(y) && x is >= 16 and <= 8192 && y is >= 16 and <= 8192
                    && x == MathF.Truncate(x) && y == MathF.Truncate(y)) { width = (int)x; height = (int)y; }
            }
            // Native linked lists can change between reads. Discard a torn transition rather than guessing.
            if (session != U32(image + 0x5f3fe4) || state != U32(session + 0xf0) || head != U32(session + 0xc8)
                || world != U32(image + 0x5f3fb8) || sourceKind != U32(session + 0x64) || creator != U32(session + sourceOffset)) return null;
            return new GameActivity(phase, multiplayer, elapsed, width, height, Room: room, Self: self, Players: players);
        }
        catch (Exception error) when (error is IOException or ArgumentException or OverflowException) { return null; }
    }

    [DllImport("kernel32.dll", SetLastError = true)] private static extern SafeProcessHandle OpenProcess(uint access, bool inherit, int processId);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool ReadProcessMemory(SafeProcessHandle process, IntPtr address, byte[] buffer, nuint size, out nuint read);
}
