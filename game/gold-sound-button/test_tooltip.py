"""Actual relocated anchor wrapper; native text measurement is stubbed."""
from pathlib import Path
import argparse,sys,struct,json
p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.analysis/'lobby_colors_1372/deps_r15'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
beta=Path(__file__).resolve().parents[1]/'beta7';raw=(beta/'PawCommonUiPayload.bin').read_bytes();fix=(beta/'PawCommonUiFixups.bin').read_bytes();checks=0
native=(a.analysis/"k2_runtime_1372_20260904.bin").read_bytes()
def check(ok,why):
 global checks
 checks+=1;assert ok,why
for image,cave in [(0x460000,0x10000000),(0x80000,0x2ec0000),(0x6a0000,0x19000000)]:
 for source in ('button','other','no-source','no-tooltip','no-manager'):
  u=Uc(UC_ARCH_X86,UC_MODE_32)
  for addr,size in [(image,0x700000),(cave,0x1000),(0x30000000,0x10000)]:u.mem_map(addr,size)
  def wr(p,v):u.mem_write(p,struct.pack('<I',v))
  def rd(p):return struct.unpack('<I',u.mem_read(p,4))[0]
  code=bytearray(raw)
  for pos in range(4,len(fix),12):
   kind,off,value=struct.unpack_from('<III',fix,pos);v={1:image+value,2:cave+value,3:image+value-(cave+off+4)}[kind];struct.pack_into('<I',code,off,v&0xffffffff)
  u.mem_write(cave,bytes(code));manager,tip,child,owner,rect,sp,end=[0x30000000+n for n in (0x1000,0x2000,0x3000,0x4000,0x5000,0x8000,0xf000)]
  wr(image+0x5f3fc0,0 if source=='no-manager' else manager);wr(manager+0x104,0 if source=='no-tooltip' else tip);wr(tip+0x74,0 if source=='no-source' else child);wr(child,cave+0x200 if source=='button' else image+0x504be4)
  wr(image+0x458c40,0x3f800000)
  wr(tip+0xb4,struct.unpack('<I',struct.pack('<f',12.0))[0])
  original=[0x44800000,0x44100000,0x438d8000]
  for off,val in zip((0x94,0x98,0x9c),original):wr(owner+off,val)
  wr(owner+0xa4,0xfeed0101);called=[]
  def hook(u,pc,size,data):
   if pc==image+0x1b0f17:
    s=u.reg_read(UC_X86_REG_ESP)
    check([rd(s+i) for i in (4,12,16,20,24,28,32)]==[123,456,0,0,0x447a0000,0,0], 'measure original formatted title with native font')
    check(bytes(u.mem_read(rd(s+8),8))==bytes(8),'measurement starts with zero width and height')
    u.mem_write(rd(s+8),struct.pack('<ff',64.0,14.0))
    u.reg_write(UC_X86_REG_ECX,0xbad);u.reg_write(UC_X86_REG_EDX,0xbad)
    u.reg_write(UC_X86_REG_EIP,rd(s));u.reg_write(UC_X86_REG_ESP,s+4)
    return
   if pc!=image+0x2b8185:return
   s=u.reg_read(UC_X86_REG_ESP);check(u.reg_read(UC_X86_REG_ECX)==owner,'native interface receiver')
   check([rd(s+i) for i in (4,8,12)]==[123,456,rect],'native text/font/rectangle arguments')
   values=[rd(owner+o) for o in (0x94,0x98,0x9c)]
   check(values==([0x447f0000,0x44000000,0x42b20000] if source=='button' else original),'only own button anchor changed')
   check(rd(owner+0xa4)==(0xfeed0100 if source=='button' else 0xfeed0101),'only downward byte changed')
   called.append(1);wr(rect,0xabcdef);u.reg_write(UC_X86_REG_EAX,rect);u.reg_write(UC_X86_REG_EIP,rd(s));u.reg_write(UC_X86_REG_ESP,s+16)
  u.hook_add(UC_HOOK_CODE,hook);wr(sp,end)
  for n,v in enumerate((123,456,rect)):wr(sp+4+n*4,v)
  u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,owner);u.reg_write(UC_X86_REG_ESI,0x98765432);u.reg_write(UC_X86_REG_EDI,0x12345678);u.reg_write(UC_X86_REG_EBP,0xabcdef01)
  u.emu_start(cave+0xa00,end,count=1000)
  check(called==[1] and rd(rect)==0xabcdef,'one native layout and its output retained')
  check([rd(owner+o) for o in (0x94,0x98,0x9c)]==original and rd(owner+0xa4)==0xfeed0101,'anchor restored for subsequent tooltips')
  check(u.reg_read(UC_X86_REG_EDI)==0x12345678 and u.reg_read(UC_X86_REG_ESI)==0x98765432 and u.reg_read(UC_X86_REG_EBP)==0xabcdef01,'nonvolatile registers')
  check(u.reg_read(UC_X86_REG_ESP)==sp+16 and u.reg_read(UC_X86_REG_EAX)==rect,'ABI/return preserved')
# Native formatter RVA E7A09 tests the body length before inserting either
# separator. Execute that branch, not a reimplementation of its condition.
u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x460000,0x700000);u.mem_write(0x460000,native)
u.mem_map(0x30000000,0x10000)
u.mem_write(0x30001000,struct.pack('<I',0x30002010));u.mem_write(0x30002004,bytes(4))
u.mem_write(0x30008000,struct.pack('<II',0x3000f000,0x30001000))
u.reg_write(UC_X86_REG_ESP,0x30008000);u.reg_write(UC_X86_REG_ECX,0) # any formatting call would fail
u.emu_start(0x547a09,0x3000f000,count=40)
check(u.reg_read(UC_X86_REG_ESP)==0x30008008,'empty body returns without adding paragraph separators')

a.out.mkdir(parents=True,exist_ok=True);(a.out/'tooltip-native-tests.json').write_text(json.dumps({'checks':checks,'passed':True,'textMeasurementStubbed':True},indent=2));print('BUTTON_TOOLTIP_PASS',checks)
