"""Verify native detachment preserves only the custom bridge particle rotation."""
from pathlib import Path
import argparse,json,struct,sys,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=json.loads((a.out/'native/prototype.json').read_text());checks=0
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW)
 code=bytearray((a.out/'native/prototype.bin').read_bytes())
 for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x20000);u.mem_map(0x30000000,0x20000)
 state=cave+m['roadState'];fx=0x20000000;de=fx+0x1000;model=fx+0x2000;root=fx+0x3000;parent=fx+0x4000;newparent=fx+0x5000;calls=[];detach=[True]
 def w(at,x):u.mem_write(at,struct.pack('<I',x))
 def mat(at,x):u.mem_write(at,struct.pack('<9f',*x))
 def readmat(at):return struct.unpack('<9f',u.mem_read(at,36))
 identity=[1,0,0,0,1,0,0,0,1]
 def native(uc,at,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);assert uc.reg_read(UC_X86_REG_ECX)==fx;calls.append(at)
  if detach[0]:w(root+0x24,newparent);mat(root+0x38,identity);mat(root+0x6c,identity)
  uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,struct.unpack('<I',u.mem_read(sp,4))[0])
 for off in [0x2cedb4]:u.hook_add(UC_HOOK_CODE,native,begin=image+off,end=image+off)
 def run(name,arg=None):
  sp=0x3000f000;u.mem_write(sp,struct.pack('<II',0x3001f000,arg or 0));u.reg_write(UC_X86_REG_ESP,sp)
  if arg is None:u.reg_write(UC_X86_REG_ECX,fx)
  u.emu_start(cave+m['exports'][name],0x3001f000,count=100000)
  assert u.reg_read(UC_X86_REG_EIP)==0x3001f000 and u.reg_read(UC_X86_REG_ESP)==sp+4
 w(state,image);run('roads_bind',state)
 for callname in ['bridge_growth_release']:
  for tag,expect in [('paws_bridge_haroun_growth_x_05',True),('paws_bridge_haroun_finish_y_32',True),('paws_bridge_build_smoke_x_05',True),('paws_bridge_build_smoke_y_32',True),('paws_bridge_build_human_scaffold_y_16',True),('paws_bridge_build_gauri_finish_x_32',True),('paws_bridge_build_undead_growth_y_16',True),('paws_bridge_build_shadow_work_x_05',True),('construction_smoke_vfx',False),('haroun_construction_vfx',False),('paws_bridge_human_growth_x_05',False)]:
   for theta in [0,.3,math.pi/2,math.pi,4.5]:
    for parenttheta in [0,.6]:
     rot=[math.cos(theta),-math.sin(theta),0,math.sin(theta),math.cos(theta),0,0,0,1];par=[math.cos(parenttheta),-math.sin(parenttheta),0,math.sin(parenttheta),math.cos(parenttheta),0,0,0,1]
     w(fx+0x10,de);w(de+8,de+0x100);u.mem_write(de+0x100,(tag+'\0').encode('utf-16le'));w(fx+0xac,model);w(model+4,2);w(model+12,root);w(root+0x24,parent);mat(root+0x6c,rot);mat(newparent+0x6c,par)
     before=len(calls);run(callname);assert len(calls)==before+1;checks+=1
     expected=rot if expect else identity;assert all(abs(x-y)<1e-6 for x,y in zip(readmat(root+0x6c),expected));checks+=1
     local=readmat(root+0x38);actual=[sum(par[i*3+k]*local[k*3+j] for k in range(3)) for i in range(3) for j in range(3)]
     if expect:assert all(abs(x-y)<1e-6 for x,y in zip(actual,rot));checks+=1
 # Native no-op detachment leaves the original local transform untouched.
 detach[0]=False;w(root+0x24,parent);mat(root+0x38,identity);before=len(calls);run('bridge_growth_release');assert len(calls)==before+1 and readmat(root+0x38)==tuple(identity);checks+=1
print('BRIDGE_EFFECT_DETACH_PASS',checks,'both image bases, original native lifecycle, growth and finish only')
