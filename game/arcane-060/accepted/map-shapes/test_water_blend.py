"""Execute the compiled water hooks: opacity, chunk ownership, isolation, ABI."""
import argparse,json,struct,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
m=json.loads((a.out/'native/prototype.json').read_text());blob=(a.out/'native/prototype.bin').read_bytes();checks=0
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW)
 code=bytearray(blob)
 for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x400000);u.mem_map(0x30000000,0x20000)
 def w(at,v):u.mem_write(at,struct.pack('<I',v&0xffffffff))
 def f(at,v):u.mem_write(at,struct.pack('<f',v))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 def rf(at):return struct.unpack('<f',u.mem_read(at,4))[0]
 world=0x20000000;session=world+0x1000;view=world+0x2000;grid=world+0x3000;tiles=world+0x10000
 self=world+0x5000;chunk=world+0x6000;shape=world+0x7000;geo=world+0x8000;verts=world+0x9000;colors=world+0xa000;cells=world+0xb000;points=world+0xc000
 state=cave+m['state'];w(state,image);w(state+4,cave+m['adapter']);w(image+0x5f3fb8,world);w(image+0x5f3fe4,session);w(image+0x5f3fa8,view)
 w(session+0xf0,2);w(world+0x30,grid);w(grid+0x1c,16);w(grid+0x20,16);w(grid+0x28,tiles);w(view+0xa8,8);w(view+0xb4,2);w(view+0x70,view+0x400)
 w(self,chunk);w(self+4,shape);w(shape+0xcc,geo);w(geo+0x20,verts);w(geo+0x28,colors);u.mem_write(geo+0xc,struct.pack('<H',1))
 defs=[];variants=[];alphas=[.6,.5,.8,.7,.6,.5];profiles={}
 for i,name in enumerate(['temperate_lake','arctic_lake','desert_lake','cursed_lake','temperate_river','arctic_river']):
  de=world+0x20000+i*0x1000;va=de+0x200;pr=de+0x400;table=de+0x500;defs.append(de);variants.append(va)
  w(de+8,de+0x100);u.mem_write(de+0x100,(name+'\0').encode('utf-16le'));w(va+0x1c,de);w(pr+8,table);w(pr+12,2)
  u.mem_write(table,struct.pack('<10f',0,1,1,1,0,3,1,1,1,alphas[i]));profiles[de]=pr
 # Real x87 native floor ABI, constant bed at -2; depth=1.5 => alpha/2.
 bed=world+0xd000;f(bed,-2);u.mem_write(image+0x2424d0,b'\xd9\x05'+struct.pack('<I',bed)+b'\xc2\x08\x00')
 captured=[]
 def native(uc,at,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);ret=0
  if at==image+0x70e6f:ret=profiles.get(r(sp+4),0)
  elif at==image+0x1b29dc:
   vec=r(sp+4);captured.append([(r(r(vec)+j*8),r(r(vec)+j*8+4))for j in range(r(vec+4))]);ret=0x1234
  elif at==image+0x398e00:
   assert uc.reg_read(UC_X86_REG_ECX)==geo+0x10 and r(sp+4)==1 and r(sp+8)==verts
   uc.reg_write(UC_X86_REG_EAX,0x5678);uc.reg_write(UC_X86_REG_ESP,sp+12);uc.reg_write(UC_X86_REG_EIP,r(sp));return
  else:raise AssertionError(hex(at))
  uc.reg_write(UC_X86_REG_EAX,ret);uc.reg_write(UC_X86_REG_ESP,sp+8);uc.reg_write(UC_X86_REG_EIP,r(sp))
 for off in [0x70e6f,0x1b29dc,0x398e00]:u.hook_add(UC_HOOK_CODE,native,begin=image+off,end=image+off)
 def run(name,values,ecx=0):
  sp=0x3000f000;u.mem_write(sp,struct.pack('<'+'I'*(len(values)+1),0x3001f000,*values));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,ecx)
  u.emu_start(cave+m['exports'][name],0x3001f000,count=10000000)
  assert u.reg_read(UC_X86_REG_EIP)==0x3001f000 and u.reg_read(UC_X86_REG_ESP)==sp+4
  return u.reg_read(UC_X86_REG_EAX)
 def paint(fn):
  for y in range(16):
   for x in range(16):
    slot=fn(x,y);c=tiles+(y*16+x)*48;w(c,variants[max(0,slot)]);w(c+0x20,0x120 if slot>=0 else 0)
 def blend(slot,x,y,alpha=None):
  w(self+8,defs[slot]);u.mem_write(verts,struct.pack('<3f',x,y,-.5));u.mem_write(colors,struct.pack('<4f',.2,.3,.4,alphas[slot]/2 if alpha is None else alpha))
  run('water_blend_vertices',[state,self]);rgba=struct.unpack('<4f',u.mem_read(colors,16));assert all(math.isfinite(v)for v in rgba)and 0<=rgba[3]<=1.00001
  assert all(abs(a-b)<1e-6 for a,b in zip(rgba[:3],[.2,.3,.4]));return rgba[3]
 # Two- and four-way seams: standard alpha-over keeps the native weighted
 # opacity, without double-opacity or holes, including arbitrary shore alpha.
 paint(lambda x,y:0 if x<8 else 2)
 for x in [15,15.25,15.5,15.75,16,16.25,16.5,16.75,17]:
  a0=blend(0,x,16);a2=blend(2,x,16);t=(x-15)/2
  assert abs(1-(1-a0)*(1-a2)-(.3*(1-t)+.4*t))<1e-5;checks+=3
 paint(lambda x,y:(0 if x<8 else 2)+(0 if y<8 else 1))
 al=[blend(j,16,16)for j in range(4)]
 assert abs(1-math.prod(1-v for v in al)-sum(alphas[:4])/8)<1e-5;checks+=5
 # Unmixed water retains all native vertex components exactly; land and
 # unsupported bogs never get new water polygons or a renderer replacement.
 paint(lambda x,y:0)
 assert abs(blend(0,15,16,.123)-.123)<1e-6;checks+=1
 before=bytes(u.mem_read(tiles,16*16*48))
 paint(lambda x,y:0 if x<8 else 2)
 # All source chunks together add each foreign (tile,material) once.
 added={};original=set()
 for slot in [0,2]:
  w(self+8,defs[slot])
  for cy in range(4):
   for cx in range(4):
    w(chunk+0xac,cx);w(chunk+0xb0,cy);pts=[(x,y)for y in range(4)for x in range(4)if (0 if cx*4+x<8 else 2)==slot]
    if not pts:continue
    u.mem_write(points,b''.join(struct.pack('<2I',*pt)for pt in pts));w(cells,points);w(cells+4,len(pts));w(cells+8,len(pts))
    assert run('water_build_blended',[state,self,cells])==0x1234;out=captured[-1];assert len(set(out))==len(out)
    for x,y in out:
     x=struct.unpack('<i',struct.pack('<I',x))[0]+cx*4;y=struct.unpack('<i',struct.pack('<I',y))[0]+cy*4
     assert 0<=x<16 and 0<=y<16
     if (0 if x<8 else 2)!=slot:added[(x,y,slot)]=added.get((x,y,slot),0)+1
    checks+=2
 assert len(added)==32 and set(added.values())=={1};checks+=2
 # No world writes. Network sessions tail through the original builder and
 # leave native colors untouched, even at an otherwise blended seam.
 unchanged=bytes(u.mem_read(tiles,16*16*48));u.mem_write(session+0x100,b'\1');assert abs(blend(0,16,16,.123)-.123)<1e-6
 assert bytes(u.mem_read(tiles,16*16*48))==unchanged;checks+=2
 # Execute the actual emitted adapters, including native callee cleanup and
 # preservation of live registers/SSE while forwarding the original args.
 for site,args,native_self,expected in [(0x1b25de,[cells],self,0x1234),(0x1b2790,[1,verts],geo+0x10,0x5678)]:
  entry=cave+next(h['entry']for h in m['hooks']if h['site']==site);sp=0x3000f000
  u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x3001f000,*args))
  saved={UC_X86_REG_EBX:self,UC_X86_REG_ESI:0x12345678,UC_X86_REG_EDI:0x23456789,UC_X86_REG_EBP:0x34567890}
  for reg,v in saved.items():u.reg_write(reg,v)
  xmm=0x112233445566778899aabbccddeeff00;u.reg_write(UC_X86_REG_XMM3,xmm);u.reg_write(UC_X86_REG_ECX,native_self);u.reg_write(UC_X86_REG_ESP,sp)
  u.emu_start(entry,0x3001f000,count=10000000)
  assert u.reg_read(UC_X86_REG_EIP)==0x3001f000 and u.reg_read(UC_X86_REG_ESP)==sp+4+4*len(args) and u.reg_read(UC_X86_REG_EAX)==expected
  assert all(u.reg_read(reg)==v for reg,v in saved.items())and u.reg_read(UC_X86_REG_XMM3)==xmm;checks+=3
print(checks,'PASS: compiled native water opacity, four-biome seams, unique chunk coverage, world isolation and relocated ABI')
