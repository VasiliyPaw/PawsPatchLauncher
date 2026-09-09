"""Execute the actual final economic gate at relocated addresses, without game I/O."""
import argparse,struct,sys,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/deps_r15'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
checks=0
for game,cave,count in [(g,c,n) for g,c in [(0x460000,0x10000000),(0x650000,0x21000000),(0x12000000,0x60000000)] for n in (9,10)]:
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(game,0x700000);u.mem_map(cave,0x30000);u.mem_map(0x30000000,0x20000)
    data=bytearray((a.native/'AssistantPayload.bin').read_bytes());fix=(a.native/'AssistantFixups.bin').read_bytes()
    for i in range(struct.unpack_from('<I',fix)[0]):
        k,o,v=struct.unpack_from('<III',fix,4+i*12);struct.pack_into('<I',data,o,((game+v) if k==1 else cave+v if k==2 else game+v-cave-o-4)&0xffffffff)
    u.mem_write(cave,bytes(data))
    def w(addr,v):u.mem_write(addr,struct.pack('<I',v))
    def f(addr,v):u.mem_write(addr,struct.pack('<f',v))
    def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    kingdom=0x30001000;production=0x30002000;upkeep=0x30003000;candidate=cave+0x8000
    w(cave+0x10c,kingdom);w(kingdom+0x1a8,production);w(kingdom+0x1c0,upkeep);w(cave+0x118,count)
    def index(resource):return resource+(1 if count==10 and resource>0 else 0)
    w(cave+0xb8,1)
    w(cave+0x130,1)
    def run(off):
        sp=0x3000f000;w(sp,0x30000000);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ESI,candidate)
        for reg,v in [(UC_X86_REG_EBX,123),(UC_X86_REG_EDI,456),(UC_X86_REG_EBP,789)]:u.reg_write(reg,v)
        u.emu_start(cave+off,0x30000000,count=4000)
        assert u.reg_read(UC_X86_REG_ESP)==sp+4
        assert [u.reg_read(x) for x in [UC_X86_REG_EBX,UC_X86_REG_EDI,UC_X86_REG_EBP]]==[123,456,789]
        return u.reg_read(UC_X86_REG_EAX)
    for resource in range(5):
        for before in [-10,-1,0,1,2,10]:
            for delta in [-3,-1,0,1,3]:
                for floor in [0,2]:
                    for i in range(count):f(production+i*4,10);f(upkeep+i*4,0);f(candidate+20+i*4,0)
                    for i in range(5):f(cave+0x1b000+i*4,0)
                    f(production+index(resource)*4,before);f(candidate+20+index(resource)*4,delta);f(cave+0x1b000+resource*4,floor)
                    expected=delta>=0 or before+delta>=min(before,0 if resource==0 else floor)
                    assert bool(run(0x3900))==expected,(resource,before,delta,floor)
                    checks+=1
    # Settings/native-input/readiness gates cannot leak an order.
    for addr in [0x7c,0x80,0xb4]:
        w(cave+addr,1);assert run(0x3900)==0;w(cave+addr,0);checks+=1
    w(cave+0xb8,0);assert run(0x3900)==0;w(cave+0xb8,1);checks+=1
    for revision,ack,allowed in [(2,0,False),(2,2,True),(3,3,False),(4,2,False),(4,4,True)]:
        w(cave+0x1c020,revision);w(cave+0x1c024,ack)
        assert bool(run(0x3900))==allowed;checks+=1
    w(cave+0x1c020,0);w(cave+0x1c024,0)
    # A busy/sieged OTHER city no longer blocks the final economic gate.
    for i in range(count):f(production+i*4,10);f(candidate+20+i*4,0)
    for i in range(5):f(cave+0x1b000+i*4,0)
    for unknown in (1,5,8,11,16):
        w(cave+0x118,unknown);assert run(0x3900)==0;checks+=1
    w(cave+0x118,count)
    w(cave+0x11c,2);w(cave+0x19004,0);w(cave+0x1900c,1)
    assert run(0x3900)==1;checks+=1
    w(cave+0x1900c,0);assert run(0x3900)==1;checks+=1
    w(cave+0x11c,0)
    w(cave+0x130,0);assert run(0x3900)==0;checks+=1;w(cave+0x130,1)
    for resource in range(5):
        f(candidate+20+index(resource)*4,-2);f(cave+0x1b020+resource*4,-9)
        assert run(0x3900)==0;checks+=1
        f(cave+0x1b040+resource*4,100) # gains must NEVER finance the next order
        assert run(0x3900)==0;checks+=1
        f(cave+0x1b020+resource*4,0);f(candidate+20+index(resource)*4,0)
    # Gear click locks native dispatch immediately, before helper polls it.
    widget=0x30005000;w(cave+0xa8,widget);w(widget+0x24,0x80)
    run(0x5300);assert r(cave+0xac)==1 and r(cave+0xb4)==1;checks+=1
    run(0x5300);assert r(cave+0xac)==1;checks+=1
    w(widget+0x24,0);run(0x5300);assert r(cave+0xac)==2;checks+=1
    # Native cursor suppression: both the per-frame renderer and WM_SETCURSOR
    # path hide the D3D cursor only while settings are open. The actual machine
    # code runs against a mock D3D ShowCursor; no desktop APIs/input are used.
    cursor=0x30006000;device=0x30006100;vt=0x30006200;fn=0x30006300;seen=0x30006400
    w(cursor+0x1c,device);w(device,vt);w(vt+0x30,fn)
    u.mem_write(fn,b'\x8b\x44\x24\x08\xa3'+struct.pack('<I',seen)+b'\x31\xc0\xc2\x08\x00')
    for offset in [0x5400,0x5500]:
        w(cave+0xb4,1);w(seen,99);u.reg_write(UC_X86_REG_ECX,cursor)
        run(offset);assert r(seen)==0;checks+=1
        w(cursor+0x1c,0);u.reg_write(UC_X86_REG_ECX,cursor);run(offset);checks+=1
        w(cursor+0x1c,device);w(cave+0xb4,0);w(seen,99)
        sp=0x3000f000;w(sp,0x30000000);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,cursor)
        u.reg_write(UC_X86_REG_ESI,123);u.reg_write(UC_X86_REG_EDI,456)
        resume=game+(0x18821a if offset==0x5400 else 0x1883e4)
        u.emu_start(cave+offset,resume,count=100)
        assert r(seen)==99
        if offset==0x5400:assert u.reg_read(UC_X86_REG_EAX)==game+0x43354e and u.reg_read(UC_X86_REG_ESP)==sp
        else:assert u.reg_read(UC_X86_REG_ESI)==cursor and u.reg_read(UC_X86_REG_EDI)==0 and u.reg_read(UC_X86_REG_ESP)==sp-8
        checks+=1
print('CITY_POLICY_NATIVE_PASS',checks,'checks; game not launched')
