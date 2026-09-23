"""ABI/ownership tests of compiled x86, plus original native click/sound code.
Allocation, string pooling and child-list services are stubbed; not a render test.
"""
from pathlib import Path
import argparse, struct, sys, json
p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.analysis/'pydeps_readable'),str(a.analysis/'lobby_colors_1372/deps_r15')]
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
beta=Path(__file__).resolve().parents[1]/'beta7'
raw=(beta/'PawCommonUiPayload.bin').read_bytes();fix=(beta/'PawCommonUiFixups.bin').read_bytes()
native=(a.analysis/'k2_runtime_1372_20260904.bin').read_bytes()
checks=0
def check(ok,msg):
 global checks
 checks+=1
 assert ok,msg
def relocate(image,cave):
 b=bytearray(raw)
 for pos in range(4,len(fix),12):
  kind,off,value=struct.unpack_from('<III',fix,pos)
  v={1:image+value,2:cave+value,3:image+value-(cave+off+4)}[kind]
  struct.pack_into('<I',b,off,v&0xffffffff)
 return bytes(b)
def rd(u,p):return struct.unpack('<I',u.mem_read(p,4))[0]
def wr(u,p,x):u.mem_write(p,struct.pack('<I',x&0xffffffff))
layouts=[(0x460000,0x10000000),(0x80000,0x2ec0000),(0x6a0000,0x19000000)]
for image,cave in layouts:
 for accepted in (False,True):
  u=Uc(UC_ARCH_X86,UC_MODE_32)
  for addr,size in ((image,0x700000),(cave,0x1000),(0x20000000,0x10000),(0x30000000,0x20000)):u.mem_map(addr,size)
  u.mem_write(cave,relocate(image,cave))
  u.mem_write(image+0x81d0f,native[0x81d0f:0x81d1d])
  # The original indirect call is the Game's native one-argument AddChild.
  # Its wrapper tail calls the same attachment service used by our button.
  u.mem_write(image+0x81d16,struct.pack('<i',(image+0x2b7486)-(image+0x81d15+5)))
  parent,child,string,control=0x30001000,0x30002000,0x30003000,0x30004000
  end=0x20000010;sp=0x20008000
  regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
  vtable=0x30005000;wr(u,vtable+0xd0,image+0x81d0f)
  initial=[0x11,parent,parent,vtable,0x555,0x666,0x777]
  for reg,val in zip(regs,initial):u.reg_write(reg,val)
  u.reg_write(UC_X86_REG_EFLAGS,0x246);u.reg_write(UC_X86_REG_ESP,sp)
  u.reg_write(UC_X86_REG_XMM0,0x123456789abcdef);u.reg_write(UC_X86_REG_FPCW,0x37f)
  wr(u,sp,end);wr(u,sp+4,control)
  calls=[]
  def ret(stack_args,result=None):
   s=u.reg_read(UC_X86_REG_ESP);target=rd(u,s)
   if result is not None:u.reg_write(UC_X86_REG_EAX,result)
   u.reg_write(UC_X86_REG_ESP,s+4+stack_args);u.reg_write(UC_X86_REG_EIP,target)
  def hook(u,pc,size,data):
   s=u.reg_read(UC_X86_REG_ESP);ecx=u.reg_read(UC_X86_REG_ECX)
   if pc==image+0x205de:
    check(rd(u,s+4)==cave+0x700,'UTF16 name pointer');check(bytes(u.mem_read(cave+0x700,38)).decode('utf-16le')=='PawGoldSoundButton\0','widget name')
    wr(u,ecx,string+16);calls.append('string');ret(4)
   elif pc==image+0x2b88c0:
    check(rd(u,rd(u,s+4))==string+16,'name object');check([rd(u,s+i) for i in (8,12,16,20)]==[1,0,0,0],'enabled, no actions/client')
    calls.append('create');u.reg_write(UC_X86_REG_XMM0,0);u.reg_write(UC_X86_REG_FPCW,0x27f);ret(0,child)
   elif pc==image+0x21375:
    check(ecx==string,'release native pooled string');calls.append('release');ret(0)
   elif pc==image+0x2b7486:
    if rd(u,s+4)==control:
     check(ecx==parent and rd(u,s+8)==0,'original EconomyBar attachment retained');calls.append('original');ret(8,1);return
    check(ecx==parent and rd(u,s+4)==child and rd(u,s+8)==0,'root child ownership');check(rd(u,child)==cave+0x200,'private UI vtable')
    calls.append('attach');ret(8,int(accepted))
   elif pc==image+0xb8b33:
    check(ecx==child and rd(u,s+4)==1,'delete unattached widget');calls.append('delete');ret(4,child)
  u.hook_add(UC_HOOK_CODE,hook)
  u.emu_start(cave+0x600,end,count=1000)
  check(calls==['original','string','create','release','attach']+([] if accepted else ['delete']),'balanced construction/ownership')
  check(u.reg_read(UC_X86_REG_ESP)==sp+8,'ret4 calling convention')
  initial[0]=1
  for reg,val in zip(regs,initial):check(u.reg_read(reg)==val,'preserved register '+str(reg))
  check(u.reg_read(UC_X86_REG_EFLAGS)==0x246,'preserved flags')
  check(u.reg_read(UC_X86_REG_XMM0)==0x123456789abcdef and u.reg_read(UC_X86_REG_FPCW)==0x37f,'preserved FP/SSE')
  # Programmatic activation cannot dereference an absent simulation action.
  u.reg_write(UC_X86_REG_ESP,sp);wr(u,sp,end);u.reg_write(UC_X86_REG_ECX,child)
  u.emu_start(rd(u,cave+0x200+0x6c),end,count=20)
  check(u.reg_read(UC_X86_REG_ESP)==sp+4,'safe actionless activation')
  for off in range(0,0xd4,4):
   want=rd(u,cave+0x200+off)
   original=struct.unpack_from('<I',native,0x504be4+off)[0]-0x460000+image
   check(want==(cave+0x780 if off==0x6c else cave+0x790 if off==0xa8 else original),'native vtable entry preserved')
  u.mem_write(end,bytes.fromhex('d91d00600030')) # fstp dword [0x30006000]
  u.reg_write(UC_X86_REG_ESP,sp);wr(u,sp,end)
  u.emu_start(rd(u,cave+0x2a8),end+6,count=20)
  check(rd(u,0x30006000)==0,'normal child sort key = 0.0')
# Run original click-state and release/cancel code at its preferred image base.
image,cave=layouts[0];u=Uc(UC_ARCH_X86,UC_MODE_32)
for addr,size in ((image,0x700000),(cave,0x1000),(0x20000000,0x10000),(0x30000000,0x10000)):u.mem_map(addr,size)
u.mem_write(image,native[:0x700000]);u.mem_write(cave,relocate(image,cave))
child=0x30002000;sp=0x20008000;end=0x20000010;wr(u,child,cave+0x200);wr(u,child+0x6c,12345)
sounds=[];queued=[]
def click_hook(u,pc,size,data):
 if pc not in (image+0x1e96a,image+0xcd1da):return
 s=u.reg_read(UC_X86_REG_ESP);arg=rd(u,s+4)
 if pc==image+0x1e96a:sounds.append(arg);n=32
 else:queued.append(arg);check(arg==0,'no actor/team command queued');n=12
 u.reg_write(UC_X86_REG_EIP,rd(u,s));u.reg_write(UC_X86_REG_ESP,s+4+n)
u.hook_add(UC_HOOK_CODE,click_hook)
def run(rva,args):
 u.reg_write(UC_X86_REG_ECX,child);u.reg_write(UC_X86_REG_ESP,sp);wr(u,sp,end)
 for i,v in enumerate(args):wr(u,sp+4+i*4,v)
 u.emu_start(image+rva,end,count=1000)
 check(u.reg_read(UC_X86_REG_ESP)==sp+4+len(args)*4,'native click stack')
for release in (0x2b8aef,0x2b8b30):
 run(0x2b8b5d,[1]);run(0x2b8b5d,[1]);run(release,[])
 check(rd(u,child+0x24)&0x100==0,'released/cancelled pressed state')
check(sounds==[12345,0,12345,0],'one native set sound per click; silent unset')
check(queued==[0,0],'only null commands passed to guarded native queue')
# Original sorted-list insertion: World already exists; attach EconomyBar,
# button, SidePanel/F1-F4, then later ControlPanel. Menus remain above button.
heap=[0x30008000]
def alloc_hook(u,pc,size,data):
 if pc!=image+0x2ef03c:return
 s=u.reg_read(UC_X86_REG_ESP);check(rd(u,s+4)==16,'native list node allocation')
 u.reg_write(UC_X86_REG_EAX,heap[0]);heap[0]+=16
 u.reg_write(UC_X86_REG_EIP,rd(u,s));u.reg_write(UC_X86_REG_ESP,s+4)
u.hook_add(UC_HOOK_CODE,alloc_hook)
for panels in ((903,904),(904,903)):
 listing=0x30007000;u.mem_write(listing,bytes(8))
 for item,key in ((900,0),(901,1),(902,0),*((p,0) for p in panels)):
  wr(u,0x30007100,item);wr(u,0x30007104,0x3f800000 if key else 0)
  u.reg_write(UC_X86_REG_ECX,listing);u.reg_write(UC_X86_REG_ESP,sp);wr(u,sp,end)
  for i,v in enumerate((0x30007108,0x30007100,0x30007104,1)):wr(u,sp+4+4*i,v)
  u.emu_start(image+0x2aec5e,end,count=1000)
  check(u.reg_read(UC_X86_REG_ESP)==sp+20,'native sorted insertion stack')
 node=rd(u,listing);order=[]
 while node:order.append(rd(u,node));node=rd(u,node+8)
 check(order==[900,902,*panels,901],'world < button < menus; EconomyBar unchanged')
a.out.mkdir(parents=True,exist_ok=True)
(a.out/'sound-button-native-tests.json').write_text(json.dumps({'checks':checks,'passed':True,'layouts':len(layouts),'realNativeClickCode':True,'servicesStubbed':True,'liveRenderValidated':False},indent=2))
print('SOUND_BUTTON_NATIVE_PASS',checks)
