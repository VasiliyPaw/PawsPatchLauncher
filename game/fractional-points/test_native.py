"""Execute actual hooks: ABI, format selection, ASLR and native CRT output."""
import argparse,ctypes,json,struct,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--legacy',type=Path,required=True);ap.add_argument('--native',type=Path,required=True);a=ap.parse_args()
sys.path.insert(0,str(a.legacy/'lobby_colors_1372/deps_r15'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
import build_native as m
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
ks=Ks(KS_ARCH_X86,KS_MODE_32);cases=0
meta=json.loads((a.native/'payload.json').read_text());base=(a.native/'payload.bin').read_bytes()
crt=ctypes.CDLL('msvcrt');fmt=crt._snwprintf;fmt.restype=ctypes.c_int
for image,cave in [(0x460000,0x10000000),(0xe40000,0x21000000),(0x12000000,0x60000000)]:
    code=bytearray(base)
    for off,im,cv in meta['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-0x460000)+cv*(cave-0x10000000))&0xffffffff)
    assert bytes(code)==m.build(ks,image,cave)[0]
    for i,(site,size,old,off) in enumerate(m.SITES):
        for ident in ('kingdom_points_consumed','company_slots_consumed','gold','kingdom_points_consumed_extra','kingdom_points_provided',''):
            u=Uc(UC_ARCH_X86,UC_MODE_32);stack=0x40008000;obj=0x30000000
            for b,n in [(image,0x700000),(cave,4096),(0x40000000,0x10000),(obj,4096)]:u.mem_map(b,n)
            u.mem_write(cave,bytes(code))
            def put(addr,v):u.mem_write(addr,struct.pack('<I',v))
            put(obj+8,obj+0x100);u.mem_write(obj+0x100,(ident+'\0').encode('utf-16le'))
            put(stack+0x18,obj);put(stack+0x20c,obj)
            regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI]
            for j,r in enumerate(regs):u.reg_write(r,0x12340000+j)
            u.reg_write(UC_X86_REG_EBP,stack+0x200);u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_EFLAGS,0x647)
            for j in range(8):u.reg_write(UC_X86_REG_XMM0+j,0xABCD0123456789+j)
            allregs=regs+[UC_X86_REG_EBP,UC_X86_REG_EFLAGS]+[UC_X86_REG_XMM0+j for j in range(8)]
            before=[u.reg_read(r) for r in allregs]
            u.emu_start(cave+off,image+site+size,count=200)
            assert before==[u.reg_read(r) for r in allregs],(i,ident,'register damage')
            end=stack if size==7 else stack-4
            assert u.reg_read(UC_X86_REG_ESP)==end
            ptr=struct.unpack('<I',u.mem_read(end,4))[0]
            assert ptr==(cave+0x880+i*0x40 if ident=='kingdom_points_consumed' else image+old),(i,ident,hex(ptr))
            cases+=1
for x,expected in [(0,'0'),(.5,'0.5'),(.75,'0.75'),(1.5,'1.5'),(19.75,'19.75'),(20,'20'),(99.25,'99.25')]:
    out=ctypes.create_unicode_buffer(128)
    fmt(out,128,ctypes.c_wchar_p('%.7g'),ctypes.c_double(x));assert out.value==expected,(x,out.value);cases+=1
    fmt(out,128,ctypes.c_wchar_p('/%.7g '),ctypes.c_double(x));assert out.value=='/'+expected+' ';cases+=1
    fmt(out,128,ctypes.c_wchar_p('%lc%.7g%s'),ctypes.c_int(0x263A),ctypes.c_double(x),ctypes.c_wchar_p('END'));assert out.value=='☺'+expected+'END';cases+=1
print('FRACTIONAL_NATIVE_PASS',cases,'ABI, ASLR, resource isolation and CRT cases')
