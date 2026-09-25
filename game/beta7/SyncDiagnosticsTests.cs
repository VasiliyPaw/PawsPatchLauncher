using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Collections.Generic;
using System.Runtime.InteropServices;

internal static class SyncDiagnosticsTests
{
    [DllImport("kernel32.dll", SetLastError = true)] static extern IntPtr VirtualAlloc(IntPtr p, UIntPtr size, uint type, uint protection);
    [DllImport("kernel32.dll")] static extern bool VirtualFree(IntPtr p, UIntPtr size, uint type);
    [DllImport("kernel32.dll")] static extern bool FlushInstructionCache(IntPtr process, IntPtr p, UIntPtr size);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate void Probe();
    // This is an isolated x86 test process, not the game. Execute the generated
    // wrapper on the real CPU too: Unicorn cannot validate the saved x87 FIP.
    static void HardwareRoundTrip()
    {
        IntPtr arena = VirtualAlloc(IntPtr.Zero, (UIntPtr)0x710000, 0x3000, 0x40);
        if (arena == IntPtr.Zero) throw new Exception("Probe allocation failed");
        try
        {
            uint image = unchecked((uint)arena.ToInt32()), code = image + 0x700000;
            uint signal = image + 0x704000, before = image + 0x705000, after = before + 0x200;
            uint data = before + 0x400, probe = code + 0x1000;
            Action<uint, byte[]> put = delegate(uint at, byte[] bytes) { Marshal.Copy(bytes, 0, new IntPtr(unchecked((int)at)), bytes.Length); };
            Func<string, byte[]> hex = delegate(string text) { var b = new byte[text.Length / 2]; for (int i = 0; i < b.Length; i++) b[i] = Convert.ToByte(text.Substring(i * 2, 2), 16); return b; };
            put(code, PawSyncDiagnostics.Build(image, code, signal));
            put(signal, PawSyncDiagnostics.InitialSignal());
            put(data, BitConverter.GetBytes(0x3f80));
            var pattern = Enumerable.Range(1, 128).Select(i => (byte)i).ToArray(); put(data + 16, pattern);
            var writer = new List<byte>(hex("DBE3D9EE0F57C00F57C1B8EFBEADDEB9EFBEADDEBAEFBEADDEC20400"));
            put(image + 0x14A5F2 + 5, writer.ToArray()); // explicit native IO surrogate
            var c = new List<byte>();
            Action<string> h = delegate(string text) { c.AddRange(hex(text)); };
            Action<uint> n = delegate(uint value) { c.AddRange(BitConverter.GetBytes(value)); };
            h("9C6081EC100200008D7C240F83E7F00FAE0757DBE3D9E8D9EB0FAE15"); n(data);
            for (int i = 0; i < 8; i++) { h("F30F6F"); c.Add((byte)(5 + 8 * i)); n(data + 16 + (uint)i * 16); }
            h("0FAE05"); n(before);
            h("6866040000B8"); n(code); h("FFD0"); // failure(1126)
            h("0FAE05"); n(after);
            h("5F0FAE0F81C410020000619DC3");
            put(probe, c.ToArray());
            if (!FlushInstructionCache(new IntPtr(-1), arena, (UIntPtr)0x710000)) throw new Exception("Probe flush failed");
            var run = (Probe)Marshal.GetDelegateForFunctionPointer(new IntPtr(unchecked((int)probe)), typeof(Probe));
            for (int i = 1; i <= 2; i++)
            {
                run();
                var b = new byte[512]; var a = new byte[512];
                Marshal.Copy(new IntPtr(unchecked((int)before)), b, 0, b.Length);
                Marshal.Copy(new IntPtr(unchecked((int)after)), a, 0, a.Length);
                if (!a.SequenceEqual(b)) throw new Exception("Hardware x87/SSE roundtrip failed at byte " + Enumerable.Range(0, 512).First(j => a[j] != b[j]));
                if (Marshal.ReadInt32(new IntPtr(unchecked((int)signal))) != i || Marshal.ReadInt32(new IntPtr(unchecked((int)(signal + 16)))) != 1)
                    throw new Exception("Hardware first/repeat capture failed");
            }
            Console.WriteLine("SYNC_DIAGNOSTICS_HARDWARE_PASS: real CPU, complete FXSAVE state including FIP, first/repeat; native IO stubbed");
        }
        finally { VirtualFree(arena, UIntPtr.Zero, 0x8000); }
    }
    static void Main(string[] args)
    {
        HardwareRoundTrip();
        Directory.CreateDirectory(args[0]);
        File.WriteAllText(Path.Combine(args[0], "hardware.json"), "{\"passed\":true,\"firstAndRepeat\":true,\"fullFxState\":true,\"nativeIoStubbed\":true}");
        var original = File.ReadAllBytes(args[1]);
        using (var sha = SHA256.Create())
            if (BitConverter.ToString(sha.ComputeHash(original)).Replace("-", "") !=
                "B865D8206990C4F055C51DE857F0B09B88AB5EE3B6AE74EE5232134001AA591C")
                throw new Exception("Unverified native image");
        if (!original.Skip(PawSyncDiagnostics.ResetRva).Take(PawSyncDiagnostics.ResetSignature.Length)
            .SequenceEqual(PawSyncDiagnostics.ResetSignature)) throw new Exception("Reset guard differs from native engine");
        uint[,] placements = { { 0x460000, 0x10000000, 0x20000100 },
            { 0x780000, 0x21000000, 0x30000F80 }, { 0xAF0000, 0x60000000, 0x70000200 } };
        for (int i = 0; i < placements.GetLength(0); i++)
        {
            uint image = placements[i, 0], code = placements[i, 1], signal = placements[i, 2];
            string prefix = Path.Combine(args[0], "case" + i);
            File.WriteAllBytes(prefix + ".bin", PawSyncDiagnostics.Build(image, code, signal));
            File.WriteAllText(prefix + ".txt", image + " " + code + " " + signal);
        }
        File.WriteAllBytes(Path.Combine(args[0], "initial.bin"), PawSyncDiagnostics.InitialSignal());
        File.WriteAllBytes(Path.Combine(args[0], "reset-original.bin"), original.Skip(PawSyncDiagnostics.ResetRva).Take(40).ToArray());
        Console.WriteLine("SYNC_DIAGNOSTICS_EXPORT_PASS: verified image/reset signature; three relocated wrappers");
    }
}
