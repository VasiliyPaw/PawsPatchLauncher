using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;

namespace PawPureFixes
{
    internal sealed class FakeMemory : IPatchMemory
    {
        internal readonly Dictionary<uint, byte> Bytes = new Dictionary<uint, byte>();
        internal readonly List<uint> CodeWrites = new List<uint>();
        internal int Operations, FailAt = -1, Allocations, Frees;
        internal bool Allocated, PartialCodeFailure, PermanentCodeFailure;
        internal readonly uint Cave;
        internal FakeMemory(uint image, uint cave)
        {
            Cave = cave;
            foreach (Signature signature in PurePatch.Guards) Seed(image + signature.Rva, signature.Bytes);
        }
        internal void Seed(uint address, byte[] data) { for (int i = 0; i < data.Length; i++) Bytes[address + (uint)i] = data[i]; }
        private void Op() { if (++Operations == FailAt) throw new IOException("Injected operation " + Operations); }
        public byte[] Read(uint address, int count)
        {
            Op(); return Enumerable.Range(0, count).Select(i => Bytes.ContainsKey(address + (uint)i) ? Bytes[address + (uint)i] : (byte)0).ToArray();
        }
        public void Write(uint address, byte[] bytes) { Op(); Seed(address, bytes); }
        public void WriteCode(uint address, byte[] bytes)
        {
            Op(); CodeWrites.Add(address); Seed(address, bytes.Take(2).ToArray());
            if (PermanentCodeFailure || PartialCodeFailure)
            {
                PartialCodeFailure = false; throw new IOException("Injected partial code write");
            }
            Seed(address, bytes);
        }
        public uint Allocate(int count) { Op(); Allocations++; Allocated = true; return Cave; }
        public void MakeExecutable(uint address, int count) { Op(); }
        public void Flush(uint address, int count) { Op(); }
        public void Free(uint address) { Op(); Frees++; Allocated = false; }
    }
    internal static class Tests
    {
        private static int checks;
        private static void Check(bool condition, string text)
        {
            checks++; if (!condition) throw new Exception("Check " + checks + ": " + text);
        }
        private static void MustFail(Action action, string message)
        {
            bool failed = false; try { action(); } catch { failed = true; } Check(failed, message);
        }
        private static int Main(string[] args)
        {
            if (args.Length == 1 && args[0] == "--sleep-fixture") { Thread.Sleep(30000); return 0; }
            if (args.Length != 1) throw new ArgumentException("Output directory required.");
            string root = Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
            uint[] images = { 0x460000, 0x80000, 0x6A0000 };
            uint[] caves = { 0x10000000, 0x2EC0000, 0x19000000 };
            for (int index = 0; index < images.Length; index++)
            {
                uint image = images[index], cave = caves[index];
                FakeMemory memory = new FakeMemory(image, cave);
                Dictionary<uint, byte> originals = new Dictionary<uint, byte>(memory.Bytes);
                Check(PurePatch.IsReady(memory, image), "original signatures ready");
                memory.Operations = 0;
                uint installed = PurePatch.Install(memory, image); int operationCount = memory.Operations;
                Check(installed == cave && memory.Allocated, "installation returns allocated cave");
                Check(memory.Read(image + PurePatch.ZeroHookRva, 5).SequenceEqual(PurePatch.Branch(0xE8, image + PurePatch.ZeroHookRva, cave)), "zero hook target");
                Check(memory.Read(image + PurePatch.TerrainHookRva, 5).SequenceEqual(PurePatch.Branch(0xE8, image + PurePatch.TerrainHookRva, cave + PurePatch.TerrainOffset)), "terrain hook target");
                Check(memory.CodeWrites.SequenceEqual(new[] { image + PurePatch.ZeroHookRva, image + PurePatch.TerrainHookRva }), "exactly two native code writes");
                foreach (Signature signature in PurePatch.Guards.Skip(2))
                    Check(memory.Read(image + signature.Rva, signature.Bytes.Length).SequenceEqual(signature.Bytes), "constructor/OOS unchanged");
                Check(memory.Bytes.All(pair =>
                    pair.Key >= cave && pair.Key < cave + PurePatch.AllocationSize ||
                    pair.Key >= image + PurePatch.ZeroHookRva && pair.Key < image + PurePatch.ZeroHookRva + 5 ||
                    pair.Key >= image + PurePatch.TerrainHookRva && pair.Key < image + PurePatch.TerrainHookRva + 5 ||
                    originals.ContainsKey(pair.Key) && originals[pair.Key] == pair.Value), "no unrelated memory writes");
                MustFail(delegate { PurePatch.Install(memory, image); }, "already installed code rejected");
                Check(memory.Allocations == 1, "duplicate rejection before allocation");
                for (int failAt = 1; failAt <= operationCount; failAt++)
                {
                    FakeMemory broken = new FakeMemory(image, cave) { FailAt = failAt };
                    MustFail(delegate { PurePatch.Install(broken, image); }, "every injected native operation failure surfaces");
                    broken.FailAt = -1;
                    Check(!broken.Allocated && broken.Bytes.Where(p => p.Key < cave || p.Key >= cave + PurePatch.AllocationSize).All(p => originals[p.Key] == p.Value), "failure restores original game bytes and releases safe cave");
                    PurePatch.Validate(broken, image);
                }
                foreach (Signature signature in PurePatch.Guards)
                {
                    FakeMemory unknown = new FakeMemory(image, cave);
                    unknown.Bytes[image + signature.Rva] ^= 0xFF;
                    MustFail(delegate { PurePatch.Install(unknown, image); }, "each incompatible signature is rejected");
                    Check(unknown.Allocations == 0 && unknown.CodeWrites.Count == 0, "signature rejection before writes");
                }
                FakeMemory partial = new FakeMemory(image, cave) { PartialCodeFailure = true };
                MustFail(delegate { PurePatch.Install(partial, image); }, "partial code write surfaces");
                Check(!partial.Allocated, "partial write restored before cave release");
                PurePatch.Validate(partial, image);
                FakeMemory permanent = new FakeMemory(image, cave) { PermanentCodeFailure = true };
                MustFail(delegate { PurePatch.Install(permanent, image); }, "rollback failure surfaces");
                Check(permanent.Allocated && permanent.Frees == 0, "possibly referenced cave retained for failed-launch termination");
                File.WriteAllBytes(Path.Combine(root, "payload-" + index + ".bin"), PurePatch.Payload(image, cave));
            }
            Check(Program.IsSupportedHash(Program.GameHash.ToLowerInvariant()), "supported exact hash accepted");
            Check(!Program.IsSupportedHash(null) && !Program.IsSupportedHash(Program.GameHash.Substring(1)) && !Program.IsSupportedHash(new string('0', 64)), "unknown hashes rejected");
            Check(Program.GameDirectory(new string[0], root) == root, "default own directory");
            Check(Program.GameDirectory(new[] { "--game-dir", root }, "unused") == root, "explicit directory");
            foreach (string flag in new[] { "--attach", "--attach-secondary", "--replace-secondary", "--bypass", "--colors", "--mod", "--test" })
                MustFail(delegate { Program.GameDirectory(new[] { flag }, root); }, "unrequested runtime switches rejected");
            string path; IntPtr baseAddress;
            Check(!Program.TrySnapshot(delegate { throw new NullReferenceException(); }, delegate { return new IntPtr(1); }, out path, out baseAddress), "unready process metadata retried");
            MustFail(delegate { Program.TrySnapshot(delegate { throw new Win32Exception(5); }, delegate { return new IntPtr(1); }, out path, out baseAddress); }, "access denial not swallowed");
            string game = Path.Combine(root, "k2.exe"); DateTime requested = new DateTime(2026, 9, 10, 0, 0, 0, DateTimeKind.Utc);
            Check(Program.IsFreshIdentity(game, requested, game.ToUpperInvariant(), requested.AddSeconds(1)), "fresh matching game accepted");
            Check(!Program.IsFreshIdentity(game, requested, game, requested.AddTicks(-1)), "old process rejected");
            Check(!Program.IsFreshIdentity(game, requested, Path.Combine(root, "other", "k2.exe"), requested.AddSeconds(1)), "foreign path rejected");
            File.WriteAllText(game, "not a game; preflight test fixture only");
            MustFail(delegate { Program.Preflight(root); }, "foreign executable rejected by read-only preflight");
            // A hidden, inert instance of this test executable verifies native
            // process identity and suspend/resume rights. It is never k2.exe;
            // its memory is only read, and it creates no windows or game data.
            string self = Assembly.GetExecutingAssembly().Location;
            using (Process child = Process.Start(new ProcessStartInfo(self, "--sleep-fixture")
                { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden }))
            {
                if (child == null) throw new InvalidOperationException("No inert test fixture.");
                try
                {
                    DateTime start = child.StartTime.ToUniversalTime();
                    MustFail(delegate { using (var wrong = new NativeMemory(child.Id, game, start)) { } }, "native handle rejects foreign executable path");
                    MustFail(delegate { using (var wrong = new NativeMemory(child.Id, self, start.AddTicks(-1))) { } }, "native handle rejects wrong creation time");
                    using (NativeMemory native = new NativeMemory(child.Id, self, start))
                    {
                        native.Suspend();
                        try
                        {
                            uint address = unchecked((uint)child.MainModule.BaseAddress.ToInt32());
                            Check(native.Read(address, 2).SequenceEqual(new byte[] { 0x4D, 0x5A }), "verified native handle reads inert fixture while suspended");
                        }
                        finally { native.Resume(); }
                    }
                    Check(!child.HasExited, "inert test fixture survives native resume");
                }
                finally { if (!child.HasExited) { child.Kill(); child.WaitForExit(5000); } }
            }
            string report = "{\"passed\":true,\"checks\":" + checks + ",\"aslrLayouts\":3,\"gameLaunched\":false,\"nativeWindowsOpened\":false}";
            File.WriteAllText(Path.Combine(root, "managed-tests.json"), report);
            Console.WriteLine(report); return 0;
        }
    }
}
