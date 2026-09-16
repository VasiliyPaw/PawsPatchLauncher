using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

namespace PawPureFixes
{
    internal static class SyncTests
    {
        static int checks;
        static void Check(bool value) { checks++; if (!value) throw new Exception("Pure sync guard/rollback failed"); }
        static bool Fails(Action f) { try { f(); return false; } catch { return true; } }
        static TransferFakeMemory Seed(uint image)
        {
            var m = new TransferFakeMemory(image);
            m.Seed(image + PureSync.FailureRva, PureSync.Signature(image));
            m.Seed(image + PureSync.MarkerRva, PurePatch.Hex("C6403501")); return m;
        }
        static void Main(string[] args)
        {
            Directory.CreateDirectory(args[0]);
            foreach (uint image in new uint[] { 0x400000, 0x460000, 0xAF0000 })
            {
                var m = Seed(image); var original = new Dictionary<uint, byte>(m.Bytes);
                uint signal = PureSync.Install(m, image); int ops = m.Operations;
                Check(signal != 0 && BitConverter.ToUInt32(m.Read(signal, 4), 0) == 0);
                Check(m.CodeWrites.SequenceEqual(new[] { image + PureSync.FailureRva, image + PureSync.MarkerRva }));
                for (int i = 1; i <= ops; i++)
                {
                    var b = Seed(image); b.FailAt = i;
                    Check(Fails(delegate { PureSync.Install(b, image); }));
                    Check(original.All(p => b.Bytes[p.Key] == p.Value)); Check(!b.Allocated);
                }
                foreach (uint address in original.Keys)
                {
                    var b = Seed(image); b.Bytes[address] ^= 1;
                    Check(Fails(delegate { PureSync.Install(b, image); }));
                    Check(b.CodeWrites.Count == 0 && !b.Allocated);
                }
                var partial = Seed(image); partial.PartialCodeFailure = true;
                Check(Fails(delegate { PureSync.Install(partial, image); }));
                Check(original.All(p => partial.Bytes[p.Key] == p.Value) && !partial.Allocated);
            }
            File.WriteAllBytes(Path.Combine(args[0], "sync-stub.bin"), PureSync.Stub(0x20000100));
            Console.WriteLine("PURE_SYNC_MANAGED_PASS checks=" + checks);
        }
    }
}
