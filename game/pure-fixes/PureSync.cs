using System;
using System.IO;
using System.Linq;

namespace PawPureFixes
{
    // Use the same first-failure native log writer as Arcane Wars. Only the
    // continuation marker is suppressed; checksum calculation is unchanged.
    internal static class PureSync
    {
        internal const uint FailureRva = 0x14A5F2, MarkerRva = 0x14A4FE;
        internal static byte[] Signature(uint image)
        {
            return new byte[] { 0xB8 }.Concat(BitConverter.GetBytes(image + 0x42EE6A))
                .Concat(PurePatch.Hex("E8E06F290083EC0C535657FF75088BF968"))
                .Concat(BitConverter.GetBytes(image + 0x4B7F44)).Concat(new byte[] { 0x68 })
                .Concat(BitConverter.GetBytes(image + 0x4B7F64)).ToArray();
        }
        internal static void Validate(IPatchMemory memory, uint image)
        {
            PurePatch.Expect(memory, image + FailureRva, Signature(image));
            PurePatch.Expect(memory, image + MarkerRva, PurePatch.Hex("C6403501"));
            PurePatch.Expect(memory, image + PawSyncDiagnostics.ResetRva, PawSyncDiagnostics.ResetSignature);
        }
        internal static uint Install(IPatchMemory memory, uint image)
        {
            Validate(memory, image);
            uint block = 0; int attempted = 0;
            var sites = new[] { (uint)PawSyncDiagnostics.ResetRva, FailureRva, MarkerRva };
            var originals = new[] { PawSyncDiagnostics.ResetSignature.Take(5).ToArray(), Signature(image).Take(5).ToArray(), PurePatch.Hex("C6403501") };
            try
            {
                // Keep the signal on its own writable page after making code RX.
                block = memory.Allocate(8192);
                var payload = new byte[8192];
                var stub = PawSyncDiagnostics.Build(image, block, block + 4096);
                Buffer.BlockCopy(stub, 0, payload, 0, stub.Length);
                var initial = PawSyncDiagnostics.InitialSignal();
                Buffer.BlockCopy(initial, 0, payload, 4096, initial.Length);
                memory.Write(block, payload);
                PurePatch.Expect(memory, block, payload);
                memory.MakeExecutable(block, 4096); memory.Flush(block, 4096);
                var patches = new[] { PurePatch.Branch(0xE9, image + PawSyncDiagnostics.ResetRva, block + PawSyncDiagnostics.ResetOffset),
                    PurePatch.Branch(0xE9, image + FailureRva, block), PurePatch.Hex("90909090") };
                for (int i = 0; i < sites.Length; i++)
                {
                    attempted = i + 1;
                    memory.WriteCode(image + sites[i], patches[i]);
                    PurePatch.Expect(memory, image + sites[i], patches[i]);
                    memory.Flush(image + sites[i], patches[i].Length);
                }
                return block + 4096;
            }
            catch
            {
                bool restored = true;
                for (int i = attempted - 1; i >= 0; i--)
                    try { memory.WriteCode(image + sites[i], originals[i]); PurePatch.Expect(memory, image + sites[i], originals[i]); memory.Flush(image + sites[i], originals[i].Length); }
                    catch { restored = false; }
                if (block != 0 && restored) memory.Free(block);
                throw;
            }
        }
    }
}
