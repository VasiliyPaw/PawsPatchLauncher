"""Execute the real relocated x86 router/wrapper with a native-layout fixture."""
import argparse,json,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'pydeps_readable'),str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
m=json.loads((a.native/'FactionVoices.json').read_text());raw=(a.native/'FactionVoices.bin').read_bytes();checks=0
def check(ok,why):
 global checks
 assert ok,why;checks+=1
for image,cave in [(0x460000,0x10000000),(0x15000000,0x29000000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,0x700000);u.mem_map(cave,0x10000);u.mem_map(0x50000000,0x100000)
 stack=0x500f0000;stop=0x500ff000;arena=0x50001000
 def put(p,*v):u.mem_write(p,struct.pack('<'+'I'*len(v),*v))
 def get(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def alloc(n=0x400):
  global arena
  v=arena;arena+=(n+15)&~15;return v
 def text(s):v=alloc((len(s)+1)*2);u.mem_write(v,(s+'\0').encode('utf-16le'));return v
 payload=bytearray(raw)
 for off,ic,cc in m['fixups']:
  n=struct.unpack_from('<I',payload,off)[0]+ic*(image-m['preferredImage'])+cc*(cave-m['preferredCave']);struct.pack_into('<I',payload,off,n&0xffffffff)
 u.mem_write(cave,bytes(payload));state=cave+m['state'];put(state,0x56574346,image,0,1,2,3,1,0,0,0,0,0,cave+m["ownerAdapter"])
 db=alloc(0x1000);collection=alloc();buckets=alloc(64*4);put(image+0x5f3fb4,db);put(db+0x584,collection);put(collection+0x30,buckets,64)
 names={}
 def audio(name):
  obj=alloc();put(obj+8,text(name));node=alloc(8);h=0
  for c in name.upper():h=(h*33+ord(c))&0xffffffff
  slot=buckets+(h%64)*4;put(node,obj,get(slot));put(slot,node);names[name]=obj;return obj
 original=audio('swordsman_select')
 for code in ['en','ru','de','fr']:audio('paws_voice_'+code+'_swordsman_select')
 vt=alloc();put(vt+0xb4,image+0x21250);put(vt+0x108,image+0x22f1f7);u.mem_write(image+0x22f1f7,bytes.fromhex("8b81e8000000c3"))
 actor=alloc();kingdom=alloc();faction=alloc();definition=alloc();put(actor,vt);put(actor+0xe8,kingdom);put(kingdom+0x23c,faction);put(faction+4,definition)
 target=alloc();put(target,vt);put(target+0x78,alloc())
 regs=[UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP];expected_regs=[0x11112222,0x22223333,0x33334444,0x44445555]
 observed=[]
 def native(uc,pc,size,data):
  if pc!=image+0x1e96a:return
  sp=uc.reg_read(UC_X86_REG_ESP);args=struct.unpack('<9I',uc.mem_read(sp,36));observed.append(args)
  check(uc.reg_read(UC_X86_REG_ECX)==0x55667788,'original audio manager ECX changed')
  check([uc.reg_read(r) for r in regs]==expected_regs,'callee-saved registers changed')
  check(uc.reg_read(UC_X86_REG_XMM0)==0x123456789abcdef0123456789abcdef0,'SSE state changed')
  uc.reg_write(UC_X86_REG_EAX,0x1234)
 u.hook_add(UC_HOOK_CODE,native);u.mem_write(image+0x1e96a,b'\xc2\x20\x00')
 def run(who='royalist',lang=0,common=0,source=kingdom,missing=False,actor_arg=target):
  put(definition+8,text(who));put(state+8,*[lang]*5,common)
  selected=original if not missing else names['paws_voice_en_swordsman_select']
  args=[stop,selected,0x20,actor_arg,0,source,0x101,0x202,0x303];put(stack,*args)
  for r,v in zip(regs,expected_regs):u.reg_write(r,v)
  u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_ECX,0x55667788);u.reg_write(UC_X86_REG_EFLAGS,0x202)
  u.reg_write(UC_X86_REG_XMM0,0x123456789abcdef0123456789abcdef0)
  before=bytes(u.mem_read(actor,0x400))+bytes(u.mem_read(kingdom,0x400))+bytes(u.mem_read(definition,0x400))
  u.emu_start(cave+m['entry'],stop,count=100000)
  check(u.reg_read(UC_X86_REG_ESP)==stack+36,'stdcall stack cleanup changed')
  check(u.reg_read(UC_X86_REG_EAX)==0x1234,'original audio return value changed')
  check(observed[-1][0]==stop and list(observed[-1][2:])==args[2:],'non-audio arguments changed, including source/target')
  check(before==bytes(u.mem_read(actor,0x400))+bytes(u.mem_read(kingdom,0x400))+bytes(u.mem_read(definition,0x400)),'simulation data was written')
  expected=selected
  if who in ['royalist','council','nationalist','ceyah','fallen'] and (source or actor_arg==actor) and lang!=common and not missing:
   expected=names['paws_voice_'+['en','ru','de','fr'][lang]+'_swordsman_select']
  check(observed[-1][1]==expected,'wrong faction speech selection')
 for who in ['royalist','council','nationalist','ceyah','fallen','monster','unknown']:
  for lang in range(4):
   for common in range(4):run(who,lang,common)
 run('royalist',1,0,source=0);run('royalist',1,0,source=0,actor_arg=actor);run('royalist',1,0,missing=True)
 # Same actor/race, changed owner faction: no race lookup or stale faction cache.
 put(state+8,1,3,2,0,1,0);put(definition+8,text('royalist'));put(stack,stop,original,0,actor,0,kingdom,0,0,0)
 u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_ECX,0x55667788);u.emu_start(cave+m['entry'],stop,count=100000)
 check(observed[-1][1]==names['paws_voice_ru_swordsman_select'],'royalist source was not Russian')
 put(definition+8,text('council'));put(stack,stop,original,0,actor,0,kingdom,0,0,0);u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_ECX,0x55667788);u.emu_start(cave+m['entry'],stop,count=100000)
 check(observed[-1][1]==names['paws_voice_fr_swordsman_select'],'same human source did not switch to Council French')
 # Explicit source kingdom must win over an actor at the attack target.
 other_kingdom=alloc();other_faction=alloc();other_definition=alloc()
 put(target+0xe8,other_kingdom);put(other_kingdom+0x23c,other_faction);put(other_faction+4,other_definition);put(other_definition+8,text('council'))
 put(definition+8,text('royalist'));put(stack,stop,original,0,target,0,kingdom,0,0,0)
 u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_ECX,0x55667788);u.emu_start(cave+m['entry'],stop,count=100000)
 check(observed[-1][1]==names['paws_voice_ru_swordsman_select'],'target Council owner overrode source Royalist owner')
print('FACTION_VOICE_NATIVE_PASS',checks)
(a.native/'native-tests.json').write_text(json.dumps(dict(passed=True,checks=checks,relocatedImages=2,liveAudioValidated=False),indent=2)+'\n')
