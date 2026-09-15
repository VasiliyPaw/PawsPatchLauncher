"""Execute the scoped dropdown rectangle hook at two ASLR layouts."""
import argparse, json, struct, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy/'pydeps_r3'));sys.path.insert(0,str(a.legacy/'deps_r15'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
m=json.loads((a.candidate/'manifest.json').read_text());raw=(a.candidate/'payload.bin').read_bytes();rel=(a.candidate/'fixups.bin').read_bytes();count=0
def check(ok):
    global count
    count+=1;assert ok,count
for game,cave in ((0x460000,0x10000000),(0x6a0000,0x19000000)):
    for slot in (-1,0,31,63):
        for width in (20.0,160.0,310.0):
            u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(cave,m['size']);u.mem_map(game,0x700000);u.mem_map(0x20000000,0x10000)
            b=bytearray(raw)
            for i in range(struct.unpack_from('<I',rel)[0]):
                k,o,v=struct.unpack_from('<III',rel,4+12*i)
                struct.pack_into('<I',b,o,(game+v if k==1 else cave+v if k==2 else game+v-(cave+o+4))&0xffffffff)
            u.mem_write(cave,bytes(b));rect=0x20002000;stack=0x20008000;widget=0x20004000
            before=struct.pack('<ffff',27.0,49.0,width,360.0);u.mem_write(rect,before)
            if slot>=0:u.mem_write(cave+0x2000+slot*32,struct.pack('<II',0x20005000,widget))
            u.mem_write(stack,struct.pack('<III',0x20009000,rect,0x200))
            regs={UC_X86_REG_EAX:rect,UC_X86_REG_EBX:123,UC_X86_REG_ECX:0x20006000,UC_X86_REG_EDX:456,UC_X86_REG_ESI:widget,UC_X86_REG_EDI:789,UC_X86_REG_EBP:0x20007000,UC_X86_REG_ESP:stack,UC_X86_REG_EFLAGS:0x246}
            for r,v in regs.items():u.reg_write(r,v)
            calls=[]
            def stop(emu,addr,size,data):
                if addr==game+0x70cab3-0x460000:calls.append(addr);emu.emu_stop()
            u.hook_add(UC_HOOK_CODE,stop);u.emu_start(cave+m['functions']['popup_rect_hook'],0,count=1000)
            check(len(calls)==1)
            check(all(u.reg_read(r)==v for r,v in regs.items()))
            check(bytes(u.mem_read(stack,12))==struct.pack('<III',0x20009000,rect,0x200))
            check(bytes(u.mem_read(rect,16))==struct.pack('<ffff',27.0,49.0,200.0 if slot>=0 else width,360.0))
result={'passed':True,'assertions':count,'payload_sha256':m['payload_sha256'],'stock_dropdown_unchanged':True,'registers_and_stack_preserved':True}
(a.candidate/'popup-width-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
