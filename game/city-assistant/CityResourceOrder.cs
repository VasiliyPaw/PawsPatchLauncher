using System;
using System.IO;
using System.Linq;

// Canonical policy vectors are gold/stone/wood/iron/mana. The verified Powers
// overlay inserts Shards immediately after gold in all native resource arrays.
internal static class CityResourceOrder
{
    internal static bool Supported(int count) { return count == 9 || count == 10; }
    internal static int NativeIndex(int economic, int count)
    {
        if (!Supported(count) || economic < 0 || economic >= 5)
            throw new InvalidDataException("Unsupported city resource order.");
        return economic + (count == 10 && economic > 0 ? 1 : 0);
    }
    internal static float[] Read(byte[] bytes, int offset, int count)
    {
        return Enumerable.Range(0,5).Select(i => BitConverter.ToSingle(bytes,offset+NativeIndex(i,count)*4)).ToArray();
    }
}
