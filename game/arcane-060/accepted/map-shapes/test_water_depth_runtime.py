"""Run the compiled installed generator with native-layout terrain fixtures.

Native painter/height callbacks are modeled; this is not a live-engine test.
It catches broad bed edits and lake repainting that pure depth math cannot.
"""
import argparse
import struct
from pathlib import Path

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ESP


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dll", type=Path, required=True)
    a = p.parse_args()
    pe = pefile.PE(str(a.dll))
    assert not hasattr(pe, "DIRECTORY_ENTRY_IMPORT")
    exports = {s.name.decode(): s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
    checks = 0
    for image, dll in [(0x400000, 0x10000000), (0x260000, 0x18000000)]:
        pe.relocate_image(dll)
        blob = pe.get_memory_mapped_image()
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(image, 0x600000)
        u.mem_map(dll, (len(blob) + 4095) & ~4095)
        u.mem_write(dll, blob)
        u.mem_map(0x20000000, 0x400000)
        u.mem_map(0x30000000, 0x20000)
        world, grid, creator, generator = 0x20000000, 0x20001000, 0x20002000, 0x20003000
        session, manager, state, rules = 0x20004000, 0x20005000, 0x20006000, 0x20007000
        cells, basehm, hm, baseraw, raw = 0x20010000, 0x20050000, 0x20051000, 0x20060000, 0x20070000
        heap, callback, stop = 0x20200000, 0x30010000, 0x3001f000

        def w(at, value):
            u.mem_write(at, struct.pack("<I", value & 0xffffffff))

        def r(at):
            return struct.unpack("<I", u.mem_read(at, 4))[0]

        def wf(at, value):
            u.mem_write(at, struct.pack("<f", value))

        def rf(at):
            return struct.unpack("<f", u.mem_read(at, 4))[0]

        def named(at, name):
            w(at + 8, at + 0x80)
            u.mem_write(at + 0x80, (name + "\0").encode("utf-16le"))
            return at

        w(image + 0x5f3fb8, world)
        w(image + 0x5f3fe4, session)
        w(image + 0x5f0030, manager)
        w(world + 0x30, grid)
        w(world + 0x34, basehm)
        w(world + 0x38, hm)
        w(world + 0x18, rules)
        w(world + 0x1c, 2)
        for i, (name, value) in enumerate([("PawsMapShape", 1), ("PawsRivers", 0)]):
            rule = named(0x20008000 + i * 0x100, name)
            w(rule + 0x20, 3)
            w(rules + i * 12, rule)
            w(rules + i * 12 + 8, value)
        w(grid + 0x1c, 64)
        w(grid + 0x20, 64)
        w(grid + 0x28, cells)
        w(grid + 0x50, 0x2000b000)
        w(0x2000b004, 0x2000b100)
        w(generator, creator)
        w(creator + 0x4c, 12345)
        w(state, image)
        w(state + 4, callback)
        w(state + 84, 1)  # afterNoise: native terrain already generated
        for at, data in [(basehm, baseraw), (hm, raw)]:
            w(at + 0xc, 64)
            w(at + 0x10, 64)
            w(at + 0x14, 1)
            w(at + 0x40, data)
        for i in range(4096):
            w(cells + i * 48 + 0x20, 0x200)
            wf(baseraw + i * 4, 2)
        variants = []
        ids = ["temperate_lake01", "arctic_lake01", "desert_lake01", "cursed_lake01", "arctic_lake02", "desert_quicksand01"]
        for i, name in enumerate(ids):
            v = named(0x20009000 + i * 0x100, name)
            variants.append(v)
            w(0x2000a000 + i * 4, v)
        w(manager + 0x24, 0x2000a000)
        w(manager + 0x28, len(variants))
        pond, puddle, dry = 32 * 64 + 32, 35 * 64 + 32, 30 * 64 + 32
        for cell, variant, flags, delta in [(pond, variants[4], 0x120, -2.3), (puddle, variants[5], 0x20, -2.15)]:
            w(cells + cell * 48, variant)
            w(cells + cell * 48 + 0x20, flags)
            wf(raw + cell * 4, delta)
        original_pond, original_puddle = bytes(u.mem_read(raw + pond * 4, 4)), bytes(u.mem_read(raw + puddle * 4, 4))
        paints, heights = [], []

        def finish(sp, args, result):
            u.reg_write(UC_X86_REG_EAX, result)
            u.reg_write(UC_X86_REG_EIP, r(sp))
            u.reg_write(UC_X86_REG_ESP, sp + 4 + args)

        def native(uc, at, size, data):
            nonlocal heap
            sp = uc.reg_read(UC_X86_REG_ESP)
            if at == image + 0x2ef03c:
                result = heap
                heap += (r(sp + 4) + 15) & ~15
                finish(sp, 0, result)
                return
            if at == image + 0x2ef05f:
                finish(sp, 0, 0)
                return
            assert at == callback
            address, self, argc, values = [r(sp + n) for n in (4, 8, 12, 16)]
            args = [r(values + i * 4) for i in range(argc)]
            rva, result = address - image, 1
            if rva == 0x2517f9:
                x, y = r(args[0]), r(args[0] + 4)
                i = y * 64 + x
                paints.append(i)
                w(cells + i * 48, args[1])
                w(cells + i * 48 + 0x20, 0x120)
            elif rva == 0x2f95f8:
                x, y, bits, _ = args
                heights.append(y * 64 + x)
                w(raw + (y * 64 + x) * 4, bits)
            elif rva == 0x24f6b0:
                for i in range(4096):
                    if (r(cells + i * 48 + 0x20) & 0x70) == 0x20:
                        u.mem_write(cells + i * 48 + 0x2c, b"\1")
            else:
                assert rva in (0x2517a3, 0x25185b, 0x20d4b, 0x25fe70), hex(rva)
            finish(sp, 0, result)

        for at in (callback, image + 0x2ef03c, image + 0x2ef05f):
            u.hook_add(UC_HOOK_CODE, native, begin=at, end=at)
        sp = 0x3000f000
        u.mem_write(sp, struct.pack("<III", stop, state, generator))
        u.reg_write(UC_X86_REG_ESP, sp)
        u.emu_start(dll + exports["generate"], stop, count=30000000)
        assert u.reg_read(UC_X86_REG_EIP) == stop and u.reg_read(UC_X86_REG_ESP) == sp + 4
        assert u.reg_read(UC_X86_REG_EAX) == 1 and r(state + 32) == 0
        assert pond not in paints and r(cells + pond * 48) == variants[4]
        assert pond not in heights and bytes(u.mem_read(raw + pond * 4, 4)) == original_pond
        assert puddle not in paints and puddle not in heights
        assert bytes(u.mem_read(raw + puddle * 4, 4)) == original_puddle
        assert r(cells + puddle * 48 + 0x20) == 0x20 and r(cells + puddle * 48) == variants[5]
        assert dry not in heights and rf(raw + dry * 4) == 0
        assert len(paints) > 100 and len(heights) > 100
        assert all(-1.50001 <= rf(raw + i * 4) + 2 <= -.49999 for i in heights)
        checks += 10
    print("WATER_DEPTH_RUNTIME_PASS", checks, "compiled generator checks at two relocations: native lake/puddle bytes preserved; new shaped sea submerged; painter/height scope")


if __name__ == "__main__":
    main()
