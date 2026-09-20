using System;

internal static class SettlementSlotsPatch
{
    // Same dynamically allocated widget class, two callers. The bottom panel
    // shows buildings only; the city list also reserves a widget for the center.
    internal static readonly uint[] Sites = { 0x0E1C7D, 0x0BB4C8 };
    internal const uint LayoutSite = 0xE2618;
    internal static readonly byte[] LayoutOriginal = TerrainPatch.Hex("F30F108784000000");
    internal static readonly byte[][] Original = {
        TerrainPatch.Hex("6A0750E81E9BFDFF83C40C"),
        TerrainPatch.Hex("6A0850E8D302000083C40C")
    };
    internal static void Validate(IMemory memory, uint image)
    {
        for (int i = 0; i < Sites.Length; i++)
            TerrainPatch.Expect(memory, image + Sites[i], Original[i]);
        // Constructor allocates its array using the supplied count; it is not
        // an inline seven-element array. Abort on a different engine layout.
        TerrainPatch.Expect(memory, image + 0x0E2361,
            TerrainPatch.Hex("8B750C8D4F746A0133DB"));
        TerrainPatch.Expect(memory, image + 0x0E243B,
            TerrainPatch.Hex("3B9F8C0000007C95"));
        TerrainPatch.Expect(memory, image + LayoutSite, LayoutOriginal);
    }
    internal static void Install(IMemory memory, uint image, Action<string> log)
    {
        Validate(memory, image);
        int attempted = -1;
        uint cave = 0;
        bool layoutAttempted = false, safeToFree = true;
        try
        {
            cave = memory.Allocate(4096);
            byte[] payload = SettlementSlotsPayload.Build(image, cave);
            memory.Write(cave, payload);
            TerrainPatch.Expect(memory, cave, payload);
            memory.MakeExecutable(cave, 4096);
            memory.Flush(cave, payload.Length);
            for (int i = 0; i < Sites.Length; i++)
            {
                attempted = i;
                memory.WriteCode(image + Sites[i] + 1, new byte[] { (byte)(8 + i) });
                byte[] expected = (byte[])Original[i].Clone();
                expected[1] = (byte)(8 + i);
                TerrainPatch.Expect(memory, image + Sites[i], expected);
                memory.Flush(image + Sites[i], expected.Length);
            }
            byte[] hook = TerrainPatch.Hex("9090909090909090");
            byte[] jump = TerrainPatch.Call(image + LayoutSite, cave); jump[0] = 0xE9;
            Buffer.BlockCopy(jump, 0, hook, 0, 5);
            layoutAttempted = true; safeToFree = false;
            memory.WriteCode(image + LayoutSite, hook);
            TerrainPatch.Expect(memory, image + LayoutSite, hook);
            memory.Flush(image + LayoutSite, hook.Length);
            log("SETTLEMENT_SLOTS r2; bottom=8 buildings; city-list=8 buildings+center; equal horizontal spacing; display only");
        }
        catch
        {
            if (layoutAttempted)
                try
                {
                    memory.WriteCode(image + LayoutSite, LayoutOriginal);
                    TerrainPatch.Expect(memory, image + LayoutSite, LayoutOriginal);
                    memory.Flush(image + LayoutSite, LayoutOriginal.Length);
                    safeToFree = true;
                }
                catch(Exception e) { log("SETTLEMENT_LAYOUT_ROLLBACK_UNCERTAIN " + e.Message); }
            for (int i = attempted; i >= 0; i--)
                try
                {
                    memory.WriteCode(image + Sites[i] + 1, new byte[] { Original[i][1] });
                    TerrainPatch.Expect(memory, image + Sites[i], Original[i]);
                    memory.Flush(image + Sites[i], Original[i].Length);
                }
                catch (Exception e) { log("SETTLEMENT_SLOTS_ROLLBACK_UNCERTAIN " + e.Message); }
            if (cave != 0 && safeToFree)
                try { memory.Free(cave); } catch(Exception e) { log("SETTLEMENT_SLOTS_FREE_FAILED " + e.Message); }
            throw;
        }
    }
}
