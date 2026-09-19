"""Execute the actual recovery stub; model allocation but use native list insertion."""
import argparse, importlib.util, json, math, struct, sys
from pathlib import Path
sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_PROT_READ,UC_PROT_EXEC
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
spec=importlib.util.spec_from_file_location('company_build',Path(__file__).with_name('build_native.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ks=Ks(KS_ARCH_X86,KS_MODE_32);raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
OBJ=0x30000000;ORG=OBJ+0x1000;NODES=OBJ+0x2000;NEW=NODES+0xE00;STACK=0x40000000
regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EFLAGS]+[UC_X86_REG_XMM0+i for i in range(8)]
cases=0
def run(image,cave,case):
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    for addr,size in [(image,0x700000),(cave,0x2000),(OBJ,0x4000),(STACK,0x10000)]:u.mem_map(addr,size)
    def put(addr,value):u.mem_write(addr,struct.pack('<I',value&0xffffffff))
    def fput(addr,value):u.mem_write(addr,struct.pack('<f',value))
    def get(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    code=m.build(ks,image,cave);u.mem_write(cave,code);u.mem_protect(cave,0x1000,UC_PROT_READ|UC_PROT_EXEC)
    compiled=a.native/f'payload-{image:X}-{cave:X}.bin'
    assert compiled.exists() and compiled.read_bytes()==code,'C# relocations differ'
    u.mem_write(image+m.HOOK,b'\xe8'+struct.pack('<I',(cave-image-m.HOOK-5)&0xffffffff))
    u.mem_write(image+0x2148d3,raw[0x2148d3:0x214903])
    u.mem_write(image+0x2925e6,raw[0x2925e6:0x29260d])
    # Only the allocator/world scheduler is modeled. The game's own linked-list
    # insertion runs verbatim, including back-links and insertion at the head.
    scheduler=bytes(ks.asm(f'push {NEW}; call {image+0x2925e6}; mov eax,0xdeadbeef; mov edx,0x12345678; xorps xmm0,xmm0; ret 4',image+0x2922ed)[0])
    u.mem_write(image+0x2922ed,scheduler)
    put(ORG,image+0x4e1ae0);put(ORG+4,OBJ);put(OBJ+0x7c,ORG);put(OBJ+0x70,OBJ+0x3000);put(OBJ+0x14,47618)
    put(OBJ+0x3000,image+0x500000);put(image+0x500064,image+0x1000);put(image+0x500080,image+0x1010)
    u.mem_write(image+0x1000,b'\xb0'+bytes([0 if case=='native-blocked' else 1])+b'\xc3');u.mem_write(image+0x1010,b'\x30\xc0\xc3')
    put(ORG+0x40,OBJ+0x3100);put(ORG+0x44,0 if case=='dead-hero' else OBJ+0x3200)
    for addr,val in [(OBJ+0x20,337.16796875),(OBJ+0x24,795.546875),(ORG+0xbc,254.328125),(ORG+0xc0,643.5859375)]:fput(addr,val)
    # Existing periodic event; adjacent GLOBAL event is deliberately unrelated.
    put(ORG+0xc,NODES);put(NODES,ORG+8);put(NODES+8,NODES+0x400);put(NODES+0xc,ORG+0xc);put(NODES+0x18,1)
    put(NODES+0x400,ORG+0x500);put(NODES+0x414,1)
    put(NEW,ORG+8);put(NEW+0x14,1)
    expect=case in ('missing','dead-hero','different-hero','no-events','y-only','negative-zero','attack','retreat','sleep')
    if case=='no-events':put(ORG+0xc,0)
    if case=='different-hero':fput(OBJ+0x3220,999);fput(OBJ+0x3224,111)
    if case in ('attack','retreat','sleep'):put(OBJ+0x3004,{'attack':10,'retreat':20,'sleep':30}[case])
    if case in ('equal','signed-zero'):
        fput(OBJ+0x20,0.0 if case=='signed-zero' else 254.328125);fput(ORG+0xbc,-0.0 if case=='signed-zero' else 254.328125);fput(OBJ+0x24,643.5859375)
    if case=='y-only':fput(OBJ+0x20,254.328125)
    if case=='negative-zero':fput(OBJ+0x20,0);fput(ORG+0xbc,-0.0)
    if case=='destroyed':put(OBJ+8,1)
    if case=='no-ai':put(OBJ+0x70,0)
    if case=='wrong-org':put(ORG,image+0x4e1ae4)
    if case=='wrong-backlink':put(OBJ+0x7c,ORG+4)
    if case=='no-actor':put(ORG+4,0)
    if case=='foreign-owner':put(NODES,ORG+0x500)
    if case=='cycle':put(NODES+0x10,NODES)
    if case.startswith('nan-'):fput({'nan-x':OBJ+0x20,'nan-y':OBJ+0x24,'nan-tx':ORG+0xbc,'nan-ty':ORG+0xc0}[case],float('nan'))
    if case=='infinite':fput(ORG+0xbc,float('inf'))
    if case.startswith('active-'):
        nodes=[NODES+i*0x20 for i in range(3)]
        for i,node in enumerate(nodes):
            put(node,ORG+8);put(node+0x10,nodes[i+1] if i<2 else 0);put(node+0x14,0);put(node+0x18,1)
        active=nodes[int(case[-1])];put(active+0x14,1);put(active+0x18,0)
    original=bytes(u.mem_read(OBJ,0x4000));scheduled=[]
    def trace(uc,addr,size,unused):
        if addr==image+0x2922ed:
            assert uc.reg_read(UC_X86_REG_ECX)==ORG+8
            assert get(uc.reg_read(UC_X86_REG_ESP)+4)==1
            scheduled.append(True)
    u.hook_add(UC_HOOK_CODE,trace)
    def invoke():
        for i,r in enumerate(regs):u.reg_write(r,(i+1)*123)
        u.reg_write(UC_X86_REG_ECX,ORG);u.reg_write(UC_X86_REG_ESP,STACK+0x8000);u.reg_write(UC_X86_REG_EFLAGS,0x246)
        # Seed x87 as well as all SSE registers; confirm FXSAVE restoration.
        init=bytes(ks.asm('fld1; fldpi',image+0x100)[0]);u.mem_write(image+0x100,init);u.emu_start(image+0x100,image+0x100+len(init))
        before=[u.reg_read(r) for r in regs]
        put(STACK+0x7ffc,image+m.HOOK+5);u.reg_write(UC_X86_REG_ESP,STACK+0x7ffc)
        u.emu_start(image+0x2148d3,image+m.HOOK+5,count=100)
        reference=[u.reg_read(r) for r in regs]+[u.reg_read(UC_X86_REG_ST0),u.reg_read(UC_X86_REG_ST1)]
        for reg,value in zip(regs,before):u.reg_write(reg,value)
        u.emu_start(image+m.HOOK,image+m.HOOK+5,count=3000)
        assert u.reg_read(UC_X86_REG_EIP)==image+m.HOOK+5,'failed to return to original caller'
        after=[u.reg_read(r) for r in regs]+[u.reg_read(UC_X86_REG_ST0),u.reg_read(UC_X86_REG_ST1)]
        assert reference==after,(case,'register state changed')
    invoke()
    assert len(scheduled)==int(expect),(case,len(scheduled),expect)
    after=bytearray(u.mem_read(OBJ,0x4000));expected=bytearray(original)
    if expect:
        def ep(addr,val):struct.pack_into('<I',expected,addr-OBJ,val)
        old=struct.unpack_from('<I',original,ORG+0xc-OBJ)[0]
        ep(ORG+0xc,NEW);ep(NEW+0xc,ORG+0xc);ep(NEW+0x10,old)
        if old:ep(old+0xc,NEW+0x10)
    assert after==expected,(case,'unexpected actor/org/order/formation write')
    invoke();assert len(scheduled)==int(expect),(case,'duplicate event')
    assert get(cave+0x1000)==2 and get(cave+0x1004)==int(expect)

names=['native-blocked','missing','dead-hero','different-hero','no-events','y-only','negative-zero','attack','retreat','sleep','equal','signed-zero','destroyed','no-ai','wrong-org','wrong-backlink','foreign-owner','cycle','nan-x','nan-y','nan-tx','nan-ty','infinite','active-0','active-1','active-2']
for image,cave in [(0x460000,0x10000000),(0xE40000,0x21000000),(0x12000000,0x60000000)]:
    for case in names:run(image,cave,case);cases+=1
report=dict(passed=True,cases=cases,invocations=cases*2,relocationBases=3,codePage='RX',dataPage='RW',nativeInsertion=True,worldScheduler='modeled',gameLaunched=False)
(a.native/'test-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
