"""Native yield/synchronizer regression for the 25 September first-tick desync.

The strategic/tactical yield functions and synchronizer guard execute original
1372 x86 instructions. SwitchToFiber is a controlled world-slice stub: it calls
the original synchronizer while the AI is suspended. Ring allocation, clock,
OS thread ID and goal-selection services are explicit stubs. No played-network
acceptance is implied.
"""
from pathlib import Path
source=Path(__file__).with_name('test_expansion_pulse.py').read_text()
exec(compile(source.split('\nfor image,cave in BASES:')[0], 'pulse:fixtures','exec'))
exec(compile('class PulseFixture'+source.split('class PulseFixture',1)[1].split('\nfor image,cave in BASES:')[0], 'pulse:class','exec'))

pe=struct.unpack_from('<I',game,60)[0]
reloc_rva,reloc_size=struct.unpack_from('<II',game,pe+24+96+5*8)
relocations=[];cursor=reloc_rva
while cursor<reloc_rva+reloc_size:
 page,size=struct.unpack_from('<II',game,cursor)
 for pos in range(cursor+8,cursor+size,2):
  value=struct.unpack_from('<H',game,pos)[0]
  if value>>12==3:relocations.append(page+(value&4095))
 cursor+=size

def native(f,start,end):
 code=bytearray(game[start:end])
 for r in relocations:
  if start<=r<end:
   check(r+4<=end,'complete relocation')
   value=struct.unpack_from('<I',code,r-start)[0]
   struct.pack_into('<I',code,r-start,(value+f.image-0x460000)&0xffffffff)
 f.u.mem_write(f.image+start,bytes(code))
 f.u.ctl_remove_cache(f.image+start,f.image+end)

def install_yields(f):
 image=f.image;sai=f.r(image+0x5f3fc8);f.sai=sai;f.sync=0x510f0000
 native(f,0x1e156b,0x1e16bb)
 native(f,0x16dff2,0x16e079)
 f.w(sai+0x24,0);f.w(sai+0x4c,100);f.w(sai+0x50,100)
 f.w(sai+0x48,0x1234);f.w(image+0x5f9380,77)
 f.asm(image+0x29c19a,'mov eax,100;ret')
 f.w(image+0x44d1c8,image+0x3000);f.asm(image+0x3000,'mov eax,77;ret')
 f.w(image+0x44d240,image+0x3100)
 f.w(f.sync,1);f.w(f.sync+0xc,10000)
 f.asm(image+0x16e87b,f'inc dword ptr [{f.sync+0x14}];mov eax,{f.sync+0x100};ret 4')
 # Simulate a main-world checksum during each suspension, then resume the AI.
 f.asm(image+0x3100,f'pushad;inc dword ptr [{f.sync+0x200}];'
  f'push 0;push 123;push {image+0x4000};mov ecx,{f.sync};call {image+0x16dff2};'
  f'movzx eax,byte ptr [{sai+0x81}];mov [{f.sync+0x204}],eax;'
  f'mov eax,[{sai+0x78}];mov [{f.sync+0x208}],eax;popad;ret 4')
 f.asm(image+0x1e838a,f'inc dword ptr [{f.stats+112}];'
  f'push 0;mov ecx,{sai};call {image+0x1e156b};ret')
 return [sai+0x68,sai+0x69]+list(range(f.sync,f.sync+0x210,4))

def direct_yield(f,rva):
 f.w(f.sp,0x62000000);f.w(f.sp+4,1)
 f.u.reg_write(UC_X86_REG_ESP,f.sp);f.u.reg_write(UC_X86_REG_ECX,f.sai)
 f.u.emu_start(f.image+rva,0x62000000,count=10000)
 check(f.u.reg_read(UC_X86_REG_ESP)==f.sp+8,'native yield stack balanced')

for image,cave in BASES:
 # Reproduce the actual former call chain, independently of the new policy:
 # SelectGoals called the strategic yield while the tactical fiber was active.
 f=PulseFixture(image,cave);install_yields(f);f.w(f.sai+0x68,0x100)
 direct_yield(f,0x1e156b)
 check(f.r(f.sync+0x200)==1 and f.r(f.sync+0x14)==0,
       'historical tactical-to-strategic yield suppresses the world checksum')
 check(f.r(f.sai+0x68)&0xffff==0x101,'historical resume poisons strategic-active flag')
 direct_yield(f,0x1e162d)
 check(f.r(f.sync+0x200)==2 and f.r(f.sync+0x14)==0,
       'even the later proper tactical yield cannot repair the leaked flag')

 # Every context except an idle strategic fiber must leave planning untouched.
 for context in ('main','tactical','both','strategic-busy','same-tactical-player'):
  f=PulseFixture(image,cave);allowed=install_yields(f)
  f.w(f.sai+0x68,{'main':0,'tactical':0x100,'both':0x101}.get(context,1))
  if context=='strategic-busy':f.u.mem_write(f.sai+0x81,b'\x01')
  if context=='same-tactical-player':f.u.mem_write(f.sai+0x80,b'\x01');f.w(f.sai+0x7c,0)
  before=bytes(f.u.mem_read(f.sai+0x68,0x1c))
  f.call(f.hook(34),obj=f.player,allowed=allowed)
  check(f.r(f.stats+112)==0,('planner must not run in this fiber context',context))
  check(bytes(f.u.mem_read(f.sai+0x68,0x1c))==before,('scheduler ownership unchanged',context))

 f=PulseFixture(image,cave);allowed=install_yields(f);f.w(f.sai+0x78,0xffffffff)
 # A suspended tactical update of a DIFFERENT player must not block this one.
 f.u.mem_write(f.sai+0x80,b'\x01');f.w(f.sai+0x7c,1)
 f.call(f.hook(34),obj=f.player,allowed=allowed)
 check(f.r(f.stats+112)==1,'strategic idle callback completes expansion')
 check(f.r(f.sync+0x200)==1 and f.r(f.sync+0x14)==1 and f.r(f.sync+8)==123,
       'native world checksum is retained during the planner yield')
 check(f.r(f.sync+0x204)==1 and f.r(f.sync+0x208)==0,
       'current player is reserved against tactical work throughout suspension')
 check(f.r(f.sai+0x68)&0xffff==1,'resume restores only the correct strategic flag')
 check(f.r(f.sai+0x78)==0xffffffff and f.u.mem_read(f.sai+0x81,1)==b'\0',
       'native player ownership restored after the extra pass')

 # Execute the original scheduler itself: caller arguments must survive its
 # cdecl wrapper, and fast work must follow its completed player/yield scope.
 native(f,0x1e20c1,0x1e2152)
 f.w(f.stats+112,0);f.f(f.world+0xe8,34);f.w(f.sync+0x14,0);f.w(f.sync+0x200,0)
 f.asm(image+0x1e1eaf,'mov eax,[esp+4];mov dword ptr [eax],0;mov dword ptr [eax+4],0;ret 4')
 f.asm(image+0x494a9,'ret')
 f.asm(image+0x3200,f'cmp byte ptr [{f.sai+0x81}],1;jne bad;'
  f'inc dword ptr [{f.sync+0x20c}];ret;bad:ud2')
 args=[f.sai+0x58,f.sai+0x78,1,f.sai+0x81,0,f.sai+0x6c,image+0x3200,image+0x1e156b]
 for i,v in enumerate(args):f.w(f.sp+4+i*4,v)
 f.w(f.sp,0x62000000);f.u.reg_write(UC_X86_REG_ESP,f.sp);f.u.reg_write(UC_X86_REG_ECX,f.sai+0x78)
 f.u.emu_start(cave+f.hook(34)['offset'],0x62000000,count=12000000)
 check(f.u.reg_read(UC_X86_REG_EIP)==0x62000000,'real scheduler callback returns')
 check(f.u.reg_read(UC_X86_REG_ESP)==f.sp+4,'eight cdecl arguments remain for native caller cleanup')
 check([f.r(f.sp+4+i*4) for i in range(8)]==args,'scheduler arguments preserved')
 check(f.r(f.sync+0x20c)==1 and f.r(f.stats+112)==1,'native player callback then extra pass both executed')
 check(f.r(f.sync+0x200)==2 and f.r(f.sync+0x14)==2,'both scheduler and expansion yields preserve checksums')
 check(f.r(f.sai+0x68)&0xffff==1 and f.u.mem_read(f.sai+0x81,1)==b'\0','scheduler flags remain balanced')

check(next(h for h in meta['wrappers'] if h['mode']==34)['site']==0x1e1b87,'hook belongs to strategic scheduler')
check(not any(h['site']==0x1ef0d9 for h in meta['wrappers']),'tactical planning hook removed')
print('AI_FIBER_SYNC_PASS',checks,'checks; original yield, synchronizer guard and strategic scheduler at three ASLR bases')
import hashlib
(a.native/'fiber-sync.json').write_text(json.dumps(dict(passed=True,checks=checks,
 relocationBases=len(BASES),nativeSha256=hashlib.sha256(raw).hexdigest().upper(),
 historicalFailureReproduced=True,originalYieldAndSynchronizer=True,
 originalStrategicScheduler=True,gameLaunched=False),indent=2)+'\n',encoding='utf-8')
