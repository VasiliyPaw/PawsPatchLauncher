"""Execute the actual generated suppression stub: ABI, state and write boundaries."""
import argparse, random, struct, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--stub',type=Path,required=True);p.add_argument('--deps',type=Path,required=True)
    a=p.parse_args();sys.path.insert(0,str(a.deps))
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_WRITE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EFLAGS, UC_X86_REG_EIP
    rng=random.Random(830);code=a.stub.read_bytes();regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
    for i in range(1000):
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        for b in (0x10000000,0x20000000,0x30000000):u.mem_map(b,0x2000)
        u.mem_write(0x10000000,code);stack=0x30001000;signal=0x20000100;end=0x10001000
        count=rng.getrandbits(32);reason=rng.getrandbits(32);flags=2|(rng.getrandbits(12)&0xCD5)
        u.mem_write(signal,struct.pack('<II',count,0));u.mem_write(stack,struct.pack('<II',end,reason))
        initial={r:rng.getrandbits(32) for r in regs}
        for r,v in initial.items():u.reg_write(r,v)
        u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_EFLAGS,flags)
        written=[];u.hook_add(UC_HOOK_MEM_WRITE,lambda _,access,address,size,value,data:written.append((address,size)))
        u.emu_start(0x10000000,end,count=100)
        assert u.reg_read(UC_X86_REG_EIP)==end and u.reg_read(UC_X86_REG_ESP)==stack+8
        assert all(u.reg_read(r)==v for r,v in initial.items()) and u.reg_read(UC_X86_REG_EFLAGS)==flags
        assert bytes(u.mem_read(signal,8))==struct.pack('<II',(count+1)&0xFFFFFFFF,reason)
        assert all(signal<=address and address+size<=signal+8 or stack-36<=address and address+size<=stack for address,size in written)
    print('PURE_SYNC_NATIVE_PASS cases=1000: registers, flags, ret4, counter, argument, write bounds')

if __name__=='__main__':main()
