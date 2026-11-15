// Local test only. Stock game EXE is never modified. Combined builds install
// guarded data files plus a separate helper, preserving backups. No attach mode.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

internal static class TerrainPatch
{
    internal const uint HookRva = 0x23ADB3, ConstructorRva = 0x91B4E;
    internal const string GameHash = "1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45";
#if COMBINED_TEST
#if RANDOM_MAP_TEST
    internal const string Revision = RandomMapBundle.Revision;
    internal const string Build = "combined-1372-" + Revision + "-terrain-colors17-sun-randommap";
#else
    internal const string Build = "combined-1372-r3-terrain-colors17-sun";
    internal const string Revision = "r3";
#endif
    internal const string ExistingHelper = "k2_paws_colors_time_1372_test_r3.exe";
    internal const string ExistingHelperHash = CombinedBundle.HelperHash;
    internal const string ExistingHelperLog = "paws_combined_test_r3_status.txt";
    internal const string ColorsLogTag = "LOBBY_COLOR_MP r17;";
#else
    internal const string Build = ReleaseStartup.Build;
    internal const string Revision = "r1";
    internal const string ExistingHelper = "k2_paws_lobby_colors_mp_1372_experimental.exe";
    internal const string ExistingHelperHash = "0FA4A3C7B2A549BF479E372B5EA824215BDB003BD723AB502FED2770B31F3ACA";
    internal const string ExistingHelperLog = "paws_lobby_colors_mp_1372_status.txt";
    internal const string ColorsLogTag = "LOBBY_COLOR_MP r16;";
#endif
    internal static readonly byte[] Original = Hex("E8966DE5FF");
    internal static readonly byte[] Constructor = Hex("C74108FFFF7F7F8BC1C7410CFFFF7FFFC74110FFFF7F7F66C741140101C741180000803FC6412000C3");
    internal static byte[] Hex(string s)
    {
        byte[] b = new byte[s.Length / 2];
        for (int i = 0; i < b.Length; i++) b[i] = Convert.ToByte(s.Substring(i * 2, 2), 16);
        return b;
    }
    internal static string HexText(byte[] b) { return BitConverter.ToString(b).Replace("-", ""); }
    internal static byte[] Call(uint from, uint to)
    {
        return new byte[] { 0xE8 }.Concat(BitConverter.GetBytes(unchecked(to - from - 5))).ToArray();
    }
    internal static byte[] Stub(uint imageBase, uint stub)
    {
        // CALL preserves the original constructor's result. MOV and RET do not
        // change flags, floating-point state, or RNG state. ECX remains 'this'.
        return Call(stub, imageBase + ConstructorRva).Concat(Hex("C7411C000080BFC3")).ToArray();
    }
    internal static void Expect(IMemory mem, uint address, byte[] expected)
    {
        if (!mem.Read(address, expected.Length).SequenceEqual(expected))
            throw new InvalidOperationException("Неизвестный код игры по адресу 0x" + address.ToString("X8") + ". Изменения не применены.");
    }
    internal static void Validate(IMemory mem, uint imageBase)
    {
        Expect(mem, imageBase + HookRva, Original);
        Expect(mem, imageBase + ConstructorRva, Constructor);
        // Stock desync marking and error-handler call must remain enabled.
        Expect(mem, imageBase + 0x14A4FE, Hex("C6403501"));
        Expect(mem, imageBase + 0x14A5F7, Hex("E8E06F2900"));
    }
    internal static uint Install(IMemory mem, uint imageBase, Action<string> log)
    {
        // The real caller suspends only the game it just started around this
        // transaction. All compatibility guards are checked before allocating.
        Validate(mem, imageBase);
        uint cave = 0;
        bool hookAttempted = false, safeToFree = true;
        try
        {
            cave = mem.Allocate(4096);
            byte[] stub = Stub(imageBase, cave);
            mem.Write(cave, stub);
            Expect(mem, cave, stub);
            mem.MakeExecutable(cave, 4096);
            mem.Flush(cave, stub.Length);
            byte[] call = Call(imageBase + HookRva, cave);
            hookAttempted = true;
            safeToFree = false;
            mem.WriteCode(imageBase + HookRva, call);
            Expect(mem, imageBase + HookRva, call);
            mem.Flush(imageBase + HookRva, call.Length);
            Expect(mem, imageBase + 0x14A4FE, Hex("C6403501"));
            Expect(mem, imageBase + 0x14A5F7, Hex("E8E06F2900"));
            log("PATCH_APPLIED build=" + Build + " imageBase=0x" + imageBase.ToString("X8") +
                " hook=0x" + (imageBase + HookRva).ToString("X8") + " stub=0x" + cave.ToString("X8") +
                " hookBytes=" + HexText(call) + " stubBytes=" + HexText(stub) +
                " radiusBits=BF800000 stockSyncChecks=true");
            return cave;
        }
        catch
        {
            if (hookAttempted)
            {
                try
                {
                    mem.WriteCode(imageBase + HookRva, Original);
                    Expect(mem, imageBase + HookRva, Original);
                    mem.Flush(imageBase + HookRva, Original.Length);
                    safeToFree = true;
                    log("ROLLBACK_VERIFIED original call restored");
                }
                catch (Exception e)
                {
                    // Do not release a stub if a live call could still target it.
                    log("ROLLBACK_UNCERTAIN stub retained until game exit: " + e.Message);
                }
            }
            if (cave != 0 && safeToFree)
            {
                try { mem.Free(cave); } catch (Exception e) { log("FREE_FAILED " + e.Message); }
            }
            throw;
        }
    }
}

internal interface IMemory
{
    byte[] Read(uint address, int count);
    void Write(uint address, byte[] bytes);
    void WriteCode(uint address, byte[] bytes);
    uint Allocate(int count);
    void MakeExecutable(uint address, int count);
    void Flush(uint address, int count);
    void Free(uint address);
}

internal sealed class NativeMemory : IMemory, IDisposable
{
    private IntPtr handle;
    private bool suspended;
    private readonly Dictionary<uint, uint> originalProtection = new Dictionary<uint, uint>();
    internal NativeMemory(int pid)
    {
        handle = OpenProcess(0x0008 | 0x0010 | 0x0020 | 0x0400 | 0x0800, false, pid);
        if (handle == IntPtr.Zero) Fail("OpenProcess");
    }
    private static IntPtr Ptr(uint a) { return new IntPtr(unchecked((int)a)); }
    private static void Fail(string operation) { throw new Win32Exception(Marshal.GetLastWin32Error(), operation); }
    internal void Suspend()
    {
        int status = NtSuspendProcess(handle);
        if (status != 0) throw new InvalidOperationException("NtSuspendProcess 0x" + status.ToString("X8"));
        suspended = true;
    }
    internal void Resume()
    {
        if (!suspended) return;
        int status = NtResumeProcess(handle);
        if (status != 0) throw new InvalidOperationException("NtResumeProcess 0x" + status.ToString("X8"));
        suspended = false;
    }
    public byte[] Read(uint a, int count)
    {
        byte[] bytes = new byte[count];
        IntPtr actual;
        if (!ReadProcessMemory(handle, Ptr(a), bytes, new IntPtr(count), out actual) || actual.ToInt64() != count) Fail("ReadProcessMemory");
        return bytes;
    }
    public void Write(uint a, byte[] b)
    {
        IntPtr actual;
        if (!WriteProcessMemory(handle, Ptr(a), b, new IntPtr(b.Length), out actual) || actual.ToInt64() != b.Length) Fail("WriteProcessMemory");
    }
    public void WriteCode(uint a, byte[] b)
    {
        uint old, ignored;
        if (!VirtualProtectEx(handle, Ptr(a), new IntPtr(b.Length), 0x40, out old)) Fail("VirtualProtectEx RWX");
        if (!originalProtection.ContainsKey(a)) originalProtection[a] = old;
        try { Write(a, b); }
        finally
        {
            if (!VirtualProtectEx(handle, Ptr(a), new IntPtr(b.Length), originalProtection[a], out ignored)) Fail("VirtualProtectEx restore");
            originalProtection.Remove(a);
        }
    }
    public uint Allocate(int count)
    {
        IntPtr a = VirtualAllocEx(handle, IntPtr.Zero, new IntPtr(count), 0x3000, 0x04);
        if (a == IntPtr.Zero) Fail("VirtualAllocEx");
        return unchecked((uint)a.ToInt32());
    }
    public void MakeExecutable(uint a, int count)
    {
        uint old;
        if (!VirtualProtectEx(handle, Ptr(a), new IntPtr(count), 0x20, out old)) Fail("VirtualProtectEx RX");
    }
    public void Flush(uint a, int count)
    {
        if (!FlushInstructionCache(handle, Ptr(a), new IntPtr(count))) Fail("FlushInstructionCache");
    }
    public void Free(uint a) { if (!VirtualFreeEx(handle, Ptr(a), IntPtr.Zero, 0x8000)) Fail("VirtualFreeEx"); }
    public void Dispose()
    {
        try { Resume(); }
        finally { if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; } }
    }
    [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr OpenProcess(uint rights, bool inherit, int pid);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool ReadProcessMemory(IntPtr p, IntPtr a, byte[] b, IntPtr n, out IntPtr read);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool WriteProcessMemory(IntPtr p, IntPtr a, byte[] b, IntPtr n, out IntPtr written);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr VirtualAllocEx(IntPtr p, IntPtr a, IntPtr n, uint allocation, uint protection);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool VirtualProtectEx(IntPtr p, IntPtr a, IntPtr n, uint protection, out uint old);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool VirtualFreeEx(IntPtr p, IntPtr a, IntPtr n, uint mode);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool FlushInstructionCache(IntPtr p, IntPtr a, IntPtr n);
    [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr h);
    [DllImport("ntdll.dll")] private static extern int NtSuspendProcess(IntPtr p);
    [DllImport("ntdll.dll")] private static extern int NtResumeProcess(IntPtr p);
}

internal sealed class FakeMemory : IMemory
{
    internal readonly Dictionary<uint, byte> Bytes = new Dictionary<uint, byte>();
    internal int FailAt = -1, Operations, Frees;
    internal bool AlwaysFailHook, Allocated;
    private void Op() { if (++Operations == FailAt) throw new IOException("injected operation " + Operations); }
    internal void Seed(uint a, byte[] b) { for (int i = 0; i < b.Length; i++) Bytes[a + (uint)i] = b[i]; }
    internal FakeMemory(uint imageBase)
    {
        Seed(imageBase + TerrainPatch.HookRva, TerrainPatch.Original);
        Seed(imageBase + TerrainPatch.ConstructorRva, TerrainPatch.Constructor);
        Seed(imageBase + 0x14A4FE, TerrainPatch.Hex("C6403501"));
        Seed(imageBase + 0x14A5F7, TerrainPatch.Hex("E8E06F2900"));
    }
    public byte[] Read(uint a, int n) { Op(); return Enumerable.Range(0, n).Select(i => Bytes.ContainsKey(a + (uint)i) ? Bytes[a + (uint)i] : (byte)0).ToArray(); }
    public void Write(uint a, byte[] b) { Op(); Seed(a, b); }
    public void WriteCode(uint a, byte[] b) { Op(); Seed(a, b.Take(2).ToArray()); if (AlwaysFailHook) throw new IOException("partial write"); Seed(a, b); }
    public uint Allocate(int n) { Op(); Allocated = true; return 0x60000000; }
    public void MakeExecutable(uint a, int n) { Op(); }
    public void Flush(uint a, int n) { Op(); }
    public void Free(uint a) { Frees++; Allocated = false; }
}
