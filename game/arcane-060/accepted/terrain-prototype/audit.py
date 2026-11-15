"""Read-only native inspection for the local terrain feasibility experiment."""
import argparse
import hashlib
import re
import struct
import sys
from pathlib import Path

LEGACY = Path(r'G:\CodexData\projects\Codex\2026-08-11\kohan-ii-d-steamlibrary-steamapps-common\work')
sys.path[:0] = [str(LEGACY / 'pydeps_readable'), str(LEGACY / 'lobby_colors_1372/deps_r15')]
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'deps'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x460000
RAW = (LEGACY / 'k2_runtime_1372_20260904.bin').read_bytes()
assert hashlib.sha256(RAW).hexdigest() == 'b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
MD = Cs(CS_ARCH_X86, CS_MODE_32)

def u32(va):
    return struct.unpack_from('<I', RAW, va - BASE)[0]

def refs(va):
    return [BASE + m.start() for m in re.finditer(re.escape(struct.pack('<I', va)), RAW)]

def disasm(va, size=1024):
    for ins in MD.disasm(RAW[va - BASE:va - BASE + size], va):
        print(f'{ins.address:08X} {ins.mnemonic} {ins.op_str}')
        if ins.mnemonic == 'ret':
            break

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['disasm', 'refs', 'calls'])
    p.add_argument('address', type=lambda s: int(s, 16))
    p.add_argument('--size', type=int, default=1024)
    a = p.parse_args()
    if a.action == 'disasm':
        disasm(a.address, a.size)
    elif a.action == 'refs':
        print(' '.join(f'{x:08X}' for x in refs(a.address)))
    else:
        for m in re.finditer(b'\xe8', RAW[:0x44d000]):
            at = m.start()
            if BASE + at + 5 + struct.unpack_from('<i', RAW, at + 1)[0] == a.address:
                print(f'{BASE+at:08X}')
