using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;

namespace PawPureFixes
{
    internal sealed class TransferFakeMemory : IPatchMemory
    {
        internal readonly Dictionary<uint, byte> Bytes = new Dictionary<uint, byte>();
        internal readonly Dictionary<uint, int> Blocks = new Dictionary<uint, int>();
        internal readonly List<uint> CodeWrites = new List<uint>();
        internal int Operations, FailAt = -1, Frees, Allocations;
        internal bool AlwaysFailHook, PartialCodeFailure;
        private uint next = 0x10000000;
        internal bool Allocated { get { return Blocks.Count != 0; } }
        internal TransferFakeMemory(uint image) { }
        internal void Seed(uint address, byte[] bytes)
        { for (int i = 0; i < bytes.Length; i++) Bytes[address + (uint)i] = bytes[i]; }
        private void Op() { if (++Operations == FailAt) throw new IOException("Injected operation " + Operations); }
        public byte[] Read(uint address, int count)
        { Op(); return Enumerable.Range(0, count).Select(i => Bytes.ContainsKey(address + (uint)i) ? Bytes[address + (uint)i] : (byte)0).ToArray(); }
        public void Write(uint address, byte[] bytes) { Op(); Seed(address, bytes); }
        public void WriteCode(uint address, byte[] bytes)
        {
            Op(); CodeWrites.Add(address); Seed(address, bytes.Take(2).ToArray());
            if (AlwaysFailHook || PartialCodeFailure)
            { PartialCodeFailure = false; throw new IOException("Injected partial hook write"); }
            Seed(address, bytes);
        }
        public uint Allocate(int size)
        {
            Op(); uint result = next; next += (uint)((size + 4095) & ~4095);
            Blocks.Add(result, size); Allocations++; return result;
        }
        public void MakeExecutable(uint address, int count) { Op(); }
        public void Flush(uint address, int count) { Op(); }
        public void Free(uint address) { Op(); if (!Blocks.Remove(address)) throw new Exception("Unknown allocation freed"); Frees++; }
    }
    internal static class ChannelTests
    {
        private static int checks;
        private static void Check(bool ok, string why) { checks++; if (!ok) throw new Exception(why); }
        private static bool Fails(Action action) { try { action(); return false; } catch { return true; } }
        private static TransferFakeMemory Seed(uint image)
        {
            var memory = new TransferFakeMemory(image);
            foreach (var guard in PurePatch.Guards) memory.Seed(image + guard.Rva, guard.Bytes);
#if PAW_PURE_FAST_TRANSFER
            foreach (var guard in PawFastTransfer.Guards()) memory.Seed(image + guard.Rva, guard.At(image));
            memory.Seed(image + 0x5F94D0, BitConverter.GetBytes(0x20000000u));
            for (int i = 0; i < 3; i++)
            {
                uint field = 0x20001000u + (uint)i * 4;
                memory.Seed(0x20000120u + (uint)i * 4, BitConverter.GetBytes(field));
                memory.Seed(field, BitConverter.GetBytes(new[] { 20, 64, 256 }[i]));
            }
#endif
            return memory;
        }
        private static void Restored(TransferFakeMemory memory, Dictionary<uint, byte> original)
        {
            Check(original.All(x => memory.Bytes[x.Key] == x.Value), "failed channel install restores all original game bytes");
            Check(!memory.Allocated, "failed channel install releases all safe allocations");
        }
        private static int Main(string[] args)
        {
            string root = Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
            foreach (uint image in new uint[] { 0x400000, 0x460000, 0xAF0000 })
            {
                var memory = Seed(image); var original = new Dictionary<uint, byte>(memory.Bytes);
                Check(PureChannel.IsReady(memory, image), "all current channel signatures ready");
                memory.Operations = 0;
                var installed = PureChannel.Install(memory, image); int operations = memory.Operations;
                Check(memory.Allocations == (PureChannel.FastTransfer ? 2 : 1), "only selected built-in allocations");
                var sites = new List<uint> { image + PurePatch.ZeroHookRva, image + PurePatch.TerrainHookRva };
#if PAW_PURE_FAST_TRANSFER
                sites.AddRange(new[] { image + PawFastTransfer.BudgetRva, image + PawFastTransfer.CadenceRva, image + PawFastTransfer.AckRva });
                Check(installed.TransferCave != 0 && installed.TransferCave != installed.PureCave, "R2 separate code and counter allocation");
                Check(PawFastTransfer.BudgetBits == 9603 && PawFastTransfer.Burst == 16, "accepted R2 constants unchanged");
#else
                Check(installed.TransferCave == 0, "stable has no transfer cave");
                Check(Assembly.GetExecutingAssembly().GetType("PawFastTransfer") == null, "stable includes no transfer implementation");
                Check(!Assembly.GetExecutingAssembly().GetManifestResourceNames().Contains("FastTransferGuards"), "stable embeds no transfer guards");
#endif
                Check(memory.CodeWrites.SequenceEqual(sites), "only pure fixes and selected R2 hooks written");
                Check(original.All(x => sites.Any(s => x.Key >= s && x.Key < s + 8) || memory.Bytes[x.Key] == x.Value), "stock protocol and OOS code unchanged outside hooks");
                foreach (var guard in PurePatch.Guards.Skip(2))
                    Check(memory.Read(image + guard.Rva, guard.Bytes.Length).SequenceEqual(guard.Bytes), "stock constructor and sync handling retained");
                for (int failure = 1; failure <= operations; failure++)
                {
                    var broken = Seed(image); broken.FailAt = failure;
                    Check(Fails(delegate { PureChannel.Install(broken, image); }), "every native operation failure surfaces " + failure);
                    Restored(broken, original);
                }
                foreach (var guard in PurePatch.Guards)
                {
                    var broken = Seed(image); broken.Bytes[image + guard.Rva] ^= 1;
                    Check(!PureChannel.IsReady(broken, image), "unready pure code waits without changes");
                    Check(Fails(delegate { PureChannel.Install(broken, image); }), "unknown pure code rejected");
                    Check(broken.Allocations == 0 && broken.CodeWrites.Count == 0, "unknown pure code rejected before writes");
                }
#if PAW_PURE_FAST_TRANSFER
                foreach (var guard in PawFastTransfer.Guards())
                {
                    var broken = Seed(image); broken.Bytes[image + guard.Rva] ^= 1;
                    Check(!PureChannel.IsReady(broken, image), "unready R2 code waits without changes");
                    Check(Fails(delegate { PureChannel.Install(broken, image); }), "unknown R2 code rejected");
                    Check(broken.Allocations == 0 && broken.CodeWrites.Count == 0, "R2 rejection also precedes pure-fix writes");
                }
                for (int field = 0; field < 3; field++)
                {
                    var broken = Seed(image); broken.Seed(0x20001000u + (uint)field * 4, BitConverter.GetBytes(999));
                    Check(!PureChannel.IsReady(broken, image), "unknown registry value is not ready");
                    Check(Fails(delegate { PureChannel.Install(broken, image); }), "unsupported registry value rejected");
                    Check(broken.Allocations == 0 && broken.CodeWrites.Count == 0, "registry rejection precedes all writes");
                }
#endif
                var partial = Seed(image); partial.PartialCodeFailure = true;
                Check(Fails(delegate { PureChannel.Install(partial, image); }), "partial native write fails launch");
                Restored(partial, original);
                var uncertain = Seed(image); uncertain.AlwaysFailHook = true;
                Check(Fails(delegate { PureChannel.Install(uncertain, image); }), "uncertain rollback fails launch");
                Check(uncertain.Allocated && uncertain.Frees == 0, "possibly referenced code retained for owned-process stop");
            }
            Check(Program.RuntimeFeatures.Contains("\"version\":\"" + PureChannel.Version + "\""), "runtime package version stamp");
            Check(Program.RuntimeFeatures.Contains("\"patchVersion\":\"" + PureChannel.PatchVersion + "\""), "public patch version stamp");
            Check(Program.RuntimeFeatures.Contains("\"channel\":\"" + PureChannel.Channel + "\""), "runtime channel stamp");
            foreach (string feature in new[] { "cityAssistant", "randomMap", "randomTime", "hostility", "bypass", "colors", "changesGameFiles" })
                Check(Program.RuntimeFeatures.Contains("\"" + feature + "\":false"), "unrelated feature disabled " + feature);
            Check(Program.RuntimeFeatures.Contains("\"fastSaveTransfer\":" + (PureChannel.FastTransfer ? "true" : "false")), "R2 only Beta");
            string report = "{\"passed\":true,\"checks\":" + checks + ",\"channel\":\"" + PureChannel.Channel + "\",\"aslrLayouts\":3,\"gameLaunched\":false}";
            File.WriteAllText(Path.Combine(root, "channel-tests.json"), report);
            Console.WriteLine(report);
#if PAW_PURE_FAST_TRANSFER
            FastTransferTests.Run(new[] { root });
#endif
            return 0;
        }
    }
}
