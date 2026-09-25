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
            var result=FirstAvailable(games,game=>
            {
                if (!allowed.TryGetValue(game.ProcessName+".exe",out var expectedHash)) return null;
                var expectedPath = Path.Combine(directory,game.ProcessName+".exe");
                var module = game.MainModule;
                if (module is null || !Path.GetFullPath(module.FileName).Equals(expectedPath, StringComparison.OrdinalIgnoreCase)) return null;
                var identity = (game.Id, game.StartTime.ToUniversalTime().Ticks, expectedPath, expectedHash);
                if (_verified != identity)
                {
                    using var file = new FileStream(expectedPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                    if (!Convert.ToHexString(SHA256.HashData(file)).Equals(expectedHash, StringComparison.OrdinalIgnoreCase)) return null;
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
                var snapshot=ReadSnapshot(checked((uint)module.BaseAddress.ToInt64()), ReadBytes);
                if(snapshot is not null)_verified=identity;
                return snapshot;
            });
            if(result is null)_verified=null;
            return result;
        }
        finally { foreach (var game in games) game.Dispose(); }
    }

    // Helpers and Steam bootstraps can remain alive beside the native game.
    // An unsupported/exited/inaccessible process must not hide a later valid one.
    public static GameActivity? FirstAvailable<T>(IEnumerable<T> candidates,Func<T,GameActivity?> observe)
    {
        foreach(var candidate in candidates)
        {
            try { if(observe(candidate) is { } activity)return activity; }
            catch(Exception error) when(error is InvalidOperationException or System.ComponentModel.Win32Exception or IOException or UnauthorizedAccessException or OverflowException or ArgumentException) { }
        }
        return null;
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
        string? DefinitionId(uint descriptor, bool random = false)
        {
            // A null WorldCreator choice means Random. During a match a missing
            // descriptor is unavailable data, never a random choice or template fallback.
            if (descriptor == 0) return random ? "random" : null;
            if (descriptor < 0x10000) return null;
            try
            {
                var address = U32(descriptor + 8); // KKC_Data UTF-16 IDS, not its numeric index at +0xc.
                if (address < 0x10000) return null;
                var value = new StringBuilder();
                for (uint i = 0; i <= 80; i++)
                {
                    var c = BitConverter.ToChar(read(checked(address + i * 2), 2));
                    if (c == 0)
                    {
                        var id = value.ToString();
                        return address == U32(descriptor + 8) && GameActivity.ValidFactionId(id) ? id.ToLowerInvariant() : null;
                    }
                    if (!char.IsAsciiLetterOrDigit(c) && c is not ('_' or '-')) return null;
                    value.Append(c);
                }
            }
            catch (Exception error) when (error is IOException or ArgumentException or OverflowException) { }
            return null;
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
            // KKC_Session::GetLocalPlayer returns this KKC_Player directly.
            // Its +4 is a different object (network peer), so comparing +4
            // against this pointer loses the owner even when Steam is connected.
            var local = manager >= 0x10000 ? U32(manager + 0xc) : 0;
            var sourceKind = U32(session + 0x64);
            var sourceOffset = sourceKind switch { 0 => 0x80u, 2 => 0x7cu, 5 => 0x88u, _ => 0x78u };
            var creator = U32(session + sourceOffset);
            var teams = new Dictionary<string,int>(StringComparer.Ordinal);
            var kingdoms = new Dictionary<string,(uint address,uint team,uint color,uint nation,uint faction)>(StringComparer.Ordinal);
            uint teamArray=0,teamCount=0,kingdomArray=0,kingdomCount=0;
            if(sourceKind<=5 && creator>=0x10000)
            {
                // WorldCreator's native team order and kingdom parameters. IDs are used
                // only to join the two lists; names and colors are never inferred from nicknames.
                teamArray=U32(creator+8);teamCount=U32(creator+0xc);
                kingdomArray=U32(creator+0x14);kingdomCount=U32(creator+0x18);
                if(teamCount>64 || kingdomCount>256) return null;
                for(uint i=0;i<teamCount;i++)
                {
                    var id=Wide(U32(checked(teamArray+i*0xc)));
                    if(id.Length==0 || !teams.TryAdd(id,(int)i+1))return null;
                }
                for(uint i=0;i<kingdomCount;i++)
                {
                    var entry=checked(kingdomArray+i*0x6c);var id=Wide(U32(entry));
                    if(id.Length==0 || !kingdoms.TryAdd(id,(entry,U32(entry+0x14),U32(entry+0x20),U32(entry+0x18),U32(entry+0x1c))))return null;
                }
            }
            string? Color(uint descriptor)
            {
                if(descriptor<0x10000)return null;
                var rgb=new[]{F32(descriptor+0x18),F32(descriptor+0x1c),F32(descriptor+0x20)};
                if(rgb.Any(c=>!float.IsFinite(c)||c<0||c>1))return null;
                return "#"+string.Concat(rgb.Select(c=>((int)MathF.Round(c*255,MidpointRounding.AwayFromZero)).ToString("X2",System.Globalization.CultureInfo.InvariantCulture)));
            }
            uint palette=0;var privateLobbyColors=false;
            if(phase=="lobby" && sourceKind!=2)
            {
                // Paw's color picker keeps pending choices outside WorldCreator until
                // launch. Recognize the published r20 ABI through its detour and two
                // independently checked routines; never mistake the template for a choice.
                var site=image+0x295516;var hook=read(site,5);
                if(hook[0]==0xe9)
                {
                    privateLobbyColors=true;
                    var target=checked((uint)((long)site+5+BitConverter.ToInt32(hook,1)));
                    if(target>=0x30000)
                    {
                        var candidate=target-0x20000;var stub=read(target,22);var init=read(candidate+0x1d000,22);
                        if(stub.AsSpan(0,18).SequenceEqual(new byte[]{0x9c,0x60,0x89,0xd9,0xe8,0xf7,0xef,0xff,0xff,0x61,0x9d,0x8b,0x43,0x20,0x89,0x45,0xf0,0xe9})
                            && (long)target+22+BitConverter.ToInt32(stub,18)==site+6
                            && init.AsSpan(0,7).SequenceEqual(new byte[]{0x53,0x56,0x57,0x89,0xce,0x83,0x3d})
                            && BitConverter.ToUInt32(init,7)==candidate+0x120 && init[11]==1 && init[12]==0x75 && init[14]==0x39 && init[15]==0x35
                            && BitConverter.ToUInt32(init,16)==candidate+0x11c && init[20]==0x75
                            && U32(candidate+0x100)==1 && U32(candidate+0x120)==1 && U32(candidate+0x11c)==session)
                            palette=candidate;
                    }
                }
            }
            string? PendingColor(string kingdomId)
            {
                if(palette==0)return null;
                var count=U32(palette+0x140);if(count is <1 or >64)return null;
                for(uint i=0;i<16;i++)
                {
                    if(Wide(U32(palette+0x300+i*4))!=kingdomId)continue;
                    var choice=U32(palette+0x600+i*4);
                    var value=choice<count?Color(U32(palette+0x200+choice*4)):null; // Random remains unspecified until allocation.
                    if(choice!=U32(palette+0x600+i*4)||U32(palette+0x11c)!=session||count!=U32(palette+0x140))throw new IOException();
                    return value;
                }
                return null;
            }
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
                    int? team=null;string? color=null;string? race=null;string? subrace=null;
                    var kingdomIdAddress=U32(player+0x24);
                    var kingdomId=Wide(kingdomIdAddress);
                    var liveKingdom=phase=="match"?U32(player+0x28):0;
                    if(liveKingdom>=0x10000)
                    {
                        // During a match, use the actual kingdom (also correct for saves
                        // and random colors), not the pre-game template's choices.
                        var liveTeam=U32(liveKingdom+0x1f8);var descriptor=U32(liveKingdom+0x1f4);
                        var nation=U32(liveKingdom+0x240);var faction=U32(liveKingdom+0x23c);
                        var factionDefinition=faction>=0x10000?U32(faction+4):0;
                        var teamId=liveTeam>=0x10000?Wide(U32(liveTeam+0x18)):"";
                        if(teams.TryGetValue(teamId,out var number))team=number;
                        color=Color(descriptor);
                        race=DefinitionId(nation);
                        // A live Faction is an instance; its +4 points to the
                        // definition selected in WorldCreator (native constructor 6869bc).
                        subrace=DefinitionId(factionDefinition);
                        if(liveKingdom!=U32(player+0x28)||liveTeam!=U32(liveKingdom+0x1f8)||descriptor!=U32(liveKingdom+0x1f4)
                            ||nation!=U32(liveKingdom+0x240)||faction!=U32(liveKingdom+0x23c)
                            ||faction>=0x10000&&factionDefinition!=U32(faction+4))return null;
                    }
                    else if(phase=="lobby" && kingdoms.TryGetValue(kingdomId,out var entry))
                    {
                        if(teams.TryGetValue(Wide(entry.team),out var number))team=number;
                        color=privateLobbyColors?PendingColor(kingdomId):Color(entry.color);
                        race=DefinitionId(entry.nation,random:true);subrace=DefinitionId(entry.faction,random:true);
                        if(entry.team!=U32(entry.address+0x14)||entry.color!=U32(entry.address+0x20)
                            ||entry.nation!=U32(entry.address+0x18)||entry.faction!=U32(entry.address+0x1c))return null;
                    }
                    // A failed WorldCreator lookup is not evidence of an observer.
                    // In the lobby require a readable, empty native kingdom IDS;
                    // in a match the native ObserverGlyphInfo branch uses +0x28 == 0.
                    var observer=!bot && (phase=="lobby"
                        ? kingdomIdAddress>=0x10000 && kingdomId.Length==0
                        : liveKingdom==0);
                    if(kingdomIdAddress!=U32(player+0x24) || kingdomId!=Wide(kingdomIdAddress)
                        || phase=="match" && liveKingdom!=U32(player+0x28))return null;
                    players.Add(new GameParticipant(key, name, bot,Observer:observer,Team:team,Color:color,Race:race,Subrace:subrace));
                    if (!bot && player == local) self = key;
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
            int? width = null, height = null;
            if (sourceKind <= 5 && creator >= 0x10000)
            {
                var x = F32(creator + 0x3c); var y = F32(creator + 0x40);
                if (float.IsFinite(x) && float.IsFinite(y) && x is >= 16 and <= 8192 && y is >= 16 and <= 8192
                    && x == MathF.Truncate(x) && y == MathF.Truncate(y)) { width = (int)x; height = (int)y; }
            }
            // Native linked lists can change between reads. Discard a torn transition rather than guessing.
            if (session != U32(image + 0x5f3fe4) || state != U32(session + 0xf0) || head != U32(session + 0xc8)
                || world != U32(image + 0x5f3fb8) || sourceKind != U32(session + 0x64) || creator != U32(session + sourceOffset)
                || manager != U32(image + 0x5f3fec) || manager >= 0x10000 && local != U32(manager + 0xc)) return null;
            if(sourceKind<=5 && creator>=0x10000 && (teamArray!=U32(creator+8)||teamCount!=U32(creator+0xc)
                ||kingdomArray!=U32(creator+0x14)||kingdomCount!=U32(creator+0x18)))return null;
            var result=new GameActivity(phase, multiplayer, elapsed, width, height, Room: room, Self: self, Players: players);
            // Escaped Unicode can make an otherwise valid large roster exceed the wire
            // envelope. Keep the phase/time instead of poisoning the normal heartbeat.
            return System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(result).Length>GameActivity.MaximumBytes-1024 ? result.Summary() : result;
        }
        catch (Exception error) when (error is IOException or ArgumentException or OverflowException) { return null; }
    }

    [DllImport("kernel32.dll", SetLastError = true)] private static extern SafeProcessHandle OpenProcess(uint access, bool inherit, int processId);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool ReadProcessMemory(SafeProcessHandle process, IntPtr address, byte[] buffer, nuint size, out nuint read);
}
