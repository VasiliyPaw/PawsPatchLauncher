"""Execute the emitted construction observer against synthetic engine fixtures.

Only definition queries/owner lookup are mocked. Traversal, deduplication,
cached contribution subtraction, aggregates and all guards are real x86.
"""
import argparse, struct, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/deps_r15'))
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/pydeps_r3'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
checks=0
for game,cave,count in [(g,c,n) for g,c in [(0x460000,0x10000000),(0x650000,0x21000000),(0x12000000,0x60000000)] for n in (9,10)]:
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(game,0x700000);u.mem_map(cave,0x30000);u.mem_map(0x30000000,0x200000)
    data=bytearray((a.native/'AssistantPayload.bin').read_bytes());fix=(a.native/'AssistantFixups.bin').read_bytes()
    for i in range(struct.unpack_from('<I',fix)[0]):
        k,o,v=struct.unpack_from('<III',fix,4+i*12)
        struct.pack_into('<I',data,o,((game+v) if k==1 else cave+v if k==2 else game+v-cave-o-4)&0xffffffff)
    u.mem_write(cave,bytes(data));ks=Ks(KS_ARCH_X86,KS_MODE_32)
    def w(addr,v):u.mem_write(addr,struct.pack('<I',v))
    def f(addr,v):u.mem_write(addr,struct.pack('<f',v))
    def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    def floats(addr):return struct.unpack('<5f',u.mem_read(addr,20))
    def stub(address,src):u.mem_write(address,bytes(ks.asm(src,addr=address)[0]))
    def run(offset,ecx=0):
        sp=0x301ff000;w(sp,0x30000000);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,ecx)
        for reg,v in [(UC_X86_REG_EBX,123),(UC_X86_REG_ESI,234),(UC_X86_REG_EDI,345),(UC_X86_REG_EBP,456)]:u.reg_write(reg,v)
        u.emu_start(cave+offset,0x30000000,count=300000)
        assert u.reg_read(UC_X86_REG_ESP)==sp+4
        assert [u.reg_read(x) for x in [UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]]==[123,234,345,456]
    kingdom=0x30001000;vt=0x30002000;owner=0x30003000
    stub(owner,f'mov eax,{kingdom}; ret');w(vt+0x108,owner)
    stub(game+0x2277b6,'xor eax,eax; ret')
    stub(game+0x29f57,'fldz; ret 8')
    stub(game+0x2a0b5,'mov eax,dword ptr [esp+4]; mov edx,dword ptr [ecx+0x33c]; fld dword ptr [edx+eax*4]; ret 8')
    stub(game+0x29ffd,'mov eax,dword ptr [esp+4]; mov edx,dword ptr [ecx+0x330]; fld dword ptr [edx+eax*4]; ret 8')
    w(cave+0x10c,kingdom);w(cave+0x118,count)
    def index(resource):return resource+(1 if count==10 and resource>0 else 0)
    def vector(values):
        raw=[0]*count
        for i,v in enumerate(values):raw[index(i)]=v
        return raw
    next_address=[0x30004000]
    def alloc():
        address=next_address[0];next_address[0]+=0x800;return address
    def definition(prod,up):
        d=alloc();w(d+0x33c,d+0x600);w(d+0x330,d+0x640)
        for i in range(count):f(d+0x600+i*4,vector(prod)[i]);f(d+0x640+i*4,vector(up)[i])
        return d
    def actor(id,definition,flags=0,target=0,prod=None,up=None):
        actor=alloc();con=alloc();eco=alloc()
        w(actor,vt);w(actor+4,definition);w(actor+0x14,id);w(actor+0x100,flags)
        w(actor+0x9c,con);w(con,game+0x4dfe58);w(con+4,actor);w(con+0x28,target)
        w(actor+0x84,eco);w(eco,game+0x4e0ef0);w(eco+4,actor)
        u.mem_write(eco+0x10,bytes([int(prod is not None),int(up is not None)]))
        w(eco+0x18,eco+0x100);w(eco+0x1c,count);w(eco+0x28,eco+0x140);w(eco+0x2c,count)
        for i in range(count):f(eco+0x100+i*4,vector(prod or [0]*5)[i]);f(eco+0x140+i*4,vector(up or [0]*5)[i])
        return actor
    zero=[0]*5;old=definition(zero,zero)
    city=actor(1,old);settle=alloc();children=alloc();w(city+0x98,settle);w(settle+0x14,city);w(settle+0x18,children)
    def scan(*actors):
        w(settle+0x1c,len(actors))
        for i,v in enumerate(actors):w(children+i*4,v)
        run(0x5600);run(0x5700,city)
    # Siege with no active work: no global economic block/phantom commitment.
    w(city+0x100,0x100000);scan();assert r(cave+0x130)==1 and r(cave+0x12c)==0;checks+=1
    w(city+0x100,0)
    # Every economic resource: subtract actually-registered current effects.
    for resource in range(5):
        for current in [-4,0,2,10]:
            for target_net in [-5,0,3,20]:
                prod=[0]*5;up=[0]*5;prod[resource]=max(0,target_net);up[resource]=max(0,-target_net)
                target=definition(prod,up);cp=[0]*5;cu=[0]*5;cp[resource]=max(0,current);cu[resource]=max(0,-current)
                building=actor(100,old,0x20000000,target,cp,cu)
                scan(building,building) # same actor cannot be double-counted
                expected=[0.]*5;expected[resource]=target_net-current
                assert r(cave+0x130)==1 and r(cave+0x12c)==1
                assert tuple(struct.unpack("<f",u.mem_read(cave+0x20014+index(i)*4,4))[0] for i in range(5))==tuple(expected)
                assert floats(cave+0x1b020)==tuple(min(0,v) for v in expected)
                assert floats(cave+0x1b040)==tuple(expected)
                checks+=4
    target=definition([20,0,0,0,0],[0,3,0,0,0])
    building=actor(200,target,0x200000,prod=None,up=[0,3,0,0,0])
    scan(building)
    assert floats(cave+0x1b020)==(0,0,0,0,0) # -3 upkeep already in live income
    assert floats(cave+0x1b040)==(20,0,0,0,0);checks+=2
    # Paused by siege: retain future losses, don't promise future gains.
    target=definition([20,0,0,0,0],[0,3,0,0,0]);building=actor(201,old,0x20100000,target,zero,zero)
    scan(building);assert floats(cave+0x1b020)==(0,-3,0,0,0) and floats(cave+0x1b040)==(0,-3,0,0,0);checks+=1
    w(building+0x100,0x20000000);w(city+0x100,0x100000);scan(building)
    assert floats(cave+0x1b040)==(0,-3,0,0,0);checks+=1;w(city+0x100,0)
    # Two simultaneous upgrades are aggregated, including manual ones.
    another=actor(202,old,0x20000000,target,zero,zero);scan(building,another)
    assert r(cave+0x12c)==2 and floats(cave+0x1b020)==(0,-6,0,0,0) and floats(cave+0x1b040)==(40,-6,0,0,0);checks+=1
    # Cancel/completion/removal clears reservations next capture, no saved ledger.
    w(r(building+0x9c)+0x28,0);w(building+0x100,0);scan(building,another)
    assert r(cave+0x12c)==1 and floats(cave+0x1b020)==(0,-3,0,0,0);checks+=1
    scan();assert r(cave+0x12c)==0 and floats(cave+0x1b020)==(0,0,0,0,0);checks+=1
    # Malformed active work/caches and nonfinite deltas fail closed, NOT siege.
    for change,restore in [
        (lambda:w(r(another+0x9c),0),lambda:w(r(another+0x9c),game+0x4dfe58)),
        (lambda:w(r(another+0x84)+4,0),lambda:w(r(another+0x84)+4,another)),
        (lambda:w(r(another+0x84)+0x1c,0),lambda:w(r(another+0x84)+0x1c,count)),
        (lambda:f(target+0x600,float('nan')),lambda:f(target+0x600,20))]:
        change();scan(another);assert r(cave+0x130)==0;restore();checks+=1
    scan(another);assert r(cave+0x130)==1;checks+=1
    run(0x5600);w(settle+0x1c,257);run(0x5700,city);assert r(cave+0x130)==0;checks+=1
print('CITY_CONSTRUCTION_NATIVE_PASS',checks,'checks; no game launched')
