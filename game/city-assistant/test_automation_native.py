"""Execute native mine traversal, queue guards and ordinary militia dispatch.

Game allocation/definition/network endpoints are fixtures. Capability testing is
the actual verified 1.3.72 machine code, and every helper branch runs as x86 at
three module/cave placements with both native resource layouts.
"""
import argparse,hashlib,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/deps_r15'))
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/pydeps_r3'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
raw=(a.legacy.parent/'k2_runtime_1372_20260904.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
checks=0
for game,cave,count in [(g,c,n) for g,c in [(0x460000,0x10000000),(0x650000,0x21000000),(0x12000000,0x60000000)] for n in (9,10)]:
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(game,0x700000);u.mem_map(cave,0x30000);u.mem_map(0x30000000,0x200000)
    payload=bytearray((a.native/'AssistantPayload.bin').read_bytes());fix=(a.native/'AssistantFixups.bin').read_bytes()
    for i in range(struct.unpack_from('<I',fix)[0]):
        k,o,v=struct.unpack_from('<III',fix,4+i*12)
        struct.pack_into('<I',payload,o,((game+v) if k==1 else cave+v if k==2 else game+v-cave-o-4)&0xffffffff)
    u.mem_write(cave,bytes(payload));ks=Ks(KS_ARCH_X86,KS_MODE_32)
    def w(addr,v):u.mem_write(addr,struct.pack('<I',v))
    def f(addr,v):u.mem_write(addr,struct.pack('<f',v))
    def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    def stub(addr,src):u.mem_write(addr,bytes(ks.asm(src,addr=addr)[0]))
    def run(off,ecx=0,eax=0):
        sp=0x301ff000;w(sp,0x30000000)
        for reg,v in [(UC_X86_REG_ESP,sp),(UC_X86_REG_ECX,ecx),(UC_X86_REG_EAX,eax),(UC_X86_REG_EBX,123),(UC_X86_REG_ESI,234),(UC_X86_REG_EDI,345),(UC_X86_REG_EBP,456)]:u.reg_write(reg,v)
        u.emu_start(cave+off,0x30000000,count=300000)
        assert u.reg_read(UC_X86_REG_ESP)==sp+4
        assert [u.reg_read(x) for x in [UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]]==[123,234,345,456]
        return u.reg_read(UC_X86_REG_EAX)
    kingdom=0x30001000;vt=0x30002000;owner=0x30003000;array=0x30004000;foreign=0x30005000
    w(kingdom+0x2d0,array);w(cave+0x10c,kingdom);w(cave+0x118,count)
    stub(owner,f'mov eax,{kingdom}; ret');w(vt+0x108,owner)
    stub(foreign,'xor eax,eax; ret')
    stub(game+0x2277b6,'xor eax,eax; ret')
    stub(game+0x29f57,'fldz; ret 8')
    stub(game+0x2a0b5,'mov eax,dword ptr [esp+4]; mov edx,dword ptr [ecx+0x33c]; fld dword ptr [edx+eax*4]; ret 8')
    stub(game+0x29ffd,'fldz; ret 8')
    stub(game+0x2053bd,'mov eax,1; ret 12')
    nextaddr=[0x30008000]
    def alloc():
        v=nextaddr[0];nextaddr[0]+=0x1000;return v
    def definition(name,delta):
        d=alloc();w(d+8,d+0x800);u.mem_write(d+0x800,(name+'\0').encode('utf-16le'));w(d+0x33c,d+0x900)
        for i,v in enumerate(delta):f(d+0x900+(i+(count==10 and i>0))*4,v)
        return d
    def actor(id,data):
        v=alloc();w(v,vt);w(v+4,data);w(v+0x14,id);w(v+0x94,v+0x400);w(v+0x9c,v+0x500);w(v+0x500,game+0x4dfe58);w(v+0x504,v)
        return v
    # Execute the game's real Toggle/Check/Uncheck methods. Check (7186d4)
    # and Uncheck (7186f2) take (notify, update), NOT a checked-state value.
    # First F1 creation must render the saved preference without treating its
    # initial unchecked widget as a user change. Cover both persisted values,
    # both prior widget states, reopening, and a subsequent native user toggle.
    start,end=0x7186b6,0x7187e3
    u.mem_write(game+start-0x460000,raw[start-0x460000:end-0x460000])
    stub(game+0x2a8211,'ud2') # Rendering must suppress the native notification.
    widget=alloc();toggle=alloc()
    stub(toggle,f'push 1; push 0; mov ecx,{widget}; call {game+0x2b86b6}; ret')
    for preference in (1,0):
        for initially_checked in (0,1):
            w(cave+0xc0,preference);w(cave+0xc4,widget);w(cave+0xc8,17)
            w(widget+0x24,0x2040 | (initially_checked<<7))
            for reopening in range(2):
                run(0x7300)
                assert r(widget+0x24)==0x2040 | (preference<<7),(preference,initially_checked,reopening)
                assert r(cave+0xc0)==preference and r(cave+0xc8)==17
                run(0x7380)
                assert r(cave+0xc0)==preference and r(cave+0xc8)==17
                checks+=3
            run(toggle-cave);run(0x7380)
            assert r(cave+0xc0)==1-preference and r(cave+0xc8)==18;checks+=1
            run(0x7300);run(0x7380)
            assert r(widget+0x24)==0x2040 | ((1-preference)<<7)
            assert r(cave+0xc0)==1-preference and r(cave+0xc8)==18;checks+=2
    # Destroyed/unavailable F1 widget must not rewrite the retained preference.
    w(cave+0xc4,0);w(cave+0xc0,1);w(cave+0xc8,19)
    run(0x7300);run(0x7380)
    assert r(cave+0xc0)==1 and r(cave+0xc8)==19;checks+=1
    for name,expected in [('human_market',1),('haroun_mine_gold',2),('undead_mine',2),('human_iron_market',1),('market_stall',0),('human_marketplace',0),('gauri_miner',0),('',0)]:
        d=definition(name,[0]*5);assert run(0x7000,eax=d)==expected;checks+=1
    assert run(0x7000)==0;checks+=1
    for race in ('human','drauga','gauri','haroun','shadow','undead'):
        for resource in ('gold','stone','wood','iron','mana'):
            effects=[0]*5;effects[('gold','stone','wood','iron','mana').index(resource)]=8
            old=definition(race+'_mine_'+resource,[0]*5);target=definition(race+'_mine_'+resource+'_upgrade',effects)
            mine=actor(100,old);w(old+0x4c0,old+0x700);w(old+0x700,target)
            w(array,mine);w(kingdom+0x2d4,1);w(cave+0x11c,0);w(cave+0x120,0);run(0x5600);run(0x6d00)
            assert r(cave+0x11c)==1 and r(cave+0x19004)==2 and r(cave+0x120)==1
            assert [r(cave+0x8000+i*4) for i in range(4)]==[100,100,target,21];checks+=2
            # Queued mine upgrade is counted even before work starts. Its actor
            # cannot get the same or an alternative branch a second time.
            w(mine+0x528,target);w(cave+0x11c,0);w(cave+0x120,0);run(0x5600);run(0x6d00)
            assert r(cave+0x12c)==1 and r(cave+0x120)==0 and r(cave+0x19004)==3
            assert struct.unpack('<5f',u.mem_read(cave+0x1b040,20))==tuple(effects);checks+=2
            # Native cancellation resets the target and immediately restores
            # the candidate; no extra cost ledger survives cancellation.
            w(mine+0x528,0);w(cave+0x11c,0);w(cave+0x120,0);run(0x5600);run(0x6d00)
            assert r(cave+0x12c)==0 and r(cave+0x120)==1;checks+=1
    # Native cities may hold many waiting/active child tasks. Only the city's
    # siege/sale status blocks unrelated building/upgrade choices.
    city=actor(200,old);center=actor(201,old);settle=alloc();w(city+0x98,settle);w(settle+0x14,center)
    w(settle+0x1c,7);w(center+0x100,0x20000000);w(center+0x528,target)
    assert run(0x2800,city)==0;checks+=1
    for flags in (0x100000,0x40000000):
        w(city+0x100,flags);assert run(0x2800,city)==1;checks+=1
    w(city+0x100,0);assert run(0x2900,center)==1;checks+=1
    # Loss of ownership removes both work forecast and candidate next capture.
    w(vt+0x108,foreign);w(cave+0x11c,0);w(cave+0x120,0);run(0x5600);run(0x6d00)
    assert r(cave+0x12c)==0 and r(cave+0x120)==0 and r(cave+0x11c)==0;checks+=1;w(vt+0x108,owner)
    # Real native CanCommand/bit-mask code, relocated with the game image.
    for start,end in [(0x68f23f,0x68f26a),(0x4c480b,0x4c4825)]:u.mem_write(game+start-0x460000,raw[start-0x460000:end-0x460000])
    w(vt+0x34,game+0x22f23f);w(cave+0x11c,0)
    for capability,expected in [(0,0),(1<<23,1),(1<<24,2)]:
        w(center+0xf0,capability);run(0x7800,city)
        assert r(cave+0x1d000)==200 and r(cave+0x1d004)==expected;checks+=1
    # Constructor + Validate + Send, with reference destruction, no direct
    # simulation mutation. All network endpoints are explicit test stubs.
    command=alloc();seen=alloc();valid=seen+8
    stub(game+0x21117,f'mov eax,{city}; ret 4')
    stub(game+0x2ef03c,f'mov eax,{command}; ret')
    stub(game+0x22f4e9,'mov eax,dword ptr [esp+4]; mov dword ptr [ecx+8],eax; mov eax,ecx; ret 4')
    stub(game+0xcd843,'mov eax,dword ptr [esp+8]; mov dword ptr [ecx],eax; mov eax,dword ptr [esp+4]; mov eax,dword ptr [eax]; mov dword ptr [ecx+4],eax; ret 8')
    stub(game+0xd3d5f,f'jmp {seen+0x200}')
    stub(seen+0x200,f'mov eax,dword ptr [{valid}]; ret')
    stub(game+0xd3d57,f'jmp {seen+0x100}')
    stub(seen+0x100,f'inc dword ptr [{seen}]; mov eax,dword ptr [ecx]; mov dword ptr [{seen+16}],eax; mov eax,dword ptr [ecx+4]; mov eax,dword ptr [eax+8]; mov dword ptr [{seen+4}],eax; ret')
    stub(game+0xd3d3c,f'inc dword ptr [{seen+12}]; ret')
    w(valid,1);w(cave+0x128,1);w(cave+0xc0,1);w(cave+0x104,7);w(cave+0x184,7);w(cave+0x188,200)
    f(cave+0x110,2);f(cave+0x18c,1);w(center+0xf0,1<<23)
    w(cave+0x180,1);run(0x7400)
    assert r(cave+0x190)==1 and r(cave+0x194)==1 and r(seen)==1 and r(seen+4)==23 and r(seen+12)==1
    assert r(center+0xf0)==1<<23 and r(seen+16)==center;checks+=2 # center is the native militia owner
    run(0x7400);assert r(seen)==1;checks+=1
    for serial,change,restore,result in [
        (2,lambda:w(center+0xf0,1<<24),lambda:w(center+0xf0,1<<23),3),
        (3,lambda:w(vt+0x108,foreign),lambda:w(vt+0x108,owner),2),
        (4,lambda:w(cave+0xc0,0),lambda:w(cave+0xc0,1),2),
        (5,lambda:w(cave+0x184,6),lambda:w(cave+0x184,7),2),
        (6,lambda:w(city+0x98,0),lambda:w(city+0x98,settle),2),
        (7,lambda:w(valid,0),lambda:w(valid,1),2)]:
        change();w(cave+0x180,serial);run(0x7400)
        assert r(cave+0x194)==serial and r(cave+0x190)==result and r(seen)==1,(serial,r(cave+0x194),r(cave+0x190),r(seen));checks+=1;restore()
    w(cave+0x180,8);f(cave+0x110,1);run(0x7400);assert r(cave+0x194)==7 and r(seen)==1;checks+=1
    f(cave+0x110,2);run(0x7400);assert r(cave+0x194)==8 and r(seen)==2;checks+=1
print('CITY_AUTOMATION_NATIVE_PASS',checks,'checks; no game launched')
