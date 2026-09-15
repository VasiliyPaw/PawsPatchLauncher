"""Execute serialization/whole-order observer hooks against delayed native I/O.

Fixture bodies stand in for original serializer and simulation, including two
payments for a selected order. The emitted hooks, ledger, reset and final gate
are real x86. Verify ABI/flags/XMM0 and both command paths across relocations.
"""
import argparse,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/deps_r15'))
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/pydeps_r3'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
checks=0
for game,cave,count in [(g,c,n) for g,c in [(0x460000,0x10000000),(0x650000,0x21000000),(0x12000000,0x60000000)] for n in (9,10)]:
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(game,0x700000);u.mem_map(cave,0x41000);u.mem_map(0x30000000,0x200000)
    data=bytearray((a.native/'AssistantPayload.bin').read_bytes());fix=(a.native/'AssistantFixups.bin').read_bytes()
    for i in range(struct.unpack_from('<I',fix)[0]):
        k,o,v=struct.unpack_from('<III',fix,4+i*12);struct.pack_into('<I',data,o,((game+v) if k==1 else cave+v if k==2 else game+v-cave-o-4)&0xffffffff)
    u.mem_write(cave,bytes(data));ks=Ks(KS_ARCH_X86,KS_MODE_32)
    def w(addr,v):u.mem_write(addr,struct.pack('<I',v))
    def f(addr,v):u.mem_write(addr,struct.pack('<f',v))
    def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    def rf(addr):return struct.unpack('<f',u.mem_read(addr,4))[0]
    def stub(addr,source):u.mem_write(addr,bytes(ks.asm(source,addr=addr)[0]))
    xmm=0x00112233445566778899aabbccddeeff
    def run(off,ecx=0,args=()):
        sp=0x301ff000;w(sp,0x30000000)
        for i,arg in enumerate(args):w(sp+4+i*4,arg)
        for reg,v in [(UC_X86_REG_ESP,sp),(UC_X86_REG_ECX,ecx),(UC_X86_REG_EAX,987),(UC_X86_REG_EBX,123),(UC_X86_REG_ESI,cave+0x8000),(UC_X86_REG_EDI,345),(UC_X86_REG_EBP,456),(UC_X86_REG_XMM0,xmm)]:u.reg_write(reg,v)
        u.emu_start(cave+off,0x30000000,count=100000)
        assert u.reg_read(UC_X86_REG_ESP)==sp+4
        assert [u.reg_read(x) for x in [UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]]==[123,cave+0x8000,345,456]
        return u.reg_read(UC_X86_REG_EAX)
    admin=0x30001000;player=0x30002000;other=0x30002100;world=0x30003000;command=0x30004000;command_data=0x30005000;order=0x30006000
    kingdom=0x30007000;gold=0x30008000;cost=gold+4;seen=gold+8
    w(game+0x5f3fec,admin);w(admin+0x230,player);w(admin+0x2a4,player);w(player+0x20,0);w(other+0x20,9)
    w(game+0x5f3fb8,world);w(game+0x5f9218,2);f(world+0xe8,1)
    w(command+8,command_data);w(command_data+0xc,13);w(command+0x14,0x3000b000);w(order+4,command);w(order+8,0x3000c000)
    w(cave+0x10c,kingdom);w(cave+0x118,count);w(cave+0xb8,1);w(kingdom+0x1a8,kingdom+0x500);w(kingdom+0x1c0,kingdom+0x600)
    for i in range(count):f(kingdom+0x500+i*4,10)
    run(0x5600);assert run(0x3900)==1;checks+=1
    stub(game+0xd43be,'mov eax,765; pop esi; pop ebx; stc; ret')
    # Targeted continuation after the original six-byte prologue.
    stub(game+0xd3d87,f'mov eax,dword ptr [{cave+0xd0}]; mov dword ptr [{seen}],eax; fld dword ptr [{gold}]; fsub dword ptr [{cost}]; fstp dword ptr [{gold}]; mov eax,876; pop esi; stc; ret')
    # Selected continuation follows its original MOV before the SEH prologue.
    # Both fixture actor payments must see the group's barrier still held.
    stub(game+0xd39e1,f'mov eax,dword ptr [{cave+0xd0}]; mov dword ptr [{seen}],eax; fld dword ptr [{gold}]; fsub dword ptr [{cost}]; fstp dword ptr [{gold}]; mov eax,dword ptr [{cave+0xd0}]; mov dword ptr [{seen+4}],eax; fld dword ptr [{gold}]; fsub dword ptr [{cost}]; fstp dword ptr [{gold}]; mov eax,876; stc; ret')
    def send(writer=None):
        assert run(0x7b00,args=(admin+0x274 if writer is None else writer,command))==765
        assert u.reg_read(UC_X86_REG_EFLAGS)&1 and u.reg_read(UC_X86_REG_XMM0)==xmm
    def process(selected=False):
        assert run(0x7c00 if selected else 0x7b80,order)==876
        assert u.reg_read(UC_X86_REG_EFLAGS)&1 and u.reg_read(UC_X86_REG_XMM0)==xmm
    # Decrees/recordings do not register, and unrelated orders do not block.
    send(admin+0x218);assert r(cave+0xd0)==0;checks+=1
    w(command_data+0xc,23);send();assert r(cave+0xd0)==0;checks+=1;w(command_data+0xc,13)
    # 3000 cash, 2000 reserve, manual600 before auto500: pending native send
    # blocks auto before any debit. After actual debit only400 can be spent.
    f(gold,3000);f(cost,600);send();assert r(cave+0xd0)==1 and run(0x3900)==0;checks+=1
    run(0x5600);assert run(0x3900)==0;checks+=1 # even a fresh capture cannot bypass pending transport
    process();assert r(seen)==1 and r(cave+0xd0)==0 and rf(gold)==2400;checks+=1
    assert run(0x3900)==0;checks+=1 # old pre-payment forecast generation is invalid
    run(0x5600);assert run(0x3900)==1 and rf(gold)<2000+500;checks+=1
    # Identical sent groups retain multiplicity. A foreign player's same
    # definition cannot acknowledge a local request (player zero is valid).
    send();send();assert r(cave+0xd0)==2;checks+=1
    w(admin+0x2a4,other);process();assert r(cave+0xd0)==2;checks+=1;w(admin+0x2a4,player)
    w(other+0x20,0);u.mem_write(other+0xe,b'\x01');w(admin+0x2a4,other)
    process();assert r(cave+0xd0)==2;checks+=1;w(admin+0x2a4,player)
    w(admin+0x230,other);send();assert r(cave+0xd0)==2;checks+=1;w(admin+0x230,player)
    process();assert r(cave+0xd0)==1;checks+=1
    process();assert r(cave+0xd0)==0;checks+=1
    # Selected commands are acknowledged only after all actors finish paying.
    w(command_data+0xc,21);f(gold,3000);send();process(True)
    assert r(seen)==1 and r(seen+4)==1 and rf(gold)==1800 and r(cave+0xd0)==0;checks+=1
    # Native rejection inside Process still returns and clears its group.
    f(cost,0);send();process();assert r(cave+0xd0)==0;checks+=1
    # A server/version rejection before Process, pause or empty output writer
    # must NEVER be guessed to have acknowledged a sent command.
    send();w(admin+0x27c,0);w(admin+0x280,3)
    for time in (1,1,20,600):f(world+0xe8,time);run(0x5600);assert r(cave+0xd0)==1 and run(0x3900)==0;checks+=1
    # Native load/time rollback invalidates the previous world's ledger only.
    f(world+0xe8,0);run(0x5600);assert r(cave+0xd0)==0 and run(0x3900)==1;checks+=1
    send();w(game+0x5f9218,0);run(0x5600);assert r(cave+0xd0)==0;checks+=1
    w(game+0x5f9218,2);run(0x5600)
    # Mutation seqlock and capacity failures do not admit automatic spending.
    w(cave+0xe0,r(cave+0xe0)+1);w(cave+0xe4,r(cave+0xe0));assert run(0x3900)==0;checks+=1
    w(cave+0xe0,r(cave+0xe0)+1);run(0x5600)
    for i in range(129):w(command+0x14,0x30010000+i*4);send()
    assert r(cave+0xdc)==1 and r(cave+0xd0)==128 and run(0x3900)==0;checks+=1
print('CITY_TRANSPORT_NATIVE_PASS',checks,'checks; delayed command fixtures, no game launched')
