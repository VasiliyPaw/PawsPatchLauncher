"""Execute compiled x86 candidate callbacks with explicit native command stubs."""
import argparse,sys,struct,json,re
from pathlib import Path
LEGACY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
sys.path[:0]=[str(LEGACY/'pydeps_readable'),str(LEGACY/'lobby_colors_1372/deps_r15')]
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);a=p.parse_args();checks=0
def check(ok,why):
 global checks
 assert ok,why
 checks+=1
class Fixture:
 def __init__(self,image,dll):
  self.u=Uc(UC_ARCH_X86,UC_MODE_32);self.image=image;self.dll=dll;self.heap=0x30000000;self.stack=self.heap+0x7f000;self.stop=self.heap+0x7e000;self.calls={};self.ticks=0;self.ks=Ks(KS_ARCH_X86,KS_MODE_32)
  self.u.mem_map(image,0x700000);self.u.mem_map(self.heap,0x80000)
  pe=pefile.PE(str(a.build/'PawUiScoutQA.dll'));b=bytearray(pe.get_memory_mapped_image());self.u.mem_map(dll,(len(b)+4095)&~4095)
  for block in pe.DIRECTORY_ENTRY_BASERELOC:
   for e in block.entries:
    if e.type==3:struct.pack_into('<I',b,e.rva,(struct.unpack_from('<I',b,e.rva)[0]+dll-pe.OPTIONAL_HEADER.ImageBase)&0xffffffff)
  self.u.mem_write(dll,bytes(b));self.exports={x.name.decode():dll+x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols}
  self.imports={};n=0
  for block in pe.DIRECTORY_ENTRY_IMPORT:
   for x in block.imports:
    addr=self.heap+0x70000+n*16;n+=1;self.w(dll+x.address-pe.OPTIONAL_HEADER.ImageBase,addr);self.imports[addr]=x.name.decode() if x.name else '#'+str(x.ordinal)
  self.u.hook_add(UC_HOOK_CODE,self.hook)
  self.host=self.heap+0x100;self.w(self.host+16,self.heap+0x6f000);self.asm(self.heap+0x6f000,'ret')
  self.world=self.heap+0x1000;self.kingdom=self.heap+0x2000;self.region=self.heap+0x3000;self.info=self.heap+0x4000;self.pl=self.heap+0x5000;self.engine=self.heap+0x6000;self.goal=self.heap+0x7000;self.node=self.heap+0x8000;self.sa=self.heap+0x9000;self.actor=self.heap+0xa000;self.defn=self.heap+0xb000
  self.w(image+0x5f3fb8,self.world);self.f(self.world+0xe8,100);self.w(self.kingdom+0x194,1);self.w(self.region+0x14,2);self.w(self.region+0x10,self.region+0x100);self.w(self.region+0x104,self.info);self.w(self.info,self.region);self.w(self.info+8,0)
  self.w(self.goal+4,self.engine);self.w(self.engine+4,self.pl);self.w(self.pl+8,self.kingdom);self.w(self.goal+0x3c,2);self.w(self.goal+0x44,self.region);self.w(self.goal+0xc,self.node);self.w(self.node,self.sa);self.w(self.sa,self.sa+0x100);self.w(self.sa+0x50,self.sa+0x200);self.w(self.actor+0xe8,self.kingdom);self.w(self.actor+4,self.defn)
  self.asm(image+0x1d42fd,'ret');self.asm(self.sa+0x300,'xor eax,eax;ret');self.asm(self.sa+0x320,'mov eax,1;ret');self.w(self.sa+0x100+0xc,self.sa+0x300);self.w(self.sa+0x100+4,self.sa+0x320)
  self.asm(image+0x1e2321,f'mov eax,{self.actor};ret 4');self.asm(image+0x1e392f,'mov eax,1;ret');self.asm(image+0x1d3e82,'mov eax,[esp+4];ret 8');self.asm(image+0x1f2c03,'ret 4');self.asm(image+0x1f397b,'ret');self.asm(image+0x25e971,'mov eax,4;ret')
  map=self.heap+0xd000;self.w(image+0x5f3fcc,map);self.w(map+0x14,map+0x100);self.w(map+0x18,1);self.w(map+0x100,self.region);self.w(self.region,1);self.f(self.region+0x54,100);self.f(self.region+0x58,200)
  self.entries={i:self.invoke(self.exports['Test_Entry'],[image,self.host,i],cdecl=True) for i in range(18)}
 def w(self,p,v):self.u.mem_write(p,struct.pack('<I',v&0xffffffff))
 def r(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
 def f(self,p,v):self.u.mem_write(p,struct.pack('<f',v))
 def asm(self,p,s):
  b=bytes(self.ks.asm(s,p)[0]);self.u.mem_write(p,b);self.u.ctl_remove_cache(p,p+len(b))
 def hook(self,u,addr,size,data):
  if addr==self.image+0x1f2c03:self.ticks+=1
  if addr in self.imports:
   name=self.imports[addr];sp=u.reg_read(UC_X86_REG_ESP)
   if name=='memset':
    dst,val,n=(self.r(sp+4+i*4) for i in range(3));u.mem_write(dst,bytes([val&255])*n);u.reg_write(UC_X86_REG_EAX,dst)
   else:raise AssertionError('unexpected import '+name)
   u.reg_write(UC_X86_REG_ESP,sp+4);u.reg_write(UC_X86_REG_EIP,self.r(sp))
 def invoke(self,at,args=[],ecx=0,cdecl=False):
  sp=self.stack;self.u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),self.stop,*args));self.u.reg_write(UC_X86_REG_ESP,sp);self.u.reg_write(UC_X86_REG_ECX,ecx);self.u.reg_write(UC_X86_REG_EDX,0);self.u.emu_start(at,self.stop,count=100000)
  check(self.u.reg_read(UC_X86_REG_ESP)==sp+4+(0 if cdecl else len(args)*4),('ABI stack',hex(at),self.u.reg_read(UC_X86_REG_ESP)-sp,args));return self.u.reg_read(UC_X86_REG_EAX)
 def allowed(self):return self.invoke(self.entries[1],[self.kingdom,self.region],cdecl=True)
 def orders(self):self.invoke(self.entries[2],[0],ecx=self.goal)
for image,dll in [(0x460000,0x10000000),(0xb30000,0x14000000),(0x12000000,0x20000000)]:
 f=Fixture(image,dll);check(f.allowed()==1,'unexplored region eligible');f.w(f.info+8,1);check(f.allowed()==0,'even partly explored region rejected');f.w(f.info+8,0)
 f.orders();check(f.ticks==1,'one native command queued');f.orders();check(f.ticks==1,'repeat source blocked');f.f(f.world+0xe8,159.9375);f.orders();check(f.ticks==1,'60 seconds not elapsed');f.f(f.world+0xe8,160);f.orders();check(f.ticks==1,'recent target stays blocked after global cooldown');f.f(f.world+0xe8,700);f.orders();check(f.ticks==2,'target may be retried after ten game minutes')
 f=Fixture(image,dll);f.w(f.info+8,10);f.orders();check(f.ticks==0,'no native command for grey fog');f.w(f.info+8,0);f.asm(image+0x1e392f,'xor eax,eax;ret');f.orders();check(f.ticks==0,'busy source retains native gate');f.asm(image+0x1e392f,'mov eax,1;ret');f.w(f.actor+0xe8,0);f.orders();check(f.ticks==0,'wrong owner rejected');f.w(f.actor+0xe8,f.kingdom)
 for race in ['human','gauri','drauga','haroun','undead','shadow']:
  for suffix in ['fort','keep','keep_1']:
   ptr=f.heap+0xc000;f.u.mem_write(ptr,(race+'_'+suffix+'\0').encode('utf-16le'));f.w(f.defn+8,ptr);check(f.invoke(f.entries[3],[f.actor],cdecl=True)==3,('fort statistics',race,suffix))
 f.u.mem_write(f.heap+0xc000,'shadow_center_city\0'.encode('utf-16le'));check(f.invoke(f.entries[3],[f.actor],cdecl=True)==4,'unrelated classification unchanged')
 # Actual compiled minimap callbacks. Only the final native mapper/draw are stubbed.
 state=f.heap+0x11000;widget=f.heap+0x12000;terrain=f.heap+0x13000;out=f.heap+0x14000;vertices=f.heap+0x15000;data=f.heap+0x16000;captured=f.heap+0x17000
 f.w(image+0x5f92f4,4);f.w(image+0x5f92b4+16,state);f.w(state,image+0x48d0dc);f.w(f.world+0x30,terrain);f.f(terrain+12,1280);f.f(terrain+16,1280)
 f.asm(image+0x2a42aa,'mov eax,[esp+4];mov dword ptr [eax],0x44200000;mov dword ptr [eax+4],0x44200000;ret 12') # native central click -> 640,640
 f.asm(image+0x2a495a,f'mov eax,[esp+8];mov [{captured}],eax;mov eax,[esp+12];mov [{captured+4}],eax;mov eax,[esp+4];ret 12')
 f.asm(image+0x17844b,'ret 8');f.w(vertices,data)
 for scale in [1+i*.1 for i in range(31)]:
  x,y=.4,.6;f.invoke(f.exports['Test_View'],[widget,*[struct.unpack('<I',struct.pack('<f',v))[0] for v in [scale,x,y]]],cdecl=True)
  f.invoke(f.entries[4],[out,200,600],ecx=widget);actual=struct.unpack('<2f',f.u.mem_read(out,8));check(abs(actual[0]-(640 if scale==1 else 512))<.001 and abs(actual[1]-(640 if scale==1 else 768))<.001,'inverse click maps cropped view center to camera center')
  f.invoke(f.entries[5],[out,struct.unpack('<I',struct.pack('<f',x))[0],struct.unpack('<I',struct.pack('<f',y))[0]],ecx=out);coords=struct.unpack('<2f',f.u.mem_read(captured,8));check(all(abs(v-w)<.00001 for v,w in zip(coords,([x,y] if scale==1 else [.5,.5]))),'camera rectangle uses matching forward map')
  raw=[]
  for uu,vv in [(0,0),(0,1),(1,1),(1,0)]:raw.extend([0,0,0,0,0,uu,vv,0])
  f.u.mem_write(data,struct.pack('<32f',*raw));f.invoke(f.entries[6],[vertices,0],ecx=out);actual=struct.unpack('<32f',f.u.mem_read(data,128));
  for j,(uu,vv) in enumerate([(0,0),(0,1),(1,1),(1,0)]):
   expected=(uu,vv) if scale==1 else ((uu-.5)/scale+x,(vv-.5)/scale+y);check(abs(actual[j*8+5]-expected[0])<.00001 and abs(actual[j*8+6]-expected[1])<.00001,'terrain/fog/marker texture crop matches forward and inverse maps')
 # Continuous camera motion updates the native cached quad, preserving its owner.
 # This catches the old VE dirty-bit path which deleted the image every frame.
 ve=f.heap+0x18000;holder=f.heap+0x19000;ui=f.heap+0x1a000;renderer=out
 f.w(image+0x5f3fbc,ui);f.w(widget+0x74,ve);f.w(ve+0xa4,holder);f.w(holder,renderer);f.w(renderer+0x5c,data);f.w(renderer+0x60,4);f.w(ve+0x88,0x404);f.asm(image+0x2a45de,'ret')
 f.invoke(f.entries[7],ecx=widget) # First world observation resets transient view state.
 raw=[]
 for uu,vv in [(0,1),(0,0),(1,1),(1,0)]:raw.extend([11,22,33,44,55,uu*.75,vv*.875,66])
 f.u.mem_write(data,struct.pack('<32f',*raw));f.invoke(f.exports['Test_View'],[widget,0x40000000,0x3f000000,0x3f000000],cdecl=True);f.invoke(f.entries[6],[vertices,0],ecx=renderer)
 for frame in range(60):
  x=.3+frame*.006;y=.4+frame*.003
  for off in [0x144,0x150,0x15c,0x168]:f.f(ui+off,x*1280);f.f(ui+off+4,y*1280)
  f.u.mem_write(renderer+0x85,b'\0');f.invoke(f.entries[7],ecx=widget)
  actual=struct.unpack('<32f',f.u.mem_read(data,128))
  check(f.r(holder)==renderer and f.r(ve+0x88)==0x404,'moving camera never deletes or invalidates the cached image')
  check(all(abs(actual[i*8+5]-(((uu-.5)/2+x)*.75))<1e-6 and abs(actual[i*8+6]-(((vv-.5)/2+y)*.875))<1e-6 for i,(uu,vv) in enumerate([(0,1),(0,0),(1,1),(1,0)])),'cached minimap follows continuous camera motion with padded texture')
  check(all(actual[i*8+j]==raw[i*8+j] for i in range(4) for j in [0,1,2,3,4,7]),'camera update preserves native quad geometry and colors')
  check(f.u.mem_read(renderer+0x85,1)==b'\1','changed quad requests native geometry upload')
 f.u.mem_write(renderer+0x85,b'\0');f.invoke(f.entries[7],ecx=widget);check(f.u.mem_read(renderer+0x85,1)==b'\0','stationary camera does not repeatedly dirty the image')
 f.w(holder,0);f.invoke(f.entries[10],ecx=ve);check(f.r(holder)==0,'missing native render cache is left for native creation')
 f=Fixture(image,dll)
 for delta,expected in [(120,1.1),(120,1.2),(60,1.2),(60,1.3),(960,2.1),(2400,4.),(120,4.),(-120,3.9),(-4800,1.),(-120,1.),(360,1.3),(0,1.3)]:
  f.invoke(f.entries[9],ecx=delta&0xffffffff);actual=struct.unpack('<f',f.u.mem_read(f.entries[11],4))[0];check(abs(actual-expected)<1e-6,'wheel uses 0.1 steps, accumulates partial detents and clamps at 1/4')
 f=Fixture(image,dll);owned=f.heap+0x18000;body=f.heap+0x19000;map=f.heap+0x1a000
 f.w(f.pl+0x4c,owned);f.w(owned,1234);f.w(f.actor,image+0x4e5c58);f.w(f.actor+0x14,1234);f.w(f.actor+0x60,body);f.f(body+0x10,100);f.w(f.defn+0x3fc,f.defn+0x500);f.w(f.defn+0x400,8);f.w(image+0x4e5c58+0x34,image+0x2700);f.asm(image+0x2700,'mov eax,1;ret 4');f.asm(image+0x21117,f'mov eax,{f.actor};ret 4');f.asm(image+0x1d4094,'ret');f.w(image+0x5f3fcc,map);f.w(map+0x14,map+0x100);f.w(map+0x18,1);f.w(map+0x100,f.region);f.f(f.region+0x54,100);f.f(f.region+0x58,200);f.w(f.goal+0x44,0)
 f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==1,'upgraded city works with empty synthetic actor pool');check(f.r(f.goal+0x44)==0,'temporary native constructor target restored');f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==1,'city planner shares global cooldown')
 f.f(f.world+0xe8,190);f.w(f.info+8,1);f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==1,'city planner never queues grey fog');f.w(f.info+8,0);f.f(f.world+0xe8,195);f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==1,'unsuccessful city scan throttled for 10 seconds');f.f(f.world+0xe8,200);f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==1,'city planner does not reuse its only recent target');f.f(f.world+0xe8,700);f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==2,'city target expiry is measured in simulation time')
 f.f(f.world+0xe8,300);f.asm(image+0x2700,'xor eax,eax;ret 4');f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==2,'native command support cannot be bypassed');f.asm(image+0x2700,'mov eax,1;ret 4');f.f(body+0x10,0);f.f(f.world+0xe8,310);f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==2,'dead city rejected');f.f(body+0x10,float('nan'));f.f(f.world+0xe8,320);f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==2,'invalid city health rejected')
 enclosing=f.heap+0x1b000;component=f.heap+0x1c000;f.w(enclosing,image+0x4e5c58);f.w(enclosing+0xe8,f.kingdom);f.w(enclosing+0x98,component);f.w(component+0x14,f.actor);f.asm(image+0x21117,f'mov eax,{enclosing};ret 4');f.f(body+0x10,100);f.f(f.world+0xe8,330);f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==3,'owned settlement resolves its upgraded city center');f.w(f.actor+0xe8,0);f.f(f.world+0xe8,430);f.invoke(f.entries[8],ecx=f.goal);check(f.ticks==3,'captured or mismatched center rejected')
# Exercise the exact generated scoring dispatcher, including its FXSAVE path.
# A non-air score must tail-call native code with untouched arguments and flags.
header=(a.build/'dispatch.h').read_text()
for image,dll in [(0x460000,0x10000000),(0xb30000,0x14000000),(0x12000000,0x20000000)]:
 f=Fixture(image,dll);addresses={name:f.heap+0x30000+i*4096 for i,name in enumerate(['orders_dispatch','update_dispatch','filter_dispatch','filter_original'])}
 for name,at in addresses.items():
  code=re.search(r'const unsigned char '+name+r'_code\[\]=\{([^}]+)\}',header).group(1);f.u.mem_write(at,bytes(int(x,16) for x in code.split(',')))
 targets={'(U)air_orders':f.entries[2],'(U)air_update':f.entries[8],'(U)allowed':f.entries[1],'(U)filter_original':addresses['filter_original']}
 for name,offset,expression in re.findall(r'\*\(U\*\)\((\w+)\+(\d+)\)=([^;]+);',header):
  if name not in addresses:continue
  expression=expression.replace('(U)('+name+'+'+str(int(offset)+4)+')',str(addresses[name]+int(offset)+4))
  for token,value in targets.items():expression=expression.replace(token,str(value))
  expression=expression.replace('base',str(image));assert re.fullmatch(r'[0-9a-fx+\-]+',expression),expression
  f.w(addresses[name]+int(offset),eval(expression,{'__builtins__':{}}))
 capture=f.heap+0x35000
 f.asm(image+0x5ceeb,f'mov dword ptr [{capture}],1; fld1; ret 36')
 for mode,explored,expected in [(0,0,1),(1,0,1),(3,0,1),(2,0,1),(2,1,0)]:
  f.w(capture,0);f.w(f.info+8,explored);f.u.reg_write(UC_X86_REG_EFLAGS,0x246);f.u.reg_write(UC_X86_REG_EBX,0x11223344);f.u.reg_write(UC_X86_REG_ESI,0x55667788);f.u.reg_write(UC_X86_REG_EDI,0x12345678);f.u.reg_write(UC_X86_REG_XMM0,0x112233445566778899aabbccddeeff00)
  f.asm(f.heap+0x36000,'fninit; fld1; ret');f.invoke(f.heap+0x36000)
  f.invoke(addresses['filter_dispatch'],[0,f.kingdom,f.region,0,0,0,0,mode,0],ecx=f.pl)
  check(f.r(capture)==expected,'generated score filter only rejects air goals in explored regions')
  check(f.u.reg_read(UC_X86_REG_EFLAGS)&0x8d5==0x246&0x8d5,'dispatcher preserves caller arithmetic flags')
  check(all(f.u.reg_read(reg)==value for reg,value in [(UC_X86_REG_EBX,0x11223344),(UC_X86_REG_ESI,0x55667788),(UC_X86_REG_EDI,0x12345678)]),'dispatcher preserves callee-saved registers')
  check(f.u.reg_read(UC_X86_REG_XMM0)==0x112233445566778899aabbccddeeff00,'air filter preserves SSE state')
  f.asm(f.heap+0x36000,f'fstp dword ptr [{capture+4}];fstp dword ptr [{capture+8}];ret');f.invoke(f.heap+0x36000)
  check(struct.unpack('<2f',f.u.mem_read(capture+4,8))==(float(expected),1.),'score result and pre-existing x87 stack are intact')
for image,dll in [(0x460000,0x10000000),(0xb30000,0x14000000),(0x12000000,0x20000000)]:
 f=Fixture(image,dll);map=f.r(image+0x5f3fcc);remote=f.heap+0x21000;explored=f.heap+0x22000
 for region,x,y,seen,rid in [(remote,800,800,0,10),(explored,1200,1200,1,11)]:
  f.w(region,rid);f.w(region+0x14,2);f.w(region+0x10,region+0x100);f.w(region+0x104,region+0x200);f.w(region+0x200,region);f.w(region+0x208,seen);f.f(region+0x54,x);f.f(region+0x58,y)
 f.w(map+0x104,remote);f.w(map+0x108,explored);f.w(map+0x18,3)
 select=lambda:f.invoke(f.entries[12],[f.kingdom,f.actor],cdecl=True)
 check(select()==remote,'remote fully black region beats a near fog hole and an explored farther region')
 f.w(explored+0x208,0);check(select() in (remote,explored),'selection stays within distant unexplored band')
 f.f(explored+0x54,800);f.f(explored+0x58,800);chosen=select();check(select()==chosen,'same simulation state gives repeatable random choice')
 f.w(map+0x18,1);f.f(f.region+0x54,10);f.f(f.region+0x58,10);check(select()==0,'short useless reconnaissance is skipped')
 terrain=f.heap+0x23000;f.w(f.world+0x30,terrain);f.f(terrain+12,1280);f.f(terrain+16,1280);f.f(f.region+0x54,255);f.f(f.region+0x58,0);check(select()==0,'minimum useful distance scales with map size');f.f(f.region+0x54,256);check(select()==f.region,'minimum useful distance boundary is accepted')
 f=Fixture(image,dll);table=f.heap+0x21000;sun=f.heap+0x22000;phase=f.heap+0x23000;enum=f.heap+0x24000;names=f.heap+0x25000
 f.w(f.world+0x18,table);f.w(f.world+0x1c,2);f.w(table,sun);f.w(table+12,phase);f.w(sun+8,names);f.u.mem_write(names,'Sun\0'.encode('utf-16le'));f.w(phase+8,names+64);f.u.mem_write(names+64,'PawsDayPhase\0'.encode('utf-16le'));f.w(sun+0x20,3);f.w(sun+0x34,enum);f.w(sun+0x38,6);f.w(phase+0x20,1)
 for i,name in enumerate(['paws_dynamic_sun','sun_default','sun_morning','sun_dusk','sun_night','sun_random']):f.w(enum+i*8,names+128+i*80);f.u.mem_write(names+128+i*80,(name+'\0').encode('utf-16le'))
 read_minutes=lambda:f.invoke(f.entries[13],[f.world],cdecl=True)
 for offset in [0,1234,3934,9599,0xffffffff]:
  f.w(table+20,offset)
  for seconds in [0,.0625,149.9375,150,300,450,599.9375,600,1244.3125,10000000]:
   f.f(f.world+0xe8,seconds);expected=((int(seconds*16)%9600+offset%9600)%9600*1440//9600+360)%1440
   check(read_minutes()==expected,'clock matches the exact serialized lighting phase across anchors, offsets and cycle wrap')
  before=read_minutes();check(read_minutes()==before,'paused simulation time leaves the clock unchanged')
 for index,expected in [(1,720),(2,360),(3,1080),(4,0)]:f.w(table+8,index);check(read_minutes()==expected,'static sunlight shows its fixed corresponding time')
 f.w(table+8,6);check(read_minutes()==0xffffffff,'invalid sun enum does not invent a clock time')
 f.w(table+8,0);f.f(f.world+0xe8,float('nan'));check(read_minutes()==0xffffffff,'invalid simulation time is rejected');f.w(f.world+0x1c,257);check(read_minutes()==0xffffffff,'malformed rule table is rejected')
 f.w(f.world+0x1c,2);f.w(table+8,5);profiles=f.heap+0x27000;db=f.heap+0x28000;f.w(image+0x5f3fb4,db)
 f.asm(image+0x2edb9,f'mov edx,[esp+4];cmp word ptr [edx+8],109;je morning;cmp word ptr [edx+8],110;je night;cmp word ptr [edx+10],101;je day;mov eax,{profiles+0x200};ret 4;morning:mov eax,{profiles};ret 4;night:mov eax,{profiles+0x300};ret 4;day:mov eax,{profiles+0x100};ret 4')
 for index,expected in enumerate([360,720,1080,0]):
  for j in range(9):f.f(profiles+index*0x100+0x18+j*4,index*.2+j*.01);f.f(f.world+0x84+j*4,index*.2+j*.01)
  check(read_minutes()==expected,'random static Sun recovers actual selected lighting profile instead of hiding clock');f.f(f.world+0xe8,10000);check(read_minutes()==expected,'static random clock does not invent a moving cycle')
 for j in range(9):f.f(f.world+0x84+j*4,float('nan'))
 check(read_minutes()==0xffffffff,'invalid lighting has no fabricated time')
reference=None
for image,dll in [(0x460000,0x10000000),(0xb30000,0x14000000),(0x12000000,0x20000000)]:
 f=Fixture(image,dll);map=f.r(image+0x5f3fcc);terrain=f.heap+0x21000;f.w(f.world+0x30,terrain);f.f(terrain+12,1280);f.f(terrain+16,1280);f.w(f.actor+0x14,77);f.w(map+0x18,32)
 regions=[]
 for i in range(32):
  r=f.heap+0x30000+i*0x300;regions.append(r);f.w(map+0x100+i*4,r);f.w(r,100+i);f.w(r+0x14,2);f.w(r+0x10,r+0x100);f.w(r+0x104,r+0x200);f.w(r+0x200,r);f.f(r+0x54,350+(i%8)*120);f.f(r+0x58,500+(i//8)*150)
 choose=lambda:f.invoke(f.entries[12],[f.kingdom,f.actor],cdecl=True)
 possibilities=set()
 for tick in range(200):f.w(f.world+0xe4,tick);possibilities.add(f.r(choose()))
 check(len(possibilities)>=6,'different simulation seeds vary distant targets')
 c=f.invoke(f.entries[15],[f.kingdom],cdecl=True);picked=[];f.w(f.world+0xe4,1000)
 for launch in range(10):
  now=100+launch*60;f.f(f.world+0xe8,now);r=choose();check(r!=0,'distant alternatives remain available');check(f.r(r) not in picked,'recent destination never repeats');picked.append(f.r(r));f.invoke(f.entries[14],[c,r,struct.unpack('<I',struct.pack('<f',now))[0]],cdecl=True)
 if reference is None:reference=picked
 else:check(picked==reference,'random target sequence is identical across process addresses')
 # Only one remaining pocket: wait rather than repeatedly send units to it.
 f.w(map+0x18,1);f.w(map+0x100,r);check(choose()==0,'no fallback into recent destination');f.f(f.world+0xe8,now+599.9375);check(choose()==0,'target exclusion persists until exact ten-minute boundary');f.f(f.world+0xe8,now+600);check(choose()==r,'target exclusion expires on simulation-time boundary')
 f=Fixture(image,dll);map=f.r(image+0x5f3fcc);terrain=f.heap+0x21000;f.w(f.world+0x30,terrain);f.f(terrain+12,1280);f.f(terrain+16,1280);f.w(map+0x18,3);regions=[]
 for i,(x,y) in enumerate([(1000,1000),(1040,1010),(700,1000)]):
  r=f.heap+0x30000+i*0x300;regions.append(r);f.w(map+0x100+i*4,r);f.w(r,10+i);f.w(r+0x14,2);f.w(r+0x10,r+0x100);f.w(r+0x104,r+0x200);f.w(r+0x200,r);f.w(r+0x100,r+0x220);f.w(r+0x220,r);f.f(r+0x54,x);f.f(r+0x58,y)
 c=f.invoke(f.entries[15],[f.kingdom],cdecl=True);f.invoke(f.entries[14],[c,regions[0],0x42c80000],cdecl=True)
 choose=lambda:f.invoke(f.entries[12],[f.kingdom,f.actor],cdecl=True)
 check(choose()==regions[2],'recent target exclusion also covers neighboring regions, changing the route')
 f.invoke(f.entries[14],[c,regions[2],0x42c80000],cdecl=True);check(choose()==0,'all recent areas blocked means no recon order')
 second=f.heap+0x22000;f.w(second+0x194,0);check(f.invoke(f.entries[12],[second,f.actor],cdecl=True)!=0,'target history is independent for each kingdom')
# Check the new interval against an unused target, so recent-target rejection
# cannot hide an incorrect global cooldown in the scorer and air dispatch.
for image,dll in [(0x460000,0x10000000),(0xb30000,0x14000000),(0x12000000,0x20000000)]:
 f=Fixture(image,dll);map=f.r(image+0x5f3fcc);other=f.heap+0x23000
 f.w(other,55);f.w(other+0x14,2);f.w(other+0x10,other+0x100);f.w(other+0x104,other+0x200);f.w(other+0x200,other);f.f(other+0x54,800);f.f(other+0x58,800)
 f.orders();check(f.ticks==1,'cooldown fixture queued first target');f.w(map+0x100,other)
 f.f(f.world+0xe8,159.9375);check(f.invoke(f.entries[1],[f.kingdom,other],cdecl=True)==0,'new target blocked just before sixty seconds');f.orders();check(f.ticks==1,'synthetic air source obeys sixty-second cooldown')
 f.f(f.world+0xe8,160);check(f.invoke(f.entries[1],[f.kingdom,other],cdecl=True)==1,'new target allowed at exactly sixty seconds');f.orders();check(f.ticks==2,'synthetic air source queues at exactly sixty seconds')
 f=Fixture(image,dll);map=f.r(image+0x5f3fcc);terrain=f.heap+0x21000;f.w(f.world+0x30,terrain);f.f(terrain+12,1280);f.f(terrain+16,1280);f.w(map+0x18,2)
 first=f.region;second=f.heap+0x23000;f.w(second,56);f.w(second+0x14,2);f.w(second+0x10,second+0x100);f.w(second+0x104,second+0x200);f.w(second+0x200,second);f.w(map+0x104,second);f.f(first+0x54,1000);f.f(first+0x58,1000);f.f(second+0x54,1080);f.f(second+0x58,1000)
 c=f.invoke(f.entries[15],[f.kingdom],cdecl=True);f.invoke(f.entries[14],[c,first,0x42c80000],cdecl=True)
 choose=lambda:f.invoke(f.entries[12],[f.kingdom,f.actor],cdecl=True)
 check(choose()==second,'target eighty units away is outside five-percent radius, inside old eight-percent radius')
 f.f(second+0x54,1063.9375);check(choose()==0,'target just inside five-percent radius is excluded');f.f(second+0x54,1064);check(choose()==second,'five-percent radius boundary is accepted')
# Native Game HUD survives some match/menu transitions. Its child list, rather
# than an expired cached pointer, determines whether the clock already exists.
for image,dll in [(0x460000,0x10000000),(0xb30000,0x14000000),(0x12000000,0x20000000)]:
 f=Fixture(image,dll);root=f.heap+0x30000;nodes=f.heap+0x31000;widgets=f.heap+0x32000;names=f.heap+0x33000;captures=f.heap+0x34000;mini=f.heap+0x35000;state=f.heap+0x36000
 f.u.mem_write(names,'PawsDayClock\0'.encode('utf-16le'));f.u.mem_write(names+100,'UI/Game/paws_day_clock.tgi\0'.encode('utf-16le'));f.w(root,image+0x48e090)
 f.asm(image+0x2b74f9,f'mov edx,[esp+4];lea eax,[ecx+0x28];loop:mov ecx,[eax];test ecx,ecx;jz fail;cmp [ecx],edx;je remove;lea eax,[ecx+8];jmp loop;remove:mov ecx,[ecx+8];mov [eax],ecx;mov dword ptr [edx+8],0;inc dword ptr [{captures}];mov eax,1;ret 8;fail:xor eax,eax;ret 8')
 f.w(image+0x504d88+4,image+0x2900);f.asm(image+0x2900,f'inc dword ptr [{captures+4}];mov eax,[esp+4];mov [{captures+8}],eax;ret 4')
 for i in range(3):
  w=widgets+i*0x100;n=nodes+i*0x20;f.w(n,w);f.w(n+8,n+0x20 if i<2 else 0);f.w(w,image+0x504d88);f.w(w+8,root);f.w(w+0x18,names+100);f.w(w+0x1c,names)
 f.w(root+0x28,nodes);existing=lambda:f.invoke(f.entries[16],[root],cdecl=True)
 check(existing()==widgets,'existing clock is reused by native template identity')
 check(f.r(nodes+8)==0 and f.r(captures)==2 and f.r(captures+4)==2 and f.r(captures+8)==1,'duplicate clock labels are detached and destroyed once through native ownership calls')
 check(existing()==widgets and f.r(captures+4)==2,'repeated HUD scan does not delete the surviving clock')
 f.w(image+0x5f92f4,4);f.w(image+0x5f92b4+16,state);f.w(state,image+0x48d0dc);f.w(mini+8,root);f.invoke(f.exports['Test_View'],[mini,0x3f800000,0x3f000000,0x3f000000],cdecl=True)
 f.invoke(f.entries[17],cdecl=True);f.w(image+0x5f92f4,2);f.invoke(f.entries[17],cdecl=True)
 f.w(image+0x5f92f4,4);f.invoke(f.exports['Test_View'],[mini,0x3f800000,0x3f000000,0x3f000000],cdecl=True);f.invoke(f.entries[17],cdecl=True)
 check(existing()==widgets and f.r(captures+4)==2,'temporary non-match phase reuses the surviving HUD clock without a new allocation')
 f.w(widgets+0x1c,names+100);check(existing()==0,'another native label with the same vtable is not mistaken for the clock')
 f.w(widgets+0x1c,names);f.w(widgets+0x18,names);check(existing()==0,'matching template name from a different file is ignored')
 f.w(root+0x28,0);check(existing()==0,'destroyed HUD with reused address never dereferences a stale cached label')
print('UI_SCOUT_NATIVE_PASS',checks,'checks; compiled x86 callbacks at three image bases; native command/visibility stubs explicit')
(a.build/'native-test.json').write_text(json.dumps(dict(checks=checks,bases=3,passed=True,nativeCommands='stubbed; real match required'),indent=2))
