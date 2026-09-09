using System;
using System.IO;
using System.Linq;

// TerrainRuntime's constant dependency only; runtime uses the real startup.
#if !FAST_SAVE_TRANSFER
internal static class ReleaseStartup { internal const string Build = "offline-test"; }
#endif

internal static class FastTransferTests
{
    private static int checks;
    private static void Check(bool ok, string name)
    { checks++; if (!ok) throw new Exception(name); }
    private static FakeMemory Seed(uint image)
    {
        var memory = new FakeMemory(image);
        foreach (var guard in PawFastTransfer.Guards()) memory.Seed(image + guard.Rva, guard.At(image));
        memory.Seed(image + 0x5F94D0, BitConverter.GetBytes(0x20000000u));
        for (int i = 0; i < 3; i++)
        {
            uint p = 0x20001000u + (uint)i * 4;
            memory.Seed(0x20000120u + (uint)i * 4, BitConverter.GetBytes(p));
            memory.Seed(p, BitConverter.GetBytes(new[] { 20, 64, 256 }[i]));
        }
        return memory;
    }
    private static bool Fails(Action action)
    { try { action(); return false; } catch { return true; } }
    private static void Restored(FakeMemory m, uint image)
    {
        Check(m.Read(image + PawFastTransfer.BudgetRva, 8).SequenceEqual(PawFastTransfer.BudgetOriginal), "budget rollback");
        Check(m.Read(image + PawFastTransfer.CadenceRva, 7).SequenceEqual(PawFastTransfer.CadenceOriginal), "cadence rollback");
        Check(m.Read(image + PawFastTransfer.AckRva, 7).SequenceEqual(PawFastTransfer.AckOriginal), "ack rollback");
    }
#if !FAST_SAVE_TRANSFER
    private static int Main(string[] args) { return Run(args); }
#endif
    internal static int Run(string[] args)
    {
        checks = 0;
        foreach (uint image in new uint[] { 0x400000, 0x460000, 0xAF0000 })
        {
            var good = Seed(image);
            uint cave = PawFastTransfer.InstallCore(good, image);
            int operationCount = good.Operations;
            Check(good.Read(image + PawFastTransfer.BudgetRva, 8).SequenceEqual(PawFastTransfer.Detour(image + PawFastTransfer.BudgetRva, cave, 8)), "budget detour");
            Check(good.Read(image + PawFastTransfer.CadenceRva, 7).SequenceEqual(PawFastTransfer.Detour(image + PawFastTransfer.CadenceRva, cave+256, 7)), "cadence detour");
            Check(good.Read(image + PawFastTransfer.AckRva, 7).SequenceEqual(PawFastTransfer.Detour(image + PawFastTransfer.AckRva, cave+512, 7)), "ack detour");
            if (args != null) File.WriteAllBytes(Path.Combine(args[0], "payload-" + image.ToString("X") + ".bin"), PawFastTransfer.Payload(image, 0x10000000));
            for (int failure = 1; failure <= operationCount; failure++)
            {
                var m = Seed(image); m.FailAt = failure;
                Check(Fails(delegate { PawFastTransfer.InstallCore(m, image); }), "injected operation must fail " + failure);
                Check(!m.Allocated, "allocation released after failure " + failure);
                Restored(m, image);
            }
            foreach (var guard in PawFastTransfer.Guards())
            {
                var m = Seed(image);
                byte[] damaged = guard.At(image); damaged[0] ^= 1;
                m.Seed(image + guard.Rva, damaged);
                Check(Fails(delegate { PawFastTransfer.InstallCore(m, image); }), "unknown code rejected");
                Check(!m.Allocated && m.Frees == 0, "no allocation before guards");
            }
            for (int field = 0; field < 3; field++)
            {
                var m = Seed(image);
                m.Seed(0x20001000u + (uint)field * 4, BitConverter.GetBytes(999));
                Check(Fails(delegate { PawFastTransfer.InstallCore(m, image); }), "modified protocol setting rejected");
                Check(!m.Allocated, "modified protocol makes no allocation");
            }
            var uncertain = Seed(image); uncertain.AlwaysFailHook = true;
            Check(Fails(delegate { PawFastTransfer.InstallCore(uncertain, image); }), "partial detour and rollback failure surfaced");
            Check(uncertain.Allocated && uncertain.Frees == 0, "never free code when rollback uncertain");
        }
        Console.WriteLine("FAST_TRANSFER_MANAGED_PASS checks=" + checks);
        return 0;
    }
}
