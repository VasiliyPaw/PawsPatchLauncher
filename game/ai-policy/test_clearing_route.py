"""Compiled clearing callbacks plus original native regional threat traversal
and path-list destruction at three ASLR bases. Route production, allocation,
diplomacy/fog and goal bookkeeping are explicit stubs, not a played match.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_clearing.py').read_text().split('\nfor image,cave in ')[0], 'test_clearing.py:fixtures','exec'))

class RouteFixture(GroupFixture):
 def __init__(self,image=0x460000,cave=0x10000000):
  super().__init__(image,cave)
  self.regions=0x510e0000;self.table=self.regions+0x100;self.router=0x510ee000;self.nodes=0x510ef000
  self.w(image+0x5f3fcc,self.regions);self.w(self.regions+0x14,self.table);self.w(self.regions+0x18,5)
  self.w(self.world+0x23c,self.router)
  for i in range(5):
   p=self.region(i);self.w(self.table+4*i,p);self.w(p,i)
   self.w(p+0x38,2);self.w(p+0x34,p+0x100)
   self.w(p+0x100,p+0x140);self.w(p+0x104,p+0x150)
  self.w(self.target+0x48,self.region(3));self.configure_sa(self.sa,0)
  self.w(image+0x4da480+0x6c,image+0x1d6817)
  self.asm(image+0x1d6817,f'inc dword ptr [{self.stats+116}];mov eax,1;ret 4')
  # Native route query ABI: ECX router, out-list/source-ID/target-ID/flags.
  self.asm(image+0x2648eb,f'''
   inc dword ptr [{self.stats+104}];cmp ecx,{self.router};jne bad;
   cmp dword ptr [esp+12],3;jne bad;cmp dword ptr [esp+16],1;jne bad;
   inc dword ptr [{self.stats+124}];
   mov eax,[esp+4];mov dword ptr [eax],{self.nodes};mov dword ptr [eax+4],{self.nodes+24};
   mov edx,[esp+8];mov [{self.nodes}],edx;mov dword ptr [{self.nodes+4}],0;
   mov dword ptr [{self.nodes+8}],{self.nodes+12};mov dword ptr [{self.nodes+12}],1;
   mov dword ptr [{self.nodes+16}],{self.nodes};mov dword ptr [{self.nodes+20}],{self.nodes+24};
   mov dword ptr [{self.nodes+24}],3;mov dword ptr [{self.nodes+28}],{self.nodes+12};mov dword ptr [{self.nodes+32}],0;
   cmp dword ptr [{self.stats+112}],0;jne bad;
   mov eax,[{self.stats+120}];test eax,eax;jz good;cmp [{self.stats+104}],eax;jae bad;
   good:mov eax,1;ret 16;bad:xor eax,eax;ret 16
  ''')
  # Actual native known-hostile-building traversal (0,1 branch), CV query and
  # owned-list destructor. Relocate only the verified absolute operands.
  for start,end in [(0x1f582a,0x1f59a7),(0x763dc,0x763ec),(0x764d6,0x76508)]:
   code=bytearray(game[start:end])
   for rva in (0x5f3fb8,0x5ef72c,0x451240):
    code=code.replace(struct.pack('<I',0x460000+rva),struct.pack('<I',image+rva))
   self.u.mem_write(image+start,bytes(code))
  self.asm(image+0x3e1285,f'inc dword ptr [{self.stats+108}];ret')
  self.asm(image+0xb8afb,f'mov eax,{self.kingdom+0x800};ret 4')
  self.w(self.kingdom,image+0x4000);self.w(image+0x4000+0x140,image+0x4200)
  self.asm(image+0x4200,'mov eax,1;ret 4')
  self.asm(image+0x21117,f'mov eax,[esp+4];and eax,65535;mov eax,[eax*4+{self.reg+0x20004}];ret 4')
  self.w(image+0x4e5c58+0x58,image+0x4300);self.asm(image+0x4300,'mov eax,1;ret 8')
  self.f(image+0x451240,0)
  # Camp guards in destination; an off-route neighboring camp in region4.
  self.threat(3);self.threat(4)
 def region(self,i):return self.regions+0x1000+i*0x400
 def configure_sa(self,sa,region):
  self.w(sa,self.image+0x4400);self.w(self.image+0x4408,self.image+0x4500);self.w(sa+0x24,self.region(region))
  self.asm(self.image+0x4500,'mov eax,[ecx+0x24];ret')
 def army(self,cv=100,x=20):
  row=super().army(cv,x);self.configure_sa(row[0],2);return row
 def threat(self,i,on=True):
  p=self.region(i);self.w(p+0x150,p+0x180 if on else 0);self.w(p+0x180,2)
 def call(self,h,*args,allowed=(),**kw):
  # Writes only to the native planner's owned scratch list (not actor state).
  return super().call(h,*args,allowed=list(allowed)+list(range(self.nodes,self.nodes+36,4)),**kw)
 def balanced(self):
  check(self.r(self.stats+124)*3==self.r(self.stats+108),'every native route node released')

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 f=RouteFixture(image,cave);f.army();f.warm()
 check(f.plan()==2,'nearby-region refusal no longer rejects clear actual routes')
 check(f.r(f.stats+104)==4,'route rechecked for each candidate and at commit')
 check(all(e[-1]==1 for e in f.events(51)),'clear routes diagnosed');f.balanced()
 f=RouteFixture(image,cave);f.army();f.army(x=24);f.threat(0);f.warm()
 check(f.plan()==2 and f.r(f.sa+0x10)==f.source,'blocked first company skipped; two later companies form complete force')
 check(any(e[-1]==2 for e in f.events(51)),'actual traversed obstruction diagnosed');f.balanced()
 for case in ('route-building','unreachable','invalid-region','wrong-destination','missing-region','different-vmethod','ordinary-target','foundation','hidden','ally','dead','wound','morale','combat','insufficient','disabled','late-refusal'):
  f=RouteFixture(image,cave);sa,act,org,unit,state=f.army()
  if case=='route-building':f.threat(1)
  if case=='unreachable':f.w(f.stats+112,1)
  if case=='invalid-region':f.w(f.table+4,0)
  if case=='wrong-destination':f.w(f.target+0x48,f.region(2))
  if case=='missing-region':f.w(f.target+0x48,0)
  if case=='different-vmethod':f.w(image+0x4da480+0x6c,image+0x2000);f.w(f.stats+28,1)
  if case=='ordinary-target':f.w(f.target,image+0x4d84d4);f.w(image+0x4d84d4+0x6c,image+0x1d6817)
  if case=='foundation':f.w(f.ldef+0x4e0,0)
  if case=='hidden':f.w(f.stats+16,0)
  if case=='ally':f.w(f.stats+12,1)
  if case=='dead':f.w(f.lair+8,1)
  if case=='wound':f.f(unit+0x210,69)
  if case=='morale':f.f(org+0x5c,46)
  if case=='combat':f.w(state,image+0x4f4e20)
  if case=='insufficient':f.f(org+0x68,20)
  if case=='disabled':f.w(f.data+4,7)
  if case=='late-refusal':f.w(f.stats+120,3)
  f.warm();check(f.plan()==0,('route fallback preserves veto',case))
  check(all(f.r(t[0]+0x10)==f.source for t in f.armies),('no partial assignment',case));f.balanced()
 # Preserve native hostility, knowledge and nonpositive-CV semantics.
 for case in ('friendly-building','unknown-building','zero-building-cv'):
  f=RouteFixture(image,cave);f.army();f.threat(1)
  if case=='friendly-building':f.asm(image+0x4200,'xor eax,eax;ret 4')
  if case=='unknown-building':f.asm(image+0x4300,'xor eax,eax;ret 8')
  if case=='zero-building-cv':f.f(f.den+0x10,0)
  f.warm();check(f.plan()>0,('native threat semantics',case));f.balanced()
print('AI_CLEARING_ROUTE_PASS',checks,'checks; 3 relocated bases; original threat traversal and list cleanup; route producer/engine services stubbed, no played match')
