"""Run the actual compiled x86 hooks in isolation, at different image bases.
Uses the old engine code for the packet-type gate, with two state queries mocked.
This is not a live multiplayer or socket test and does not open the game.
"""
import argparse, json, pathlib, struct, sys
parser = argparse.ArgumentParser()
parser.add_argument('--work', type=pathlib.Path, required=True)
parser.add_argument('--out', type=pathlib.Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.work/'lobby_colors_1372/pydeps_r3'))
sys.path.insert(0, str(args.work/'lobby_colors_1372/deps_r15'))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *

raw = (args.work/'k2_runtime_1372_20260904.bin').read_bytes()
guards = json.loads((args.out/'guards.json').read_text())['ranges']
checks = 0
def check(ok, msg):
    global checks
    checks += 1
    if not ok: raise AssertionError(msg)

class Fixture:
    def __init__(self, image, patched=True):
        self.image=image; self.cave=0x10000000
        self.u=Uc(UC_ARCH_X86, UC_MODE_32)
        self.u.mem_map(image, 0x700000)
        self.u.mem_map(self.cave, 0x2000)
        self.u.mem_map(0x20000000, 0x10000)
        self.u.mem_map(0x30000000, 0x20000)
        self.u.mem_map(0x70000000, 0x1000)
        self.admin=0x20000000; self.node=0x20001000
        self.conn=0x20002000; self.netconn=0x20003000; self.stream=0x20004000
        self.stack=0x30010000; self.stop=0x70000000
        self.playing=False; self.behind=False
        for guard in guards:
            b=bytearray(raw[guard['rva']:guard['rva']+guard['size']])
            for p in guard['fixups']:
                struct.pack_into('<I',b,p,struct.unpack_from('<I',b,p)[0]+image-0x460000)
            self.u.mem_write(image+guard['rva'],bytes(b))
        self.u.mem_write(self.cave,(args.out/f'payload-{image:X}.bin').read_bytes())
        if patched:
            for rva,to,size in ((0x151936,self.cave,8),(0x1500f6,self.cave+256,7),(0x1501d1,self.cave+512,7)):
                self.u.mem_write(image+rva,b'\xe9'+struct.pack('<i',to-(image+rva)-5)+b'\x90'*(size-5))
        self.w(image+0x5f3fec,self.admin); self.w(image+0x5f3fc4,self.node)
        self.w(self.admin+0x2e4,self.admin); self.w(self.admin+0x2e8,self.admin)
        self.w(self.conn+0x42c,self.netconn); self.w(self.conn+0x98,1)
        self.w(self.conn+0x3c,2); self.w(self.conn+0x3fc,1615176)
        self.w(self.conn+0x430,7)
        self.w(self.conn+0x424,-1)
        self.window()
        self.u.mem_write(image+0x480834,struct.pack('<f',0.1))
        self.u.mem_write(image+0x4bc060,struct.pack('<f',0.02))
        self.u.mem_write(image+0x458c3c,struct.pack('<f',0.1))
        self.u.hook_add(UC_HOOK_CODE,self.hook)
    def w(self,a,n): self.u.mem_write(a,struct.pack('<I',n&0xffffffff))
    def r(self,a): return struct.unpack('<I',self.u.mem_read(a,4))[0]
    def window(self, first=0, count=256, unsent=0):
        # Native sender metadata is a ring of 12-byte records, not file bytes.
        self.records=0x20005000
        for offset,value in ((0x3c8,first),(0x3cc,first+count),(0x3d0,256),(0x3d4,self.records)):
            self.w(self.conn+offset,value)
        for i in range(first,first+count):
            self.w(self.records+((i+0x80000000)%256)*12, int(i<unsent))
    def client(self, received=1, size=1615176, fresh=True):
        self.w(self.admin+0x2e4,self.conn); self.w(self.admin+0x2e8,self.conn)
        self.w(self.conn+0x424,size); self.w(self.conn+0x408,received)
        self.u.mem_write(self.netconn+0x2c,struct.pack('<f',1.01 if fresh else .9))
    def hook(self,u,address,size,user):
        rva=address-self.image
        if rva in (0x1501df,0x1492d1):
            result=int(self.behind) if rva==0x1501df else int(not self.playing)
            esp=u.reg_read(UC_X86_REG_ESP)
            u.reg_write(UC_X86_REG_EAX,result)
            u.reg_write(UC_X86_REG_EIP,self.r(esp));u.reg_write(UC_X86_REG_ESP,esp+4)
    def packet_type(self,elapsed):
        self.u.mem_write(self.node+0x50,struct.pack('<f',1+elapsed))
        self.u.mem_write(self.netconn+0x90,struct.pack('<f',1.0))
        self.w(self.stack,self.stop)
        self.u.reg_write(UC_X86_REG_ESP,self.stack)
        self.u.reg_write(UC_X86_REG_ECX,self.conn)
        self.u.reg_write(UC_X86_REG_ESI,0x11223344)
        self.u.reg_write(UC_X86_REG_EDI,0x22334455)
        self.u.reg_write(UC_X86_REG_EBX,0x33445566)
        self.u.reg_write(UC_X86_REG_EBP,0x44556677)
        self.u.emu_start(self.image+0x150009,self.stop,count=10000)
        check(self.u.reg_read(UC_X86_REG_EIP)==self.stop,'query terminates within instruction budget')
        check(self.u.reg_read(UC_X86_REG_ESP)==self.stack+4,'packet type stack balanced')
        for reg,value in ((UC_X86_REG_ESI,0x11223344),(UC_X86_REG_EDI,0x22334455),(UC_X86_REG_EBX,0x33445566),(UC_X86_REG_EBP,0x44556677)):
            check(self.u.reg_read(reg)==value,'callee-saved register unchanged')
        return self.u.reg_read(UC_X86_REG_EAX)
    def budget(self,state,length,used):
        self.w(self.conn+0x3c,state); self.w(self.conn+0x3fc,length)
        self.w(self.stream+8,used//8); self.w(self.stream+12,used%8)
        self.u.reg_write(UC_X86_REG_EBX,self.stream)
        self.u.reg_write(UC_X86_REG_EBP,self.conn)
        self.u.reg_write(UC_X86_REG_ESI,3075)
        self.u.reg_write(UC_X86_REG_ESP,self.stack)
        self.u.emu_start(self.image+0x151936,self.image+0x151943,count=200)
        check(self.u.reg_read(UC_X86_REG_ESP)==self.stack,'budget stack unchanged')
        check(self.u.reg_read(UC_X86_REG_ECX)==self.conn,'serializer receiver preserved')
        check(self.u.reg_read(UC_X86_REG_EBX)==self.stream,'stream preserved')
        return self.u.reg_read(UC_X86_REG_ESI)

for image in (0x400000,0x460000,0xaf0000):
    f=Fixture(image)
    for elapsed in (0,.01,.03,.2):
        for count in (0,1,8,15,16,17,0xffffffff):
            f.w(f.netconn+8,count)
            check(f.packet_type(elapsed)==(5 if count<16 else 0),'bounded per-pass burst, even at same timestamp')
            check(f.r(f.netconn+8)==count,'query does not advance packet accounting')
    # Actual native first-unsent query, including ring wrap, empty and inflight windows.
    for first,count,unsent in ((0,0,0),(0,256,256),(250,20,270),(250,20,269),(100,256,355)):
        f=Fixture(image); f.window(first,count,unsent); f.w(f.netconn+8,1)
        check(f.packet_type(0)==(5 if unsent<first+count else 0),'stop on drained or fully inflight native window')
        f.w(f.netconn+8,0)
        check(f.packet_type(0)==5,'one first packet still lets stock refresh/retry run')
    # Execute the stock list loop which resets all peers independently.
    f=Fixture(image); second=f.netconn+0x900; list1=f.admin+0x800; list2=list1+16
    f.w(f.node+0x70,list1); f.w(list1,f.netconn); f.w(list1+4,list2); f.w(list2,second); f.w(list2+4,0)
    f.w(f.netconn+8,16); f.w(second+8,7)
    f.u.reg_write(UC_X86_REG_ESI,f.node)
    f.u.emu_start(image+0x15be7a,image+0x15be8f,count=100)
    check(f.r(f.netconn+8)==0 and f.r(second+8)==0,'actual stock pass resets each peer')
    # Run ten bounded send passes, with stock counter increments at their actual site.
    # File serialization is not emulated here; the window stays eligible on purpose.
    for _ in range(10):
        f.w(f.netconn+8,0)
        for count in range(16):
            check(f.packet_type(0)==5,'burst progress')
            f.u.reg_write(UC_X86_REG_EBX,f.netconn)
            f.u.emu_start(image+0x15c53a,image+0x15c53d,count=1)
        check(f.packet_type(0)==0,'actual counter caps send loop')
    for state,length in ((0,100),(1,100),(2,0),(2,-1)):
        f=Fixture(image); f.w(f.conn+0x3c,state); f.w(f.conn+0x3fc,length)
        check(f.packet_type(.03)==0,'idle/completed/invalid file stays stock')
        check(f.packet_type(.2)==5,'idle path retains original 100 ms gate')
    # Other native states and frame-budget handling must remain bit-for-bit decisions.
    for condition in ('playing','behind','handshake','disconnected','async'):
        for elapsed in (.01,.03,.2):
            actual=[]
            for patched in (False,True):
                f=Fixture(image,patched)
                if condition=='playing': f.playing=True
                if condition=='behind': f.behind=True
                if condition=='handshake': f.w(f.conn+0x98,0x101)
                if condition=='disconnected': f.w(f.conn+0x98,0)
                if condition=='async': f.w(f.admin+0x2ec,0x100)
                actual.append(f.packet_type(elapsed))
            check(actual[0]==actual[1],'unrelated state unchanged '+condition)
    for received,size,active in ((0,-1,False),(1,0,False),(1,64,True),(2,64,False),(2,65,True),(3,65,False),(25238,1615176,True),(25239,1615176,False),(1,0x7fffffff,True)):
        for fresh in (False,True):
            for sent in (0,1,16):
                f=Fixture(image); f.client(received,size,fresh); f.w(f.netconn+8,sent)
                check(f.packet_type(.03)==(4 if active and fresh and sent==0 else 0),'fast ACK only for new input, unfinished receive, first packet')
                check(f.packet_type(.2)==4,'ACK fallback preserves normal timer including final ACK')
    # Client states not using the normal host branch retain their original decision.
    for role in ('other-peer','server-not-host','async','gameplay','gameplay-fast'):
        for elapsed in (0,.03,.2):
            actual=[]
            for patched in (False,True):
                f=Fixture(image,patched); f.client()
                if role=='other-peer': f.w(f.admin+0x2e8,f.node)
                if role=='server-not-host': f.w(f.admin+0x2e4,f.node)
                if role=='async': f.w(f.admin+0x2ec,1)
                if role.startswith('gameplay'): f.w(f.admin+0x2ec,0x100)
                if role=='gameplay-fast': f.w(f.admin+0x2e1,1)
                actual.append(f.packet_type(elapsed))
            check(actual[0]==actual[1],'unrelated client state unchanged '+role)
    for state,length in ((2,1615176),(0,1615176),(1,1615176),(2,0),(2,-1)):
        for used in (3,143,1024,3075):
            f=Fixture(image)
            active=state==2 and length>0
            check(f.budget(state,length,used)==(9603 if active else 3075)-used,'bounded remaining bit budget')
            check(f.r(f.cave+4096)==int(active),'diagnostic counter changes only for file transfer')
            check(f.r(f.cave+4100)==(7 if active else 0),'generation recorded without protocol change')

result=dict(checks=checks, result='PASS', scope='actual hook instructions and stock packet-type gate; socket/file I/O and live transfer not tested')
(args.out/'native-tests.json').write_text(json.dumps(result,indent=2))
print('FAST_TRANSFER_NATIVE_PASS',json.dumps(result))
