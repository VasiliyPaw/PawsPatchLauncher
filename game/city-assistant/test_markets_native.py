"""Execute market branch selection and capture of native shortage purchase costs."""
import argparse, hashlib, struct, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/deps_r15'))
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/pydeps_r3'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
raw=(a.legacy.parent/'k2_runtime_1372_20260904.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
# Engine's actual shortage-cost lookup/multiplication (definition +1c vector).
assert raw[0x239420:0x23942a]==bytes.fromhex('8b521c7414f30f590c8a')
checks=0
for game,cave in [(0x460000,0x10000000),(0x650000,0x21000000),(0x12000000,0x60000000)]:
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(game,0x700000);u.mem_map(cave,0x46000);u.mem_map(0x30000000,0x40000)
    payload=bytearray((a.native/'AssistantPayload.bin').read_bytes());fix=(a.native/'AssistantFixups.bin').read_bytes()
    for i in range(struct.unpack_from('<I',fix)[0]):
        k,o,v=struct.unpack_from('<III',fix,4+i*12)
        struct.pack_into('<I',payload,o,((game+v) if k==1 else cave+v if k==2 else game+v-cave-o-4)&0xffffffff)
    u.mem_write(cave,bytes(payload));ks=Ks(KS_ARCH_X86,KS_MODE_32)
    def w(addr,v):u.mem_write(addr,struct.pack('<I',v))
    def f(addr,v):u.mem_write(addr,struct.pack('<f',v))
    def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    def stub(addr,src):
        u.mem_write(addr,bytes(ks.asm(src,addr=addr)[0]));u.ctl_remove_cache(addr,addr+0x100)
    def run(off,ecx=0,edx=0,eax=0,args=()):
        sp=0x3003f000;w(sp,0x30000000)
        for i,v in enumerate(args):w(sp+4+i*4,v)
        for reg,v in [(UC_X86_REG_ESP,sp),(UC_X86_REG_ECX,ecx),(UC_X86_REG_EDX,edx),(UC_X86_REG_EAX,eax),(UC_X86_REG_EBX,123),(UC_X86_REG_ESI,234),(UC_X86_REG_EDI,345),(UC_X86_REG_EBP,456)]:u.reg_write(reg,v)
        try: u.emu_start(cave+off,0x30000000,count=100000)
        except Exception as error:
            raise AssertionError(f'entry {off:x}, EIP={u.reg_read(UC_X86_REG_EIP):x} ECX={u.reg_read(UC_X86_REG_ECX):x} EAX={u.reg_read(UC_X86_REG_EAX):x} EBP={u.reg_read(UC_X86_REG_EBP):x}') from error
        assert u.reg_read(UC_X86_REG_EIP)==0x30000000
        assert u.reg_read(UC_X86_REG_ESP)==sp+4
        assert [u.reg_read(x) for x in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]==[123,234,345,456]
        return u.reg_read(UC_X86_REG_EAX)
    actor=0x30001000;source=0x30002000;bank=0x30003000;bazaar=0x30004000;nodes=0x30005000;context=0x30006000;seen=0x30007000
    w(actor+4,source);w(source+8,source+0x800)
    w(source+0x4c0,nodes);w(nodes,bank);w(nodes+4,nodes+8);w(nodes+8,bazaar);w(nodes+12,0)
    # Property stubs verify the actor-specific modifier context and balance
    # the x87 stack just like the actual query APIs.
    stub(game+0x2277b6,f'mov eax,{context}; ret')
    for off,field in [(0x2a0b5,0x100),(0x29ffd,0x104)]:
        stub(game+off,f'cmp dword ptr [esp+8],{context}; jne bad; fld dword ptr [ecx+{field}]; ret 8; bad: int3')
    for race in ('human','gauri','haroun','drauga','shadow','undead','human_sovereign','human_merchant'):
        u.mem_write(source+0x800,(race+'_market\0').encode('utf-16le'))
        for base in (0,20,30):
            f(source+0x100,base);f(bank+0x100,base+40);f(bazaar+0x100,base+5)
            assert run(0x30e00,actor,bank)==1
            assert run(0x30e00,actor,bazaar)==0;checks+=2
            f(bank+0x104,39) # direct gold upkeep makes the +5 branch greater
            assert run(0x30e00,actor,bank)==0
            assert run(0x30e00,actor,bazaar)==1;checks+=2
            f(bank+0x104,0)
        for bad in (0,-1,float('nan'),float('inf'),float('-inf')):
            f(source+0x100,20);f(bank+0x100,20+bad);f(bazaar+0x100,20)
            assert run(0x30e00,actor,bank)==0
            assert run(0x30e00,actor,bazaar)==0;checks+=2
    f(source+0x100,20);f(bank+0x100,60);f(bazaar+0x100,25)
    # Integration: enumeration excludes the weak branch even when the best
    # branch's native CanUpgrade fails; no auto fallback to +5 occurs.
    w(actor,actor+0x800);w(actor+0x800+0x108,game+0x1000)
    w(actor+0x9c,actor+0x900);w(cave+0x10c,context)
    stub(game+0x1000,f'mov eax,{context}; ret')
    stub(cave+0x2a00,f'inc dword ptr [{seen}]; mov eax,dword ptr [esp+12]; mov dword ptr [{seen+4}],eax; ret')
    stub(game+0x2053bd,f'mov eax,dword ptr [esp+4]; cmp eax,{bank}; setne al; movzx eax,al; ret 12')
    w(seen,0);run(0x2c00,args=(actor,actor));assert r(seen)==0;checks+=1
    stub(game+0x2053bd,'mov eax,1; ret 12')
    w(seen,0);run(0x2c00,args=(actor,actor));assert r(seen)==1 and r(seen+4)==bank,(r(seen),hex(r(seen+4)),run(0x30e00,actor,bank));checks+=1
    u.mem_write(source+0x800,'human_blacksmith\0'.encode('utf-16le'))
    w(seen,0);run(0x2c00,args=(actor,actor));assert r(seen)==2;checks+=1
    # Invalid/looped lists fail closed; target must really belong to this actor.
    u.mem_write(source+0x800,'human_market\0'.encode('utf-16le'))
    w(nodes+12,nodes);assert run(0x30e00,actor,bank)==0;checks+=1;w(nodes+12,0)
    unknown=0x30008000;f(unknown+0x100,100);assert run(0x30e00,actor,unknown)==0;checks+=1
    # Rates are sampled from definitions with both Shards resource layouts.
    for count in (9,10):
        for economic,rate in enumerate((0,2,3,4,5)):
            i=economic+(count==10 and economic>0)
            w(source+0x18,1 if economic else 0);w(source+0x1c,source+0x900);f(source+0x900,rate)
            assert run(0x30d00,i,eax=source)==source
            assert struct.unpack('<f',u.mem_read(cave+0x280+i*4,4))[0]==rate;checks+=1
        for rate in (0,.5,8.75):
            f(source+0x900,rate);run(0x30d00,4,eax=source)
            assert struct.unpack('<f',u.mem_read(cave+0x290,4))[0]==rate;checks+=1
        w(source+0x1c,0);run(0x30d00,4,eax=source)
        assert r(cave+0x290)==0x7fc00000;checks+=1
print('CITY_MARKETS_NATIVE_PASS',checks,'checks; no game launched')
