using System;
using System.IO;
using System.Reflection;

// Offline only: export the actual emitter from each built helper without
// invoking its entry point, attaching to a process or writing game memory.
internal static class ExportSavedOwnerFixtures
{
    private static int Main(string[] args)
    {
        var type = Assembly.LoadFile(Path.GetFullPath(args[0])).GetType("K2PawFamilyPostgen1372", true);
        var method = type.GetMethod("BuildFamilyOwnerStub", BindingFlags.NonPublic | BindingFlags.Static);
        Directory.CreateDirectory(args[1]);
        var maps = (string[,])type.GetField("ActorKingdomMap", BindingFlags.NonPublic | BindingFlags.Static).GetValue(null);
        var index = type.GetMethod("GetTargetKingdomIndex", BindingFlags.NonPublic | BindingFlags.Static);
        using (var rows = new StreamWriter(Path.Combine(args[1], "mappings.tsv")))
            for (int i = 0; i < maps.GetLength(0); ++i)
                rows.WriteLine(maps[i, 0] + "\t" + maps[i, 1] + "\t" + index.Invoke(null, new object[] { maps[i, 1] }));
        int[] images = { 0x460000, 0xe40000, 0x12000000 };
        int[] stubs = { 0x10000000, 0x21000000, 0x60000000 };
        for (int i = 0; i < images.Length; ++i)
            for (int site = 0; site < 2; ++site)
            {
                string counter = site == 0 ? "CounterInitialConstructor" : "CounterMaterializedConstructor";
                int count = (int)type.GetField(counter, BindingFlags.NonPublic | BindingFlags.Static).GetRawConstantValue();
                byte[] code = (byte[])method.Invoke(null, new object[] {
                    new IntPtr(images[i]), new IntPtr(images[i] + (site == 0 ? 0x22c7cc : 0x22d00f)),
                    new byte[] { 0x89, 0x87, 0xe8, 0, 0, 0 }, new IntPtr(0x30000000),
                    new IntPtr(stubs[i]), count, IntPtr.Zero });
                File.WriteAllBytes(Path.Combine(args[1], i + "-" + site + ".bin"), code);
            }
        return 0;
    }
}
