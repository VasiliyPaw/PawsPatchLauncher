"""Emulate the actual x86 detour and original clamp; never open the live game."""
import argparse, importlib.util, json, struct, sys
from pathlib import Path
sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--fixtures',type=Path);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import *
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
spec=importlib.util.spec_from_file_location('camera_build',Path(__file__).with_name('build_native.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ks=Ks(KS_ARCH_X86,KS_MODE_32)
OBJ=0x30000000;STACK=0x40000000
regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EFLAGS]+[UC_X86_REG_XMM0+i for i in range(8)]
def run(data,request,image,cave,patched,at_continuation=False):
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    for address,size in [(image,0x700000),(cave,0x1000),(OBJ,0x1000),(STACK,0x10000)]:u.mem_map(address,size)
    u.mem_write(image+0x175D20,m.GUARD);u.mem_write(OBJ,bytes(data))
    if patched:
        code=m.build(ks,image,cave)
        compiled=a.native/f'payload-{image:X}-{cave:X}.bin'
        if compiled.exists():assert compiled.read_bytes()==code
        u.mem_write(cave,code)
        u.mem_write(image+m.HOOK,b'\xe9'+struct.pack('<I',(cave-image-m.HOOK-5)&0xffffffff)+b'\x90'*3)
    for i,r in enumerate(regs):u.reg_write(r,(i+1)*123)
    u.reg_write(UC_X86_REG_EDI,OBJ);u.reg_write(UC_X86_REG_EBP,STACK+0x8100);u.reg_write(UC_X86_REG_ESP,STACK+0x8000)
    u.reg_write(UC_X86_REG_EFLAGS,0x246)
    u.reg_write(UC_X86_REG_XMM1,int.from_bytes(struct.pack('<f',request),'little'))
    u.emu_start(image+m.HOOK,image+(m.HOOK+8 if at_continuation else 0x175D70),count=200)
    assert u.reg_read(UC_X86_REG_EIP)==image+(m.HOOK+8 if at_continuation else 0x175D70)
    return bytes(u.mem_read(OBJ,len(data))),[u.reg_read(r) for r in regs],bytes(u.mem_read(STACK+0x8000,0x200))

def put(b,off,v):struct.pack_into('<I',b,off,v & 0xffffffff)
def base(image):
    b=bytearray(1024)
    for off,val in [(0,image+0x4C385C),(0x148,0x3F800000),(0x14C,0x44000000),(0x20C,0x3F000000),(0x210,0x3F9AE148),(0x218,0x41700000)]:put(b,off,val)
    return b
cases=0;excluded=0;captured=0
for image,cave in [(0x460000,0x10000000),(0xE40000,0x21000000),(0x12000000,0x60000000)]:
    candidates=[(base(image),True,'gameplay')]
    for off,values in [(0,[image+0x50C56C,image+0x53BAF4,image+0x4E779C]),(0x20C,[0x3E99999A,0,0x7FC00000]),(0x210,[0x41200000,0x40400000,0x7FC00000]),(0x148,[0,0x3DCCCCCD]),(0x14C,[0,0x45800000,0x7FC00000]),(0x218,[0,0x41F00000])]:
        for value in values:
            b=base(image);put(b,off,value);candidates.append((b,False,f'guard-{off:X}-{value:X}'))
    already=base(image);put(already,0x210,0x40000000);put(already,0x14C,0x44800000);candidates.append((already,True,'already-applied'))
    if a.fixtures:
        for name in ('far-1','near-1','far-2'):
            records=json.loads((a.fixtures/(name+'.json')).read_text())['objects']
            for r in records:
                b=bytearray.fromhex(r['bytes']);v=struct.unpack_from('<I',b)[0]
                put(b,0,v-0xE40000+image)
                accept=all(struct.unpack_from('<I',b,o)[0]==v for o,v in [(0,image+0x4C385C),(0x20C,0x3F000000),(0x210,0x3F9AE148),(0x148,0x3F800000),(0x14C,0x44000000),(0x218,0x41700000)])
                candidates.append((b,accept,name+'-'+str(r['address'])));captured+=1
    for b,accept,name in candidates:
        expected=bytearray(b)
        if accept:put(expected,0x210,0x40000000);put(expected,0x14C,0x44800000)
        else:excluded+=1
        for request in (0.1,0.5,0.8,1.21,1.5,2.5,3.0,10.0):
            actual=run(b,request,image,cave,True)
            reference=run(expected,request,image,cave,False)
            assert actual==reference,(hex(image),name,request,'native state differs')
            cases+=1
        # At the continuation even flags and all non-original SSE state agree.
        assert run(b,2.5,image,cave,True,True)==run(expected,2.5,image,cave,False,True)
report=dict(passed=True,emulatedClampCases=cases,excludedCameras=excluded,capturedCameraRecords=captured,relocationBases=3,maximum=2.0,gameLaunched=False,liveMemoryRead=False,liveMemoryWritten=False)
(a.native/'test-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
