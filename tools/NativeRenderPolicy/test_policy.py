"""Execute the emitted x86 policy: quota regression, no preload, callback/ABI."""
import argparse, importlib.util, json, re, struct
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('cache_rig',REPO/'game/resource-cache/test_native.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);a=parser.parse_args()
meta=json.loads((a.native/'payload.json').read_text());payload=(a.native/'payload.bin').read_bytes();passed=[]
overlay=(REPO/'game/terrain-texture-pool/data/data/UVars_k2.tgi').read_text()
def setting(name):
 values=re.findall(r'\bint\s+'+name+r'\s*=\s*(\d+)',overlay);assert len(values)==1;return int(values[0])
model_ram=setting('ResourceCacheNiAVObjRAMWeight');model_vram=setting('ResourceCacheNiAVObjVRAMWeight')
assert model_ram==model_vram==60
class Rig(t.Rig):
 def __init__(self,*args,**kw):
  self.animationLocks=0;self.callbacks=0
  super().__init__(*args,**kw)
 def hook(self,u,at,n,data):
  if at==self.image+0x1b546d:
   self.animationLocks+=1;self.ret()
  elif at==t.STOP+0x500:
   assert self.get(self.state+92)==1
   self.callbacks+=1
  else:super().hook(u,at,n,data)

# Reproduce the old quota bug by executing the original retail instructions.
r=Rig(meta,payload);m,c=r.caches();r.call(t.IMAGE+0x1b5c02,(c[2],1,0),m)
assert len({r.get(p+8) for p in c})==1 and all(r.get(p+0x18)==0 for p in c)
passed.append('retail quota bug reproduced')
for image,cave in [(t.IMAGE,t.CAVE),(0x1200000,0x41000000),(0x3100000,0x61000000)]:
 # Actual quota code with the native settings from the data overlay. The
 # aggregate other classes keep positive quotas; total budgets do not grow.
 r=Rig(meta,payload,image,cave);m,c=r.caches();ram_total=1596392192;vram_total=990834176
 r.put(m+0x30,0,ram_total,200,0,vram_total,180)
 for p,rw,vw in [(c[0],30,30),(c[1],100,100),(c[2],70,50)]:r.put(p+0x14,rw);r.put(p+0x24,vw)
 r.put(image+0x5fc910,101);r.put(image+0x5fc924,102)
 r.call(cave+meta['hooks'][1]['entry'],(c[0],30,30),m)
 old_ram=r.get(c[0]+8);old_vram=r.get(c[0]+0x18)
 r.call(cave+meta['hooks'][1]['entry'],(c[0],model_ram,model_vram),m)
 assert r.get(c[0]+8)==ram_total*60//230>old_ram
 assert r.get(c[0]+0x18)==vram_total*60//210>old_vram
 assert r.get(m+0x34)==ram_total and r.get(m+0x40)==vram_total
 assert all(r.get(p+8)>0 and r.get(p+0x18)>0 for p in c)
 assert sum(r.get(p+8) for p in c)<=ram_total and sum(r.get(p+0x18) for p in c)<=vram_total
 assert r.get(c[1]+0x14)==r.get(c[1]+0x24)==100 and not r.calls
 passed.append('data-defined model/effect quotas grow within original totals at '+hex(image))
 for ram,vram in [(1,0),(40,50),(0,0),(0xffffffff//1000,0xffffffff//2000)]:
  r=Rig(meta,payload,image,cave);m,c=r.caches();r.call(cave+meta['hooks'][1]['entry'],(c[2],ram,vram),m)
  for p in c:
   assert r.get(p+8)==510000000*r.get(p+0x14)//(50+ram)
   assert r.get(p+0x18)==180000000*r.get(p+0x24)//(50+vram)
  assert sum(r.get(p+8) for p in c)<=510000000 and sum(r.get(p+0x18) for p in c)<=180000000
  assert r.u.reg_read(t.UC_X86_REG_XMM0)==0x99887766554433221122334455667788
  assert r.u.reg_read(t.UC_X86_REG_ESP)==t.STACK+0x80000+16
  passed.append('quota shares, ABI and ASLR '+str((image,ram,vram)))
 for zero in [False,True]:
  r=Rig(meta,payload,image,cave);m,c=r.caches();p=t.HEAP+0x1500;r.put(p+4,199)
  if zero:
   r.put(m+0x30,0,0,0,0,0,0)
   for q in c:r.put(q+0x14,0);r.put(q+0x24,0)
  r.call(cave+meta['hooks'][1]['entry'],(p,0 if zero else 10,0),m)
  assert r.get(m+0x38)==(0 if zero else 61)
  assert r.get(p+8)==(0 if zero else 510000000*10//61)
  passed.append('pending cache class, zero='+str(zero)+' at '+hex(image))
 r=Rig(meta,payload,image,cave);m,c=r.caches();r.put(image+0x5fc924,102)
 r.call(cave+meta['hooks'][1]['entry'],(c[1],1,0),m)
 assert r.get(c[1]+0x14)==100 and r.get(c[1]+0x24)==100
 passed.append('existing sequence weights remain 100/100 at '+hex(image))
 # Even the former enable=3 cannot load resources. No manager table or resource
 # list is mapped beyond the ordinary quota map: any old traversal would fail.
 for enabled in [0,1,3]:
  for phase in [2,4,6]:
   for low in [False,True]:
    r=Rig(meta,payload,image,cave);r.low=low;m,c=r.caches();manager=m-0x9c
    uv=t.HEAP+0x60000;cache=uv+0x400
    r.put(image+0x5f3fd4,manager);r.put(image+0x5f9480,uv);r.put(uv+0x100,cache);r.put(cache,50)
    r.put(image+0x5f92f4,phase);r.put(image+0x5f3fb8,t.HEAP+0x50000);r.put(r.state+12,enabled)
    # Callback calls rc_tick recursively. Only the outer invocation may run.
    callback=t.STOP+0x500;tick=cave+meta['exports']['rc_tick']
    b=b'\x68'+struct.pack('<I',r.state)+b'\xe8'+struct.pack('<i',tick-(callback+10))+b'\x83\xc4\x04\xc3'
    r.u.mem_write(callback,b);r.put(r.state+104,callback)
    for _ in range(5):r.call(tick,(r.state,))
    assert not r.calls and r.callbacks==5 and r.get(r.state+92)==0
    assert all(r.get(r.state+o)==0 for o in range(28,84,4)), 'preparation counters must remain zero'
    assert r.get(r.state+20)==(5 if enabled else 0)
    assert r.animationLocks==(1 if enabled and not low else 0)
    assert r.get(cache)==(80 if enabled and not low else 50)
    assert r.get(r.state+108)==(1 if enabled and not low else 0)
    passed.append('no preload, headroom, callback/reentry '+str((image,enabled,phase,low)))
result=dict(passed=True,cases=len(passed),checks=passed,liveGameTested=False)
(a.native/'policy-tests.json').write_text(json.dumps(result,indent=2))
print('NATIVE_POLICY_PASS',len(passed),'cases; original bug, three ASLR bases, no resource calls, unchanged animation policy, callback/reentry')
