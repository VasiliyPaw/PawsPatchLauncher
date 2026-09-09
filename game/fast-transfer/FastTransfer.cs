// Built-in Beta R2. Native save protocol, block size, ACKs and simulation
// ticks remain stock. Install exclusively in the fresh process owned by startup.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;

internal static class PawFastTransfer
{
    internal const uint BudgetRva = 0x151936, CadenceRva = 0x1500F6, AckRva = 0x1501D1;
    internal const int BudgetBits = 1200 * 8 + 3;
    internal const int Burst = 16;
    internal static readonly byte[] BudgetOriginal = TerrainPatch.Hex("8B43088BCDC1E003");
    internal static readonly byte[] CadenceOriginal = TerrainPatch.Hex("6A05E972FFFFFF");
    internal static readonly byte[] AckOriginal = TerrainPatch.Hex("6A04E9A9FEFFFF");
    private static int pid;
    private static uint stats;
    private static uint previousPackets;
    private static long nextPoll;
    private static Action<string> logger;

    internal sealed class Guard
    {
        internal uint Rva;
        internal byte[] Bytes;
        internal int[] Fixups;
        internal byte[] At(uint image)
        {
            byte[] b = (byte[])Bytes.Clone();
            foreach (int offset in Fixups)
                Buffer.BlockCopy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(b, offset) + image - 0x460000)), 0, b, offset, 4);
            return b;
        }
    }

    internal static List<Guard> Guards()
    {
        var result = new List<Guard>();
        using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("FastTransferGuards"))
        using (var r = new BinaryReader(s))
        {
            if (r.ReadInt32() != 0x31544650) throw new InvalidDataException("Transfer guard format");
            int count = r.ReadInt32();
            if (count < 1 || count > 64) throw new InvalidDataException("Transfer guard count");
            for (int i = 0; i < count; i++)
            {
                uint rva = r.ReadUInt32(); int size = r.ReadInt32();
                if (size <= 0 || size > 16384) throw new InvalidDataException("Transfer guard size");
                byte[] b = r.ReadBytes(size);
                int fixes = r.ReadInt32();
                if (b.Length != size || fixes < 0 || fixes > size / 4) throw new InvalidDataException("Transfer guard fixups");
                int[] offsets = new int[fixes];
                for (int j = 0; j < fixes; j++)
                {
                    offsets[j] = r.ReadInt32();
                    if (offsets[j] < 0 || offsets[j] > size - 4) throw new InvalidDataException("Transfer relocation");
                }
                result.Add(new Guard { Rva = rva, Bytes = b, Fixups = offsets });
            }
            if (s.Position != s.Length) throw new InvalidDataException("Trailing transfer guard data");
        }
        return result;
    }

    internal static void Validate(IMemory memory, uint image)
    {
        foreach (Guard guard in Guards())
            TerrainPatch.Expect(memory, image + guard.Rva, guard.At(image));
        // These are the *live* registry values, not assumed registration defaults.
        uint registry = BitConverter.ToUInt32(memory.Read(image + 0x5F94D0, 4), 0);
        if (registry == 0) throw new InvalidDataException("Transfer registry unavailable");
        int[] expected = { 20, 64, 256 };
        for (int i = 0; i < 3; i++)
        {
            uint value = BitConverter.ToUInt32(memory.Read(registry + 0x120u + (uint)i * 4, 4), 0);
            if (value == 0 || BitConverter.ToInt32(memory.Read(value, 4), 0) != expected[i])
                throw new InvalidDataException("Unsupported live transfer setting " + i);
        }
    }

    private sealed class Code
    {
        internal readonly List<byte> B = new List<byte>();
        private readonly uint origin;
        internal Code(uint origin) { this.origin = origin; }
        internal void Add(string hex) { B.AddRange(TerrainPatch.Hex(hex)); }
        internal void U32(uint n) { B.AddRange(BitConverter.GetBytes(n)); }
        internal int Jump(byte condition) { Add("0F"); B.Add(condition); int p = B.Count; U32(0); return p; }
        internal void Bind(int operand, int target) { Put(B, operand, unchecked((uint)(target - operand - 4))); }
        internal void To(uint target) { Add("E9"); U32(unchecked(target - origin - (uint)B.Count - 4)); }
        internal void Call(uint target) { Add("E8"); U32(unchecked(target - origin - (uint)B.Count - 4)); }
    }
    private static void Put(List<byte> b, int offset, uint value)
    { byte[] v = BitConverter.GetBytes(value); for (int i = 0; i < 4; i++) b[offset + i] = v[i]; }
    internal static byte[] Detour(uint from, uint to, int size)
    {
        var c = new Code(from); c.To(to);
        while (c.B.Count < size) c.Add("90");
        return c.B.ToArray();
    }

    internal static byte[] Payload(uint image, uint cave)
    {
        byte[] result = new byte[8192]; // code RX on page 1, counters RW on page 2
        var b = new Code(cave);
        b.Add("837D3C02"); int noTransfer = b.Jump(0x85);
        b.Add("83BDFC03000000"); int invalidSize = b.Jump(0x8E);
        b.Add("BE"); b.U32(BudgetBits);
        b.Add("FF05"); b.U32(cave + 4096);
        b.Add("8B8530040000A3"); b.U32(cave + 4100);
        int stock = b.B.Count;
        b.B.AddRange(BudgetOriginal);
        b.To(image + BudgetRva + (uint)BudgetOriginal.Length);
        b.Bind(noTransfer, stock); b.Bind(invalidSize, stock);
        Buffer.BlockCopy(b.B.ToArray(), 0, result, 0, b.B.Count);

        var c = new Code(cave + 256);
        c.Add("837E3C02"); int idle = c.Jump(0x85);
        c.Add("83BEFC03000000"); int invalid = c.Jump(0x8E);
        // Stock SendPackets resets this PER-PEER counter before its fair loop,
        // and stock packet accounting increments it. Never modify either one.
        c.Add("8B8E2C040000837908"); c.B.Add((byte)Burst);
        int capped = c.Jump(0x83); // unsigned >= also rejects a corrupt negative count
        c.Add("83790800"); int first = c.Jump(0x84);
        // After the first packet, only continue while the native sender has
        // unsent metadata. The stock first packet can refill the window or retry.
        // This read-only stock query does not dequeue or mark anything as sent.
        c.Add("8D8EB4030000"); c.Call(image + 0x158857);
        c.Add("3B86CC030000"); int drained = c.Jump(0x8D);
        int send = c.B.Count;
        c.Add("B8050000005EC3");
        int wait = c.B.Count;
        c.Add("33C05EC3");
        int fallback = c.B.Count;
        c.Add("6A05"); c.To(image + 0x15006F);
        c.Bind(idle, fallback); c.Bind(invalid, fallback);
        c.Bind(capped, wait); c.Bind(drained, wait); c.Bind(first, send);
        Buffer.BlockCopy(c.B.ToArray(), 0, result, 256, c.B.Count);

        var a = new Code(cave + 512);
        // Already in the normal client->host lobby branch. xmm0 holds the
        // original elapsed time and ECX the net connection; preserve both for fallback.
        a.Add("8B862404000085C0"); int noReceive = a.Jump(0x8E);
        // ceil(size / 64) + one header block, overflow-safe for positive int sizes.
        a.Add("48C1E80683C0023B8608040000"); int complete = a.Jump(0x8E);
        a.Add("83790800"); int alreadyAcked = a.Jump(0x85);
        a.Add("F30F10492C0F2F8990000000"); int noNewPacket = a.Jump(0x86);
        a.Add("B8040000005EC3");
        int ackFallback = a.B.Count;
        a.Add("6A04"); a.To(image + 0x150081);
        a.Bind(noReceive, ackFallback); a.Bind(complete, ackFallback);
        a.Bind(alreadyAcked, ackFallback); a.Bind(noNewPacket, ackFallback);
        Buffer.BlockCopy(a.B.ToArray(), 0, result, 512, a.B.Count);
        return result;
    }

    internal static uint InstallCore(IMemory memory, uint image)
    {
        Validate(memory, image); // No allocations or writes before all checks pass.
        uint cave = memory.Allocate(8192);
        bool budgetTouched = false, cadenceTouched = false, ackTouched = false;
        try
        {
            byte[] payload = Payload(image, cave);
            memory.Write(cave, payload);
            TerrainPatch.Expect(memory, cave, payload);
            memory.MakeExecutable(cave, 4096);
            memory.Flush(cave, 4096);
            budgetTouched = true;
            memory.WriteCode(image + BudgetRva, Detour(image + BudgetRva, cave, BudgetOriginal.Length));
            cadenceTouched = true;
            memory.WriteCode(image + CadenceRva, Detour(image + CadenceRva, cave + 256, CadenceOriginal.Length));
            ackTouched = true;
            memory.WriteCode(image + AckRva, Detour(image + AckRva, cave + 512, AckOriginal.Length));
            memory.Flush(image + BudgetRva, BudgetOriginal.Length);
            memory.Flush(image + CadenceRva, CadenceOriginal.Length);
            memory.Flush(image + AckRva, AckOriginal.Length);
            TerrainPatch.Expect(memory, image + BudgetRva, Detour(image + BudgetRva, cave, BudgetOriginal.Length));
            TerrainPatch.Expect(memory, image + CadenceRva, Detour(image + CadenceRva, cave + 256, CadenceOriginal.Length));
            TerrainPatch.Expect(memory, image + AckRva, Detour(image + AckRva, cave + 512, AckOriginal.Length));
            return cave;
        }
        catch
        {
            // Caller holds the process suspended. A failed rollback aborts the
            // owned fresh launch; never free code still targeted by a detour.
            if (ackTouched)
            { memory.WriteCode(image + AckRva, AckOriginal); memory.Flush(image + AckRva, AckOriginal.Length); TerrainPatch.Expect(memory, image + AckRva, AckOriginal); }
            if (cadenceTouched)
            { memory.WriteCode(image + CadenceRva, CadenceOriginal); memory.Flush(image + CadenceRva, CadenceOriginal.Length); TerrainPatch.Expect(memory, image + CadenceRva, CadenceOriginal); }
            if (budgetTouched)
            { memory.WriteCode(image + BudgetRva, BudgetOriginal); memory.Flush(image + BudgetRva, BudgetOriginal.Length); TerrainPatch.Expect(memory, image + BudgetRva, BudgetOriginal); }
            memory.Free(cave);
            throw;
        }
    }

    internal static void Install(Process game, IntPtr imageBase, Action<string> log)
    {
#if FAST_SAVE_TRANSFER
        if (pid != 0 || game.HasExited || imageBase != ReleaseStartup.VerifiedImage)
            throw new InvalidOperationException("Transfer startup identity check failed.");
#endif
        uint image = unchecked((uint)imageBase.ToInt32());
        // This entry is called only inside the existing verified fresh startup.
        using (var memory = new NativeMemory(game.Id))
        {
            memory.Suspend();
            try { stats = InstallCore(memory, image) + 4096; }
            finally { memory.Resume(); }
        }
        pid = game.Id; logger = log;
        log("FAST_TRANSFER_R2_READY pid=" + pid + "; liveCodeGuards=" + Guards().Count +
            "; liveSettings=20/64/256; fileBudgetBytes=1200; maxPacketsPerPeerPerPass=" + Burst +
            "; stopBurstWhenDrained=true; receiveAckPerPass=1; stockBandwidthLimits=true; nativeProtocol=true; diskExeUnchanged=true");
    }

    internal static void Tick()
    {
        if (stats == 0 || DateTime.UtcNow.Ticks < nextPoll) return;
        nextPoll = DateTime.UtcNow.AddSeconds(5).Ticks;
        using (var memory = new NativeMemory(pid))
        {
            byte[] b = memory.Read(stats, 8);
            uint packets = BitConverter.ToUInt32(b, 0);
            if (packets == previousPackets) return;
            logger("FAST_TRANSFER_R2_PROGRESS packets=" + packets + "; generation=" + BitConverter.ToUInt32(b, 4));
            previousPackets = packets;
        }
    }
}
