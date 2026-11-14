"""Execute the actual experimental budget/ABI/quota code at three ASLR bases."""
import importlib.util,json,struct
from build import REPO,OUT,write,RAM_PERCENT
spec=importlib.util.spec_from_file_location('rig',REPO/'game/resource-cache/test_native.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
meta=json.loads((OUT/'native/payload/payload.json').read_text());payload=(OUT/'native/payload/payload.bin').read_bytes();checks=[]
M=1024**2;G=1024**3
class Rig(t.Rig):
 def __init__(self,*args,**kw):
  self.va=3500*M;self.phys=10*G;self.load=30;self.api=True;self.gpu=200*M;self.refreshes=0;self.callbacks=0
  super().__init__(*args,**kw)
 def hook(self,u,at,n,data):
  sp=u.reg_read(t.UC_X86_REG_ESP)
  if at==t.STOP+0x200:
   if self.api:self.u.mem_write(self.get(sp+4),struct.pack('<II7Q',64,self.load,32*G,self.phys,48*G,20*G,4*G,self.va,0))
   self.ret(int(self.api),args=4)
  elif at==self.image+0x18a946:self.ret(self.gpu)
  elif at==self.image+0x1b546d:self.refreshes+=1;self.ret()
  elif at==t.STOP+0x500:self.callbacks+=1;self.ret()
  else:super().hook(u,at,n,data)
 def budget(self,ram=RAM_PERCENT/100,video=.6,force=0):
  bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
  self.call(self.cave+meta['hooks'][2]['entry'],(bits(ram),bits(video),force),self.manager)
  assert self.u.reg_read(t.UC_X86_REG_ESP)==t.STACK+0x80000+16
  assert self.u.reg_read(t.UC_X86_REG_XMM0)==0x99887766554433221122334455667788
  assert 0<=self.get(self.manager+0x34)<=3*G and 0<=self.get(self.manager+0x40)<=3*G
  return self.get(self.manager+0x34),self.get(self.manager+0x40)
 def setup(self):
  self.manager,c=self.caches();self.put(self.manager+0x30,750*M,1500*M,51,700*M,900*M,90)
  renderer=t.HEAP+0x30000;self.put(self.image+0x5f3f98,renderer);self.put(renderer+0x254,0xffffffff)
  return c

for image,cave in [(t.IMAGE,t.CAVE),(0x1200000,0x41000000),(0x3100000,0x61000000),(0x1200000,0xb1000000)]:
 r=Rig(meta,payload,image,cave);r.setup();ram,vr=r.budget();assert ram>2*G and vr>2*G
 checks.append('real adapter exceeds old 2GiB budgets without signed conversion at '+hex(image))
 for va in [0,128*M,511*M,767*M,768*M,900*M,1024*M,3500*M,4*G]:
  for physical,load in [(10*G,30),(128*M,30),(10*G,95)]:
   r=Rig(meta,payload,image,cave);r.setup();r.va=va;r.phys=physical;r.load=load;ram,vr=r.budget()
   if va<768*M or physical<384*M or load>=90:assert ram<=750*M*.75 and vr<=700*M*.75,(image,va,physical,load,ram,vr,r.get(r.state+132))
   if 768*M<=va<1024*M:assert ram<=1500*M and vr<=900*M
   checks.append('headroom '+str((image,va,physical,load)))
 for frac in [0,.25,.8,1,1.5,-1,float('inf'),float('nan')]:
  r=Rig(meta,payload,image,cave);r.setup();r.budget(frac,frac);checks.append('fraction bounded '+str((image,frac)))
 r=Rig(meta,payload,image,cave);r.setup();r.api=False;r.put(r.manager+0x34,0xffffffff);r.put(r.manager+0x40,0xffffffff)
 assert r.budget()==(0x7fffffff,0x7fffffff);checks.append('API failure disables high budgets '+hex(image))
 r=Rig(meta,payload,image,cave);r.setup();r.put(r.manager+0x30,0xfffffff0);r.put(r.manager+0x3c,0xfffffff0);assert r.budget()==(3*G,3*G)
 checks.append('64-bit intermediate arithmetic cannot wrap '+hex(image))
 r=Rig(meta,payload,image,cave);c=r.setup();r.put(r.manager+0x34,3*G);r.put(r.manager+0x40,3*G)
 r.put(image+0x5fc924,102);r.call(cave+meta['hooks'][1]['entry'],(c[1],1,0),r.manager)
 assert r.get(c[1]+20)==r.get(c[1]+36)==120
 assert all(r.get(p+8)<=1792*M and r.get(p+24)<=1792*M for p in c)
 assert sum(r.get(p+8)for p in c)<=3*G and sum(r.get(p+24)for p in c)<=3*G
 checks.append('120 sequence weights; per-class unsigned quotas bounded '+hex(image))
 # Pressure poll uses the actual compiled VIEW callback, invoking only the
 # native full-refresh entry. High memory has no repeat refreshes.
 for low in [False,True]:
  r=Rig(meta,payload,image,cave);r.setup();r.va=256*M if low else 3500*M
  resource=r.manager-0x9c;r.put(image+0x5f3fd4,resource);r.put(image+0x5f92f4,4);r.put(r.state+108,1);r.put(r.state+104,t.STOP+0x500)
  for _ in range(3):r.clock+=1100;r.call(cave+meta['exports']['rc_tick'],(r.state,))
  assert r.callbacks==3 and r.refreshes==(3 if low else 0) and not r.calls
  checks.append('pressure watchdog '+str((image,low)))
write(OUT/'native-tests.json',dict(passed=True,cases=len(checks),checks=checks,liveGameTested=False));print('EXPANDED_NATIVE_PASS',len(checks))
