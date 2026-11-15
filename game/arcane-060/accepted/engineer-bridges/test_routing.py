"""Execute the compiled planner and native path adapters on synthetic rivers."""
from pathlib import Path
import argparse,json,struct,sys
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
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x400000);u.mem_map(0x30000000,0x20000)
 state=cave+m['roadState'];world=0x20000000;session=world+0x1000;grid=world+0x2000;tiles=world+0x10000;registry=world+0x100000
 arena=world+0x200000;allocation=[arena];commands=[];queue=[];freed=[];friendly=[1];picked=[0];activations=[];selection=[False]
 def w(at,v):u.mem_write(at,struct.pack('<I',v&0xffffffff))
 def f(at,v):u.mem_write(at,struct.pack('<f',v))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 def rf(at):return struct.unpack('<f',u.mem_read(at,4))[0]
 def native(uc,at,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);self=uc.reg_read(UC_X86_REG_ECX);ret=0;clean=0
  if at==image+0x2ef03c:ret=allocation[0];allocation[0]+=((r(sp+4)+15)//16)*16
  elif at==image+0x3e1285:freed.append(r(sp+4))
  elif at==image+0x22f3d7:u.mem_write(self,bytes(u.mem_read(r(sp+4),64)));w(self+4,0);ret=self;clean=4
  elif at==image+0x42fca:freed.append(r(r(sp+4))) if False else freed.append(r(self))
  elif at==image+0x279429:
   cmd=r(sp+4);item=(r(r(cmd+8)+12),rf(cmd+24),rf(cmd+28),u.mem_read(cmd+60,1)[0]);commands.append(item)
   if not item[3]:queue.clear()
   queue.append(item);ret=1 if not item[3] else 0;clean=4
  elif at==image+0x2d8c10:ret=picked[0]
  elif at==image+0x2be624:ret=world+0xf0000
  elif at==image+0x22f2ce:ret=friendly[0];clean=4
  elif at in [image+0x26f1cf,image+0x26f0d1]:
   count=6 if at==image+0x26f1cf else 5;activations.append((at-image,list(struct.unpack('<'+'I'*count,u.mem_read(sp+4,count*4)))));ret=1;clean=count*4
  elif at==image+0x263752:activations.append((at-image,list(struct.unpack('<6I',u.mem_read(sp+4,24)))));ret=0x123;clean=24
  elif at==image+0x27031c:activations.append((at-image,list(struct.unpack('<2I',u.mem_read(sp+4,8)))));ret=1;clean=8
  elif at==image+0x270431:activations.append((at-image,[]));ret=1
  elif at==image+0x279072:w(self+12,0)
  elif at==image+0x216535:activations.append((at-image,list(struct.unpack('<3I',u.mem_read(sp+4,12)))));ret=1;clean=12
  elif at==image+0x20583d:pass
  elif at==image+0x20dbcb:ret=1
  elif at==image+0x205e72:w(r(self+4)+0x100,0x40000000)
  elif at==image+0x205ec2:w(r(self+4)+0x100,0x08000000)
  elif at==image+0x22a99c:activations.append(('economy-refresh',self))
  elif at==image+0x202f8c:f(self+0x10,rf(sp+4));clean=16
  elif at==image+0x202e47:activations.append(('heal',r(r(sp+4)),rf(r(sp+4)+4)));clean=4
  elif at==image+0x245157:activations.append(('dying',r(sp+4)));w(r(sp+4)+8,r(r(sp+4)+8)|2);clean=4
  elif at==image+0x24516a:w(r(sp+4)+8,r(r(sp+4)+8)|1);clean=8
  elif at==image+0x2c6a85:f(r(sp+12)+8,-2);ret=1;clean=12
  elif at==image+0x27b99b:
   node=allocation[0];allocation[0]+=64;u.mem_write(node,bytes(u.mem_read(r(sp+4),32)));w(node+36,r(self+4));w(self+4,node);activations.append(('path-port',self,node));clean=4
  elif at==image+0x2ebc74:activations.append(('stock-outline',list(struct.unpack('<6I',u.mem_read(sp+4,24)))));ret=world+0xec000;clean=24
  elif at==image+0x2e4590:w(self+0x54,(r(self+0x54)&~0x800000)|(0x800000 if selection[0] else 0));ret=0x53
  elif at==image+0x2d00af:ret=0x73
  elif at==image+0x1a43c4:activations.append(('ground-position',self,struct.unpack('<2f',u.mem_read(r(sp+4),8))));clean=4
  elif at==image+0x1a43f0:
   xy=struct.unpack('<2f',u.mem_read(r(sp+4),8));activations.append(('ground-direction',self,xy));f(self+0x30,0);f(self+0x34,0);f(self+0x38,xy[0]);f(self+0x3c,xy[1]);clean=4
  elif at==image+0x1a4474:
   size=struct.unpack('<2f',u.mem_read(sp+4,8));activations.append(('ground-size',self,size));f(self+0x74,size[0]);f(self+0x78,size[1]);clean=8
  else:raise AssertionError(hex(at))
  uc.reg_write(UC_X86_REG_EAX,ret);uc.reg_write(UC_X86_REG_ESP,sp+4+clean);uc.reg_write(UC_X86_REG_EIP,r(sp))
 for off in [0x2ef03c,0x3e1285,0x22f3d7,0x42fca,0x279429,0x2d8c10,0x2be624,0x22f2ce,0x26f1cf,0x26f0d1,0x263752,0x27031c,0x270431,0x279072,0x216535,0x20583d,0x20dbcb,0x205e72,0x205ec2,0x22a99c,0x202f8c,0x202e47,0x245157,0x24516a,0x2c6a85,0x27b99b,0x2ebc74,0x2e4590]:u.hook_add(UC_HOOK_CODE,native,begin=image+off,end=image+off)
 for off in [0x2d00af,0x1a43c4,0x1a43f0,0x1a4474]:u.hook_add(UC_HOOK_CODE,native,begin=image+off,end=image+off)
 def run(name,values,self=None):
  sp=0x3000f000;u.mem_write(sp,struct.pack('<'+'I'*(len(values)+1),0x3001f000,*values));u.reg_write(UC_X86_REG_ESP,sp)
  if self is not None:u.reg_write(UC_X86_REG_ECX,self)
  u.emu_start(cave+m['exports'][name],0x3001f000,count=10000000)
  assert u.reg_read(UC_X86_REG_EIP)==0x3001f000 and u.reg_read(UC_X86_REG_ESP)==sp+4+(len(values)*4 if self is not None else 0)
  return u.reg_read(UC_X86_REG_EAX)
 w(state,image);w(state+4,cave+m['adapter']);w(image+0x5f3fc0,0);run('roads_tick',[state,0]);w(state+12,world)
 w(image+0x5f3fb8,world);w(image+0x5f3fe4,session);w(image+0x5f9218,2);w(image+0x5ef72c,registry);w(session+0xf0,2)
 w(world+0x30,grid);w(grid+4,1);w(grid+28,64);w(grid+32,64);w(grid+40,tiles)
 span=state+run('bridge_field',[2]);w(state+run('bridge_field',[0]),world);w(state+run('bridge_field',[1]),1)
 a=world+0x80000;w(a,image+0x4e5c58);w(a+20,100);w(registry+0x20004+100*4,a);w(span,100);w(span+24,1)
 for off,v in [(4,57),(8,71),(12,31-3.2),(16,31+3.2),(20,1.08),(2080,1),(2084,0),(2088,7)]:f(span+off,v)
 def reset_river(gap=True):
  for y in range(64):
   for x in range(64):w(tiles+(y*64+x)*48+32,0x100 if 30<=x<=33 and not (gap and y<3) else 0x200)
  for y in range(14,17):
   for x in range(28,36):w(tiles+(y*64+x)*48+32,0x200)
 def plan(sx,sy,dx,dy):
  at=world+0x90000;n=run('bridge_route_plan',[state,*[struct.unpack('<I',struct.pack('<f',v))[0] for v in (sx,sy,dx,dy)],at]);return [struct.unpack('<2f',u.mem_read(at+i*8,8)) for i in range(n)]
 def valid_route(points,start,goal):
  assert points and points[-1]==goal
  last=start
  for point in points:
   fc=(int(last[1])//2)*64+int(last[0])//2;tc=(int(point[1])//2)*64+int(point[0])//2
   assert run('bridge_route_clear_check',[tiles,fc,tc,64]),(last,point)
   last=point
 reset_river();ports=plan(40,60,88,60);valid_route(ports,(40,60),(88.,60.))
 assert len(ports)<=5 and min(y for x,y in ports)<40;checks+=4
 reverse=plan(88,60,40,60);valid_route(reverse,(88,60),(40.,60.));checks+=1
 # The nearer of two completed crossings wins, in both directions.
 second=span+2092;other=world+0x81000;w(other,image+0x4e5c58);w(other+20,102);w(registry+0x20004+102*4,other);w(second,102);w(second+24,1)
 for off,v in [(4,57),(8,71),(12,59.8),(16,66.2),(20,1.08),(2080,1),(2084,0),(2088,7)]:f(second+off,v)
 w(state+run('bridge_field',[1]),2)
 for y in range(30,33):
  for x in range(28,36):w(tiles+(y*64+x)*48+32,0x200)
 near=plan(40,60,88,60);valid_route(near,(40,60),(88.,60.));assert min(y for x,y in near)>50;checks+=1
 valid_route(plan(88,60,40,60),(88,60),(40.,60.));checks+=1
 w(state+run('bridge_field',[1]),1);reset_river()
 # A model's long dry approaches must not become mandatory path ports.
 # Only its original river cells constrain the crossing route.
 w(span+28,12)
 for index,(x,y) in enumerate((x,y) for y in range(14,17) for x in range(30,34)):w(span+32+index*4,x|(y<<16))
 trimmed=plan(40,60,88,60);valid_route(trimmed,(40,60),(88.,60.));assert len(trimmed)<=5;checks+=3
 w(span+28,0)
 assert plan(40,60,40,100)==[];checks+=1
 inside=plan(40,60,64,31);assert inside and all(x<=65 for x,y in inside);checks+=1
 fromdeck=plan(64,31,88,60);assert fromdeck and all(x>=63 for x,y in fromdeck);checks+=1
 # Removing a bridge must never return an incomplete crossing; the dry detour
 # stays the native engine's responsibility when no bridge lies on the route.
 w(a+8,2)
 for y in range(14,17):
  for x in range(30,34):w(tiles+(y*64+x)*48+32,0x100)
 assert plan(40,60,88,60)==[];checks+=1
 reset_river(False);assert plan(40,60,88,60)==[];checks+=1
 w(a+8,0);reset_river();company=world+0x82000;mind=company+0x400;de=company+0x800;cmd=company+0xc00;actdef=de+0x100
 w(company,image+0x4e5c58);w(company+20,101);w(registry+0x20004+101*4,company);w(company+4,actdef);w(actdef+0x234,0x100);w(company+0x7c,1);f(company+32,40);f(company+36,60);w(mind+4,company);w(cmd+8,de);w(de+12,5);w(cmd+12,4);f(cmd+24,88);f(cmd+28,60)
 # Right-click a visible deck whose terrain intersection is under water.
 # At an oblique camera angle that raw point lies outside the deck corridor.
 ui=world+0xd0000;cam=world+0xd1000;view=world+0xd2000;bridge_def=world+0xd3000
 w(image+0x5f3fbc,ui);w(image+0x5fafe0,cam+0x200);w(cam+0x200,cam)
 w(image+0x4e5c58+0x138,image+0x22f2ce)
 w(a+4,bridge_def);w(bridge_def+8,bridge_def+0x100);u.mem_write(bridge_def+0x100,'paws_bridge_stone_y_08\0'.encode('utf-16le'))
 f(a+32,64);f(a+36,31);f(a+40,1);f(a+44,1);f(a+48,0);w(view+20,a);picked[0]=view
 for off,v in [(0x90,114),(0x94,-19),(0x98,51)]:f(cam+off,v)
 for off,v in [(0x184,61),(0x188,34),(0x18c,-2)]:f(ui+off,v)
 assert run('bridge_context_pick',[state,0])==0;checks+=1
 assert abs(rf(ui+0x184)-64)<.001 and abs(rf(ui+0x188)-31)<.001 and abs(rf(ui+0x18c)-1)<.001;checks+=3
 friendly[0]=0;assert run('bridge_context_pick',[state,0])==0;checks+=1
 friendly[0]=1;w(a+0x100,0x200000);assert run('bridge_context_pick',[state,0])==view;checks+=1
 # AI object travel becomes a crossing, while explicit building interactions
 # keep the original native object activation and all five arguments intact.
 w(a+0x100,0);move=world+0xe0000;w(move+4,mind);w(mind+0x20,cmd);w(de+12,5)
 args=[0,a,3,0x12345678,0x87654321]
 run('bridge_move_to_actor',args,self=move);kind,got=activations[-1];assert kind==0x26f1cf and got[0]==0 and got[3:]==args[2:];checks+=2
 assert struct.unpack('<f',struct.pack('<I',got[1]))[0]>71 and struct.unpack('<f',struct.pack('<I',got[2]))[0]==31;checks+=2
 for command in [0,3,4]:
  w(de+12,command);run('bridge_move_to_actor',args,self=move);assert activations[-1]==(0x26f0d1,args);checks+=1
 # An explicit repair/resume preserves the object command but moves its
 # approach state to an accessible landing, including an unfinished span.
 w(de+12,3);w(cmd+16,100);w(a+0x100,0x200000)
 run('bridge_move_to_actor',args,self=move);kind,got=activations[-1];assert kind==0x26f1cf and got[3:]==args[2:] and r(cmd+16)==100;checks+=3
 assert abs(struct.unpack('<f',struct.pack('<I',got[1]))[0]-54.5)<.001 and struct.unpack('<f',struct.pack('<I',got[2]))[0]==31;checks+=2
 w(a+0x100,0);w(cmd+16,0);w(de+12,5)
 path=world+0xe1000;query=world+0xe2000;w(query+0x1c,company)
 def region_args(sx,sy,dx,dy):return [path,*[struct.unpack('<I',struct.pack('<f',v))[0] for v in [sx,sy,dx,dy]],query]
 before=len(activations);saved_flags=r(company+8);args=region_args(40,60,88,60)
 assert run('bridge_region_route',args,self=world+0xe3000)==1 and len(activations)>before;checks+=2
 head=r(path+4);assert r(company+8)==saved_flags and head and r(path+0x18)==0xffffffff;checks+=3
 actual=[]
 while head:
  actual.append((rf(head),rf(head+4)));assert r(head+16)==2
  if not r(head+36):assert abs(rf(head+8))+abs(rf(head+12))>.99;checks+=1
  head=r(head+36)
 assert actual==ports and commands==[];checks+=2
 w(path+4,0)
 # Unit queries retain their own native destinations and collision planner;
 # no ordinal lane offset pushes a copied route off a narrow deck.
 org=world+0xf1000;members=org+0x100;unit=org+0x200;element=org+0x400
 w(company+0x7c,org);w(org+4,company);w(org+0x2c,2);w(org+0x28,members);w(members,unit);w(members+4,unit+0x100)
 for index in range(2):
  mover=unit+index*0x100;w(mover,image+0x4e5c58);w(mover+20,103+index);w(registry+0x20004+(103+index)*4,mover);w(mover+0x80,element+index*0x100);w(element+index*0x100+0x10,company);w(query+0x1c,mover)
  assert run('bridge_region_route',args,self=world+0xe3000)==1;head=r(path+4);lane=[]
  while head:lane.append((rf(head),rf(head+4)));head=r(head+36)
  assert lane==ports and lane[-1]==(88.,60.);checks+=3
  w(path+4,0)
 w(query+0x1c,company)
 args=region_args(40,60,40,100)
 assert run('bridge_region_route',args,self=world+0xe3000)==0x123 and activations[-1]==(0x263752,args);checks+=2
 for flag in [0x1000,0x200000]:
  w(company+8,flag);args=region_args(40,60,88,60);assert run('bridge_region_route',args,self=world+0xe3000)==0x123;checks+=1
 attack=world+0xe4000;w(attack+4,mind);w(attack+16,100);w(mind+0x20,0)
 before=len(activations);assert run('bridge_attack_activate',[0,a],self=attack)==0 and len(activations)==before;checks+=2
 w(attack+12,2);run('bridge_attack_tick',[state,attack]);assert r(attack+12)==0 and r(attack+16)==0;checks+=2
 w(mind+0x20,cmd);w(de+12,0);w(cmd+12,1);w(cmd+16,100)
 assert run('bridge_attack_activate',[0,a],self=attack)==1 and activations[-1]==(0x27031c,[0,a]);checks+=2
 w(attack+16,100);w(attack+12,2);run('bridge_attack_tick',[state,attack]);assert activations[-1]==(0x270431,[]) and r(attack+12)==2;checks+=2
 w(cmd+12,4);assert run('bridge_attack_activate',[0,a],self=attack)==0;checks+=1
 before=len(activations);assert run('bridge_auto_organization',[a,1,1],self=world+0xe5000)==0 and len(activations)==before;checks+=2
 assert run('bridge_auto_organization',[company,1,1],self=world+0xe5000)==1 and activations[-1]==(0x216535,[company,1,1]);checks+=2
 w(company+0x70,mind);w(org+4,company);w(cmd+12,1);w(cmd+16,100);w(de+12,0)
 assert run('bridge_auto_organization',[a,1,1],self=org)==1 and activations[-1]==(0x216535,[a,1,1]);checks+=2
 # Native saved razing state, exact simulated-time decay, cancellable upkeep.
 body=world+0xe6000;construction=world+0xe7000;w(a+0x60,body);w(construction+4,a)
 def health_step(dt):return run('bridge_health_check',[state,struct.unpack('<I',struct.pack('<f',dt))[0]])
 w(a+8,0);w(a+0x100,0);f(body+16,1000);f(body+20,1000)
 run('bridge_construction_commands',[],self=construction);assert r(a+0xf0)&(1<<22) and not r(a+0xf0)&(1<<19);checks+=2
 run('bridge_raze_start',[],self=construction);assert r(a+0x100)&0x40000000 and activations[-1]==('economy-refresh',a);checks+=2
 assert run('bridge_upkeep_active',[a])==0;checks+=1
 u.mem_write(bridge_def+0x100,'paws_bridge_wood_y_08\0'.encode('utf-16le'))
 health_step(1);assert rf(body+16)==990;checks+=1
 health_step(.5);assert rf(body+16)==985;checks+=1
 health_step(0);assert rf(body+16)==985;checks+=1
 run('bridge_construction_commands',[],self=construction);assert r(a+0xf0)&(1<<19) and not r(a+0xf0)&(1<<22);checks+=2
 run('bridge_raze_cancel',[],self=construction);assert not r(a+0x100)&0x40000000 and run('bridge_upkeep_active',[a])==1;checks+=2
 health_step(10);assert rf(body+16)==985;checks+=1
 u.mem_write(bridge_def+0x100,'paws_bridge_stone_y_08\0'.encode('utf-16le'));f(body+16,2000);f(body+20,2000);w(a+0x100,0x40000000)
 health_step(2);assert rf(body+16)==1980;checks+=1
 u.mem_write(bridge_def+0x100,'paws_bridge_haroun_stone_y_08\0'.encode('utf-16le'));w(a+0x100,0)
 health_step(5);assert rf(body+16)==1990;checks+=1
 health_step(10);assert rf(body+16)==2000;checks+=1
 w(a+0x100,0x40000000);f(body+16,5);health_step(1);assert rf(body+16)==0 and r(a+8)&2 and activations[-1]==('dying',a);checks+=3
 # Paid Haroun construction uses native periodic modifiers, never wall time
 # or a pulse on a preview/unpaid provisional site. Completion keeps only .1%.
 props=world+0xed000;mods=props+0x200;modifier=props+0x300;paid=props+0x400;w(body+4,a)
 w(a+8,0);w(a+0x78,props);w(a+0x9c,construction);w(construction+0x10,paid);w(construction+0x14,1)
 w(props+0xc0,mods);w(props+0xc4,1);w(mods,modifier);f(modifier+0xc,15);f(paid,0);w(a+0x100,0x200000);f(body+16,100)
 health_step(1);assert rf(body+16)==100;checks+=1
 saved_name=props+0xa00;w(a+0x18,saved_name);u.mem_write(saved_name,'paws_bridge_meta1|U123|\0'.encode('utf-16le'))
 f(paid,160);health_step(1);assert rf(body+16)==100;checks+=1
 u.mem_write(saved_name,'paws_bridge_meta1|P123|\0'.encode('utf-16le'))
 f(paid,160);health_step(1);assert rf(body+16)==115;checks+=1
 w(props+0xc4,2);w(mods+4,modifier+0x20);f(modifier+0x20+0xc,10);health_step(.5);assert rf(body+16)==127.5;checks+=1
 w(a+0x100,0);health_step(1);assert rf(body+16)==129.5;checks+=1
 packet=props+0x500;f(packet+4,25);before=len(activations);run('bridge_periodic_heal',[packet],self=body);assert len(activations)==before;checks+=1
 # Only caretaker construction of the base Haroun keep receives fivefold
 # work. Outposts, upgrades, finished repairs and other workers stay native.
 healer=props+0x600;healer_def=props+0x800;w(healer+4,healer_def);w(healer_def+8,healer_def+0x100);w(packet,healer);f(packet+4,1)
 for target,worker,building,expected in [('haroun_keep','caretaker',True,5),('haroun_outpost','caretaker',True,1),('haroun_keep_1','caretaker',True,1),('haroun_keep','combat_caretaker',True,1),('haroun_keep','caretaker',False,1)]:
  u.mem_write(bridge_def+0x100,(target+'\0').encode('utf-16le'));u.mem_write(healer_def+0x100,(worker+'\0').encode('utf-16le'));w(a+0x100,0x200000 if building else 0)
  run('bridge_construct_heal',[packet],self=body);assert activations[-1]==('heal',healer,expected) and rf(packet+4)==1;checks+=2
 u.mem_write(bridge_def+0x100,'paws_bridge_haroun_stone_y_08\0'.encode('utf-16le'))
 # A persistent command flag uses its final deck plane even though the
 # original FXC placement grounded it on the bed; unrelated FX stay native.
 w(a+8,0);w(a+0x100,0);fxc=world+0xe8000;vfxdef=world+0xe9000;point=world+0xea000
 w(fxc+0x3c,vfxdef);w(vfxdef+8,vfxdef+0x100);u.mem_write(vfxdef+0x100,'waypoint_move_location\0'.encode('utf-16le'));f(point,64);f(point+4,31)
 assert run('bridge_waypoint_position',[0,0,point],self=fxc)==1 and abs(rf(point+8)-1.08)<1e-5;checks+=2
 u.mem_write(vfxdef+0x100,'fire_effect\0'.encode('utf-16le'));run('bridge_waypoint_position',[0,0,point],self=fxc);assert rf(point+8)==-2;checks+=1
 # Add the stock projected selection only on the native selection edge.
 w(view+0x10,bridge_def);w(view+0x54,0);w(bridge_def+0x148,vfxdef);selection[0]=True
 assert run('bridge_selection_tick',[],self=view)==0x53;checks+=1
 assert activations[-1]==('stock-outline',[vfxdef,view,0,image+0x603694,0,0]) and r(world+0xec000+0x78)==vfxdef;checks+=2
 before=len(activations);run('bridge_selection_tick',[],self=view);assert len(activations)==before;checks+=1
 selection[0]=False;run('bridge_selection_tick',[],self=view);assert len(activations)==before;checks+=1
 selection[0]=True;w(view+20,0);run('bridge_selection_tick',[],self=view);assert len(activations)==before;checks+=1
 # Fixed-size racial terrain aprons follow both actual rotated endpoints.
 # The native projected-texture tick and callee-clean position ABI survive.
 ground=world+0xf3000;projector=world+0xf4000;grounddef=world+0xf5000
 w(ground+0x90,view);w(view+20,a);w(ground+0x10,grounddef);w(grounddef+8,grounddef+0x100)
 u.mem_write(grounddef+0x100,'paws_bridge_ground_human\0'.encode('utf-16le'))
 w(ground+0xd4,projector);w(projector,projector+0x100);w(projector+0x100+0x38,image+0x1a43c4)
 w(projector+0x100+0x3c,image+0x1a43f0)
 for axis in ['x','y']:
  u.mem_write(bridge_def+0x100,('paws_bridge_human_wood_'+axis+'_08\0').encode('utf-16le'))
  for ux,uy in [(1,0),(0,-1),(.6,-.8)]:
   f(a+44,ux);f(a+48,uy)
   gx,gy=(uy,-ux) if axis=='x' else (ux,uy)
   for end in [-7,7]:
    f(ground+0x38,end if axis=='x' else 0);f(ground+0x3c,end if axis=='y' else 0)
    actorBefore=bytes(u.mem_read(a,0x200));gridBefore=bytes(u.mem_read(tiles,64*64*48))
    assert run('bridge_decal_tick',[state,ground])==0x73
    kind,receiver,xy=activations[-1];side=-1 if end>0 else 1
    assert kind=='ground-position' and receiver==projector and abs(xy[0]-(64+gx*6.2*side))<.0001 and abs(xy[1]-(31+gy*6.2*side))<.0001;checks+=2
    assert abs(rf(projector+0x74)-8)<1e-5 and abs(rf(projector+0x78)-7.2)<1e-5;checks+=2
    assert abs(rf(projector+0x38)-gx*side)<1e-5 and abs(rf(projector+0x3c)-gy*side)<1e-5;checks+=2
    assert bytes(u.mem_read(a,0x200))==actorBefore and bytes(u.mem_read(tiles,64*64*48))==gridBefore;checks+=2
    first=len(activations);assert run('bridge_decal_tick',[state,ground])==0x73 and len(activations)==first+1 and activations[-1][0]=='ground-position';checks+=2
 before=len(activations);u.mem_write(grounddef+0x100,'unrelated_decal\0'.encode('utf-16le'));assert run('bridge_decal_tick',[state,ground])==0x73 and len(activations)==before;checks+=1
print('ROUTING_PASS',checks,'compiled checks across two relocations')
