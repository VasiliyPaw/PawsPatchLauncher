using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace PawPureFixes
{
    internal interface IPatchMemory
    {
        byte[] Read(uint address, int count);
        void Write(uint address, byte[] bytes);
        void WriteCode(uint address, byte[] bytes);
        uint Allocate(int count);
        void MakeExecutable(uint address, int count);
        void Flush(uint address, int count);
        void Free(uint address);
    }

    internal sealed class Signature
    {
        internal readonly uint Rva;
        internal readonly byte[] Bytes;
        internal Signature(uint rva, string hex) { Rva = rva; Bytes = PurePatch.Hex(hex); }
    }

    // Only two guarded call sites. No game data, menu, palette, map selection,
    // resource, diplomacy, settings or synchronization-bypass changes.
    internal static class PurePatch
    {
        internal const uint ZeroHookRva = 0xBF99F;
        internal const uint FormatterRva = 0x2BCD9F;
        internal const uint TerrainHookRva = 0x23ADB3;
        internal const uint ConstructorRva = 0x91B4E;
        internal const int AllocationSize = 4096;
        internal const uint TerrainOffset = 0x80;
        internal static readonly Signature[] Guards = {
            new Signature(ZeroHookRva, "E8FBD31F00"),
            new Signature(TerrainHookRva, "E8966DE5FF"),
            new Signature(ConstructorRva, "C74108FFFF7F7F8BC1C7410CFFFF7FFFC74110FFFF7F7F66C741140101C741180000803FC6412000C3"),
            new Signature(0x14A4FE, "C6403501"),
            new Signature(0x14A5F7, "E8E06F2900")
        };
        internal static byte[] Hex(string text)
        {
            byte[] bytes = new byte[text.Length / 2];
            for (int i = 0; i < bytes.Length; i++) bytes[i] = Convert.ToByte(text.Substring(i * 2, 2), 16);
            return bytes;
        }
        internal static byte[] Branch(byte opcode, uint from, uint to)
        {
            return new[] { opcode }.Concat(BitConverter.GetBytes(unchecked(to - from - 5))).ToArray();
        }
        internal static byte[] ZeroStub(uint image, uint cave)
        {
            // Preserve EAX/flags. Normalize only the exact +/-0 display copies
            // consumed by the original formatter; no resource-state writes.
            byte[] code = Hex("9C508B44241425FFFFFF7F7508C7442414000000008B44241825FFFFFF7F7508C744241800000000589D");
            return code.Concat(Branch(0xE9, cave + (uint)code.Length, image + FormatterRva)).ToArray();
        }
        internal static byte[] TerrainStub(uint image, uint cave)
        {
            // Replay the complete original constructor, then initialize the
            // previously uninitialized radius field. MOV/RET preserve flags,
            // FP state and constructor result; no RNG call is added or removed.
            return Branch(0xE8, cave, image + ConstructorRva)
                .Concat(Hex("C7411C000080BFC3")).ToArray();
        }
        internal static byte[] Payload(uint image, uint cave)
        {
            byte[] result = new byte[AllocationSize];
            byte[] zero = ZeroStub(image, cave), terrain = TerrainStub(image, cave + TerrainOffset);
            if (zero.Length > TerrainOffset || TerrainOffset + terrain.Length > result.Length)
                throw new InvalidDataException("Invalid pure-fix payload layout.");
            Buffer.BlockCopy(zero, 0, result, 0, zero.Length);
            Buffer.BlockCopy(terrain, 0, result, (int)TerrainOffset, terrain.Length);
            return result;
        }
        internal static void Expect(IPatchMemory memory, uint address, byte[] expected)
        {
            if (!memory.Read(address, expected.Length).SequenceEqual(expected))
                throw new InvalidDataException("Unsupported game code at 0x" + address.ToString("X8") + ". No unchecked patch is permitted.");
        }
        internal static void Validate(IPatchMemory memory, uint image)
        {
            foreach (Signature signature in Guards) Expect(memory, image + signature.Rva, signature.Bytes);
        }
        internal static bool IsReady(IPatchMemory memory, uint image)
        {
            return Guards.All(s => memory.Read(image + s.Rva, s.Bytes.Length).SequenceEqual(s.Bytes));
        }
        internal static uint Install(IPatchMemory memory, uint image)
        {
            // The caller suspends the verified, newly launched game around the
            // entire transaction. Every signature is checked before allocation.
            Validate(memory, image);
            uint cave = 0;
            int attemptedHooks = 0;
            try
            {
                cave = memory.Allocate(AllocationSize);
                byte[] payload = Payload(image, cave);
                memory.Write(cave, payload);
                Expect(memory, cave, payload);
                memory.MakeExecutable(cave, AllocationSize);
                memory.Flush(cave, AllocationSize);
                for (int i = 0; i < 2; i++)
                {
                    Signature site = Guards[i];
                    uint target = cave + (i == 0 ? 0 : TerrainOffset);
                    byte[] call = Branch(0xE8, image + site.Rva, target);
                    attemptedHooks = i + 1; // A native write may fail after a partial write.
                    memory.WriteCode(image + site.Rva, call);
                    Expect(memory, image + site.Rva, call);
                    memory.Flush(image + site.Rva, call.Length);
                }
                // The constructor and BOTH stock OOS sites must remain intact.
                foreach (Signature signature in Guards.Skip(2)) Expect(memory, image + signature.Rva, signature.Bytes);
                return cave;
            }
            catch (Exception failure)
            {
                bool restored = true;
                for (int i = attemptedHooks - 1; i >= 0; i--)
                {
                    try
                    {
                        Signature site = Guards[i];
                        memory.WriteCode(image + site.Rva, site.Bytes);
                        Expect(memory, image + site.Rva, site.Bytes);
                        memory.Flush(image + site.Rva, site.Bytes.Length);
                    }
                    catch { restored = false; }
                }
                // Retain memory if a call might still target it. The runtime
                // terminates only its own verified incomplete launch on failure.
                if (cave != 0 && restored) memory.Free(cave);
                if (!restored) throw new InvalidOperationException("Pure-fix rollback failed; the verified incomplete launch must be stopped.", failure);
                throw;
            }
        }
    }
}
