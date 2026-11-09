"""Execute product-only animation policy and callback boundaries in x86."""
import argparse,importlib.util,json,struct
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('cache_fixture',REPO/'game/resource-cache/test_native.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
class Rig(f.Rig):
 def __init__(self,*args,**kwargs):
  self.phys=6<<30;self.virtual=2<<30;self.load=30;self.memory_ok=True;self.recalc=0
  super().__init__(*args,**kwargs)
 def hook(self,u,at,n,data):
  if at==f.STOP+0x200:
   p=self.get(u.reg_read(f.UC_X86_REG_ESP)+4)
   u.mem_write(p,struct.pack('<II7Q',64,self.load,8<<30,self.phys,8<<30,6<<30,4<<30,self.virtual,0));self.ret(int(self.memory_ok),args=4)
  elif at==self.image+0x1b546d:self.recalc+=1;self.ret()
  else:super().hook(u,at,n,data)
def main():
 p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);a=p.parse_args()
 meta=json.loads((a.native/'payload.json').read_text());payload=(a.native/'payload.bin').read_bytes();checks=[]
 for image,cave in [(f.IMAGE,f.CAVE),(0x1200000,0x41000000)]:
  r=Rig(meta,payload,image,cave);m,c=r.caches();r.put(image+0x5fc924,102)
  r.call(cave+meta['hooks'][1]['entry'],(c[1],1,0),m)
  assert r.get(c[1]+0x14)==100 and r.get(c[1]+0x24)==100
  assert sum(r.get(q+8) for q in c)<=510000000 and sum(r.get(q+0x18) for q in c)<=180000000
  checks.append('sequence class100/100 with conserved budgets at '+hex(image))
 for values,accepted in [({},True),({'virtual':512<<20,'phys':384<<20},True),({'virtual':(512<<20)-1},False),({'phys':(384<<20)-1},False),({'load':90},False),({'memory_ok':False},False)]:
  r=Rig(meta,payload);m,c=r.caches();r.put(f.IMAGE+0x5f3fd4,m-0x9c)
  uv=f.HEAP+0x60000;value=uv+0x400;r.put(f.IMAGE+0x5f9480,uv);r.put(uv+0x100,value);r.put(value,25)
  for key,v in values.items():setattr(r,key,v)
  callback=f.STOP+0x500;count=f.HEAP+0x68000
  r.u.mem_write(callback,b'\x83\x05'+struct.pack('<I',count)+b'\x01\xc3');r.put(r.state+104,callback)
  for _ in range(3):r.call(f.CAVE+meta['exports']['rc_tick'],(r.state,))
  assert r.recalc==int(accepted) and r.get(value)==(80 if accepted else 25) and r.get(r.state+108)==int(accepted)
  assert r.get(count)==3 and r.get(r.state+92)==0
  r.put(r.state+92,1);r.call(f.CAVE+meta['exports']['rc_tick'],(r.state,));assert r.get(count)==3
  if not accepted:
   r.phys=6<<30;r.virtual=2<<30;r.load=30;r.memory_ok=True;r.put(r.state+92,0)
   r.call(f.CAVE+meta['exports']['rc_tick'],(r.state,));assert r.recalc==1 and r.get(value)==80
  checks.append('memory boundary, finite retry and nonreentrant callback '+str(values))
 (a.native/'product-policy-tests.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2))
 print('PRODUCT_CACHE_POLICY_PASS',len(checks))
if __name__=='__main__':main()
