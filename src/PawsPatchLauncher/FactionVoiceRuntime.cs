using System.Buffers.Binary;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;

namespace PawsPatchLauncher;

public sealed class FactionVoiceException(string code, Exception? inner = null) : Exception(code, inner) { public string Code { get; } = code; }
public sealed record FactionVoicePayload(byte[] Bytes, int Entry, int State, int Site, byte[] Guard);

public static class FactionVoiceRuntime
{
    internal static bool RequiresPresentationReady(InstallState installed, string launchedExecutable)
    {
        if (Path.GetFileName(launchedExecutable).Equals("k2.exe", StringComparison.OrdinalIgnoreCase)
            || installed.AppliedSettings is not { DataOnly: false } settings || !GameMod.PawPatchSelected(settings)) return false;
        var owner = settings.Mod switch
        {
            GameMod.ArcaneWars => "pawpatch-core",
            GameMod.Vanilla or GameMod.Immortals => "pure-fixes-runtime",
            _ => null
        };
        return owner is not null && installed.Modules.TryGetValue(owner, out var runtime) && runtime.Enabled
            && runtime.Files.Any(f => f.Path.Replace('\\', '/').Equals("paws_presentation.ini", StringComparison.OrdinalIgnoreCase));
    }

    internal static string PresentationReadyEventName(int gameId, long startTimeUtcTicks)
        => FormattableString.Invariant($"Local\\PawPresentationReady-{gameId}-{startTimeUtcTicks}");

    internal static bool PresentationReady(Process game)
    {
        // Only the helper creates/signals this manual-reset event. Never create
        // a substitute event or infer readiness from an arbitrary loose INI.
        var name = PresentationReadyEventName(game.Id, game.StartTime.ToUniversalTime().Ticks);
        if (!EventWaitHandleAcl.TryOpenExisting(name, EventWaitHandleRights.Synchronize, out var ready)) return false;
        using (ready) return ready.WaitOne(0);
    }

    internal static void EnsureLauncherSucceeded(Process? launcher, string phase)
    {
        if (launcher is not null && launcher.HasExited && launcher.ExitCode != 0)
            throw new FactionVoiceException("faction-voice-startup",
                new IOException("Game launcher failed during " + phase + "; exit code " + launcher.ExitCode));
    }

    public static FactionVoicePayload Build(uint image, uint cave, UserSettings settings)
    {
        CustomVoices.Validate(settings);
        byte[] Resource(string suffix)
        {
            using var stream = typeof(FactionVoiceRuntime).Assembly.GetManifestResourceStream("PawsPatchLauncher.Assets." + suffix)
                ?? throw new InvalidDataException("Missing faction voice runtime");
            using var output = new MemoryStream(); stream.CopyTo(output); return output.ToArray();
        }
        var bytes = Resource("FactionVoices.bin"); using var meta = JsonDocument.Parse(Resource("FactionVoices.json")); var root = meta.RootElement;
        if (root.GetProperty("revision").GetInt32() != 1 || !Convert.ToHexString(SHA256.HashData(bytes)).Equals(root.GetProperty("sha256").GetString(), StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Faction voice runtime identity mismatch");
        var oldImage = root.GetProperty("preferredImage").GetUInt32(); var oldCave = root.GetProperty("preferredCave").GetUInt32();
        foreach (var fix in root.GetProperty("fixups").EnumerateArray())
        {
            var off = fix[0].GetInt32(); var delta = fix[1].GetInt32() * ((long)image - oldImage) + fix[2].GetInt32() * ((long)cave - oldCave);
            var value = BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(off, 4));
            BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(off, 4), unchecked((uint)(value + delta)));
        }
        var state = root.GetProperty("state").GetInt32();
        BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(state, 4), 0x56574346);
        BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(state + 4, 4), image);
        for (var i = 0; i < CustomVoices.Groups.Count; i++)
            BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(state + 8 + i * 4, 4), (uint)GameLanguages.VoiceChoices.ToList().IndexOf(CustomVoices.Language(settings, CustomVoices.Groups[i])));
        BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(state + 48, 4), cave + root.GetProperty("ownerAdapter").GetUInt32());
        return new(bytes, root.GetProperty("entry").GetInt32(), state, root.GetProperty("site").GetInt32(), Convert.FromHexString(root.GetProperty("guard").GetString()!));
    }

    public static async Task<UserSettings?> PrepareAsync(string directory, UserSettings settings)
    {
        await new ModuleInstaller(directory).MigrateFactionVoiceModuleAsync();
        if (!CustomVoices.NeedsRuntime(settings)) return null;
        if (!string.Equals(await CryptoAndIO.Sha256Async(Path.Combine(directory, "k2.exe")), KohanActivityReader.SupportedSha256, StringComparison.OrdinalIgnoreCase))
            throw new FactionVoiceException("faction-voice-version");
        if (!File.Exists(Path.Combine(directory, "data/Audio/paws_faction_voices.tgi"))) throw new FactionVoiceException("faction-voice-resources");
        return JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!;
    }

    public static Task InstallAsync(string directory, UserSettings? settings, DateTimeOffset started, Process? launcher = null)
        => settings is null ? Task.CompletedTask : Task.Run(async () =>
        {
            var installer = new ModuleInstaller(directory);
            await installer.MigrateFactionVoiceModuleAsync();
            var requirePresentation = RequiresPresentationReady(installer.LoadState(), launcher?.StartInfo.FileName ?? "");
            var path = Path.GetFullPath(Path.Combine(directory, "k2.exe")); var deadline = Stopwatch.StartNew();
            var phase = "waiting-for-game";
            Exception? lastError = null;
            while (deadline.Elapsed < TimeSpan.FromSeconds(40))
            {
                EnsureLauncherSucceeded(launcher, phase);
                foreach (var game in Process.GetProcessesByName("k2"))
                using (game)
                {
                    try
                    {
                        if (game.StartTime.ToUniversalTime() < started.UtcDateTime.AddSeconds(-1) || game.MainModule is not { } module
                            || !Path.GetFullPath(module.FileName).Equals(path, StringComparison.OrdinalIgnoreCase)) continue;
                        using var process = OpenProcess(0x438, false, game.Id);
                        if (process.IsInvalid) throw new Win32Exception();
                        var image = checked((uint)module.BaseAddress.ToInt64());
                        if (TryInstall(process, game, image, settings, requirePresentation && launcher?.Id != game.Id, launcher, ref phase)) return;
                    }
                    catch (Exception error) when (error is InvalidOperationException or ArgumentException or Win32Exception) { lastError = error; }
                }
                EnsureLauncherSucceeded(launcher, phase);
                await Task.Delay(100);
            }
            throw new FactionVoiceException("faction-voice-startup", new IOException("Faction speech setup timed out: " + phase, lastError));
        });

    internal static bool TryInstall(SafeProcessHandle process, Process game, uint image, UserSettings settings,
        bool requirePresentation, Process? launcher, ref string phase)
    {
        EnsureLauncherSucceeded(launcher, phase);
        if (requirePresentation)
        {
            phase = "waiting-for-helper-ready";
            if (!PresentationReady(game)) return false;
        }
        phase = "waiting-for-native-code";
        var probe = Build(image, 0x10000000, settings);
        if (!Read(process, image + (uint)probe.Site, probe.Guard.Length).SequenceEqual(probe.Guard)) return false; // Steam is still unpacking.
        phase = "waiting-for-audio-definitions";
        if (!HasVoiceDefinitions(process, image)) return false;
        EnsureLauncherSucceeded(launcher, phase);
        Install(process, game, image, settings);
        return true;
    }

    static bool HasVoiceDefinitions(SafeProcessHandle process, uint image)
    {
        uint U32(uint p) => BinaryPrimitives.ReadUInt32LittleEndian(Read(process, p, 4));
        var db = U32(image + 0x5f3fb4); if (db < 0x10000) return false;
        var collection = U32(db + 0x584); if (collection < 0x10000) return false;
        var buckets = U32(collection + 0x30); var count = U32(collection + 0x34);
        if (buckets < 0x10000 || count is 0 or > 65536) return false;
        foreach (var language in GameLanguages.VoiceChoices)
        {
            var id = "paws_voice_" + language + "_swordsman_select"; uint hash = 0;
            foreach (var c in id) hash = unchecked(hash * 33 + char.ToUpperInvariant(c));
            var node = U32(buckets + hash % count * 4); var found = false;
            for (var n = 0; node >= 0x10000 && n < 128; n++, node = U32(node + 4))
            {
                var data = U32(node); if (data < 0x10000) continue;
                var name = U32(data + 8); if (name < 0x10000) continue;
                var actual = new System.Text.StringBuilder();
                for (var i = 0; i <= id.Length; i++)
                {
                    var c = (char)BinaryPrimitives.ReadUInt16LittleEndian(Read(process, name + (uint)(i * 2), 2));
                    if (c == 0) break; actual.Append(c);
                }
                if (actual.ToString().Equals(id, StringComparison.OrdinalIgnoreCase)) { found = true; break; }
            }
            if (!found) return false;
        }
        return true;
    }

    static void Install(SafeProcessHandle process, Process game, uint image, UserSettings settings)
    {
        var preview = Build(image, 0x10000000, settings);
        var allocation = VirtualAllocEx(process, IntPtr.Zero, (nuint)preview.Bytes.Length, 0x3000, 0x40);
        if (allocation == IntPtr.Zero) throw new Win32Exception();
        var cave = checked((uint)allocation.ToInt64()); var payload = Build(image, cave, settings); var site = image + (uint)payload.Site;
        var changed = false; var suspended = new List<SafeWaitHandle>();
        try
        {
            Write(process, cave, payload.Bytes);
            if (!Read(process, cave, payload.Bytes.Length).SequenceEqual(payload.Bytes)) throw new IOException("Faction audio payload readback failed");
            // Suspend every current thread before replacing the five-byte call.
            // No engine function is invoked while the process is suspended.
            var ids = new HashSet<int>();
            for (var pass = 0; pass < 4; pass++)
            {
                game.Refresh(); var added = false;
                foreach (ProcessThread thread in game.Threads)
                {
                    if (!ids.Add(thread.Id)) continue;
                    var handle = OpenThread(0x004A, false, (uint)thread.Id);
                    if (handle.IsInvalid || SuspendThread(handle) == uint.MaxValue) { handle.Dispose(); throw new Win32Exception(); }
                    suspended.Add(handle); added = true;
                    var context = Marshal.AllocHGlobal(716);
                    try
                    {
                        Marshal.Copy(new byte[716], 0, context, 716); Marshal.WriteInt32(context, 0x10001);
                        var ok = IntPtr.Size == 8 ? Wow64GetThreadContext(handle, context) : GetThreadContext(handle, context);
                        if (!ok) throw new Win32Exception();
                        var pc = unchecked((uint)Marshal.ReadInt32(context, 184));
                        if (pc >= site && pc < site + payload.Guard.Length) throw new IOException("Audio dispatch is currently executing; retry launch");
                    }
                    finally { Marshal.FreeHGlobal(context); }
                }
                if (!added) break;
                if (pass == 3) throw new IOException("Game threads did not settle for audio setup");
            }
            if (!Read(process, site, payload.Guard.Length).SequenceEqual(payload.Guard)) throw new IOException("Audio dispatch changed before setup");
            var call = new byte[5]; call[0] = 0xe8;
            BinaryPrimitives.WriteInt32LittleEndian(call.AsSpan(1), unchecked((int)(cave + (uint)payload.Entry - site - 5)));
            changed = true; ProtectedWrite(process, site, call);
            if (!Read(process, site, 5).SequenceEqual(call)) throw new IOException("Audio dispatch readback failed");
            if (!FlushInstructionCache(process, allocation, (nuint)payload.Bytes.Length) || !FlushInstructionCache(process, new IntPtr(site), 5)) throw new Win32Exception();
            try
            {
                Directory.CreateDirectory(ActivityStore.Root);
                File.WriteAllText(Path.Combine(ActivityStore.Root, "faction-voice-runtime.json"), JsonSerializer.Serialize(new
                { processId = game.Id, image, cave, state = cave + (uint)payload.State, languages = CustomVoices.Copy(settings), installed = true }));
            }
            catch (IOException) { }
        }
        catch (Exception error)
        {
            var restored = !changed;
            if (changed)
            {
                try { ProtectedWrite(process, site, payload.Guard); FlushInstructionCache(process, new IntPtr(site), 5); restored = Read(process, site, 5).SequenceEqual(payload.Guard); }
                catch { }
            }
            if (restored) VirtualFreeEx(process, allocation, 0, 0x8000);
            throw new FactionVoiceException("faction-voice-startup", error);
        }
        finally { foreach (var thread in suspended) { ResumeThread(thread); thread.Dispose(); } }
    }
    static byte[] Read(SafeProcessHandle process, uint address, int size)
    {
        var bytes = new byte[size];
        if (!ReadProcessMemory(process, new IntPtr(address), bytes, (nuint)size, out var done) || done != (nuint)size) throw new Win32Exception();
        return bytes;
    }
    static void Write(SafeProcessHandle process, uint address, byte[] bytes)
    {
        if (!WriteProcessMemory(process, new IntPtr(address), bytes, (nuint)bytes.Length, out var done) || done != (nuint)bytes.Length) throw new Win32Exception();
    }
    static void ProtectedWrite(SafeProcessHandle process, uint address, byte[] bytes)
    {
        if (!VirtualProtectEx(process, new IntPtr(address), (nuint)bytes.Length, 0x40, out var old)) throw new Win32Exception();
        try { Write(process, address, bytes); }
        finally { VirtualProtectEx(process, new IntPtr(address), (nuint)bytes.Length, old, out _); }
    }
    [DllImport("kernel32.dll", SetLastError = true)] static extern SafeProcessHandle OpenProcess(uint access, bool inherit, int pid);
    [DllImport("kernel32.dll", SetLastError = true)] static extern SafeWaitHandle OpenThread(uint access, bool inherit, uint id);
    [DllImport("kernel32.dll", SetLastError = true)] static extern uint SuspendThread(SafeWaitHandle thread);
    [DllImport("kernel32.dll", SetLastError = true)] static extern uint ResumeThread(SafeWaitHandle thread);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool Wow64GetThreadContext(SafeWaitHandle thread, IntPtr context);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool GetThreadContext(SafeWaitHandle thread, IntPtr context);
    [DllImport("kernel32.dll", SetLastError = true)] static extern IntPtr VirtualAllocEx(SafeProcessHandle process, IntPtr address, nuint size, uint type, uint protection);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool VirtualFreeEx(SafeProcessHandle process, IntPtr address, nuint size, uint type);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool VirtualProtectEx(SafeProcessHandle process, IntPtr address, nuint size, uint protection, out uint old);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool ReadProcessMemory(SafeProcessHandle process, IntPtr address, byte[] bytes, nuint size, out nuint read);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool WriteProcessMemory(SafeProcessHandle process, IntPtr address, byte[] bytes, nuint size, out nuint written);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool FlushInstructionCache(SafeProcessHandle process, IntPtr address, nuint size);
}
