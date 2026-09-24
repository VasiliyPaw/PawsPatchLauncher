import argparse,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15'),str(a.legacy/'pydeps_readable')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
meta=json.loads((a.native/'ai-policy.json').read_text());raw=(a.native/'ai-policy.bin').read_bytes();ks=Ks(KS_ARCH_X86,KS_MODE_32)
cases=0
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for h in meta['wrappers']:
  if h['mode']>=4:continue # Separate limit/lifecycle suite uses their real ABIs.
  uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(image,0x690000);uc.mem_map(cave,(meta['allocation']+4095)&~4095)
  obj,pl,engine,k,world,definition,resources=0x51000000,0x51001000,0x51002000,0x51003000,0x51004000,0x51005000,0x51006000
  uc.mem_map(obj,0x10000);uc.mem_map(0x61000000,0x10000);uc.mem_map(0x62000000,0x1000)
  def w(at,n):uc.mem_write(at,struct.pack('<I',n))
  def fl(at,n):uc.mem_write(at,struct.pack('<f',n))
  code=bytearray(raw)
  for off,im,cv in meta['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-meta['image'])+cv*(cave-meta['cave']))&0xffffffff)
  uc.mem_write(cave,bytes(code));w(image+0x5f3fb8,world);fl(world+0xe8,600)
  w(obj,image+0x4d9274);w(obj+4,engine);w(engine+4,pl);w(pl+8,k);w(obj+0x44,definition)
  w(engine+0xe8,k);w(engine+0x14,123);w(image+0x5f3fc8,0x51007000);w(0x5100706c,0x51007100);w(0x51007070,1);w(0x51007100,pl)
  fl(obj+0x38,125);w(definition+8,definition+128);uc.mem_write(definition+128,'company_test\0'.encode('utf-16le'))
  w(k+0x1a8,resources);w(k+0x1c0,resources+128);w(k+0x1cc,resources+256);w(k+0x1d0,9)
  fl(resources,500);fl(resources+128,100);fl(resources+256,10000)
  # Real native caller ABI, with the unknown game callee mocked explicitly.
  native=f'mov eax,0xc0ffee; mov ecx,0x1234; mov edx,0x5678;'
  if h['fp']:native+=f'fld dword ptr [{resources+512}];'
  native+=f'ret {h["argc"]*4}'
  fl(resources+512,123.5);uc.mem_write(image+h['target'],bytes(ks.asm(native,image+h['target'])[0]))
  uc.mem_write(0x62000100,bytes(ks.asm(f'fstp tbyte ptr [{resources+544}]',0x62000100)[0]))
  sp=0x6100f000;w(sp,0x62000000)
  for j in range(h['argc']):w(sp+4+j*4,0)
  if h['mode']>=2:w(sp+4,definition);fl(sp+8,100);fl(sp+12,200)
  regs={UC_X86_REG_EBX:0xabcdef12,UC_X86_REG_ESI:0x12345678,UC_X86_REG_EDI:0x22334455,UC_X86_REG_EBP:0x33445566}
  for reg,v in regs.items():uc.reg_write(reg,v)
  for i in range(8):uc.reg_write(UC_X86_REG_XMM0+i,0x12340000123400001234000012340000+i)
  uc.reg_write(UC_X86_REG_ECX,pl if h['mode']==2 else obj);uc.reg_write(UC_X86_REG_ESP,sp)
  touched=[]
  uc.hook_add(UC_HOOK_MEM_WRITE,lambda u,access,at,size,value,data:touched.append((at,size)))
  game_before=bytes(uc.mem_read(obj,0x10000))
  uc.emu_start(cave+h['offset'],0x62000000,count=50000)
  assert bytes(uc.mem_read(obj,0x10000))==game_before
  assert all(cave+meta['dataOffset']<=at<cave+meta['allocation'] or 0x61000000<=at<0x61010000 for at,size in touched)
  assert uc.reg_read(UC_X86_REG_ESP)==sp+4+h['argc']*4
  assert uc.reg_read(UC_X86_REG_EAX)==0xc0ffee
  for reg,v in regs.items():assert uc.reg_read(reg)==v
  for i in range(8):assert uc.reg_read(UC_X86_REG_XMM0+i)==0x12340000123400001234000012340000+i
  d=bytes(uc.mem_read(cave+meta['dataOffset'],256));assert struct.unpack_from('<I',d)[0]==1
  assert struct.unpack_from('<I',d,252)[0]==1
  assert struct.unpack_from('<I',d,128+16)[0]==k
  assert struct.unpack_from('<f',d,128+44)[0]==400
  assert d[192:204]==b'company_test'
  assert bytes(uc.mem_read(obj+0x38,4))==struct.pack('<f',125)
  if h['fp']:uc.emu_start(0x62000100,0x62000106,count=1)
  # Repeated evaluations remain observable in counters but do not flood disk.
  for t,expected in [(600,1),(604,1),(605,2),(100,3)]:
   fl(world+0xe8,t);uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,pl if h['mode']==2 else obj)
   uc.emu_start(cave+h['offset'],0x62000000,count=50000)
   header=bytes(uc.mem_read(cave+meta['dataOffset'],128));assert struct.unpack_from('<I',header)[0]==expected
   if h['fp']:uc.emu_start(0x62000100,0x62000106,count=1)
  assert struct.unpack_from('<I',header,8+h['mode']*4)[0]==5
  if h['mode']==0:
   # Continuous priority jitter must not evict rare recruitment records.
   for t,score,state,final,expected in [(101,126,0,0,3),(102,127,0,0,3),(102,127,2,0,4),(102,127,2,1,5),(103,128,2,2,5)]:
    fl(world+0xe8,t);fl(obj+0x38,score);w(obj+8,state);fl(obj+0x34,final)
    uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,obj)
    uc.emu_start(cave+h['offset'],0x62000000,count=50000)
    assert struct.unpack('<I',bytes(uc.mem_read(cave+meta['dataOffset'],4)))[0]==expected
    cases+=1
   # A burst of 6,000 ephemeral goal addresses previously overwrote the ring
   # before the helper's next drain. Distinct kinds/definitions exercise the
   # budget, not just the semantic cache. No decision or game state changes.
   uc.mem_write(cave+meta['dataOffset'],bytes(meta['allocation']-meta['dataOffset']))
   fl(world+0xe8,200)
   for j in range(6000):
    w(obj,image+0x4d9274);w(obj+0x44,definition);w(obj+8,j);fl(obj+0x34,j&1)
    uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,obj)
    uc.emu_start(cave+h['offset'],0x62000000,count=50000)
   header=bytes(uc.mem_read(cave+meta['dataOffset'],128))
   assert struct.unpack_from('<I',header)[0]<=64
   assert struct.unpack_from('<I',header,8)[0]==6000
   assert struct.unpack_from('<I',header,8+25*4)[0]>5000
   # Rare recruit preparation still gets through an exhausted bulk budget.
   rare=next(x for x in meta['wrappers'] if x['mode']==1)
   uc.mem_write(image+rare['target'],bytes(ks.asm('mov eax,0xc0ffee; ret',image+rare['target'])[0]))
   uc.ctl_remove_cache(image+rare['target'],image+rare['target']+64)
   before_count=struct.unpack_from('<I',header)[0]
   uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,obj)
   uc.emu_start(cave+rare['offset'],0x62000000,count=50000)
   assert struct.unpack('<I',bytes(uc.mem_read(cave+meta['dataOffset'],4)))[0]==before_count+1
   cases+=2
  cases+=1
  if h['fp']:
   # A native float return may carry extended precision. Diagnostics preserves
   # all 80 bits unless the enabled policy intentionally vetoes that candidate.
   extended=struct.pack('<QH',(1<<63)+(1<<13),16383)
   uc.mem_write(resources+528,extended)
   uc.mem_write(image+h['target'],bytes(ks.asm(f'fld tbyte ptr [{resources+528}]; mov eax,0xc0ffee; ret 20',image+h['target'])[0]))
   uc.ctl_remove_cache(image+h['target'],image+h['target']+64)
   uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,pl)
   uc.emu_start(cave+h['offset'],0x62000000,count=50000)
   uc.mem_write(0x62000100,bytes(ks.asm(f'fstp tbyte ptr [{resources+544}]',0x62000100)[0]))
   uc.emu_start(0x62000100,0x62000106,count=1)
   assert bytes(uc.mem_read(resources+544,10))==extended,(bytes(uc.mem_read(resources+544,10)).hex(),extended.hex(),hex(uc.reg_read(UC_X86_REG_FPSW)))
   # Independently vary ownership, committed work, position, and list order.
   # Allied plans no longer veto scores; native results and precision stay intact.
   other,otherK,otherE,goal,node,city,container,center= [obj+x for x in (0x8000,0x9000,0xa000,0xb000,0xc000,0xd000,0xe000,0xf000)]
   base_fixture=bytes(uc.mem_read(obj,0x10000))
   for scenario,veto in [('disabled',False),('ally',False),('enemy',False),('no_parent',False),('far',False),('inactive',False),('unassigned',False),('repair',False),('own_committed_first',False),('own_committed_second',False),('ally_city',False),('enemy_city',False),('other_definition',False),('self_only',False)]:
    uc.mem_write(obj,base_fixture);uc.mem_write(cave+meta['dataOffset'],bytes(meta['allocation']-meta['dataOffset']))
    w(cave+meta['dataOffset']+4,0 if scenario=='disabled' else 1)
    w(pl+0xc,engine);w(k+0x1f8,0 if scenario=='no_parent' else 0x5555)
    w(0x51007070,1 if scenario=='self_only' else 2);w(0x51007100,pl);w(0x51007104,other)
    w(other+8,otherK);w(other+0xc,otherE);w(otherK+0x1f8,0x9999 if scenario.startswith('enemy') else 0x5555)
    w(otherE+0xc,node);w(node,goal);w(goal,image+(0x4da3f8 if scenario=='repair' else 0x4da6b0));w(goal+4,otherE);w(goal+8,1 if scenario=='inactive' else 2);w(goal+0xc,0 if scenario=='unassigned' else node+16)
    fl(goal+0x48,500 if scenario=='far' else 100);fl(goal+0x4c,200)
    if scenario.startswith('own_committed'):
     w(engine+0xc,node+32);w(node+32,goal+128);w(goal+128,image+0x4da6b0);w(goal+132,engine);w(goal+136,2);w(goal+140,node+48);fl(goal+128+0x48,100);fl(goal+128+0x4c,200)
     if scenario.endswith('second'):w(0x51007100,other);w(0x51007104,pl)
    if scenario in ('ally_city','enemy_city','other_definition'):
     w(otherE+0xc,0);w(otherK+0x2dc,node);w(otherK+0x2e0,1);w(node,city);w(city+0xe8,otherK);w(city+0x94,city+512);w(city+0x98,container);w(container+0x14,center);w(center+4,definition+32 if scenario=='other_definition' else definition);fl(city+0x20,100);fl(city+0x24,200)
    game_before=bytes(uc.mem_read(obj,0x10000));uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,pl)
    uc.emu_start(cave+h['offset'],0x62000000,count=100000)
    assert bytes(uc.mem_read(obj,0x10000))==game_before,scenario
    event=bytes(uc.mem_read(cave+meta['dataOffset']+128,128))
    assert (struct.unpack_from('<f',event,36)[0]==0)==veto,scenario
    uc.emu_start(0x62000100,0x62000106,count=1)
    assert bytes(uc.mem_read(resources+544,10))==(bytes(10) if veto else extended),scenario
    cases+=1
print('AI_NATIVE_WRAPPER_PASS',cases,'ABI/policy cases; no game object writes; extended precision preserved; native callees mocked')
