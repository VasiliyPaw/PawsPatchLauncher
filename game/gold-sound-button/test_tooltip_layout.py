"""Run the shipped anchor hook and original native rectangle layout together.

Only font measurement and the tooltip-manager getter are stubbed. Different
glyph sizes verify fitted width/height instead of a fixed empty panel.
"""
import argparse,json,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.analysis/'lobby_colors_1372/deps_r15'))
sys.path.insert(0,str(a.analysis/'pydeps_readable'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
native=(a.analysis/'k2_runtime_1372_20260904.bin').read_bytes()
root=Path(__file__).resolve().parents[1]/'beta7'
payload=(root/'PawCommonUiPayload.bin').read_bytes();fix=(root/'PawCommonUiFixups.bin').read_bytes()
checks=0
def check(ok,why):
    global checks
    checks+=1;assert ok,why
for image,cave in [(0x460000,0x10000000),(0x80000,0x2ec0000),(0x6a0000,0x19000000)]:
 for width,height in [(64.,14.),(80.,18.),(96.,20.)]:
  u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,0x700000);u.mem_write(image,native)
  u.mem_map(cave,0x1000);u.mem_map(0x30000000,0x10000)
  def wr(p,v):u.mem_write(p,struct.pack('<I',v))
  def rd(p):return struct.unpack('<I',u.mem_read(p,4))[0]
  def rf(p):return struct.unpack('<f',u.mem_read(p,4))[0]
  def wf(p,v):u.mem_write(p,struct.pack('<f',v))
  md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
  for ins in md.disasm(native[0x2b8185:0x2b82d3],0x718185):
   if ins.disp_size==4 and 0x460000<=ins.disp<0xb60000:
    wr(image+ins.address-0x460000+ins.disp_offset,image+ins.disp-0x460000)
  code=bytearray(payload)
  for at in range(4,len(fix),12):
   kind,off,value=struct.unpack_from('<III',fix,at)
   result={1:image+value,2:cave+value,3:image+value-(cave+off+4)}[kind]
   struct.pack_into('<I',code,off,result&0xffffffff)
  u.mem_write(cave,bytes(code))
  manager,tip,child,owner,rect,sp,end=[0x30000000+n for n in (0x1000,0x2000,0x3000,0x4000,0x5000,0x8000,0xf000)]
  wr(image+0x5f3fc0,manager);wr(manager+0x104,tip);wr(tip+0x74,child);wr(child,cave+0x200)
  wf(tip+0xb4,12.);wf(tip+0xb8,6.);calls=[]
  def hook(u,pc,size,data):
   s=u.reg_read(UC_X86_REG_ESP)
   if pc==image+0x2bca18:
    u.reg_write(UC_X86_REG_EAX,tip);u.reg_write(UC_X86_REG_EIP,rd(s));u.reg_write(UC_X86_REG_ESP,s+4)
   elif pc==image+0x1b0f17:
    check(rd(s+4)==123 and rd(s+12)==456,'same text and font in both measurements')
    calls.append(rf(s+24));u.mem_write(rd(s+8),struct.pack('<ff',width,height))
    u.reg_write(UC_X86_REG_EIP,rd(s));u.reg_write(UC_X86_REG_ESP,s+4)
  u.hook_add(UC_HOOK_CODE,hook);u.mem_write(sp,struct.pack('<IIII',end,123,456,rect))
  u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,owner)
  u.emu_start(cave+0xa00,end,count=1000)
  left,top,right,bottom=struct.unpack('<ffff',u.mem_read(rect,16));epsilon=rf(image+0x458c40)
  check(calls==[1000.,width+epsilon],'title measurement determines the native wrapping width')
  check(abs(right-left-(width+24.+2*epsilon))<0.001,'width follows glyphs plus native padding')
  check(abs(bottom-top-(height+12.+epsilon))<0.001,'one title line plus native vertical padding')
  check(right==1020. and bottom==512.,'above button and aligned to its right edge')
  check(u.reg_read(UC_X86_REG_ESP)==sp+16,'native stack convention')
a.out.mkdir(parents=True,exist_ok=True)
(a.out/'tooltip-layout-tests.json').write_text(json.dumps(dict(passed=True,checks=checks,originalNativeLayout=True,fontMeasurementStubbed=True,gameLaunched=False),indent=2))
print('BUTTON_NATIVE_LAYOUT_PASS',checks)
