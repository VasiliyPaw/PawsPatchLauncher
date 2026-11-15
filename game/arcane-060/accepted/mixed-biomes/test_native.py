"""Execute compiled x86 payload, relocation, region and spawn boundaries."""
from pathlib import Path
import json,sys,struct,re,collections,time
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];OUT=WS/'outputs/mixed-biomes-r2-20261106';LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
sys.path[:0]=[str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
meta=json.loads((OUT/'native/payload.json').read_text());original=(OUT/'native/payload.bin').read_bytes();checks=0
raw=(LEG/'k2_runtime_1372_20260904.bin').read_bytes()
def check(v,label):
 global checks
 assert v,label;checks+=1
def one(image,cave):
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,0x700000);u.mem_map(cave,meta['size']+meta['stateBytes']);u.mem_map(0x20000000,0x10000);u.mem_map(0x30000000,0x10000);u.mem_map(0x31000000,0x1000);u.mem_write(0x31000000,b'\xcc')
 b=bytearray(original)
 for at,im,cv in meta['fixups']:struct.pack_into('<I',b,at,(struct.unpack_from('<I',b,at)[0]+im*(image-0x460000)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_write(cave,bytes(b))
 def w(p,v):u.mem_write(p,struct.pack('<I',v))
 def r(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 state=cave+meta['state'];w(state,image)
 def call(at,args,eax=0):
  sp=0x3000f000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x31000000,*args));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_EAX,eax);u.reg_write(UC_X86_REG_EFLAGS,0x246);u.reg_write(UC_X86_REG_ECX,0xdeadbeef)
  try:u.emu_start(at,0x31000000,count=100000000)
  except Exception:
   print('EMU FAILURE',hex(at),hex(u.reg_read(UC_X86_REG_EIP)),hex(u.reg_read(UC_X86_REG_EAX)),hex(u.reg_read(UC_X86_REG_ECX)),bytes(u.mem_read(at,80)).hex());raise
  check(u.reg_read(UC_X86_REG_EIP)==0x31000000,'function returned');return u.reg_read(UC_X86_REG_EAX)
 world=0x20000000;mp=world+0x1000;svar=world+0x2000;value=world+0x3000
 w(image+0x5f3fb8,world);w(world+0x30,mp);w(svar+0x1b4,value)
 cap=cave+meta['capCore'];cap_site=cave+next(h['entry'] for h in meta['hooks'] if h['site']==0x235c4c)
 resource_id=world+0x3800;resource_test=world+0x3900;w(resource_test+8,resource_id);u.mem_write(resource_id,('unit_limit_provided\0').encode('utf-16le'));u.reg_write(UC_X86_REG_EDX,resource_test)
 for width,height in ((384,384),(1152,1152),(1198,1198),(1200,1200),(1280,1280),(2048,2048),(2048,1152),(1152,2048),(600,600)):
  for native in (20,17,25,30):
   w(mp+0x1c,width//2);w(mp+0x20,height//2);u.mem_write(mp+12,struct.pack('<ff',width,height));w(value,native);pointer=call(cap,[],svar);expected=25 if min(width,height)>=1200 and native==20 else native
   check(r(pointer)==expected,('cap',width,height,native));check(u.reg_read(UC_X86_REG_ECX)==0xdeadbeef,'ECX preserved');check(u.reg_read(UC_X86_REG_EFLAGS)==0x246,'flags preserved');check(r(value)==native,'stored setting untouched')
 # Execute the complete original native resource-production clamp with the
 # actual call-site replacement. Notifications are the only mocked callee.
 stock=bytearray(raw[0x235c12:0x235c90])
 for at,rva in ((0x25,0x5f3fb4),(0x36,0x5f95f0)):struct.pack_into('<I',stock,at,image+rva)
 u.mem_write(image+0x235c12,bytes(stock));u.mem_write(image+0x239377,b'\xc2\x04\x00')
 u.mem_write(image+0x235c4c,b'\xe8'+struct.pack('<i',cap_site-(image+0x235c4c+5))+b'\x90')
 db=world+0x4000;resource=db+0x100;resource_array=db+0x200;kingdom=world+0x5000;production=kingdom+0x400;effective=production+0x100
 resource_index=7
 w(image+0x5f3fb4,db);w(db+0x34,resource_array);w(resource_array+4*resource_index,resource);w(resource+8,resource_id);w(image+0x5f95f0,svar);w(svar+0x1b4,value);w(value,20);w(kingdom+0x1b4,production);w(kingdom+0x1a8,effective)
 for side in (384,1152,1200,1280,2048,384):
  w(mp+0x1c,side//2);w(mp+0x20,side//2);u.mem_write(mp+12,struct.pack('<ff',side,side))
  for limited in (0,1):
   u.mem_write(resource+0x2c,bytes([limited]))
   for amount in (0.,19.,20.,21.,25.,30.):
    w(production+4*resource_index,0);u.reg_write(UC_X86_REG_ECX,kingdom);sp=0x3000f000;bits=struct.unpack('<I',struct.pack('<f',amount))[0];u.mem_write(sp,struct.pack('<III',0x31000000,resource_index,bits));u.reg_write(UC_X86_REG_ESP,sp)
    u.emu_start(image+0x235c12,0x31000000,count=1000)
    check(struct.unpack('<f',u.mem_read(effective+4*resource_index,4))[0]==(min(amount,25 if side>=1200 else 20) if limited else amount),('native economy',side,limited,amount))
    check(u.reg_read(UC_X86_REG_ESP)==sp+12,'native resource ABI')
 for name in ('kingdom_points_provided','gold','unit_limit_consumed','unit_limit_provided_extra'):
  u.mem_write(resource_id,(name+'\0').encode('utf-16le'));u.reg_write(UC_X86_REG_EDX,resource_test);w(mp+0x1c,1024);w(mp+0x20,1024);u.mem_write(mp+12,struct.pack('<ff',2048,2048));check(r(call(cap,[],svar))==20,('other resource unchanged',name))
 u.mem_write(resource_id,('unit_limit_provided\0').encode('utf-16le'))
 for width,height in ((float('nan'),2048),(2048,float('inf')),(-1200,2048),(1199.99,2048),(1200.,1200.)):
  u.mem_write(mp+12,struct.pack('<ff',width,height));u.reg_write(UC_X86_REG_EDX,resource_test);check(r(call(cap,[],svar))==(25 if width==height==1200 else 20),'finite physical map dimensions')
 geom=state+72;region=cave+meta['exports']['at_layout'];allowed=cave+meta['exports']['allowed'];masks=json.loads((OUT/'spawn-index.json').read_text())
 grid=[];seed=1372;size=32;call(cave+meta['exports']['prepare_regions'],[state,size,size,seed]);cellbase=geom+92
 for y in range(size):grid.append(list(u.mem_read(cellbase+y*size,size)))
 counts=collections.Counter(b for row in grid for b in row)
 check(set(counts)==set(range(4)),'four regions')
 for biome in range(4):
  cells={(x,y) for y in range(size) for x in range(size) if grid[y][x]==biome};seen=set();queue=[next(iter(cells))]
  while queue:
   p=queue.pop()
   if p in seen or p not in cells:continue
   seen.add(p);x,y=p;queue.extend(((x+1,y),(x-1,y),(x,y+1),(x,y-1)))
  check(len(seen)>size*size//20,'large connected area');check(len(cells)>size*size//12,'large biome')
 w(state+12,world);w(state+16,seed);w(state+28,1);w(mp+0x1c,size);w(mp+0x20,size)
 obj=world+0x4000;ident=obj+0x100;point=obj+0x300;w(obj+8,ident)
 samples={b:next((x,y) for y,row in enumerate(grid) for x,v in enumerate(row) if v==b) for b in range(4)}
 for name,mask in masks.items():
  u.mem_write(ident,(name+'\0').encode('utf-16le'))
  for biome,(x,y) in samples.items():
   u.mem_write(point,struct.pack('<ff',x*2+.25,y*2+.25));result=call(allowed,[state,obj,point]);check(result==bool(mask&(1<<biome)),('spawn',name,biome))
 snapshot=bytes(u.mem_read(cellbase,size*size));call(cave+meta['exports']['prepare_regions'],[state,size,size,seed]);check(bytes(u.mem_read(cellbase,size*size))==snapshot,'repeat deterministic')
 # Exercise the actual stdcall wrapper. The native validator may relocate its
 # point across a border; the gate must inspect that final point, not the hint.
 native_calls=[];target=cave+meta['hooks'][1]['entry'];trampoline=cave+meta['hooks'][1]['entry']-0x100
 def validator(uc,at,n,_):
  if at!=trampoline:return
  sp=uc.reg_read(UC_X86_REG_ESP);args=struct.unpack('<7I',uc.mem_read(sp+4,28));native_calls.append(args)
  check(args==(111,obj,333,point,555,666,777),'native args intact')
  x,y=samples[1];uc.mem_write(point,struct.pack('<ff',x*2+.25,y*2+.25));uc.reg_write(UC_X86_REG_EAX,0xabcdef01);uc.reg_write(UC_X86_REG_ESP,sp+32);uc.reg_write(UC_X86_REG_EIP,r(sp))
 handle=u.hook_add(UC_HOOK_CODE,validator)
 u.mem_write(ident,('lair_spider_lair_arctic\0').encode('utf-16le'))
 result=call(target,[111,obj,333,point,555,666,777]);check(result==0xabcdef01,'allowed native result retained');check(len(native_calls)==1,'native called once')
 u.mem_write(ident,('lair_spider_lair_desert\0').encode('utf-16le'))
 result=call(target,[111,obj,333,point,555,666,777]);check(result==0,'post-adjustment biome denied');check(len(native_calls)==2,'native called once per attempt');check(u.reg_read(UC_X86_REG_ESP)==0x3000f020,'stdcall balanced')
 u.hook_del(handle)
 # Same production C code built for host supplies cross-architecture reference
 # masks; execute the real relocated x86 cache builder for varied seeds.
 import hashlib
 references=json.loads((OUT/'geometry-x86-references.json').read_text())
 for test_seed,expected_hash in references.items():
  call(cave+meta['exports']['prepare_regions'],[state,32,32,int(test_seed)])
  check(hashlib.sha256(bytes(u.mem_read(cellbase,1024))).hexdigest()==expected_hash,('x86/host identical partition',test_seed))
 # Native creator settings are a private array: copy common density to the
 # other three climates, scaled by actual areas; unrelated settings unchanged.
 creator=world+0x7000;settings=world+0x7200;names=world+0x7600
 keys=[f'random_{kind}{biome}camps' for kind in ('monsterlair','monsterlargelair','techlair') for biome in ('temperate','arctic','desert','cursed')]+['random_settlements']
 w(creator+0x64,settings);w(creator+0x68,len(keys));w(state+20,100);w(state+24,100)
 for b,area in enumerate((1000,2000,3000,4000)):w(state+56+b*4,area)
 for density in (0.,0.5,2.,4.5):
  for i,key in enumerate(keys):
   ptr=names+i*128;u.mem_write(ptr,(key+'\0').encode('utf-16le'));w(settings+i*8,ptr);u.mem_write(settings+i*8+4,struct.pack('<f',density if i<12 and i%4==0 else 987.))
  call(cave+meta['exports']['shared_groups'],[state,creator])
  for i in range(12):
   actual=struct.unpack('<f',u.mem_read(settings+i*8+4,4))[0];check(abs(actual-density*(i%4+1)/10)<0.000001,('common density',density,i))
  check(struct.unpack('<f',u.mem_read(settings+12*8+4,4))[0]==987.,'unrelated setting retained')
 compare=cave+meta['exports']['natural_compare'];a_ptr=world+0x6000;b_ptr=a_ptr+4;item_a=a_ptr+0x100;item_b=a_ptr+0x200;text_a=a_ptr+0x300;text_b=a_ptr+0x500
 w(a_ptr,item_a);w(b_ptr,item_b);w(item_a+12,text_a);w(item_b+12,text_b)
 for left,right in [('1','2'),('2','10'),('9','10'),('10','11'),('2v2','2v10'),('Custom','2'),('Пользовательский','2'),('2 Free For All','10 Free For All'),('16','16')]:
  for x,y,expected in ((left,right,0 if left==right else -1),(right,left,0 if left==right else 1)):
   u.mem_write(text_a,(x+'\0').encode('utf-16le'));u.mem_write(text_b,(y+'\0').encode('utf-16le'));result=call(compare,[a_ptr,b_ptr]);result=struct.unpack('<i',struct.pack('<I',result))[0];check((result>0)-(result<0)==expected,('numeric comparator',x,y))
 print('RELOCATION_PASS',hex(image),hex(cave),dict(counts),flush=True)
for image,cave in ((0x460000,0x10000000),(0x620000,0x12000000),(0xd00000,0x14000000)):one(image,cave)
# Source definitions are the exact extracted mod used by this fixture.
ids=set()
for p in (WS/'outputs/mixed-biomes-20261106/definitions/Terrain').rglob('*.tgi'):
 ids.update(re.findall(r'(?mi)^\s*IDS\s*=\s*(\w+)',p.read_text(encoding='utf-8')))
variations=re.findall(r'"([a-z_]+\d\d)"',(HERE/'biomes.c').read_text());missing=[n for n in variations if n not in ids]
check(not missing,('missing variations',missing))
report=dict(passed=True,checks=checks,relocationBases=3,spawnDefinitions=len(json.loads((OUT/'spawn-index.json').read_text())),scope='Actual compiled x86 region/gate/cap code; no replacement for full game generation and save/load')
(OUT/'native-tests.json').write_text(json.dumps(report,indent=2));print('NATIVE_PASS',checks)
