"""Execute relocated production x86 generation, native climate gate and light tick."""
import re,struct,collections
from context import *
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *

checks=0
def check(ok,label):
 global checks
 assert ok,label
 checks+=1

def one(image,cave):
 native=OUT/'world-native-r2/native';meta=read(native/'payload.json');u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,0x700000);u.mem_map(cave,meta['size']+meta['stateBytes']);heap=0x30000000;u.mem_map(heap,0x80000);stop=heap+0x7e000;stack=heap+0x7f000
 def w(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
 def r(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def f(p,v):u.mem_write(p,struct.pack('<f',v))
 def text(p,s):u.mem_write(p,(s+chr(0)).encode('utf-16le'))
 def string(p):
  result=''
  for i in range(160):
   c=struct.unpack('<H',u.mem_read(p+i*2,2))[0]
   if not c:return result
   result+=chr(c)
  raise AssertionError('unterminated fixture')
 b=bytearray((native/'payload.bin').read_bytes())
 for at,im,cv in meta['fixups']:struct.pack_into('<I',b,at,(struct.unpack_from('<I',b,at)[0]+im*(image-0x460000)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_write(cave,bytes(b));state=cave+meta['state'];w(state,image);w(state+4,cave+meta['adapter'])
 world=heap+0x1000;mp=heap+0x2000;creator=heap+0x3000;gen=heap+0x4000;rmc=heap+0x5000;rules=heap+0x6000;grid=heap+0x10000;db=heap+0x7000
 w(image+0x5f3fb8,world);w(world+0x30,mp);w(gen,creator);w(creator+0x50,rmc);w(rmc+8,rmc+64);text(rmc+64,'paws_mixed_biomes');w(world+0x18,rules);w(world+0x1c,3);w(mp+0x1c,32);w(mp+0x20,32);w(mp+0x28,grid);w(image+0x5f3fb4,db)
 # Actual native WorldRules records, not replacement phase/selection routines.
 for i,(name,kind,value)in enumerate([('Sun',3,'paws_dynamic_sun'),('PawsDayPhase',1,''),('PawsBiomes',3,'paws_all')]):
  definition=heap+0x8000+i*0x300;enum=definition+0x100;w(rules+i*12,definition);w(definition+8,definition+64);text(definition+64,name);w(definition+0x20,kind);w(definition+0x34,enum);w(definition+0x38,1);w(enum,enum+32);text(enum+32,value)
 variations=re.findall(r'"((?:temperate|arctic|desert)_[a-z]+\d\d)"',(OUT/'world-native-r2/source/biomes.c').read_text());variations=list(dict.fromkeys(variations));manager=heap+0xb000;array=manager+0x100;w(image+0x5f0030,manager);w(manager+0x24,array);w(manager+0x28,len(variations));definitions={}
 for i,name in enumerate(variations):
  p=heap+0xc000+i*0x100;w(array+i*4,p);w(p+8,p+32);text(p+32,name);definitions[name]=p
 for i in range(32*32):w(grid+i*0x30,definitions['temperate_grass01'])
 light=[];nativecalls=collections.Counter()
 profiles={name:heap+0x24000+i*0x100 for i,name in enumerate(['sun_morning','sun_afternoon','sun_dusk','sun_night'])}
 for i,p in enumerate(profiles.values()):
  for j in range(9):f(p+0x18+j*4,i*.2+j*.01)
 def engine(uc,at,n,data):
  rva=at-image;sp=uc.reg_read(UC_X86_REG_ESP);result=0;argc=0;nativecalls[rva]+=1
  if rva==0x256f19:result=1
  elif rva in [0x2517a3,0x20d4b]:pass
  elif rva==0x25185b:argc=1
  elif rva==0x2517f9:
   argc=2;point=r(sp+4);x=r(point);y=r(point+4);w(grid+(y*32+x)*0x30,r(sp+8))
  elif rva==0x2edb9:argc=1;name=string(r(sp+4));check(name in profiles,('native sun profile',name));result=profiles[name]
  elif rva==0x23daac:argc=4;light.append(struct.unpack('<9f',u.mem_read(r(sp+4),36)))
  else:raise AssertionError(('unexpected native engine call',hex(rva)))
  uc.reg_write(UC_X86_REG_EAX,result);uc.reg_write(UC_X86_REG_ESP,sp+4+argc*4);uc.reg_write(UC_X86_REG_EIP,r(sp))
 u.hook_add(UC_HOOK_CODE,engine,begin=image,end=image+0x6fffff)
 def call(name,args):
  u.mem_write(stack,struct.pack('<'+'I'*(len(args)+1),stop,*args));u.reg_write(UC_X86_REG_ESP,stack);u.emu_start(cave+meta['exports'][name],stop,count=10000000);check(u.reg_read(UC_X86_REG_EIP)==stop,'compiled callback returned');check(u.reg_read(UC_X86_REG_ESP)==stack+4,'cdecl callback ABI');return u.reg_read(UC_X86_REG_EAX)
 snapshots=[];masks=set();phases=set()
 for random in [False,True]:
  text(heap+0x8000+2*0x300+0x100+32,'paws_random'if random else'paws_all')
  for seed in range(32 if random else 3):
   w(creator+0x4c,seed);check(call('generate',[state,gen])==1,'actual compiled generator succeeded');check(r(state+52)==0,'all native terrain definitions resolved');cells=bytes(u.mem_read(state+164,1024));ids=set(cells);check(ids<=set(range(3)),'no foreign fourth climate');check(ids==set(range(3))if not random else 1<=len(ids)<=3,'native biome choice');masks.add(sum(1<<i for i in ids));phases.add(r(rules+12+8));check(r(rules+20)<9600,'serialized phase range')
   for k,climate in enumerate(cells):
    pointer=r(grid+k*0x30);expected=('temperate','arctic','desert')[climate];check(string(r(pointer+8)).startswith(expected),'native paint matches spawn partition')
   # Reset native generator output between independent map creations.
   for k in range(1024):w(grid+k*0x30,definitions['temperate_grass01'])
   if not random:snapshots.append(cells)
 check(masks==set(range(1,8)),'all seven native biome subsets exercised');check(len(phases)>25,'random saved start phases vary')
 before=r(rules+20);colors=[]
 for seconds in [0.,.0625,150.,300.,450.,599.9375,600.,1244.3125]:
  f(world+0xe8,seconds);call('world_tick',[state,world]);check(r(rules+20)==before,'lighting never advances serialized seed offset');phase=(int(seconds*16)%9600+before%9600)%9600;segment=phase//2400;t=(phase%2400)/2400;t=t*t*(3-2*t);expected=[segment*.2+j*.01+(((segment+1)%4)*.2-segment*.2)*t for j in range(9)];check(max(abs(a-b)for a,b in zip(light[-1],expected))<2e-7,'native simulation lighting agrees with serialized phase');colors.append(light[-1])
 check(colors[0]==colors[6],'full cycle wraps exactly');call('world_tick',[state,world]);check(light[-1]==colors[-1],'paused simulation does not advance light')
 # Static/native RMC fallback retains native generation and no mixed gate.
 text(rmc+64,'rmc_temperate03');check(call('generate',[state,gen])==1 and r(state+28)==0,'ordinary maps retain native generator');before=len(light);text(heap+0x8000+0x100+32,'sun_afternoon');call('world_tick',[state,world]);check(len(light)==before,'static sun stays native')
 print('PURE_WORLD_NATIVE_BASE_PASS',hex(image),hex(cave),flush=True)
 return snapshots

def main():
 reference=None
 for image,cave in [(0x460000,0x10000000),(0x620000,0x12000000),(0xd00000,0x14000000)]:
  actual=one(image,cave)
  if reference is None:reference=actual
  else:check(actual==reference,'identical map partitions across ASLR')
 write(OUT/'world-native-r2/native-tests.json',dict(passed=True,checks=checks,bases=3,engine='explicit native generation/paint/light stubs; compiled world rules and geometry execute',allSevenNativeBiomeSubsets=True));print('PURE_WORLD_NATIVE_PASS',checks)
if __name__=='__main__':main()
