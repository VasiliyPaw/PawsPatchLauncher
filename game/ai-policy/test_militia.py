"""Final garrison priority and kingdom-reserve interaction in compiled hooks.
Native prerequisite/payment services are controlled fixtures, not a game test.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_economy.py').read_text().split('\nfor image,cave in ')[0], 'economy:fixtures', 'exec'))
targets = json.loads(Path(__file__).with_name('militia-upgrades.json').read_text())

def target(f, ids):
 f.w(f.military+8,f.military+0x600)
 f.u.mem_write(f.military+0x600,(ids+'\0').encode('utf-16le'))
 f.w(f.military+0x430,1);f.w(f.military+0x4e0,f.markerdef)

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for ids in targets:
  f=EconomyFixture(image,cave);target(f,ids);f.f(f.target+0x38,2)
  f.invoke(0,f.target,[f.budget,0],allowed=[f.target+0x38])
  check(struct.unpack('<f',f.u.mem_read(f.target+0x38,4))[0]==100000,('all races and factions',ids))
  check(len(f.events(49))==1,'militia priority diagnosed')
 for case in ('native-zero','native-negative','native-nan','already-high','disabled','ordinary-upgrade','not-center','foundation','wrong-goal','short-name','unterminated'):
  f=EconomyFixture(image,cave);target(f,'human_center_citadel_militia');before=2.0
  if case=='native-zero':before=0
  if case=='native-negative':before=-1
  if case=='native-nan':before=float('nan')
  if case=='already-high':before=200000
  if case=='disabled':f.w(f.data+4,7)
  if case=='ordinary-upgrade':target(f,'human_center_citadel')
  if case=='not-center':f.w(f.military+0x430,0)
  if case=='foundation':f.w(f.military+0x4e0,0)
  if case=='wrong-goal':f.w(f.target,image+0x4da628)
  if case=='short-name':target(f,'x')
  if case=='unterminated':f.u.mem_write(f.military+0x600,('x'*96).encode('utf-16le'))
  f.f(f.target+0x38,before);original=bytes(f.u.mem_read(f.target+0x38,4))
  f.invoke(0,f.target,[f.budget,0])
  check(bytes(f.u.mem_read(f.target+0x38,4))==original,('native unavailable and unrelated scores preserved',case))
 for militia in (False,True):
  for native in (0,1):
   f=EconomyFixture(image,cave);f.builder_alive();f.sovereign();f.f(f.stock,250)
   target(f,'human_center_citadel_militia' if militia else 'human_center_citadel')
   f.w(f.target+0x1c,f.recruit+0x400);f.w(f.target+0x20,9);f.f(f.recruit+0x400,100)
   got=f.invoke(30,f.target,[f.budget,0],native=native)
   check(got==int(militia and native),('kingdom reserve exemption preserves native rejection',militia,native))

# Original actor-priority evaluation used by Upgrade::Evaluate through
# 1EE537. Hash lookup, owned-count and property list are controlled services;
# the value/duplicate arithmetic is the game's real x86, not our callback.
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for owned in (0,1,5):
  f=EconomyFixture(image,cave);node=f.rs+0x1100;entry=node+0x40
  f.w(node+4,entry);f.f(entry+4,100000)
  f.u.mem_write(image+0x5c7b9,game[0x5c7b9:0x5c8ef])
  f.asm(image+0x64679,f'mov eax,[esp+4];mov eax,[eax];cmp eax,{f.military};jne absent;mov eax,{node};ret 4;absent:xor eax,eax;ret 4')
  f.asm(image+0x1eeb0b,f'mov eax,{owned};ret 4')
  f.asm(image+0x29949,'mov eax,[esp+4];mov dword ptr [eax],0;mov dword ptr [eax+4],0;ret 4')
  for definition,expected in ((f.military,100000),(f.builder,0)):
   driver=f'fninit;push 1;push {f.player};push {definition};mov ecx,{f.ego};call {image+0x5c7b9};fstp dword ptr [{f.stats+24}];nop'
   code=bytes(ks.asm(driver,0x62000000)[0]);f.u.mem_write(0x62000000,code);f.u.ctl_remove_cache(0x62000000,0x62001000);f.u.reg_write(UC_X86_REG_ESP,f.sp)
   f.u.emu_start(0x62000000,0x62000000+len(code),count=10000)
   check(f.u.reg_read(UC_X86_REG_EIP)==0x62000000+len(code) and f.u.reg_read(UC_X86_REG_ESP)==f.sp,'native actor priority ABI')
   check(struct.unpack('<f',f.u.mem_read(f.stats+24,4))[0]==expected,('native actor priority, no repetition penalty',owned,expected))

print('AI_MILITIA_PASS',checks,'checks; 19 upgrade targets, 3 ASLR bases; original actor-priority arithmetic; native rejection, ordinary priorities, toggle and reserve preserved; engine services mocked')
