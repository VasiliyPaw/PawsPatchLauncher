"""Execute emitted x86 wrappers. Native disk IO and ring destruction are explicit
stubs: these tests prove ABI, first-error retention and rearming, not live disk IO.
"""
import argparse, json, random, struct, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--fixtures', type=Path, required=True)
p.add_argument('--deps', type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.deps))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import *

rng = random.Random(925)
checks = 0
def check(ok, why):
    global checks
    checks += 1
    assert ok, why
def pack(n): return struct.pack('<I', n & 0xffffffff)
regs = [UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
        UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP]

for case in sorted(a.fixtures.glob('case*.txt')):
    image, code, signal = map(int, case.read_text().split())
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    for base, size in [(image, 0x700000), (code, 0x2000), (signal & ~0xfff, 0x2000),
                       (0x40000000, 0x20000), (0x50000000, 0x20000)]: u.mem_map(base, size)
    world, network, film = 0x50000000, 0x50001000, 0x50002000
    stack, end, scratch = 0x40018000, code + 0x1000, 0x50004000
    failure, reset = image + 0x14a5f2, image + 0x16dfca
    original_calls, reset_calls, writes = [], [], []
    def w(at, n): u.mem_write(at, pack(n))
    def rd(at): return struct.unpack('<I', u.mem_read(at, 4))[0]
    u.mem_write(code, case.with_suffix('.bin').read_bytes())
    u.mem_write(signal, (a.fixtures / 'initial.bin').read_bytes())
    w(image + 0x5f3fb8, world); w(image + 0x5f3ff0, network)
    w(world + 0xe8, 0x43049fff)
    w(network + 0x10, 1); w(network + 0x14, 304230); w(network + 8, 0x12345678)
    # The displaced reset instructions plus its actual native body execute.
    # Its two ring-container services below are bounded fakes (no native heap).
    body = bytearray((a.fixtures / 'reset-original.bin').read_bytes())
    u.mem_write(reset, bytes(body))
    u.mem_write(failure, b'\xe9' + pack(code - failure - 5))
    u.mem_write(reset, b'\xe9' + pack(code + 0x200 - reset - 5))
    w(scratch + 0x800, 0x1f80)
    # Native writer surrogate deliberately damages volatile integer/FP state.
    # The hook verifies the original this/argument/SEH descriptor before it runs.
    surrogate = bytes.fromhex('DBE3D9EE0FAE15') + pack(scratch + 0x800)
    surrogate += bytes.fromhex('B811111111B922222222BA333333330F57C00F57C1F9C20400')
    u.mem_write(failure + 5, surrogate)
    u.mem_write(image + 0x16ea3b, b'\xc3')
    u.mem_write(image + 0x16eb27, b'\xc2\x04\x00')
    def hook(uc, address, size, data):
        sp = uc.reg_read(UC_X86_REG_ESP)
        if address == failure + 5:
            original_calls.append((uc.reg_read(UC_X86_REG_ECX), rd(sp + 4)))
            check(uc.reg_read(UC_X86_REG_EAX) == image + 0x42ee6a, 'SEH relocation')
            check(not (uc.reg_read(UC_X86_REG_EFLAGS) & 0x400), 'DF clear for native writer')
        elif address == image + 0x16ea3b:
            reset_calls.append(('clear', uc.reg_read(UC_X86_REG_ECX)))
        elif address == image + 0x16eb27:
            reset_calls.append(('baseline', uc.reg_read(UC_X86_REG_ECX), rd(sp + 4)))
    u.hook_add(UC_HOOK_CODE, hook)
    u.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, at, size, val, data: writes.append((at, size)))
    def fxstate():
        u.mem_write(code + 0x1100, bytes.fromhex('0FAE05') + pack(scratch))
        u.emu_start(code + 0x1100, code + 0x1107, count=2)
        return bytes(u.mem_read(scratch, 512))
    # Seed non-default x87 and all SSE registers, including a non-default MXCSR.
    u.mem_write(code + 0x1200, bytes.fromhex('DBE3D9EBD9E8'))
    u.emu_start(code + 0x1200, code + 0x1206, count=5)
    u.reg_write(UC_X86_REG_MXCSR, 0x3f80)
    for r in range(UC_X86_REG_XMM0, UC_X86_REG_XMM7 + 1): u.reg_write(r, rng.getrandbits(128))
    def fail(index, expected_calls, label):
        before = fxstate()
        values = {r: rng.getrandbits(32) for r in regs}
        flags = 2 | (rng.getrandbits(12) & 0xcd5)
        sp = stack - 4 * rng.randrange(4)  # all stack alignments
        for r, val in values.items(): u.reg_write(r, val)
        u.reg_write(UC_X86_REG_ESP, sp); u.reg_write(UC_X86_REG_EFLAGS, flags)
        u.mem_write(sp, pack(end) + pack(index)); writes.clear()
        u.emu_start(failure, end, count=2000)
        check(u.reg_read(UC_X86_REG_EIP) == end and u.reg_read(UC_X86_REG_ESP) == sp + 8, label + ' ret4')
        check(all(u.reg_read(r) == val for r, val in values.items()), label + ' integer state')
        check(u.reg_read(UC_X86_REG_EFLAGS) == flags, label + ' flags')
        check(rd(signal + 4) == index, label + ' last index')
        check(len(original_calls) == expected_calls, label + ' first writer only')
        if original_calls and expected_calls != rd(signal + 20): raise AssertionError('return count')
        check(all(signal <= at and at + size <= signal + 64 or sp - 4096 <= at and at + size <= sp
                  for at, size in writes), label + ' no writes into world/synchronizer/code')
        after = fxstate()
        # Unicorn's FXRSTOR leaves the last x87 instruction address unchanged.
        # Check every other saved byte (values, control/status/tag, MXCSR, XMM).
        check(after[:8] + after[12:] == before[:8] + before[12:], label + ' x87/SSE/MXCSR')
        if rd(signal + 24) == index:
            check(original_calls[-1] == (values[UC_X86_REG_ECX], index), label + ' original this/argument')
    fail(304230, 1, 'first')
    check(rd(signal + 32) == 1 and rd(signal + 36) == 304230 and rd(signal + 40) == 0x12345678,
          'ring metadata records index ahead of local ring without dereferencing it')
    check(rd(signal + 28) == world and rd(signal + 44) == 0x43049fff, 'world/time metadata')
    first = bytes(u.mem_read(signal + 24, 24))
    for i in range(1000): fail(304231 + i, 1, 'repeat')
    check(rd(signal) == 1001 and bytes(u.mem_read(signal + 24, 24)) == first, 'first evidence retained')
    def reset_baseline(this, baseline, checksum):
        u.reg_write(UC_X86_REG_ECX, this); u.reg_write(UC_X86_REG_ESI, 0xdeadbeef)
        u.reg_write(UC_X86_REG_ESP, stack)
        u.mem_write(stack, pack(end) + pack(baseline) + pack(checksum))
        u.emu_start(reset, end, count=200)
        check(u.reg_read(UC_X86_REG_EIP) == end and u.reg_read(UC_X86_REG_ESP) == stack + 12, 'reset ret8')
        check(u.reg_read(UC_X86_REG_ESI) == 0xdeadbeef and rd(this + 8) == checksum, 'native reset preserved')
        check(bytes(u.mem_read(this, 2)) == b'\x01\x01', 'native enables preserved')
        check(reset_calls[-2:] == [('clear', this + 0x10), ('baseline', this + 0x10, (baseline + 1) & 0xffffffff)], 'native ring calls preserved')
    reset_baseline(film, 100, 99)
    check(rd(signal + 8) == 1 and rd(signal + 12) == 1, 'film does not rearm network capture')
    fail(400000, 1, 'after film reset')
    reset_baseline(network, 0, 0)
    check(rd(signal + 8) == 2 and rd(signal + 12) == 0, 'new session rearmed at same world address')
    fail(42, 2, 'new match')
    reset_baseline(network, 89000, 0xdeadf00d)
    fail(89005, 3, 'save restore')
    check(rd(signal + 40) == 0xdeadf00d, 'save baseline recorded')
    # Null metadata never carries a previous match's stale values.
    reset_baseline(network, 0, 0)
    w(image + 0x5f3fb8, 0); w(image + 0x5f3ff0, 0)
    fail(7, 4, 'null metadata')
    check(bytes(u.mem_read(signal + 28, 20)) == bytes(20), 'missing metadata cleared')
    w(image + 0x5f3ff0, network); w(signal + 8, 0xffffffff)
    reset_baseline(network, 0, 0)
    check(rd(signal + 8) == 1, 'epoch zero reserved on rollover')
    fail(8, 5, 'epoch rollover')
    # A nested failure during an active capture cannot enter the writer again.
    reset_baseline(network, 0, 0)
    w(signal + 12, rd(signal + 8))
    fail(9, 5, 'claimed/in-progress')
    w(signal, 0xffffffff); fail(10, 5, 'counter rollover')
    check(rd(signal) == 0, 'old 32-bit counter ABI preserved')

result = dict(passed=True, checks=checks, relocations=3, nativeWriter='explicit stub',
              nativeReset='original instructions with stubbed ring-container services')
(a.fixtures / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print('SYNC_DIAGNOSTICS_NATIVE_PASS', json.dumps(result))
