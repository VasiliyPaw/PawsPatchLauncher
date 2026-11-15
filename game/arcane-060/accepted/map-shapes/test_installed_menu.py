"""Exercise the emitted installed menu logic against typed native-widget stubs."""
from pathlib import Path
import argparse,json,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();meta=json.loads((a.out/'native/prototype.json').read_text());blob=(a.out/'native/prototype.bin').read_bytes();checks=0
assert meta['installed'] and not any(h['site']==0xc772e for h in meta['hooks'])
for image,cave in [(BASE,0x10000000),(0x230000,0x19000000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW);code=bytearray(blob)
 for off,im,cv in meta['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,meta['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x20000);u.mem_map(0x30000000,0x10000);u.mem_map(0x31000000,4096)
 def w(at,v):u.mem_write(at,struct.pack('<I',v))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 def ws(at,s):u.mem_write(at,(s+'\0').encode('utf-16le'))
 data=cave+meta['uiState'];m=data+24;menu=0x20000000;mapDrop=menu+0x1000;mapList=menu+0x1100;river=menu+0x2000;shape=menu+0x3000;records=menu+0x6000;defs=[menu+0x7000,menu+0x7400];item=menu+0x8000;table=item+0x100;holder=item+0x200;text=item+0x300
 w(data,image);w(m,data);w(m+4,menu);w(m+8,river);w(m+16,shape);w(menu+0x138,mapDrop);w(mapDrop+0x6c,mapList);w(menu+0xfc+0xc,records);w(menu+0xfc+0x10,2);w(item,table);w(table+8,0x31000100);w(holder,text)
 for j,(name,count) in enumerate([('PawsRivers',18),('PawsMapShape',4)]):
  de=defs[j];values=menu+0x9000+j*0x200;w(records+j*12,de);w(de+8,de+0x80);ws(de+0x80,name);w(de+0x20,3);w(de+0x34,values);w(de+0x38,count)
  for i in range(count):
   string=menu+0xa000+j*0x2000+i*128;w(values+i*8,string);w(values+i*8+4,string+64);ws(string,f'value_{j}_{i}');ws(string+64,str(i))
 options={};selected={}
 def native(uc,addr,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);self=uc.reg_read(UC_X86_REG_ECX);n=0;value=0
  if addr==image+0x2a22d2:assert self==mapList;value=item
  elif addr==0x31000100:assert self==item;value=holder
  elif addr==image+0x2a2a1e:assert self in (river,shape);options[self]=[]
  elif addr==image+0x2a294a:
   n=3;assert self in (river,shape);identifier=r(r(sp+8));j=0 if self==river else 1;values=r(defs[j]+0x34);index=(r(sp+8)-values)//8;assert identifier==r(values+index*8);options[self].append(index)
  elif addr==image+0x2a2a38:n=1;selected[self]=r(sp+4)
  elif addr==image+0x296c07:
   n=2;items=r(self+0xc);count=r(self+0x10);matches=[items+i*12 for i in range(count) if r(items+i*12)==r(sp+4)];assert len(matches)==1;w(matches[0]+8,r(sp+8))
  else:raise AssertionError(hex(addr))
  uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+n*4)
 for off in (0x2a22d2,0x2a2a1e,0x2a294a,0x2a2a38,0x296c07):u.hook_add(UC_HOOK_CODE,native,begin=image+off,end=image+off)
 u.hook_add(UC_HOOK_CODE,native,begin=0x31000100,end=0x31000100)
 for width,height,index,maximum in [(256,256,17,1),(384,384,17,1),(512,512,2,2),(768,768,6,3),(1024,1024,17,5),(1280,1280,17,6),(2048,2048,17,10),(256,1024,8,1)]:
  ws(text,f'{width} x {height}');w(records+8,index);w(records+12+8,2);w(m+24,0);sp=0x3000f000;w(sp,0x31000f00);w(sp+4,data);w(sp+8,menu);u.reg_write(UC_X86_REG_ESP,sp)
  u.emu_start(cave+meta['exports']['menu_rivers_refresh'],0x31000f00,count=200000)
  assert u.reg_read(UC_X86_REG_ESP)==sp+4;checks+=1
  assert options[river]==list(range(maximum+1))+[17] and options[shape]==[0,1,2,3];checks+=1
  expected=17 if index==17 else min(index,maximum);assert r(records+8)==expected;checks+=1
  assert selected[river]==(maximum+1 if expected==17 else expected) and selected[shape]==2;checks+=1
  assert r(m+32)==maximum and r(m+24)==0;checks+=1
 # Native command functors pass an argument-list pointer even for a command
 # with no textual arguments. The callee must consume that stack word.
 sp=0x3000f000;w(sp,0x31000f00);w(sp+4,0x2001f000);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,0)
 u.emu_start(cave+meta['exports']['menu_qa_dispatch'],0x31000f00,count=1000)
 assert u.reg_read(UC_X86_REG_ESP)==sp+8;checks+=1
 # Preference callbacks keep rivers per exact map dimensions and shape
 # globally, including explicit zero and Random. Fresh dialog state mimics
 # restarting the game; the persisted dictionary remains external to it.
 prefs={}
 def preference(uc,at,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);kind=r(sp+4);key=r(sp+8);value=r(sp+12)
  if at==0x31000200:value=prefs.get((kind,key),value)
  else:prefs[kind,key]=value;value=1
  uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4)
 for at in [0x31000200,0x31000300]:u.hook_add(UC_HOOK_CODE,preference,begin=at,end=at)
 def call(name,values):
  sp=0x3000f000;u.mem_write(sp,struct.pack('<'+'I'*(len(values)+1),0x31000f00,*values));u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(cave+meta['exports'][name],0x31000f00,count=200000);assert u.reg_read(UC_X86_REG_ESP)==sp+4
 call('menu_settings',[data,0x31000200,0x31000300]);w(m+36,0)
 ws(text,'512 x 512');w(records+8,2);w(records+20,3);call('menu_rivers_refresh',[data,menu]);call('menu_remember',[data,menu])
 assert prefs[0,512*4096+512]==2 and prefs[1,0]==3;checks+=1
 ws(text,'1280 x 1280');call('menu_rivers_refresh',[data,menu]);assert r(records+8)==17 and r(records+20)==3;checks+=1
 w(records+8,6);call('menu_remember',[data,menu]);ws(text,'512 x 512');call('menu_rivers_refresh',[data,menu]);assert r(records+8)==2;checks+=1
 ws(text,'384 x 384');call('menu_rivers_refresh',[data,menu]);assert r(records+8)==17;call('menu_remember',[data,menu]);checks+=1
 w(records+8,0);call('menu_remember',[data,menu]);ws(text,'1280 x 1280');call('menu_rivers_refresh',[data,menu]);assert r(records+8)==6;checks+=1
 w(m+36,0);w(records+8,17);w(records+20,0);call('menu_rivers_refresh',[data,menu]);assert r(records+8)==6 and r(records+20)==3;checks+=1
 ws(text,'384 x 384');call('menu_rivers_refresh',[data,menu]);assert r(records+8)==0;checks+=1
 # Launch directly from the lobby after a fresh process: the saved native
 # FogOfWar preference and custom rules reach the live session map settings
 # even when no map dialog was opened or committed.
 info=menu+0x10000;launchRules=menu+0x16000;fogDef=menu+0x17000;session=menu+0x18000;preferences=menu+0x19000
 w(image+0x5f3fe4,session);w(session+0xf0,2);w(session+0x64,0);w(session+0x80,info);w(image+0x5f9a0c,preferences)
 w(info+0x50,menu+0x17500);w(info+0x20+0xc,launchRules);w(info+0x20+0x10,3)
 for i,de in enumerate([defs[0],defs[1],fogDef]):w(launchRules+i*12,de)
 w(fogDef+8,fogDef+0x100);ws(fogDef+0x100,'FogOfWar');w(fogDef+0x20,3)
 u.mem_write(info+0x3c,struct.pack('<2f',1280,1280));w(launchRules+4,0x12340000);w(launchRules+8,17);w(launchRules+20,0);w(launchRules+28,0x12340000);w(launchRules+32,2)
 merges=[]
 def merge(uc,at,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);assert uc.reg_read(UC_X86_REG_ECX)==preferences and r(sp+4)==info+0x20;merges.append(1)
  if bytes(uc.mem_read(launchRules+28,1))==b"\0":w(launchRules+32,0)
  uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+8)
 u.hook_add(UC_HOOK_CODE,merge,begin=image+0x142fe0,end=image+0x142fe0)
 call('menu_launch_settings',[data]);assert r(launchRules+8)==6 and r(launchRules+20)==3 and r(launchRules+32)==0 and len(merges)==1;checks+=1
 for mode in [1,2,3,4,5]:
  w(session+0x64,mode);call('menu_launch_settings',[data]);assert len(merges)==1;checks+=1
 w(session+0x64,0);w(session+0xf0,3);call('menu_launch_settings',[data]);assert len(merges)==1;checks+=1
 w(session+0xf0,2);w(session+0x100,1);call('menu_launch_settings',[data]);assert len(merges)==1;checks+=1
 w(session+0x100,0);w(launchRules+4,1);w(launchRules+8,0);w(launchRules+28,1);w(launchRules+32,2)
 call('menu_launch_settings',[data]);assert r(launchRules+8)==0 and r(launchRules+32)==2;checks+=1
print('INSTALLED_RIVER_MENU_PASS',checks,'compiled checks: typed list access, all sizes, random last, stable enum IDs and size clamping')
