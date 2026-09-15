"""Exercise actual emitted preference/save hooks at three relocated bases."""
import argparse,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/deps_r15'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
checks=0
def check(value,reason):
    global checks
    assert value,reason
    checks+=1
for game,cave in [(0x460000,0x10000000),(0x650000,0x21000000),(0x12000000,0x60000000)]:
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(game,0x700000);u.mem_map(cave,0x46000);u.mem_map(0x30000000,0x20000)
    data=bytearray((a.native/'AssistantPayload.bin').read_bytes());fix=(a.native/'AssistantFixups.bin').read_bytes()
    for i in range(struct.unpack_from('<I',fix)[0]):
        k,o,v=struct.unpack_from('<III',fix,4+i*12)
        struct.pack_into('<I',data,o,((game+v) if k==1 else cave+v if k==2 else game+v-cave-o-4)&0xffffffff)
    u.mem_write(cave,bytes(data))
    def w(addr,v):u.mem_write(addr,struct.pack('<I',v&0xffffffff))
    def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    def f(addr,v):u.mem_write(addr,struct.pack('<f',v))
    def text(addr):return bytes(u.mem_read(addr,1024)).decode('utf-16le').split('\0')[0]
    world,session,name,task=0x30001000,0x30003000,0x30004100,0x30005000
    toggle,numeric=0x30006000,0x30007000
    w(game+0x5f3fb8,world);w(game+0x5f3fe4,session);w(game+0x5f9218,2);w(session+0x64,2);w(session+0x68,name)
    def source(value):w(name-12,len(value));u.mem_write(name,(value+'\0').encode('utf-16le'))
    source('Save/ПРОДОЛЖИТЬ.RSG');f(world+0xe8,123)
    # Actual native Check/Uncheck preserve their bit semantics. Render and
    # resource-manager completion calls use narrow ABI stubs, no live I/O.
    raw=(a.legacy.parent/'k2_runtime_1372_20260904.bin').read_bytes()
    for start,end in [(0x7186b6,0x7187e3)]:u.mem_write(game+start-0x460000,raw[start-0x460000:end-0x460000])
    native={game+0x205de:'string',game+0x21375:'free',game+0x2a4ea1:'render',game+0x1ce720:'complete'}
    seen=[]
    def hook(uc,addr,size,_):
        if addr not in native:return
        action=native[addr];sp=uc.reg_read(UC_X86_REG_ESP);ecx=uc.reg_read(UC_X86_REG_ECX);clean=0
        if action=='string':w(ecx,r(sp+4));clean=4
        elif action=='render':seen.append(('render',ecx));clean=4
        elif action=='complete':seen.append(('complete',ecx,r(sp+4)));clean=4
        uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+clean)
    u.hook_add(UC_HOOK_CODE,hook)
    def run(off,arg=None):
        sp=0x3001f000;end=0x30000000
        w(sp,end if arg is None else arg)
        if arg is not None:end=game+0x1c19fe
        for reg,val in [(UC_X86_REG_ESP,sp),(UC_X86_REG_EAX,45),(UC_X86_REG_ECX,task),(UC_X86_REG_EDX,99),
                        (UC_X86_REG_EBX,123),(UC_X86_REG_ESI,task),(UC_X86_REG_EDI,789),(UC_X86_REG_EBP,888)]:u.reg_write(reg,val)
        u.emu_start(cave+off,end,count=20000)
        check(u.reg_read(UC_X86_REG_ESP)==sp+4,'stack preserved')
        check([u.reg_read(reg) for reg in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]==[123,task,789,888],'nonvolatile registers preserved')
    run(0x1a00)
    check(r(cave+0x1b0)==2 and r(cave+0xb8)==0,'world boundary blocks until restored')
    check(r(cave+0x1b8)==2 and text(cave+0x1f000)=='Save/ПРОДОЛЖИТЬ.RSG','exact selected source copied')
    f(world+0xe8,130);run(0x1a00);check(r(cave+0x1b0)==2,'normal time advance does not reset')
    w(cave+0x40,0);w(cave+0x44,333);w(cave+0x1b4,2);w(cave+0xb8,1)
    w(cave+0x4c,toggle);w(toggle+0x24,0x80);w(cave+0x50,numeric);w(numeric+0x6c,numeric+0x100)
    f(cave+0x1b004,17);run(0x1a00)
    check(r(cave+0x40)==0 and not r(toggle+0x24)&0x80 and r(cave+0x44)==333,'loaded OFF/reserve displayed')
    check(r(cave+0x7c)==0 and r(cave+0x58)==1,'pending render completed')
    for enabled in (1,0,1):
        w(cave+0x40,enabled);run(0x30600);run(0x30600)
        check(bool(r(toggle+0x24)&0x80)==bool(enabled) and r(cave+0x44)==333,'reopening panel retains settings')
    # Successful save captures its owning generation and committed settings.
    source('Save/New name.RSG');w(task+0x20,name)
    for i,val in enumerate([1.,2.,3.,4.]):f(cave+0x1b004+i*4,val)
    for serial in range(1,21):
        run(0x30900,2);slot=cave+0x41000+(serial&15)*0x500
        check(r(cave+0x1c0)==serial and r(slot)==serial and r(slot+4)==2,'save ring publishes exact serial and party')
        check(text(slot+16)=='Save/New name.RSG' and r(slot+0x414)==333,'save path and reserve captured')
        check(struct.unpack('<4f',u.mem_read(slot+0x418,16))==(1,2,3,4),'save floors captured')
        check(seen[-1]==('complete',task,2),'original successful completion preserved')
    run(0x30900,3);check(r(cave+0x1c0)==20 and seen[-1]==('complete',task,3),'failed save is not bound')
    w(cave+0xb8,0);run(0x30900,2);check(r(cave+0x1c0)==20,'unresolved party is never attributed')
    w(cave+0xb8,1);w(cave+0x1b4,1);run(0x30900,2);check(r(cave+0x1c0)==20,'stale generation rejected')
    # Rewind, and menu->new game with same world pointer/time, both publish.
    f(world+0xe8,120);run(0x1a00);check(r(cave+0x1b0)==4 and r(cave+0xb8)==0,'loading earlier save invalidates readiness')
    w(game+0x5f9218,0);run(0x1a00);check(r(cave+0x74)==0,'menu forgets world address')
    w(game+0x5f9218,2);w(session+0x64,0);run(0x1a00)
    check(r(cave+0x1b0)==6 and r(cave+0x1b8)==0,'new match identified separately from saved source')
    # Invalid length is ignored, never truncated into another real filename.
    w(name-12,512);w(game+0x5f9218,0);run(0x1a00);w(game+0x5f9218,2);run(0x1a00)
    check(text(cave+0x1f000)=='','oversized source rejected')
print('CITY_PREFERENCES_NATIVE_PASS',checks,'checks; no game launched')
