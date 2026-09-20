"""Run the game's morale decision verbatim and compare the isolated Exhausted hook."""
import argparse, importlib.util, json, struct, sys
from pathlib import Path
sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_PROT_READ,UC_PROT_EXEC
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
spec=importlib.util.spec_from_file_location('exhaustion_build',Path(__file__).with_name('build_native.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ks=Ks(KS_ARCH_X86,KS_MODE_32);raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
OBJ=0x30000000;ORG=OBJ+0x1000;AI=OBJ+0x2000;STACK=0x40000000
regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EFLAGS]+[UC_X86_REG_XMM0+i for i in range(8)]

def run(image,cave,case):
    name,cur,maximum,threshold,expected,option=case
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    for addr,size in [(image,0x700000),(cave,0x2000),(OBJ,0x4000),(STACK,0x10000)]:u.mem_map(addr,size)
    def put(addr,value):u.mem_write(addr,struct.pack('<I',value&0xffffffff))
    def fput(addr,value):u.mem_write(addr,struct.pack('<f',value))
    def get(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    code=m.build(ks,image,cave);u.mem_write(cave,code);u.mem_protect(cave,0x1000,UC_PROT_READ|UC_PROT_EXEC)
    assert (a.native/f'payload-{image:X}-{cave:X}.bin').read_bytes()==code,'C# relocation differs'
    u.mem_write(image+m.DECISION,raw[m.DECISION:m.DECISION+len(m.DECISION_GUARD)])
    u.mem_write(image+m.HOOK-3,raw[m.HOOK-3:m.HOOK+26])
    u.mem_write(image+m.HOOK,b'\xe8'+struct.pack('<I',(cave-image-m.HOOK-5)&0xffffffff))
    put(ORG+4,OBJ);put(OBJ+0x7c,ORG);put(OBJ+0x70,AI)
    put(AI,image+0x500000);put(image+0x50005c,image+0x1000)
    # The native nonzero-morale branch queries CAI. Only that external virtual
    # query is modeled; both of its possible results are covered below.
    u.mem_write(image+0x1000,b'\xb0'+bytes([1 if option=='query-true' else 0])+b'\xc3')
    if option=='command28':put(AI+0x28,1)
    if option=='command2c':put(AI+0x2c,1)
    fput(ORG+0x5c,cur);fput(ORG+0x60,maximum);fput(ORG+0xb8,threshold)
    before_world=bytes(u.mem_read(OBJ,0x4000));calls=[]
    u.hook_add(UC_HOOK_CODE,lambda uc,addr,size,data:calls.append(addr) if addr==image+m.DECISION else None)
    for i,r in enumerate(regs):u.reg_write(r,(i+1)*123)
    u.reg_write(UC_X86_REG_ECX,ORG);u.reg_write(UC_X86_REG_ESP,STACK+0x8000);u.reg_write(UC_X86_REG_EFLAGS,0x246)
    init=bytes(ks.asm('fld1; fldpi',image+0x100)[0]);u.mem_write(image+0x100,init);u.emu_start(image+0x100,image+0x100+len(init))
    start=[u.reg_read(r) for r in regs]
    put(STACK+0x7ffc,image+m.HOOK+5);u.reg_write(UC_X86_REG_ESP,STACK+0x7ffc)
    u.emu_start(image+m.DECISION,image+m.HOOK+5,count=200)
    reference=[u.reg_read(r) for r in regs]+[u.reg_read(UC_X86_REG_ST0),u.reg_read(UC_X86_REG_ST1)]
    for reg,value in zip(regs,start):u.reg_write(reg,value)
    u.emu_start(image+m.HOOK,image+m.HOOK+5,count=1000)
    assert u.reg_read(UC_X86_REG_EIP)==image+m.HOOK+5,(name,'did not return')
    actual=[u.reg_read(r) for r in regs]+[u.reg_read(UC_X86_REG_ST0),u.reg_read(UC_X86_REG_ST1)]
    assert actual[1:]==reference[1:],(name,'non-return registers changed')
    assert len(calls)==2,(name,'original decision not called exactly once per invocation')
    assert actual[0]==(2 if expected else reference[0]),(name,actual[0],reference[0])
    if expected:assert reference[0] in (0,1),(name,'fixture no longer reproduces blocked native exit')
    assert get(cave+0x1000)==1 and get(cave+0x1004)==int(expected),(name,'counters')
    assert bytes(u.mem_read(OBJ,0x4000))==before_world,(name,'morale/order/actor writes')
    # The caller's real CMP/Jcc still chooses its own native state transition.
    # Set ESI to a mapped state fixture, execute MOV/POP/CMP/JE only.
    u.reg_write(UC_X86_REG_ESI,OBJ+0x3000);put(STACK+0x8000,0x1234)
    u.emu_start(image+m.HOOK+5,image+0x27792a,count=4)
    expected_ip=image+0x27792a if actual[0]==2 else image+0x274a2c
    assert u.reg_read(UC_X86_REG_EIP)==expected_ip,(name,'native Exhausted transition differed')

N=float('nan');I=float('inf')
cases=[
 ('observed-deadland-full',16,16,20,True,''),
 ('deadland-full-query-true',16,16,20,True,'query-true'),
 ('deadland-partial-query-true',15.999,16,20,False,'query-true'),
 ('observed-deadland-partial',15.999,16,20,False,''),
 ('observed-before-recovery',2.5,16,20,False,''),
 ('cap-at-threshold-full',20,20,20,True,''),
 ('cap-at-threshold-partial',19.999,20,20,False,''),
 ('tiny-positive-cap',0.125,0.125,20,True,''),
 ('over-cap-finite',17,16,20,True,''),
 ('normal-at-threshold',20,48,20,False,''),
 ('normal-observed-exit',20.125,48,20,False,''),
 ('normal-full',48,48,20,False,''),
 ('normal-partial',16,48,20,False,''),
 ('cap-zero',0,0,20,False,''),('cap-negative',1,-16,20,False,''),
 ('threshold-zero',16,16,0,False,''),('threshold-negative',16,16,-1,False,''),
 ('negative-morale',-1,16,20,False,''),
 ('zero-morale-false',0,16,20,False,''),('zero-morale-true',0,16,20,False,'query-true'),
 ('native-command28',16,16,20,False,'command28'),('native-command2c',16,16,20,False,'command2c'),
 ('nan-current',N,16,20,False,''),('nan-cap',16,N,20,False,''),('nan-threshold',16,16,N,False,''),
 ('inf-current',I,16,20,False,''),('inf-cap',16,I,20,False,''),('inf-threshold',16,16,I,False,''),
 ('negative-inf-current',-I,16,20,False,''),('negative-zero',-0.,16,20,False,''),
]
count=0
for image,cave in [(0x460000,0x10000000),(0xE40000,0x21000000),(0x12000000,0x60000000)]:
    for case in cases:run(image,cave,case);count+=1
report=dict(passed=True,cases=count,relocationBases=3,nativeMoraleDecision=True,nativeExhaustedExitBranch=True,worldWrites=False,gameLaunched=False)
(a.native/'test-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
