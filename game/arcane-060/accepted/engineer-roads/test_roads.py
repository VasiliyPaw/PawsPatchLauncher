"""Exercise compiled road jobs against native ABI stubs; no live-game writes."""
import sys,json,struct,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
m=json.loads((args.out/'native/prototype.json').read_text());blob=(args.out/'native/prototype.bin').read_bytes();checks=0
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW)
 code=bytearray(blob)
 for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x200000);u.mem_map(0x30000000,0x20000)
 state=cave+m['roadState'];world=0x20000000;session=world+0x1000;map_=world+0x2000;tiles=world+0x10000
 registry=world+0x100000;company=world+0x70000;unit=company+0x1000;kingdom=unit+0x1000;org=kingdom+0x1000
 worker=org+0x1000;body=worker+0x1000;element=body+0x1000;ai=element+0x1000;ai_state=ai+0x1000
 mgr=ai_state+0x1000;variants=mgr+0x1000;grass=variants+0x1000;road=grass+0x1000;ui=road+0x1000
 jobs=state+404;queue=[];invoked=[];retain_water=[False]
 def w(at,v):u.mem_write(at,struct.pack('<I',v&0xffffffff))
 def f(at,v):u.mem_write(at,struct.pack('<f',v))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 def run(at=None,self=0,values=None,clean=0):
  sp=0x3000f000;values=values if values is not None else [state,world]
  u.mem_write(sp,struct.pack('<'+'I'*(len(values)+1),0x3001f000,*values));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,self)
  u.emu_start(at or cave+m['exports']['roads_tick'],0x3001f000,count=10000000)
  assert u.reg_read(UC_X86_REG_EIP)==0x3001f000 and u.reg_read(UC_X86_REG_ESP)==sp+4+clean,(hex(u.reg_read(UC_X86_REG_EIP)),hex(u.reg_read(UC_X86_REG_ESP)),hex(sp+4+clean))
 def reset():
  u.mem_write(state,bytes(2452));w(state,image);w(state+4,cave+m['adapter']);w(state+12,world)
  w(image+0x5f3fb8,world);w(image+0x5f3fe4,session);w(image+0x5f9218,2);w(image+0x5ef72c,registry);w(image+0x5f3fc0,ui)
  w(session+0xf0,2);w(session+0x100,0);w(world+0x30,map_);w(world+0xd8,0);f(world+0xe8,1)
  w(map_+4,1);w(map_+0x1c,16);w(map_+0x20,16);w(map_+0x28,tiles)
  for i in range(256):w(tiles+i*0x30,grass);w(tiles+i*0x30+0x20,0x200)
  for a,ident in [(company,1),(unit,2)]:w(a,image+0x4e5c58);w(a+8,0);w(a+0x14,ident);w(registry+0x20004+ident*4,a);w(a+0xe8,kingdom);f(a+0x20,16);f(a+0x24,16)
  w(company+0x7c,org);w(company+0x100,0);w(company+0x70,ai);w(ai+0x14,ai+0x100);w(ai+0x100,ai_state);w(ai_state,image+0x4f4df0)
  w(org+4,company);w(org+0x2c,1);w(org+0x28,org+0x100);w(org+0x100,unit)
  w(unit+0xa8,worker);w(worker,image+0x4df830);w(worker+4,unit);w(unit+0x60,body);w(body+4,unit);f(body+0x10,1)
  w(unit+0x80,element);w(element+4,unit);w(element+0x10,company);w(unit+0x70,0);w(unit+0x100,0);w(kingdom+0x14,3)
  w(image+0x5f0030,mgr);w(mgr+0x24,variants);w(mgr+0x28,2);w(variants,grass);w(variants+4,road)
  for a,name in [(grass,'temperate_grass01'),(road,'temperate_road01')]:w(a+8,a+0x100);u.mem_write(a+0x100,(name+'\0').encode('utf-16-le'))
  invoked.clear();queue.clear()
 def submit():w(state+40+r(state+36)%32*4,1);w(state+36,r(state+36)+1)
 def native(uc,addr,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);invoked.append(addr);ret=0;clean=0
  if addr==image+0x2be624:ret=kingdom
  elif addr==image+0x2517a3:queue.clear()
  elif addr==image+0x2517f9:
   point=r(sp+4);queue.append((r(point),r(point+4),r(sp+8)));clean=8
  elif addr==image+0x25185b:
   for x,y,v in queue:
    if not retain_water[0]:w(tiles+(y*16+x)*0x30,v)
   clean=4
  elif addr==image+0x24a522:
   w(uc.reg_read(UC_X86_REG_ECX),r(sp+4));clean=12
  elif addr==image+0x2424b2:clean=4
  elif addr==image+0x20d4b:pass
  elif addr==image+0x24f6b0:ret=1
  elif addr==image+0x25fe70:
   for ty in range(16):
    for tx in range(16):
     if r(tiles+(ty*16+tx)*0x30)==bridge:u.mem_write(tiles+(ty*16+tx)*0x30+0x2c,b'\x01')
   clean=12
  else:raise AssertionError(hex(addr))
  uc.reg_write(UC_X86_REG_EAX,ret);uc.reg_write(UC_X86_REG_ESP,sp+4+clean);uc.reg_write(UC_X86_REG_EIP,r(sp))
 for off in [0x2be624,0x2517a3,0x2517f9,0x25185b,0x24a522,0x2424b2,0x20d4b,0x24f6b0,0x25fe70]:u.hook_add(UC_HOOK_CODE,native,begin=image+off,end=image+off)
 # UI construction and event handler need the same owned controls as a match.
 label=world+0xe1000;button=world+0xe2000;selection=world+0xe3000
 created=[0,0]
 def ui_native(uc,addr,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);self=uc.reg_read(UC_X86_REG_ECX);ret=0;clean=0
  if addr==image+0x205de:
   source=r(sp+4);text=bytearray()
   for i in range(32768):
    char=bytes(u.mem_read(source+i*2,2));text.extend(char)
    if char==b'\0\0':break
   u.mem_write(world+0x1c0000,bytes(text));w(self,world+0x1c0000);clean=4
  elif addr==image+0x21375:pass
  elif addr==image+0x81d30:ret=label+created[0]*0x400;created[0]+=1
  elif addr==image+0x2b88c0:ret=button+created[1]*0x400;created[1]+=1
  elif addr==image+0x2b7486:clean=8
  elif addr==image+0x2b8b5d:w(self+0x24,r(self+0x24)&~0x100);clean=4
  elif addr==image+0xd4e76:clean=4
  else:raise AssertionError(hex(addr))
  uc.reg_write(UC_X86_REG_EAX,ret);uc.reg_write(UC_X86_REG_ESP,sp+4+clean);uc.reg_write(UC_X86_REG_EIP,r(sp))
 for off in [0x205de,0x21375,0x81d30,0x2b88c0,0x2b7486,0x2b8b5d,0xd4e76]:u.hook_add(UC_HOOK_CODE,ui_native,begin=image+off,end=image+off)
 oldreset=reset;planbase=state+17140;event=world+0xf9000
 def reset():
  created[:]=[0,0]
  oldreset();u.mem_write(state+2452,bytes(20000));w(unit+4,world+0xf0000);w(world+0xf0008,world+0xf0100);u.mem_write(world+0xf0100,'engineer\0'.encode('utf-16le'))
  w(image+0x5f3fbc,ui);w(ui+0x13c,selection);w(selection+8,selection+0x100);w(selection+0x100,selection+0x200);w(selection+0x214,company);w(ui+0x60,ui)
  run(cave+m['exports']['roads_create'],values=[state,ui]);run()
 def ev(code,flags,x=16,y=16):
  w(event+8,code);w(event+4,flags);f(ui+0x184,x);f(ui+0x188,y);run(cave+m['exports']['roads_event'],self=ui,values=[event],clean=4)
 def arm():w(button+0x24,0x100);run(r(r(button)+0xcc),self=button,values=[])
 # Planning never paints terrain or creates construction until mouse release.
 reset();arm();assert r(planbase)==1;checks+=1
 ev(0x100,1);assert r(planbase+4)==1 and r(state+24)==0;checks+=1
 ev(0x100,2,22,22);assert r(planbase+8)==1 and r(planbase)==0 and r(planbase+12)==4;checks+=1
 assert [r(planbase+36+i*4) for i in range(4)]==[x|(x<<16) for x in range(8,12)];checks+=1
 # Slow or fast dragging produces a continuous line in every octant.
 for x,y in [(8,8),(8,20),(20,8),(20,20),(8,16),(16,8),(22,16),(16,22)]:
  reset();arm();ev(0x100,1);ev(0x100,2,x,y);n=r(planbase+12);pts=[r(planbase+36+i*4) for i in range(n)]
  assert r(planbase+8)==1 and pts[-1]==(x//2|((y//2)<<16)) and all(abs((a&65535)-(b&65535))<=1 and abs((a>>16)-(b>>16))<=1 for a,b in zip(pts,pts[1:]));checks+=1
 for code in [0x101,0x1b]:
  reset();arm();ev(0x100,1);ev(code,1);assert not r(planbase) and not r(planbase+8) and not r(state+24);checks+=1
 for at,val in ([] if m.get('multiplayer')else [(session+0x100,1)])+[(session+0xf0,1),(world+0xd8,6),(image+0x5f9218,1),(company+0xe8,0),(worker,0),(company+8,1),(unit+8,1),(body+0x10,0),(element+0x10,0)]:
  reset();w(at,val);arm();assert not r(planbase);checks+=1
 reset();u.mem_write(world+0xf0100,'pioneering_soldier\0'.encode('utf-16le'));arm();assert not r(planbase);checks+=1
 for name in ['pioneer','Pioneer','pilgrim','founder','settler','kingdom_pioneer','leader_settler','sovereignnat_founder','sovereignroy_pilgrim']:
  reset();u.mem_write(world+0xf0100,(name+'\0').encode('utf-16le'));arm();assert not r(planbase);checks+=1
 for name in ['engineer','caretaker','forge','crafter','nightbringer','boneweaver','Engineer','Caretaker','Forge','Crafter','Nightbringer','Boneweaver','CRAFTER','kingdom_nightbringer','sovereignnat_boneweaver']:
  reset();u.mem_write(world+0xf0100,(name+'\0').encode('utf-16le'));arm();assert r(planbase)==1;checks+=1
 reset();arm();ev(0x100,1);w(tiles+(10*16+10)*0x30+0x20,0x100);ev(0x100,2,22,22);assert not r(planbase+8) and not r(state+24);checks+=1
 reset();arm();ev(0x100,1);w(ui+0x60,0);ev(0x100,2);assert not r(planbase+8);checks+=1
 reset();arm();f(world+0xe8,.5);run();assert not r(planbase);checks+=1
 reset();arm();w(session+0x100,1);run();assert bool(r(planbase))==bool(m.get('multiplayer'));checks+=1
 # Command and terrain integration: a released plan advances only at its
 # fixed coordinates; the approach and ordinary moves cannot paint a trail.
 defs=world+0xd0000;defmove=defs+0x1000;defstop=defs+0x2000;cmd=defs+0x3000;pl=defs+0x4000
 moves=[];constructs=[]
 def commands(uc,addr,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);self=uc.reg_read(UC_X86_REG_ECX);ret=0;clean=0
  if addr==image+0x2ef03c:ret=cmd
  elif addr==image+0x22f4e9:u.mem_write(cmd,bytes(64));w(cmd+8,r(sp+4));ret=cmd;clean=4
  elif addr==image+0x22f651:
   assert self==cmd and r(sp+4)==company
   
   if r(cmd+8)==3:constructs.append(r(cmd+0x10))
   else:moves.append(tuple(struct.unpack('<2f',u.mem_read(cmd+0x18,8))))
   ret=1;clean=4
  elif addr==image+0x42fca:pass
  elif addr==0x3001d100:
   assert self==company and r(sp+4)==0 and r(r(sp+8))==cmd and r(sp+12)==0
   ret=1;clean=12
  elif addr==0x3001d000:ret=1;clean=4
  else:raise AssertionError(hex(addr))
  uc.reg_write(UC_X86_REG_EAX,ret);uc.reg_write(UC_X86_REG_ESP,sp+4+clean);uc.reg_write(UC_X86_REG_EIP,r(sp))
 for addr in [image+o for o in [0x2ef03c,0x22f4e9,0x22f651,0x42fca]]+[0x3001d000,0x3001d100]:u.hook_add(UC_HOOK_CODE,commands,begin=addr,end=addr)
 w(image+0x4e5c58+0x150,0x3001d100);w(image+0x4e5c58+0x34,0x3001d000);w(image+0x5f3fb4,defs);w(defs+0x298,defs+0x100);u.mem_write(defs+0x100,bytes(156))
 for i,(de,name) in enumerate([(defmove,'move'),(defstop,'stop')]):w(defs+0x100+i*4,de);w(de+8,de+0x100);u.mem_write(de+0x100,(name+'\0').encode('utf-16le'))
 reset();u.mem_write(road+0x100,'paws_engineer_road01\0'.encode('utf-16le'))
 arm();ev(0x100,1,20,20);ev(0x100,2,22,20);run();assert moves[-1]==(21.,21.) and r(state+24)==0;checks+=1
 for a in [company,unit]:f(a+0x20,21);f(a+0x24,21)
 f(world+0xe8,2);run();assert r(state+24)==9 and r(jobs+36)==1;checks+=1
 f(world+0xe8,2.1);run();assert moves[-1]==(23.,21.) and r(state+24)==9;checks+=1
 for a in [company,unit]:f(a+0x20,23)
 f(world+0xe8,3);run();assert r(state+24)==12;checks+=1
 arm();f(world+0xe8,4);run();assert r(jobs)==0;checks+=1
 f(company+0x20,25);f(unit+0x20,25);f(world+0xe8,5);run();assert r(state+24)==12;checks+=1
 if m.get('bridges'):
  hm=world+0xc0000;basehm=hm+0x100;hp=hm+0x1000;bp=hm+0x3000;water=road+0x400;bridge=road+0x800
  pts=world+0xc8000
  nation=world+0xf2000;bridge_def=world+0xf3000;built=world+0xf4000;economy=built+0x400
  found=[];spawned=[];spawn_fail=[False];missing=[False]
  def bridge_native(uc,addr,size,_):
   sp=uc.reg_read(UC_X86_REG_ESP);self=uc.reg_read(UC_X86_REG_ECX);ret=0;clean=0
   if addr==image+0x2edb9:
    assert self==defs+0x500
    text=bytes(u.mem_read(r(sp+4),90)).decode('utf-16le').split('\0')[0];found.append(text)
    u.mem_write(bridge_def+0x100,(text+'\0').encode('utf-16le'));ret=0 if missing[0] else bridge_def;clean=4
   elif addr==image+0x91a87:
    u.mem_write(self,bytes(96));f(self+0x18,-1)
   elif addr==image+0x242eee:
    assert self==world
    ctx=r(sp+4);assert r(ctx+4)==bridge_def and r(ctx+0x28)==kingdom
    spawned.append(tuple(struct.unpack('<3f',u.mem_read(ctx+8,12))))
    if not spawn_fail[0]:
     w(built,image+0x4e5c58);w(built+4,bridge_def);w(built+8,0);w(built+0x100,0x200000 if r(ctx+0x38) else 0);w(built+0x14,100);w(built+0xe8,kingdom);w(built+0x84,0 if r(ctx+0x38) else economy)
     u.mem_write(built+0x20,bytes(u.mem_read(ctx+8,12)));w(registry+0x20004+100*4,built);ret=built
     w(built+0x18,r(ctx+0x1c));w(built+0x60,built+0x600);f(built+0x610,1)
    clean=4
   elif addr==image+0x24338e:w(built+8,3);clean=4
   elif addr==image+0x275a71:clean=4
   elif addr==image+0x20d6b:ret=r(sp+4)
   elif addr==image+0x2428db:clean=4
   elif addr==image+0x22a9ab:pass
   elif addr==image+0x23e482:
    u.mem_write(self+0x2c,bytes(u.mem_read(r(sp+4),12)));clean=4
   elif addr==image+0x23e242:
    assert self in (built,company,unit)
    u.mem_write(self+0x20,bytes(u.mem_read(r(sp+4),12)));clean=4
   else:raise AssertionError(hex(addr))
   uc.reg_write(UC_X86_REG_EAX,ret);uc.reg_write(UC_X86_REG_ESP,sp+4+clean);uc.reg_write(UC_X86_REG_EIP,r(sp))
  for off in [0x2edb9,0x91a87,0x242eee,0x24338e,0x23e482,0x23e242,0x275a71,0x20d6b,0x2428db,0x22a9ab]:u.hook_add(UC_HOOK_CODE,bridge_native,begin=image+off,end=image+off)
  def bridge_reset():
   reset();w(world+0x38,hm);w(world+0x34,basehm)
   w(map_+0x50,world+0xc9000);w(world+0xc9004,world+0xca000);w(world+0x248,world+0xcb000)
   w(kingdom+0x240,nation);w(nation+8,nation+0x100);u.mem_write(nation+0x100,'Human\0'.encode('utf-16le'))
   w(defs+0xc,defs+0x500);w(bridge_def+8,bridge_def+0x100);w(registry+0x20004+100*4,0)
   found.clear();spawned.clear();spawn_fail[0]=False;missing[0]=False;w(bridge_def+0x328,0)
   for at,data in [(hm,hp),(basehm,bp)]:
    w(at+0xc,33);w(at+0x10,33);w(at+0x14,0);w(at+0x1c,0);w(at+0x40,data)
   for at,name in [(water,'temperate_river01'),(bridge,'paws_engineer_bridge01')]:w(at+8,at+0x100);u.mem_write(at+0x100,(name+'\0').encode('utf-16le'))
   w(mgr+0x28,4);w(variants+8,water);w(variants+12,bridge)
   for y in range(16):
    for x in range(7,9):w(tiles+(y*16+x)*0x30,water);w(tiles+(y*16+x)*0x30+0x20,0x120)
   for y in range(33):
    for x in range(33):f(bp+(y*33+x)*4,2);f(hp+(y*33+x)*4,-3 if 14<=x<=18 else 0)
   for i in range(8):w(pts+i*4,(i+4)|(8<<16))
  def check(n=8):run(cave+m['exports']['bridge_check'],values=[state,pts,n]);return u.reg_read(UC_X86_REG_EAX)
  bridge_reset();assert check()==1;checks+=1
  # The reachable bank can reverse a diagonal preview. Its Bresenham tie
  # cell differs from independently rasterizing the opposite direction.
  w(map_+0x20,20)
  for at in [hm,basehm]:w(at+0x14,1)
  for i in range(33*33):f(hp+i*4,0)
  for y in range(16,20):
   for x in range(16):w(tiles+(y*16+x)*48,water if x in [7,8] else grass);w(tiles+(y*16+x)*48+32,0x120 if x in [7,8] else 0x200)
  diagonal=[(4,13),(5,12),(6,11),(7,10),(7,9),(8,8),(9,7),(10,6),(11,5)]
  for points in [diagonal,list(reversed(diagonal))]:
   for i,(x,y) in enumerate(points):w(pts+i*4,x|(y<<16))
   assert check(len(points))==1;checks+=1
  # The same reversed order must reach native site creation from its bank.
  for obj in [company,unit]:f(obj+0x20,23);f(obj+0x24,11)
  run(cave+m['exports']['bridge_request'],values=[state,1,pts,len(diagonal)]);f(world+0xe8,2);run()
  assert r(jobs)==1 and len(spawned)==1;checks+=2
  bridge_reset()
  # Long rotated/crossing decks overlap even when neither centre lies on
  # the other's line. Mobile wildlife is ignored; a static structure is not.
  def occupied():
   run(cave+m['exports']['bridge_occupied_check'],values=[state,pts,8,1]);return u.reg_read(UC_X86_REG_EAX)
  obstacle=world+0xee000;obdef=obstacle+0x400
  w(obstacle,image+0x4e5c58);w(obstacle+4,obdef);w(obdef+8,obdef+0x100);u.mem_write(obdef+0x100,'paws_bridge_stone_y_12\0'.encode('utf-16le'));w(obstacle+0x14,101);w(registry+0x20004+101*4,obstacle);f(obstacle+0x20,16);f(obstacle+0x24,25);f(obstacle+0x2c,0);f(obstacle+0x30,1)
  assert occupied()==1;checks+=1
  f(obstacle+0x20,40);assert occupied()==0;checks+=1
  f(obstacle+0x20,16);u.mem_write(obdef+0x100,'lake_fish\0'.encode('utf-16le'));w(obstacle+0x6c,obstacle+0x800);assert occupied()==0;checks+=1
  w(obstacle+0x6c,0);f(obstacle+0x24,17);assert occupied()==1;checks+=1
  w(registry+0x20004+101*4,0)
  # Passable water-group marshes and bogs cannot be used as either bank,
  # nor may a bridge continue across a swamp to another distant bank.
  wetdef=world+0xee400;w(wetdef+8,wetdef+0x100)
  for ident,xy,flags in [('temperate_mist_swamp01',(4,8),0x20),('desert_quicksand01',(11,8),0x20),('cursed_marsh01',(7,8),0x120),('arctic_snowswamp01',(4,8),0x200)]:
   bridge_reset();u.mem_write(wetdef+0x100,(ident+'\0').encode('utf-16le'));x,y=xy;w(tiles+(y*16+x)*0x30,wetdef);w(tiles+(y*16+x)*0x30+0x20,flags);assert check()==0;checks+=1
  # Water is mandatory; water endpoints, excessive span, mountains, steep banks,
  # broken line, deep water and mismatched height grids are all rejected.
  for mode in range(9):
   bridge_reset()
   if mode==0:
    for y in range(16):
     for x in range(7,9):w(tiles+(y*16+x)*0x30+0x20,0x200)
   elif mode==1:w(pts,7|(8<<16))
   elif mode==2:w(tiles+(8*16+6)*0x30+0x20,0x100)
   elif mode==3:f(hp+(17*33+23)*4,4)
   elif mode==4:w(pts+12,7|(9<<16))
   elif mode==5:f(hp+(17*33+15)*4,-20)
   elif mode==6:w(basehm+0xc,32)
   elif mode==7:f(hp+(17*33+9)*4,float('nan'))
   else:w(pts+28,11|(9<<16))
   assert check()==0;checks+=1
  bridge_reset();assert check(33)==0 and check(4)==0;checks+=1
  # Tool routes use bridge validation; road tool cannot cross the same water.
  run(cave+m['exports']['bridge_request'],values=[state,1,pts,8]);assert r(planbase+8)==1 and r(planbase+12)==8;checks+=1
  f(world+0xe8,2);run();assert r(jobs)==1 and r(jobs+40)==1 and r(state+24)==0;checks+=1
  # A structure appearing after the order but before arrival cancels the
  # intent, without a bridge actor or changed water left behind.
  block=world+0xee000;bd=block+0x400;w(block,image+0x4e5c58);w(block+4,bd);w(bd+8,bd+0x100);u.mem_write(bd+0x100,'outpost\0'.encode('utf-16le'));w(block+8,0);w(block+0x14,101);f(block+0x20,16);f(block+0x24,17);w(registry+0x20004+101*4,block)
  for obj in [company,unit]:f(obj+0x20,9);f(obj+0x24,17)
  f(world+0xe8,3);run();assert r(jobs)==0 and not spawned and r(tiles+(8*16+7)*0x30)==water;checks+=1
  w(registry+0x20004+101*4,0)
  bridge_reset();run(cave+m['exports']['bridge_request'],values=[state,1,pts,8]);f(world+0xe8,2);run()
  # Cancelling while approaching leaves the blocked river and heights untouched.
  arm();f(world+0xe8,3);run();assert r(jobs)==0 and r(state+24)==0;checks+=1
  assert r(tiles+(8*16+7)*0x30)==water;checks+=1
  # A surviving engineer stuck away from the landing cannot hold a job forever.
  bridge_reset();run(cave+m['exports']['bridge_request'],values=[state,1,pts,8])
  f(company+0x20,9);f(company+0x24,17);f(unit+0x20,29);f(unit+0x24,29)
  f(world+0xe8,2);run();assert r(jobs)==1;checks+=1
  f(world+0xe8,63);run();assert r(jobs)==0 and r(state+24)==0 and r(state+28)==1;checks+=1
  bridge_reset();arm();ev(0x100,1,8,16);ev(0x100,2,22,16);assert not r(planbase+8);checks+=1
  def setheight(uc,addr,size,_):
   sp=uc.reg_read(UC_X86_REG_ESP);assert uc.reg_read(UC_X86_REG_ECX)==hm
   x=r(sp+4);y=r(sp+8);assert x<33 and y<33 and r(sp+16)==0
   w(hp+(y*33+x)*4,r(sp+12));uc.reg_write(UC_X86_REG_ESP,sp+20);uc.reg_write(UC_X86_REG_EIP,r(sp))
  u.hook_add(UC_HOOK_CODE,setheight,begin=image+0x2f95f8,end=image+0x2f95f8)
  bridge_reset();oldbase=bytes(u.mem_read(bp,33*33*4));oldheight=bytes(u.mem_read(hp,33*33*4))
  # Native movement can complete four units short. The worker is in range;
  # the bridge must start instead of silently dropping the green preview.
  f(company+0x20,9);f(company+0x24,13);f(unit+0x20,9);f(unit+0x24,13)
  run(cave+m['exports']['bridge_request'],values=[state,1,pts,8]);f(world+0xe8,2);run()
  assert r(jobs)==1 and len(spawned)==1;checks+=2
  bridge_reset();oldbase=bytes(u.mem_read(bp,33*33*4));oldheight=bytes(u.mem_read(hp,33*33*4))
  run(cave+m['exports']['bridge_commit'],values=[state,pts,8]);assert u.reg_read(UC_X86_REG_EAX)==1;checks+=1
  assert bytes(u.mem_read(bp,33*33*4))==oldbase and bytes(u.mem_read(hp,33*33*4))==oldheight;checks+=1
  assert found==['paws_bridge_'+('human_' if 'human' in m.get('styles',[]) else '')+'stone_y_08'] and len(spawned)==1 and spawned[0][:2]==(16.,17.);checks+=1
  assert all(r(tiles+(y*16+x)*0x30)==bridge for y in range(7,10)for x in range(7,9));checks+=1
  assert all(r(tiles+(y*16+x)*0x30)==grass for y in range(7,10)for x in [3,4,5,6,9,10,11,12]);checks+=1
  # Higher-priority native water transitions must not leave holes or cause
  # the completed bridge to repaint every simulation tick.
  bridge_reset();retain_water[0]=True
  run(cave+m['exports']['bridge_commit'],values=[state,pts,8])
  assert all(r(tiles+(y*16+x)*0x30)==bridge for y in range(7,10)for x in range(7,9));checks+=1
  run();before=r(state+24);calls=invoked.count(image+0x25185b)
  for tick in range(3,8):f(world+0xe8,tick);run()
  assert r(state+24)==before and invoked.count(image+0x25185b)==calls;checks+=1
  w(built+8,2);run()
  assert all(r(tiles+(y*16+x)*0x30)==water for y in range(7,10)for x in range(7,9));checks+=1
  retain_water[0]=False
  # A neighbouring span's bounding box includes the first bridge, but its
  # transition cleanup must not turn that finished deck back into water.
  bridge_reset();run(cave+m['exports']['bridge_commit'],values=[state,pts,8])
  nearby=pts+0x200
  for i in range(8):w(nearby+i*4,(4+i)|(5<<16))
  before=[r(tiles+(y*16+x)*0x30)for y in range(7,10)for x in range(7,9)]
  run(cave+m['exports']['bridge_trim_check'],values=[state,nearby,8])
  assert before==[r(tiles+(y*16+x)*0x30)for y in range(7,10)for x in range(7,9)] and bridge in before;checks+=2
  # Nation chooses the model ID. One completed bridge is one native actor;
  # failed allocation/unknown definition never opens an unpaid invisible route.
  for name,material in [('Human','stone'),('human','stone'),('Haroun','wood'),('haroun','wood'),('Gauri','stone'),('Drauga','stone'),('Shadow','stone'),('Undead','stone')]:
   bridge_reset();u.mem_write(nation+0x100,(name+'\0').encode('utf-16le'))
   run(cave+m['exports']['bridge_commit'],values=[state,pts,8]);assert u.reg_read(UC_X86_REG_EAX)==1 and found==[f'paws_bridge_{name.lower()+"_" if name.lower() in m.get("styles",[]) else ""}{material}_y_08'];checks+=1
  # Both material slots route independently, including shorter Human/Gauri
  # prefixes; every choice creates the corresponding native definition.
  for name in ['Human','Gauri','Drauga','Haroun','Shadow','Undead']:
   for wood in [0,1]:
    bridge_reset();u.mem_write(nation+0x100,(name+'\0').encode('utf-16le'))
    run(cave+m['exports']['bridge_commit_material'],values=[state,pts,8,wood])
    prefix=name.lower()+'_' if name.lower() in m.get('styles',[]) else ''
    assert u.reg_read(UC_X86_REG_EAX)==1 and found==[f'paws_bridge_{prefix}{"wood" if wood else "stone"}_y_08'];checks+=1
  for failure in [missing,spawn_fail]:
   bridge_reset();failure[0]=True
   run(cave+m['exports']['bridge_commit'],values=[state,pts,8]);assert u.reg_read(UC_X86_REG_EAX)==0
   assert r(tiles+(8*16+7)*0x30)==water and bytes(u.mem_read(hp,33*33*4))==oldheight;checks+=1
  # Native modified cost, purchase-resource affordability, debit and paid
  # construction vector. Queued/failed work is free; real work is charged once.
  paid=[]
  def economy_native(uc,addr,size,_):
   sp=uc.reg_read(UC_X86_REG_ESP);self=uc.reg_read(UC_X86_REG_ECX);ret=0;clean=0
   if addr==image+0x2277b6:ret=0
   elif addr==image+0x29eaa:
    vector=r(sp+4);assert r(vector+4)==1;f(r(vector),75 if 'wood' in bytes(u.mem_read(bridge_def+0x100,90)).decode('utf-16le') else 125);clean=8
   else:
    vector=r(sp+4);amount=struct.unpack('<f',u.mem_read(r(vector),4))[0];gold=struct.unpack('<f',u.mem_read(kingdom+0x600,4))[0];clean=4
    if addr==image+0x2351d7:ret=int(gold>=amount)
    elif addr==image+0x2359d8:f(kingdom+0x600,gold-amount);paid.append(amount)
    elif addr==image+0x205b0f:paid.append(('refund-vector',amount))
   uc.reg_write(UC_X86_REG_EAX,ret);uc.reg_write(UC_X86_REG_ESP,sp+4+clean);uc.reg_write(UC_X86_REG_EIP,r(sp))
  for off in [0x2277b6,0x29eaa,0x2351d7,0x2359d8,0x205b0f]:u.hook_add(UC_HOOK_CODE,economy_native,begin=image+off,end=image+off)
  bridge_reset();w(bridge_def+0x328,1);w(kingdom+0x1d0,1);f(kingdom+0x600,200)
  run(cave+m['exports']['bridge_request'],values=[state,1,pts,8])
  for obj in [company,unit]:f(obj+0x20,9);f(obj+0x24,17)
  run();assert r(jobs)==1 and not paid;checks+=1
  w(built+0x9c,built+0x800);f(built+0x610,2);f(world+0xe8,2);run();assert paid==[125,('refund-vector',125)];checks+=1
  f(world+0xe8,3);run();assert paid==[125,('refund-vector',125)];checks+=1
  # A paid saved site must not require or debit another purchase when a
  # continuation/first-work check runs with an empty remaining stockpile.
  f(kingdom+0x600,0)
  run(cave+m['exports']['bridge_funds_check'],values=[state,bridge_def,company,built])
  assert u.reg_read(UC_X86_REG_EAX)==1 and paid==[125,('refund-vector',125)];checks+=2
  # Both saved metadata versions and both native material prices recognize
  # the paid flag. Repeated resume checks cannot silently buy the same site.
  text=r(built+0x18)
  for version in [1,2]:
   u.mem_write(text,(f'paws_bridge_meta{version}|P0|\0').encode('utf-16le'))
   for material in ['wood','stone']:
    u.mem_write(bridge_def+0x100,(f'paws_bridge_{material}_y_08\0').encode('utf-16le'))
    for repeat in range(3):
     run(cave+m['exports']['bridge_funds_check'],values=[state,bridge_def,company,built])
     assert u.reg_read(UC_X86_REG_EAX)==1 and paid==[125,('refund-vector',125)] and struct.unpack('<f',u.mem_read(kingdom+0x600,4))[0]==0;checks+=1
  bridge_reset();w(bridge_def+0x328,1);f(kingdom+0x600,124);paid.clear()
  run(cave+m['exports']['bridge_request'],values=[state,1,pts,8])
  for obj in [company,unit]:f(obj+0x20,9);f(obj+0x24,17)
  run();assert not r(jobs) and not spawned and not paid;checks+=1
  # The exact native result survives outside a live saved bridge and for water,
  # flying and terrain queries. Rebuilt cache after clock rollback uses actors.
  bridge_reset();run();run(cave+m['exports']['bridge_commit'],values=[state,pts,8])
  xy=pts+0x100
  def floor(x,y,flags=0x122,original=-1):
   f(xy,x);f(xy+4,y)
   run(cave+m['exports']['bridge_floor'],values=[state,world,xy,flags,struct.unpack('<I',struct.pack('<f',original))[0]])
   return struct.unpack('<f',struct.pack('<I',u.reg_read(UC_X86_REG_EAX)))[0]
  assert abs(floor(16,17)-2.08)<1e-5;checks+=1
  # Saved legacy and six racial IDs all retain walkable deck height; wooden
  # decks use the same +0.1 surface offset under every prefix.
  saved_name=bytes(u.mem_read(bridge_def+0x100,96))
  for prefix in ['',*['%s_'%name for name in ['human','gauri','drauga','haroun','shadow','undead']]]:
   for material in ['wood','stone']:
    u.mem_write(bridge_def+0x100,(f'paws_bridge_{prefix}{material}_y_08\0').encode('utf-16le'))
    assert abs(floor(16,17)-(2.18 if material=='wood' else 2.08))<1e-5;checks+=1
  u.mem_write(bridge_def+0x100,saved_name)
  for x,y in [(0,17),(16,12),(16,22),(25,17)]:assert floor(x,y)==-1;checks+=1
  for flags in [0x123,0,1,3,5,0x121]:assert floor(16,17,flags)==-1;checks+=1
  assert floor(16,17,original=5)==5;checks+=1
  assert floor(float('nan'),17)==-1;checks+=1
  w(built+8,1);assert floor(16,17)==-1;checks+=1
  w(built+8,0);f(world+0xe8,.25);run();assert abs(floor(16,17)-2.08)<1e-5;checks+=1
  # Native construction starts with an unfinished object, issues the real
  # construct target command and leaves water blocked until completion.
  # Cached water-island IDs cannot trap land movers on a completed bridge.
  # Only the bridge's current corridor changes identity; deletion and SP
  # guards restore the original IDs, without rebuilding native AI objects.
  bridge_reset();run();run(cave+m['exports']['bridge_commit'],values=[state,pts,8])
  rects=world+0xdd000
  for y in range(16):
   for x in range(16):
    cell=tiles+(y*16+x)*0x30;rect=rects+(2 if 7<=x<=8 else 0 if x<7 else 1)*16;w(cell+0x10,rect)
  for i,v in enumerate([3,8,21]):w(rects+i*16+8,v)
  run(cave+m['exports']['bridge_navigation_refresh'],values=[state])
  def island(x,y):
   run(cave+m['exports']['bridge_walk_island'],self=tiles+(y*16+x)*0x30,values=[]);return u.reg_read(UC_X86_REG_EAX)
  assert island(7,8)==3 and island(11,8)==3 and island(7,3)==21;checks+=3
  collision=world+0xde000;hook=next(h for h in m['hooks'] if h['site']==0x244727)
  for flags,want in [(0x100,3),(0x200,21),(0,21)]:
   w(collision+0x3c,flags);u.reg_write(UC_X86_REG_EBP,collision)
   run(cave+hook['entry'],self=tiles+(8*16+7)*0x30,values=[]);assert u.reg_read(UC_X86_REG_EAX)==want;checks+=1
  w(built+0x100,0x200000);run(cave+m['exports']['bridge_navigation_refresh'],values=[state]);assert island(7,8)==21 and island(11,8)==8;checks+=2
  w(built+0x100,0);w(session+0x100,1);assert island(7,8)==(3 if m.get('multiplayer')else 21);checks+=1
  w(session+0x100,0);w(built+8,2);run(cave+m['exports']['bridge_navigation_refresh'],values=[state]);assert island(7,8)==21 and island(11,8)==8;checks+=2
  for i in range(256):w(tiles+i*0x30+0x10,0)
  bridge_reset();run(cave+m['exports']['bridge_request'],values=[state,1,pts,8])
  for obj in [company,unit]:f(obj+0x20,9);f(obj+0x24,17)
  run();assert r(built+0x100)&0x200000 and constructs[-1]==100 and r(state+24)==0;checks+=1
  assert not r(built+0x84);checks+=1
  run(cave+m['exports']['bridge_occupied_check'],values=[state,pts,8,77]);assert u.reg_read(UC_X86_REG_EAX)==0;checks+=1
  # A provisional site does not reserve the footprint, and a no-progress
  # command rolls back its native actor without ever opening the river.
  f(world+0xe8,14);run();assert r(jobs)==0 and r(built+8)&3 and r(tiles+(8*16+7)*0x30)==water;checks+=1
  bridge_reset();run(cave+m['exports']['bridge_request'],values=[state,1,pts,8])
  for obj in [company,unit]:f(obj+0x20,9);f(obj+0x24,17)
  run();assert not (r(built+8)&3);checks+=1
  # A cancelled approach/build transaction leaves no empty native site.
  arm();run();assert r(jobs)==0 and r(built+8)&3;checks+=1
  bridge_reset();run(cave+m['exports']['bridge_request'],values=[state,1,pts,8])
  for obj in [company,unit]:f(obj+0x20,9);f(obj+0x24,17)
  run();assert r(jobs)==1;checks+=1
  # Company construction must reach a dry landing, with native unit abilities
  # still responsible for their individual working distances.
  w(ai+4,company)
  run(cave+m['exports']['bridge_work_range'],self=ai,values=[built],clean=4);assert u.reg_read(UC_X86_REG_EAX)==1;checks+=1
  f(company+0x20,30)
  run(cave+m['exports']['bridge_work_range'],self=ai,values=[built],clean=4);assert u.reg_read(UC_X86_REG_EAX)==0;checks+=1
  f(company+0x20,9);w(built+0xe8,0)
  run(cave+m['exports']['bridge_work_range'],self=ai,values=[built],clean=4);assert u.reg_read(UC_X86_REG_EAX)==1;checks+=1
  w(built+0xe8,kingdom)
  f(built+0x610,2);f(world+0xe8,10);run();assert r(state+24)==0 and r(jobs)==1;checks+=1
  run(cave+m['exports']['bridge_occupied_check'],values=[state,pts,8,77]);assert u.reg_read(UC_X86_REG_EAX)==1;checks+=1
  w(built+0x100,0);w(built+0x84,economy);run();assert r(state+24)==6 and not r(jobs);checks+=1
  before=r(state+24);run();assert r(state+24)==before;checks+=1
  assert not(r(built+8)&0x800);checks+=1
  # Destruction closes real navigation cells and restores exact saved water.
  w(built+8,2);run();assert all(r(tiles+(y*16+x)*0x30)==water for y in range(7,10) for x in range(7,9));checks+=1
  assert bytes(u.mem_read(hp,33*33*4))==oldheight;checks+=1
  # Only automatic candidate/collision checks skip bridges; all other native
  # candidates and non-SP execution still call the original predicate.
  bridge_reset();run(cave+m['exports']['bridge_commit'],values=[state,pts,8])
  ai_vt=world+0xe8000;w(ai,ai_vt);w(ai_vt+0xa4,0x3001d000);w(image+0x4e5c58+0x16c,0x3001d000)
  for export,self in [('bridge_auto_candidate',ai),('bridge_auto_collision',company)]:
   run(cave+m['exports'][export],self=self,values=[built],clean=4);assert u.reg_read(UC_X86_REG_EAX)==0;checks+=1
   run(cave+m['exports'][export],self=self,values=[unit],clean=4);assert u.reg_read(UC_X86_REG_EAX)==1;checks+=1
   w(session+0x100,1);run(cave+m['exports'][export],self=self,values=[built],clean=4);assert u.reg_read(UC_X86_REG_EAX)==(0 if m.get('multiplayer')else 1);checks+=1
   w(session+0x100,0)
  # A company on the far bank must approach that bank, never cross blocked
  # water to reach the numerically first endpoint of the bridge plan.
  bridge_reset();f(company+0x20,27);f(unit+0x20,27);f(company+0x24,17);f(unit+0x24,17)
  run(cave+m['exports']['bridge_request'],values=[state,1,pts,8]);run()
  assert moves[-1]==(23.,17.) and r(jobs+44)==11|(8<<16),(moves[-1],hex(r(jobs+44)));checks+=1
  # Selection uses actor data's deck rectangle, not the 3-D model bound.
  bridge_reset();run();run(cave+m['exports']['bridge_commit'],values=[state,pts,8])
  vfx=world+0xed000;vdata=vfx+0x400;attachment=vfx+0x800;passed=[]
  w(vfx+0x10,vdata);w(vdata+8,vdata+0x100);u.mem_write(vdata+0x100,'selected_square_vfx\0'.encode('utf-16le'));w(vfx+0x90,attachment);w(attachment+0x14,built)
  def decal_native(uc,addr,size,_):
   sp=uc.reg_read(UC_X86_REG_ESP)
   if addr==image+0x2d0749:passed.append(r(sp+4));clean=4;ret=0
   else:clean=0;ret=1
   uc.reg_write(UC_X86_REG_EAX,ret);uc.reg_write(UC_X86_REG_ESP,sp+4+clean);uc.reg_write(UC_X86_REG_EIP,r(sp))
  for off in [0x2d0749,0x2d00af,0x2d0779]:u.hook_add(UC_HOOK_CODE,decal_native,begin=image+off,end=image+off)
  run(cave+m['exports']['bridge_decal_tick'],values=[state,vfx]);assert passed==[bridge_def+0x38] and u.reg_read(UC_X86_REG_EAX)==1;checks+=1
  passed.clear();hook=next(h for h in m['hooks'] if h['site']==0x50e3c8);run(cave+hook['entry'],self=vfx,values=[]);assert passed==[bridge_def+0x38] and u.reg_read(UC_X86_REG_EAX)==1;checks+=1
  w(attachment+0x14,unit);passed.clear();run(cave+m['exports']['bridge_decal_tick'],values=[state,vfx]);assert not passed;checks+=1
  w(attachment+0x14,built);w(session+0x100,1);run(cave+m['exports']['bridge_decal_tick'],values=[state,vfx]);assert bool(passed)==bool(m.get('multiplayer'));checks+=1
  w(session+0x100,0)
  # Cursor near the river chooses both dry banks automatically.
  bridge_reset();run(cave+m['exports']['bridge_auto_check'],values=[state,7,8,pts+0x200])
  assert 5<=u.reg_read(UC_X86_REG_EAX)<=8 and (r(pts+0x200)&65535)<7 and (r(pts+0x200+(u.reg_read(UC_X86_REG_EAX)-1)*4)&65535)>8;checks+=1
  for y in range(16):
   for x in range(7,9):w(tiles+(y*16+x)*0x30+0x20,0x200)
  run(cave+m['exports']['bridge_auto_check'],values=[state,7,8,pts+0x200]);assert u.reg_read(UC_X86_REG_EAX)==0;checks+=1
  # The same hover planner selects a non-cardinal span across a diagonal
  # river, with enough dry space for a whole engineer company at both banks.
  bridge_reset()
  for y in range(16):
   for x in range(16):
    wet=abs(x-y)<=1;w(tiles+(y*16+x)*0x30,water if wet else grass);w(tiles+(y*16+x)*0x30+0x20,0x120 if wet else 0x200)
  for y in range(33):
   for x in range(33):f(hp+(y*33+x)*4,0)
  run(cave+m['exports']['bridge_auto_check'],values=[state,7,7,pts+0x200]);n=u.reg_read(UC_X86_REG_EAX)
  assert n>=5,n;p0=r(pts+0x200);p1=r(pts+0x200+4*(n-1));assert (p0&65535)!=(p1&65535) and (p0>>16)!=(p1>>16);checks+=1
  # Angled native actors, walkable deck strips and height queries survive a
  # cache rebuild. AABB corners outside the rotated deck must remain water.
  import math
  for delta in range(-4,4):
   bridge_reset()
   x0,y0,x1,y1=4,8,11,8+delta;dx=x1-x0;dy=y1-y0;sx=1;sy=1 if dy>=0 else -1;ady=abs(dy);err=dx-ady;path=[];x,y=x0,y0
   while True:
    path.append(x|(y<<16))
    if (x,y)==(x1,y1):break
    e=2*err
    if e>-ady:err-=ady;x+=sx
    if e<dx:err+=dx;y+=sy
   for i,p in enumerate(path):w(pts+4*i,p)
   assert check(len(path))==1,(delta,path);checks+=1
   run(cave+m['exports']['bridge_commit'],values=[state,pts,len(path)]);assert u.reg_read(UC_X86_REG_EAX)==1;checks+=1
   cx,cy=x0+x1+1,y0+y1+1;length=math.hypot(dx,dy);heading=struct.unpack('<2f',u.mem_read(built+0x2c,8))
   assert abs(heading[0]-dx/length)<1e-5 and abs(heading[1]-dy/length)<1e-5;checks+=1
   assert abs(floor(cx,cy)-2.08)<1e-5;checks+=1
   # Exact cross-river cells form one four-connected component, not the
   # entire bounding rectangle around a diagonal bridge.
   deck={(x,y) for y in range(16) for x in range(16) if r(tiles+(y*16+x)*0x30)==bridge}
   assert deck;connected={next(iter(deck))};pending=list(connected)
   while pending:
    x,y=pending.pop()
    for q in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
     if q in deck and q not in connected:connected.add(q);pending.append(q)
   assert connected==deck;checks+=1
   for x,y in deck:assert abs((x*2+1-cx)*heading[1]-(y*2+1-cy)*heading[0])<=3.001;checks+=1
   assert floor(cx-heading[1]*5,cy+heading[0]*5)==-1;checks+=1
   f(world+0xe8,.1);run();assert abs(floor(cx,cy)-2.08)<1e-5;checks+=1
   w(built+8,2);run();assert all(r(tiles+(y*16+x)*0x30)==water for x,y in deck);checks+=1
  run(cave+m['exports']['bridge_fixture_offset'],values=[]);assert u.reg_read(UC_X86_REG_EAX)==19280;checks+=1
  if m.get('installed'):
   # The camera/selection global is VWorld, while a placement brush belongs
   # to the native GameInterface parent of the current control panel.
   reset();panel=world+0xfb000;game=world+0xfc000;w(ui+0x60,panel);w(panel+8,game);w(game,image+0x48e090);run()
   run(cave+m['exports']['bridge_field'],values=[9]);assert r(state+u.reg_read(UC_X86_REG_EAX))==game;checks+=1
print(checks,'PASS: compiled native drag input, route continuity, engineer identity, ownership, water, cancellation, lifecycle, relocated ABI')

