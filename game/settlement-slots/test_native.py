"""Exercise the original engine's dynamic layout with the new widget counts."""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
legacy=Path(a.legacy);sys.path.insert(0,str(legacy/'lobby_colors_1372/deps_r15'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP,UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP
raw=(legacy/'k2_runtime_1372_20260904.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
for off,b in [(0xE1C7D,'6a0750e81e9bfdff83c40c'),(0xBB4C8,'6a0850e8d302000083c40c'),
              (0xE2361,'8b750c8d4f746a0133db'),(0xE243B,'3b9f8c0000007c95')]:
    assert raw[off:off+len(bytes.fromhex(b))]==bytes.fromhex(b),(hex(off),'guard changed')
# Verify center-inclusion is enabled only by the city-list caller, and that
# update/hide loops are bounded by the same dynamic count, not another constant.
assert raw[0xBB4ED:0xBB4F4]==bytes.fromhex('c6809000000001')
assert raw[0xBB4F7:0xBB4FE]==bytes.fromhex('c6809100000001')
assert raw[0xE29AF:0xE29B7]==bytes.fromhex('3bb78c0000007ce3')
checks=7
BASE=0x460000;OBJ=0x50000000;STACK=0x60000000;STOP=0x70000000;RESULT=OBJ+0xF000
pack=lambda v:struct.pack('<I',v)
def run(count,horizontal,width,height,cw,ch,border,sep,uniform=True):
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(BASE,(len(raw)+4095)&~4095);u.mem_write(BASE,raw)
    if uniform:
        code=bytearray((a.native/'payload.bin').read_bytes())
        for off in json.loads((a.native/'payload.json').read_text())['fixups']:
            struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+BASE-0x460000+0x10000000-CAVE)&0xffffffff)
        u.mem_map(CAVE,0x1000);u.mem_write(CAVE,bytes(code))
        u.mem_write(BASE+0xE2618,b'\xe9'+pack((CAVE-BASE-0xE2618-5)&0xffffffff)+b'\x90'*3)
    u.mem_map(OBJ,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
    def wi(a,v):u.mem_write(a,pack(v))
    def wf(a,v):u.mem_write(a,struct.pack('<f',v))
    def rf(a):return struct.unpack('<f',u.mem_read(a,4))[0]
    def ri(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    wi(OBJ+0x74,OBJ+0x100);wi(OBJ+0x8C,count);u.mem_write(OBJ+0x90,bytes([horizontal]))
    wf(OBJ+0x80,border);wf(OBJ+0x84,border);wf(OBJ+0x88,sep)
    wf(OBJ+0x300,width);wf(OBJ+0x304,height)
    children=[OBJ+0x1000+i*0x400 for i in range(count)]
    for i,c in enumerate(children):wi(OBJ+0x100+i*4,c);wf(c+0x300,cw);wf(c+0x304,ch)
    # Only external widget accessors and floor() are mocked. All iteration,
    # count arithmetic and placement execute real game instructions.
    u.mem_write(BASE+0x2B7E47,b'\xc3')
    u.mem_write(BASE+0x2B6FC8,bytes.fromhex('d98100030000c3'))
    u.mem_write(BASE+0x2B6FF2,bytes.fromhex('d98104030000c3'))
    u.mem_write(BASE+0x2B701C,bytes.fromhex('c20800'))
    u.mem_write(BASE+0x3F5180,b'\xdd\x05'+pack(RESULT)+b'\xc3')
    placed=[]
    def hook(uc,address,size,_):
        sp=uc.reg_read(UC_X86_REG_ESP);c=uc.reg_read(UC_X86_REG_ECX)
        if address==BASE+0x2B701C:
            x,y=rf(sp+4),rf(sp+8);placed.append((c,x,y))
        elif address==BASE+0x3F5180:
            v=struct.unpack('<d',uc.mem_read(sp+4,8))[0]
            uc.mem_write(RESULT,struct.pack('<d',math.floor(v)))
    u.hook_add(UC_HOOK_CODE,hook)
    wi(STACK+0xF000,STOP);u.reg_write(UC_X86_REG_ESP,STACK+0xF000);u.reg_write(UC_X86_REG_ECX,OBJ)
    saved={UC_X86_REG_EBX:0xBAADF00D,UC_X86_REG_ESI:0x12345678,UC_X86_REG_EDI:0xABCDEF01,UC_X86_REG_EBP:0x13572468}
    for reg,v in saved.items():u.reg_write(reg,v)
    u.emu_start(BASE+0xE25E2,STOP,count=10000)
    assert u.reg_read(UC_X86_REG_EIP)==STOP
    assert u.reg_read(UC_X86_REG_ESP)==STACK+0xF004
    for reg,v in saved.items():assert u.reg_read(reg)==v
    assert [c for c,x,y in placed]==children,(count,placed)
    for c,x,y in placed:
        assert x>=0 and y>=0 and x+cw<=width+0.01 and y+ch<=height+0.01,(count,x,y,width,height)
    for i,(_,x,y) in enumerate(placed):
        for _,xx,yy in placed[:i]:
            assert x+cw<=xx+0.01 or xx+cw<=x+0.01 or y+ch<=yy+0.01 or yy+ch<=y+0.01
    if horizontal and uniform:
        gaps=[placed[i][1]-placed[i-1][1]-cw for i in range(1,count)]
        assert max(gaps)-min(gaps)<0.001,(count,gaps)
        assert abs(placed[-1][1]+cw+border-width)<0.01
    return [(x,y) for c,x,y in placed]
for BASE,CAVE in [(0x460000,0x10000000),(0xE40000,0x21000000),(0x12000000,0x61000000)]:
    for scale in (1,1.25,1.5,2):
        old=run(7,0,208*scale,114*scale,47*scale,53*scale,0,0,False)
        new=run(8,0,208*scale,114*scale,47*scale,53*scale,0,0)
        assert new[:7]==old  # Existing bottom slots keep their exact positions.
        run(9,1,440*scale,50*scale,38*scale,38*scale,5*scale,20*scale)
        run(9,1,440*scale,58*scale,38*scale,48*scale,5*scale,20*scale)
        checks+=5
print('SETTLEMENT_SLOTS_NATIVE_PASS',checks,'guards/layout cases; equal gaps and right edge; ABI; 3 ASLR bases, four scales')
