"""Round-trip compact bridge water records through the compiled payload."""
from pathlib import Path
import sys,argparse,json,struct
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=json.loads((a.out/'native/prototype.json').read_text());blob=(a.out/'native/prototype.bin').read_bytes();checks=0
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW);code=bytearray(blob)
 for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x200000);u.mem_map(0x30000000,0x20000)
 world=0x20000000;state=cave+m['roadState'];grid=world+0x1000;tiles=world+0x10000;manager=world+0xe0000;defs=manager+0x1000;listing=manager+0x8000;arena=[world+0x100000]
 def w(at,v):u.mem_write(at,struct.pack('<I',v&0xffffffff))
 def f(at,v):u.mem_write(at,struct.pack('<f',v))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 def text(at):
  out=bytearray()
  while True:
   c=bytes(u.mem_read(at,2));at+=2
   if c==b'\0\0':return out.decode('utf-16le')
   out.extend(c)
 def native(uc,at,size,data):
  sp=uc.reg_read(UC_X86_REG_ESP);src=r(sp+4);s=text(src);dest=arena[0]+16;arena[0]+=len(s)*2+48;u.mem_write(dest,s.encode('utf-16le')+b'\0\0');w(dest-12,len(s));w(uc.reg_read(UC_X86_REG_ECX),dest);uc.reg_write(UC_X86_REG_EAX,0);uc.reg_write(UC_X86_REG_ESP,sp+8);uc.reg_write(UC_X86_REG_EIP,r(sp))
 u.hook_add(UC_HOOK_CODE,native,begin=image+0x205de,end=image+0x205de)
 def run(name,args):
  sp=0x3000f000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x3001f000,*args));u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(cave+m['exports'][name],0x3001f000,count=10000000);assert u.reg_read(UC_X86_REG_EIP)==0x3001f000 and u.reg_read(UC_X86_REG_ESP)==sp+4;return u.reg_read(UC_X86_REG_EAX)
 w(state,image);w(state+4,cave+m['adapter']);w(state+12,world);w(state+16,12345);w(world+0x30,grid);w(grid+4,1);w(grid+28,128);w(grid+32,128);w(grid+40,tiles);w(image+0x5f0030,manager);w(manager+0x24,listing);w(manager+0x28,4)
 names=['temperate_lake01','arctic_lake01','desert_lake01','cursed_lake01']
 for i,name in enumerate(names):
  de=defs+i*256;w(listing+i*4,de);w(de+8,de+64);u.mem_write(de+64,(name+'\0').encode('utf-16le'))
 pts=world+0xf0000
 for diagonal in [False,True]:
  for length in ([5,16,22] if diagonal else [5,16,32]):
   for count in [1,4]:
    for pending in [0,1]:
     expected={}
     for y in range(128):
      for x in range(128):
       wet=40<=x<=40+length and (40<=y<=40+length if diagonal else 39<=y<=41);cell=tiles+(y*128+x)*48;v=defs+((x+y)%count)*256;w(cell,v);w(cell+32,0x120 if wet else 0x200)
     for i in range(length):w(pts+i*4,(40+i)|((40+i if diagonal else 40)<<16))
     value=run('bridge_metadata_write_check',[state,pts,length,pending]);assert value
     encoded=text(value);assert len(encoded)<1024 and encoded.startswith('paws_bridge_meta2|'+('U' if pending else 'P'));checks+=2
     for y in range(36,40+length+5):
      for x in range(36,40+length+5):
       actual=run('bridge_metadata_read_check',[state,value,x,y])
       if actual:assert actual==defs+((x+y)%count)*256;expected[x,y]=actual
     assert expected;checks+=len(expected)
     # Native save strings must round-trip verbatim, including the paid marker.
     copy=value+0x10000;u.mem_write(copy,(encoded+'\0').encode('utf-16le'))
     for (x,y),v in expected.items():assert run('bridge_metadata_read_check',[state,copy,x,y])==v
     checks+=len(expected)
 old=world+0xf8000;u.mem_write(old,'paws_bridge_meta1|P1|42,40,temperate_lake01;\0'.encode('utf-16le'));assert run('bridge_metadata_read_check',[state,old,42,40])==defs;checks+=1
print('BRIDGE_METADATA_PASS',checks,'round-trip, legacy, length and biome checks')
