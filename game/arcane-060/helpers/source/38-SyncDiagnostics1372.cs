using System;
using System.Collections.Generic;

// The native SyncFailure routine only writes synclogs (including its fallback
// path). The separate local-OOS marker controls continuation. Keep that bypass,
// but run the original writer once per native NETWORK synchronizer baseline.
// No engine checksum, RNG, command, world or save field is changed here.
internal static class PawSyncDiagnostics
{
    internal const int SignalSize = 64, CodeSize = 1024, ResetOffset = 0x200;
    internal const int ResetRva = 0x16DFCA;
    internal static readonly byte[] ResetSignature = Hex("8B442408568D711089410866C7010101");

    // +0/+4 retain the old counter/last-index ABI used by the UI and monitor.
    // +8 baseline epoch, +12 captured epoch, +16 writer attempts, +20 returns,
    // +24 first index, +28 world, +32/+36 local ring bounds, +40 checksum,
    // +44 game-time bits. A returned writer is not proof of successful disk IO;
    // the native log contains the filename and any write/fallback failure.
    internal static byte[] InitialSignal()
    {
        var data = new byte[SignalSize]; data[8] = 1; return data;
    }

    internal static byte[] Build(uint image, uint code, uint signal)
    {
        var result = new byte[CodeSize];
        var b = new Emitter(code);
        b.H("9C60B8"); b.U(signal);                         // pushfd; pushad; eax=state
        b.H("8B542428895004F0FF00");                     // last index; counter++
        b.H("8B480889C78B470C39C8"); b.Jz("done");   // eax=captured; ecx=current; edi=state
        b.H("F00FB14F0C"); b.Jne("done");             // atomic claim BEFORE calling writer
        b.H("89F8FF4010895018");
        b.H("C7402000000000C7402400000000C7402800000000C7402C00000000");
        b.H("8B0D"); b.U(image + 0x5F3FB8); b.H("89481C");
        b.H("85C9"); b.Jz("noWorld");
        b.H("8B89E800000089482C");                     // game time, read-only
        b.Label("noWorld");
        b.H("8B0D"); b.U(image + 0x5F3FF0); b.H("85C9"); b.Jz("noRing");
        b.H("8B51108950208B51148950248B5108895028");
        b.Label("noRing");
        b.H("8BEC81EC100200008D7C240F83E7F00FAE0757"); // ebp=saved regs; aligned FXSAVE
        b.H("FC8B4D18FF7528");                          // clear DF; original this / index
        b.Call(code + 0x300);
        b.H("5F0FAE0F81C410020000");                   // FXRSTOR; restore stack
        b.H("FF05"); b.U(signal + 20);                 // original writer returned
        b.Label("done"); b.H("619DC20400");          // preserve all regs/flags; ret4
        Copy(b.Finish(), result, 0, ResetOffset);

        b = new Emitter(code + ResetOffset);
        b.H("9C60");                                  // observe reset, not replace it
        b.H("3B0D"); b.U(image + 0x5F3FF0); b.Jne("resetDone");
        b.H("B8"); b.U(signal);
        b.H("FF4008"); b.Jne("epochReady"); b.H("FF4008"); // zero is reserved for unclaimed
        b.Label("epochReady"); b.H("C7400C00000000"); // next baseline, permit one capture
        b.Label("resetDone"); b.H("619D");
        b.H("8B44240856");                            // displaced native instructions
        b.Jump(image + ResetRva + 5);
        Copy(b.Finish(), result, ResetOffset, 0x100);

        b = new Emitter(code + 0x300);
        b.H("B8"); b.U(image + 0x42EE6A);              // displaced SEH descriptor
        b.Jump(image + 0x14A5F2 + 5);
        Copy(b.Finish(), result, 0x300, 0x100);
        return result;
    }

    static void Copy(byte[] code, byte[] target, int offset, int limit)
    {
        if (code.Length > limit) throw new InvalidOperationException("Sync diagnostics code overlaps");
        Buffer.BlockCopy(code, 0, target, offset, code.Length);
    }
    static byte[] Hex(string text)
    {
        var b = new byte[text.Length / 2];
        for (int i = 0; i < b.Length; i++) b[i] = Convert.ToByte(text.Substring(i * 2, 2), 16);
        return b;
    }
    sealed class Emitter
    {
        readonly uint origin;
        readonly List<byte> bytes = new List<byte>();
        readonly Dictionary<string, int> labels = new Dictionary<string, int>();
        readonly List<KeyValuePair<int, string>> branches = new List<KeyValuePair<int, string>>();
        internal Emitter(uint at) { origin = at; }
        internal void H(string text) { bytes.AddRange(Hex(text)); }
        internal void U(uint n) { bytes.AddRange(BitConverter.GetBytes(n)); }
        internal void Label(string name) { labels.Add(name, bytes.Count); }
        internal void Jz(string name) { H("0F84"); Local(name); }
        internal void Jne(string name) { H("0F85"); Local(name); }
        void Local(string name) { branches.Add(new KeyValuePair<int, string>(bytes.Count, name)); U(0); }
        internal void Jump(uint target) { H("E9"); Relative(target); }
        internal void Call(uint target) { H("E8"); Relative(target); }
        void Relative(uint target) { U(unchecked(target - origin - (uint)bytes.Count - 4)); }
        internal byte[] Finish()
        {
            byte[] result = bytes.ToArray();
            foreach (var j in branches)
                Buffer.BlockCopy(BitConverter.GetBytes(labels[j.Value] - j.Key - 4), 0, result, j.Key, 4);
            return result;
        }
    }
}
