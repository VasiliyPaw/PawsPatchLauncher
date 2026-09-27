"""Run original 1372 ScheduleThink, queue operations and scheduler in x86.

Allocation/free, SVar storage, player work and the final fiber yield are explicit
stubs. Player callbacks reschedule through the original machine code. This is
an offline loaded-queue regression, not played-save or multiplayer acceptance.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_routing.py').read_text().split('\nfor image,cave in ')[0], 'routing:fixtures','exec'))
from unicorn import UC_HOOK_CODE

pe=struct.unpack_from('<I',game,60)[0]
reloc_rva,reloc_size=struct.unpack_from('<II',game,pe+24+96+5*8)
relocations=[];cursor=reloc_rva
while cursor<reloc_rva+reloc_size:
 page,size=struct.unpack_from('<II',game,cursor)
 for pos in range(cursor+8,cursor+size,2):
  value=struct.unpack_from('<H',game,pos)[0]
  if value>>12==3:relocations.append(page+(value&4095))
 cursor+=size

class QueueFixture(Fixture):
 def __init__(self,image=0x460000,cave=0x10000000,patched=True,kind=0):
  super().__init__(image,cave);self.sai=self.player+0x100;self.kind=kind
  self.queue=self.sai+0x58+kind*8;self.setting=0x510f1200;self.heap=0x510a0000
  self.events=[];self.initial_time=12412.1875;self.f(self.world+0xe8,self.initial_time)
  # Original queue operations, scheduling (including SEH), and dispatch.
  for lo,hi in [(0x1e0b1a,0x1e0d46),(0x1e1d08,0x1e1d43),
                (0x1e1e5f,0x1e1e9a),(0x1e1eaf,0x1e1ecc),
                (0x1e1f7d,0x1e2013),(0x494a9,0x494cb),
                (0x1e20c1,0x1e2152),(0x3e15dc,0x3e15fb)]:
   code=bytearray(game[lo:hi])
   for r in relocations:
    if lo<=r<hi:struct.pack_into('<I',code,r-lo,(struct.unpack_from('<I',code,r-lo)[0]+image-0x460000)&0xffffffff)
   self.u.mem_write(image+lo,bytes(code))
  if patched:
   for h in meta['wrappers']:
    if h['mode'] in (52,53,54):self.u.mem_write(image+h['site'],b'\xe8'+struct.pack('<i',cave+h['offset']-image-h['site']-5))
  self.w(self.stats+80,self.heap)
  self.asm(image+0x2ef03c,f'mov eax,[{self.stats+80}];add dword ptr [{self.stats+80}],16;ret')
  self.asm(image+0x3e1285,'ret')
  self.w(0x2c,0x510f1000);self.w(0x510f1000,0x510f1100)
  self.w(image+0x60487c,0);self.w(0x510f1104,1)
  self.w(image+0x5fcd78,self.setting);self.w(image+0x5fcd80,self.setting)
  self.w(image+0x5fcd7c,0);self.w(image+0x5fcd84,0)
  self.f(self.setting,2);self.f(image+0x451248,1);self.f(image+0x458c38,0)
  self.players=0x510f2000;self.w(self.sai+0x6c,self.players);self.w(self.sai+0x70,10)
  for i in range(11):
   pl=0x510f3000+i*32
   self.w(pl,i if i<10 else 0xffffffff);self.f(pl+4,20 if i<4 else 10)
   if i<10:self.w(self.players+i*4,pl)
  self.callback=image+0x3400;self.yield_callback=image+0x3500
  self.asm(self.callback,f'inc dword ptr [ecx+8];push {kind};push 0;push dword ptr [ecx+4];push dword ptr [ecx];mov ecx,{self.sai};call {image+0x1e0b1a};ret')
  self.asm(image+0x1e9dc9,f'mov ecx,{0x510f3000+10*32};jmp {self.callback}')
  self.asm(self.yield_callback,f'inc dword ptr [{self.stats+84}];ret 4')
  def on_callback(u,address,size,data):
   pl=u.reg_read(UC_X86_REG_ECX)
   self.events.append((self.r(pl),self.read_float(self.world+0xe8)))
  self.u.hook_add(UC_HOOK_CODE,on_callback,begin=self.callback,end=self.callback)

 def read_float(self,p):return struct.unpack('<f',self.u.mem_read(p,4))[0]
 def invoke(self,entry,args,obj=0,callee_args=True):
  self.w(self.sp,0x62000000)
  for i,v in enumerate(args):self.w(self.sp+4+i*4,v)
  saved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0x87654321,UC_X86_REG_EDI:0xcafe,UC_X86_REG_EBP:self.frame}
  for r,v in saved.items():self.u.reg_write(r,v)
  self.u.reg_write(UC_X86_REG_ESP,self.sp);self.u.reg_write(UC_X86_REG_ECX,obj)
  self.u.emu_start(entry,0x62000000,count=100000)
  check(self.u.reg_read(UC_X86_REG_EIP)==0x62000000,'native queue function returns')
  check(self.u.reg_read(UC_X86_REG_ESP)==self.sp+4+(len(args)*4 if callee_args else 0),'native stack and SEH epilogue balanced')
  check(all(self.u.reg_read(r)==v for r,v in saved.items()),'native callee-save registers preserved')
 def schedule(self,index,delay,first=False):
  self.invoke(self.image+0x1e0b1a,[index&0xffffffff,bits(delay),int(first),self.kind],self.sai)
 def tick(self,time,blocked=-2):
  self.f(self.world+0xe8,time)
  self.invoke(self.image+0x1e20c1,[self.queue,self.sai+0x78,blocked&0xffffffff,self.sai+0x81,int(blocked!=-2),self.sai+0x6c,self.callback,self.yield_callback],callee_args=False)
  check(self.u.mem_read(self.sai+0x81,1)==b'\0','player ownership restored')
 def nodes(self):
  result=[];node=self.r(self.queue)
  while node:
   check(len(result)<32,'bounded queue without cycles')
   result.append((self.r(node),self.read_float(node+4)));node=self.r(node+8)
  return result
 def load_queue(self):
  # Exact order/deadlines from the frozen save, captured before any fix.
  ids=[9,7,5,4,6,0xffffffff,8,3,2,1,0]
  for i,index in enumerate(ids):
   node=self.heap+i*16;self.w(node,index);self.f(node+4,12413.875+2*i)
   self.w(node+8,node+16 if i+1<len(ids) else 0)
  self.w(self.queue,self.heap);self.w(self.queue+4,self.heap+10*16)
  self.w(self.stats+80,self.heap+11*16)

BASES=[(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]
expected_trace=None;report=[]
for image,cave in BASES:
 for patched in (False,True):
  f=QueueFixture(image,cave,patched);f.load_queue()
  for t in range(4801):f.tick(f.initial_time+t/8)
  counts=[sum(i==n for i,t in f.events) for n in range(10)]
  check(bool(min(counts[:4]))==patched,('original starvation reproduced; all actual kingdoms resume with fix',patched,counts))
  if patched:
   check(min(counts)>=20,('no player starves, including formerly empty slot 8',counts))
   check(all(b[1]-a[1]>=2 for a,b in zip(f.events,f.events[1:])),'original two-second global spacing retained')
   check(max(next(t for i,t in f.events if i==n) for n in range(4))-f.initial_time<44,'loaded deadlines recover within their remaining time plus one queue service window')
   check(len(f.nodes())==11 and len({i for i,t in f.nodes()})==11,'native duplicate suppression and queue size retained')
   if expected_trace is None:expected_trace=f.events
   else:check(f.events==expected_trace,'same simulated dispatch sequence at different ASLR addresses')
  else:check(counts[:4]==[0]*4,'all four actual kingdoms reproduce the observed freeze')
  report.append(dict(image=hex(image),patched=patched,counts=counts,dispatches=len(f.events)))

 # Tactical and disabled behavior must match completely unmodified scheduling.
 for kind,mask in ((0,7),(1,15)):
  traces=[]
  for patched in (False,True):
   f=QueueFixture(image,cave,patched,kind);f.w(f.data+4,mask);f.load_queue()
   for t in range(241):f.tick(f.initial_time+t/8)
   traces.append((f.events,f.nodes()))
  check(traces[0]==traces[1],('disabled/tactical queue identical to stock',kind,mask))

 f=QueueFixture(image,cave);f.schedule(0,20);f.schedule(1,20)
 check(f.nodes()==[(0,f.initial_time+20),(1,f.initial_time+20)],'equal deadlines keep native insertion order without drift')
 f.schedule(0,30);check(f.nodes()==[(0,f.initial_time+20),(1,f.initial_time+20)],'later duplicate cannot postpone an existing entry')
 f.schedule(1,10);check(f.nodes()==[(1,f.initial_time+10),(0,f.initial_time+20)],'earlier duplicate uses native unlink and sorted reinsert')
 check(f.r(0)==0,'native exception chain restored')

 f=QueueFixture(image,cave);f.schedule(0,0);f.schedule(1,0)
 f.tick(f.initial_time,blocked=0);check(not f.events,'tactical ownership blocks same strategic player')
 f.tick(f.initial_time);check(f.events==[(0,f.initial_time)],'blocked turn does not consume global spacing')
 before=f.nodes();f.tick(f.initial_time);check(f.nodes()==before and len(f.events)==1,'spacing only changes peek copy, not stored deadlines')
 f.tick(f.initial_time+1.875);check(len(f.events)==1,'no early dispatch')
 f.tick(f.initial_time+2);check(f.events[-1]==(1,f.initial_time+2),'due player runs at the gap boundary')
 f.schedule(2,0);f.tick(1);check(f.events[-1]==(1,f.initial_time+2),'time rollback never makes future entries runnable')
 f.schedule(3,0);f.tick(1);check(f.events[-1]==(3,1),'rollback resets dispatch spacing for reloaded game time')

 # Native initial spread is preserved; the compatibility phase/mask gates
 # cannot use the original insertion return pointer as a truthy skip result.
 for first in (False,True):
  f=QueueFixture(image,cave);f.schedule(5,22,first)
  check(f.nodes()[0][1]==f.initial_time+(12 if first else 22),'native first-update staggering retained')
 for gap in (0,0.5,3):
  f=QueueFixture(image,cave);f.f(f.setting,gap);f.schedule(0,0);f.schedule(1,0)
  f.tick(f.initial_time);f.tick(f.initial_time+gap)
  check(f.events==[(0,f.initial_time),(1,f.initial_time+gap)],('native configurable spacing respected',gap))

 # Exercise the new bridges' full flags/SIMD/register contract independently
 # of the native scheduler, including failed pop and failed peek returns.
 f=QueueFixture(image,cave);temp=f.query+0x400
 f.call(f.hook(54),obj=f.queue,native=0xabcd01)
 f.w(temp,3);f.f(temp+4,f.initial_time)
 check(f.call(f.hook(53),args=[temp],obj=f.queue,native=0xabcd01,allowed=[temp+4])==0xabcd01,'peek AL and high EAX bits retained')
 check(f.read_float(temp+4)==f.initial_time+2,'only temporary peek deadline is paced')
 f.f(f.world+0xe8,f.initial_time+1)
 f.call(f.hook(54),obj=f.queue,native=0xabcd00)
 f.f(temp+4,f.initial_time)
 f.call(f.hook(53),args=[temp],obj=f.queue,native=0xabcd01,allowed=[temp+4])
 check(f.read_float(temp+4)==f.initial_time+2,'empty pop does not consume dispatch time')
 f.f(temp+4,0)
 f.call(f.hook(53),args=[temp],obj=f.queue,native=0xabcd00)
 check(f.read_float(temp+4)==0,'failed peek leaves native output untouched')
 other=f.world+0x700;f.f(other+0xe8,f.initial_time+1);f.w(image+0x5f3fb8,other)
 f.call(f.hook(53),args=[temp],obj=f.queue,native=0xabcd01)
 check(f.read_float(temp+4)==0,'new world cannot inherit previous pacing')
 f.w(image+0x5f3fb8,f.world);f.call(f.hook(54),obj=f.queue,native=1)
 f.call(f.hook(48),args=[0,f.kingdom,0,0],native=f.player)
 f.call(f.hook(53),args=[temp],obj=f.queue,native=1)
 check(f.read_float(temp+4)==0,'player reconstruction resets spacing even with reused world and time')

 # The cached SVar is not initialized during the earliest new-match enqueue.
 # Keep the original initialization path for that first call, then preserve
 # the native configured gap on the remaining new and loaded entries.
 f=QueueFixture(image,cave);f.w(image+0x5fcd78,0);f.w(image+0x5fcd7c,2)
 f.asm(image+0x3e1573,'mov eax,[esp+4];mov dword ptr [eax],0xffffffff;ret')
 f.asm(image+0x3e1522,'mov eax,[esp+4];mov dword ptr [eax],1;ret')
 f.asm(image+0x65a44,f'mov eax,{f.setting};ret 8')
 f.schedule(0,0)
 check(f.r(image+0x5fcd78)==f.setting and f.nodes()==[(0,f.initial_time+2)],'first enqueue retains native SVar initialization and initial spacing')
 f.schedule(1,0);check(f.nodes()==[(1,f.initial_time),(0,f.initial_time+2)],'initialized scheduling no longer shifts existing deadlines')

print('AI_STRATEGIC_QUEUE_PASS',checks,'checks; original starvation and restored fair dispatch at three ASLR bases')
import hashlib
(a.native/'strategic-queue.json').write_text(json.dumps(dict(passed=True,checks=checks,
 nativeSha256=hashlib.sha256(raw).hexdigest().upper(),runs=report,
 originalScheduleThink=True,originalQueueOperations=True,originalScheduler=True,
 gameLaunched=False),indent=2)+'\n',encoding='utf-8')
