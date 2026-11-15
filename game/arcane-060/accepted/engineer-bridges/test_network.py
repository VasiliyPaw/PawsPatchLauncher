"""Compiled common-order receiver and native network-field contract.
Geometry/ownership use explicit native ABI fixtures, not a live match.
"""
from pathlib import Path
source=Path(__file__).with_name('test_ai.py').read_text()
exec(compile(source[:source.index('for image,cave in')],str(Path(__file__).with_name('test_ai.py')),'exec'))
assert m.get('multiplayer');checks=0
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 for replica in ['host','remote']:
  f=Fixture(image,cave);f.w(f.session+0x100,1);admin=0x20780000;f.w(image+0x5f3fec,admin);f.w(admin+0x2e4,admin if replica=='host'else admin+4)
  cmd=0x20790000;definition=f.definition('move');f.w(definition+0xc,5);f.w(cmd+8,definition)
  # Exact live network serializer masks flags to 11 bits; point fields are
  # present only under 4 and 8, integer field under 16, +30 is only one bit.
  flags=0x40|0x400|4|8|16;payload=0x42524700|12|128
  assert flags<0x800 and flags&4 and flags&8 and flags&16;checks+=4
  f.w(cmd+0xc,flags&0x7ff);f.w(cmd+0x28,payload)
  for i,v in enumerate([87,97,109,97]):f.f(cmd+0x18+i*4,v)
  forwarded=[]
  def native_process(uc,addr,size,_):
   sp=uc.reg_read(UC_X86_REG_ESP);forwarded.append(f.r(sp+4));uc.reg_write(UC_X86_REG_EAX,1);uc.reg_write(UC_X86_REG_ESP,sp+8);uc.reg_write(UC_X86_REG_EIP,f.r(sp))
  f.u.hook_add(UC_HOOK_CODE,native_process,begin=image+0x22f651,end=image+0x22f651)
  def receive():return f.call('bridge_net_process',[f.builder],selfptr=cmd)
  assert receive()==1;checks+=1
  job,jobsize,tools,construction,committed,*_=f.jobLayout
  assert f.r(f.state+job)==100 and f.r(f.state+job+4)==2;checks+=2
  assert f.r(f.state+tools)==1 and f.r(f.state+job+32)==12;checks+=2
  assert f.r(f.state+job+44)==43|(48<<16);checks+=1
  nl=f.constants('bridge_net_layout',3);assert f.r(f.state+nl[0]+4)==100;checks+=1
  assert not forwarded;checks+=1
  # A genuine ordinary move remains ordinary and cancels on every replica.
  f.w(cmd+0xc,0x44);assert receive()==1 and f.r(f.state+job)==0 and forwarded==[f.builder];checks+=3
  # Matching tagged malformed packets are dropped, never becoming movements.
  f.w(cmd+0xc,flags)
  for packet,coords in [(0x42524700,[87,97,109,97]),(payload,[88,97,109,97]),(payload,[87,float('nan'),109,97]),(0x42524700|33,[87,97,109,97])]:
   f.w(cmd+0x28,packet)
   for i,v in enumerate(coords):f.f(cmd+0x18+i*4,v)
   assert receive()==0 and f.r(f.state+job)==0 and forwarded==[f.builder];checks+=3
  # Other native move flags/signatures are forwarded without interpretation.
  f.w(cmd+0x28,123);assert receive()==1 and len(forwarded)==2;checks+=2
 # The host must reserve an AI builder even after the common restore pass
 # has already reconstructed that builder's paid job on every replica.
 f=Fixture(image,cave);f.w(f.session+0x100,1);f.w(image+0x5f3fec,admin);f.w(admin+0x2e4,admin)
 site=f.danger;f.make_actor(site,300,f.kingdom,97,97);f.w(site+4,f.definition('paws_bridge_wood_y_12'));f.w(site+0x100,0x200000)
 f.w(site+0x60,site+0x500);f.f(site+0x510,100);f.f(site+0x514,2000)
 f.move(f.builder,85,97);cmd=f.builder+0xb00;f.w(cmd+8,f.definition('repair'));f.w(f.r(cmd+8)+0xc,3);f.w(cmd+0xc,1);f.w(cmd+0x10,300)
 f.w(f.state+f.call('bridge_field',[1]),1);f.w(f.state+f.call('bridge_field',[2]),300)
 job,jobsize,tools,construction,committed,*_=f.jobLayout
 f.w(f.state+job,100);f.w(f.state+job+4,2);f.w(f.state+tools,1);f.w(f.state+construction,300);f.w(f.state+committed,1)
 f.tick(0);assert f.count(10)==1 and f.count(2)==0;checks+=2
 ai=f.state+f.aiLayout[0]+f.aiLayout[2];assert f.r(ai+4)==100 and f.r(ai+8)==300 and f.r(ai+12)==1;checks+=3
print('NETWORK_BRIDGE_PASS',checks,'compiled receiver/ownership/cancellation/restore/field checks on host and remote replicas at two relocations')
