"""Build only a local terrain probe; does not patch or launch a game."""
import argparse,json,struct,subprocess
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import LEGACY,RAW,BASE
import pefile
from keystone import Ks,KS_ARCH_X86,KS_MODE_32

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--compiler',required=True);p.add_argument('--menu',action='store_true');p.add_argument('--roads',action='store_true');p.add_argument('--bridges',action='store_true');p.add_argument('--installed',action='store_true');p.add_argument('--trace-routing',action='store_true');p.add_argument('--multiplayer',action='store_true');a=p.parse_args()
if a.multiplayer:assert a.bridges and a.installed
if a.bridges:a.roads=True
a.out.mkdir(parents=True,exist_ok=True)
art_path=a.out.parent/'bridge-art.json'
styles=list(json.loads(art_path.read_text()).get('styles',{})) if art_path.exists() else []
sources=[str(Path(__file__).with_name('generator.c'))]
if a.menu:
 from localization import c_header
 (a.out/'menu_text.h').write_text(c_header(),encoding='ascii')
 sources.append(str(Path(__file__).with_name('installed_menu.c' if a.installed else 'menu.c')))
if a.roads:
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engineer-roads'))
 from texts import header
 (a.out/'road_text.h').write_text(header(),encoding='ascii')
 sources.append(str(Path(__file__).resolve().parents[1]/'engineer-roads/roads.c'))
subprocess.run([a.compiler,'-shared','-nostdlib','-Wall','-Werror','-I'+str(a.out),'-Wl,--image-base=0x10000000',*(['-DPAWS_BRIDGE_ROUTE_TRACE'] if a.trace_routing else []),*(['-DPAWS_BRIDGE_MULTIPLAYER'] if a.multiplayer else []),*(['-DPAWS_BRIDGES'] if a.bridges else []),*(['-DPAWS_INSTALLED_RIVERS'] if a.installed else []),*['-DPAWS_BRIDGE_'+style.upper() for style in styles],*sources,'-o',str(a.out/'prototype.dll')],check=True)
pe=pefile.PE(str(a.out/'prototype.dll'));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT')
code=bytearray(pe.get_memory_mapped_image());exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
fix=[(e.rva,0,1) for b in pe.DIRECTORY_ENTRY_BASERELOC for e in b.entries if e.type==3]
ks=Ks(KS_ARCH_X86,KS_MODE_32);cave=0x10000000
wrapper=(len(code)+4095)&~4095;adapter=wrapper+0x200;state=wrapper+0x2000
code.extend(bytes(state-len(code)))
# Native callee cleans arguments. Retains cdecl caller's preserved registers.
asm='push ebp;mov ebp,esp;push ebx;push esi;mov ebx,[ebp+16];mov esi,[ebp+20];test ebx,ebx;jz call_native;args:dec ebx;push dword ptr [esi+ebx*4];test ebx,ebx;jnz args;call_native:mov ecx,[ebp+12];call dword ptr [ebp+8];pop esi;pop ebx;leave;ret;'
data=bytes(ks.asm(asm,cave+adapter)[0]);code[adapter:adapter+len(data)]=data
# StageTerrain replacement: preserve all native register/FPU state except EAX
# (native boolean result), leaving the caller's normal test al,al in place.
site=0x25697a;assert RAW[site:site+5]==bytes.fromhex('e89a050000')
asm=f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push ecx;push {cave+state};call {cave+exports["generate"]};add esp,8;mov [ebp+28],eax;fxrstor [esp];mov esp,ebp;popad;popfd;ret;'
data=bytes(ks.asm(asm,cave+wrapper)[0]);code[wrapper:wrapper+len(data)]=data
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
for ins in md.disasm(data,cave+wrapper):
    for op in ins.operands:
        if op.type!=CS_OP_IMM:continue
        if op.imm==cave+state:fix.append((ins.address-cave+ins.imm_offset,0,1))
        if ins.mnemonic in ('call','jmp') and BASE<=op.imm<BASE+len(RAW):fix.append((ins.address-cave+ins.imm_offset,1,-1))
hooks=[dict(site=site,entry=wrapper,kind='call',before=RAW[site:site+5].hex())]
if a.installed:
 # Preserve native hills/noise, then paint rivers before actor placement.
 # Painting at StageTerrain lets the later noise stage cut dry mountain
 # crossings straight through an otherwise continuous water mask.
 noise_site=0x2569b9;noise_target=0x256f58;off=wrapper+0x100
 assert RAW[noise_site:noise_site+5]==b'\xe8'+struct.pack('<i',noise_target-noise_site-5)
 asm=f'push ecx;call {BASE+noise_target};pop ecx;test al,al;jz finished;pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push ecx;push {cave+state};call {cave+exports["generate_after_noise"]};add esp,8;mov [ebp+28],eax;fxrstor [esp];mov esp,ebp;popad;popfd;finished:ret;'
 data=bytes(ks.asm(asm,cave+off)[0]);assert len(data)<0x100;code[off:off+len(data)]=data
 for ins in md.disasm(data,cave+off):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if op.imm==cave+state:fix.append((ins.address-cave+ins.imm_offset,0,1))
   if ins.mnemonic=='call' and op.imm==BASE+noise_target:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 hooks.append(dict(site=noise_site,entry=off,kind='call',before=RAW[noise_site:noise_site+5].hex()))
 island_site=0x2567df;island_target=0x24a7da;off=wrapper+0x240
 assert RAW[island_site:island_site+5]==b'\xe8'+struct.pack('<i',island_target-island_site-5)
 asm=f'push ecx;call {BASE+island_target};pop ecx;pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push eax;push ecx;push {cave+state};call {cave+exports["placement_island"]};add esp,12;mov [ebp+28],eax;fxrstor [esp];mov esp,ebp;popad;popfd;ret;'
 data=bytes(ks.asm(asm,cave+off)[0]);assert len(data)<0xc0;code[off:off+len(data)]=data
 for ins in md.disasm(data,cave+off):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if op.imm==cave+state:fix.append((ins.address-cave+ins.imm_offset,0,1))
   if ins.mnemonic=='call' and op.imm==BASE+island_target:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 hooks.append(dict(site=island_site,entry=off,kind='call',before=RAW[island_site:island_site+5].hex()))
if a.installed:
 bed_site=0x256b80;bed_target=0x24e988;off=wrapper+0x1000
 assert RAW[bed_site:bed_site+5]==b'\xe8'+struct.pack('<i',bed_target-bed_site-5)
 asm=f'call {BASE+bed_target};pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push {cave+state};call {cave+exports["finish_river_bed"]};add esp,4;fxrstor [esp];mov esp,ebp;popad;popfd;ret;'
 data=bytes(ks.asm(asm,cave+off)[0]);assert len(data)<0x100;code[off:off+len(data)]=data
 for ins in md.disasm(data,cave+off):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if op.imm==cave+state:fix.append((ins.address-cave+ins.imm_offset,0,1))
   if ins.mnemonic=='call' and op.imm==BASE+bed_target:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 hooks.append(dict(site=bed_site,entry=off,kind='call',before=RAW[bed_site:bed_site+5].hex()))
if a.installed:
 # This call is shared by Launch and the native confirmation path. Its one
 # original stack argument belongs to the original callee (tail jump).
 launch_site=0x104d8d;launch_target=0x13c0d8;off=wrapper+0x1100
 assert RAW[launch_site:launch_site+5]==b'\xe8'+struct.pack('<i',launch_target-launch_site-5),RAW[launch_site:launch_site+5].hex()
 asm=f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push {cave+state+256};call {cave+exports["menu_launch_settings"]};add esp,4;fxrstor [esp];mov esp,ebp;popad;popfd;jmp {BASE+launch_target};'
 data=bytes(ks.asm(asm,cave+off)[0]);assert len(data)<0x100;code[off:off+len(data)]=data
 for ins in md.disasm(data,cave+off):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if op.imm==cave+state+256:fix.append((ins.address-cave+ins.imm_offset,0,1))
   if ins.mnemonic=='jmp' and op.imm==BASE+launch_target:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 hooks.append(dict(site=launch_site,entry=off,kind='call',before=RAW[launch_site:launch_site+5].hex()))
if a.menu:
 # Only this native class gets the new controls; stock load/save dialogs keep
 # their original virtual methods. All methods have zero stack arguments.
 for index,(loc,target,name,mode) in enumerate([
  (0x4a67e0,0x11a7b4,'menu_create','after'),
  (0x4a6820,0x11b8b8,'menu_populate','after' if a.installed else 'replace'),
  (0x11c370,0x119f91,'menu_destroy','before')]):
  off=wrapper+0x300+index*0x180;addr=cave+off;uistate=cave+state+256
  invoke=f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push dword ptr [ebp+24];push {uistate};call {cave+exports[name]};add esp,8;fxrstor [esp];mov esp,ebp;popad;popfd;'
  # Preserve the original this pointer through the original create call.
  original=f'push ecx;call {BASE+target};pop ecx;'
  asm=(original+invoke if mode=='after' else invoke+original if mode=='before' else invoke)+'ret;'
  data=bytes(ks.asm(asm,addr)[0]);assert len(data)<0x180;code[off:off+len(data)]=data
  for ins in md.disasm(data,addr):
   for op in ins.operands:
    if op.type!=CS_OP_IMM:continue
    if op.imm==uistate:fix.append((ins.address-cave+ins.imm_offset,0,1))
    if ins.mnemonic=='call' and op.imm==BASE+target:fix.append((ins.address-cave+ins.imm_offset,1,-1))
  iscall=mode=='before';before=RAW[loc:loc+(5 if iscall else 4)]
  assert before==(b'\xe8'+struct.pack('<i',target-loc-5) if iscall else struct.pack('<I',BASE+target))
  hooks.append(dict(site=loc,entry=off,kind='call' if iscall else 'pointer',before=before.hex()))
 # Size/profile/settings refreshes keep the river menu within the selected
 # size's limit. Native WorldRules carry the stable enum into saves/seeds.
 off=wrapper+0xb00;addr=cave+off;uistate=cave+state+256
 asm=f'push ecx;call {BASE+0x11ba60};pop ecx;pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push dword ptr [ebp+24];push {uistate};call {cave+exports["menu_rivers_refresh"]};add esp,8;fxrstor [esp];mov esp,ebp;popad;popfd;ret;'
 data=bytes(ks.asm(asm,addr)[0]);assert len(data)<0x100;code[off:off+len(data)]=data
 for ins in md.disasm(data,addr):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if op.imm==uistate:fix.append((ins.address-cave+ins.imm_offset,0,1))
   if ins.mnemonic=='call' and op.imm==BASE+0x11ba60:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 for loc in (0x11a6db,0x11a7ac,0x11b898):
  assert RAW[loc:loc+5]==b'\xe8'+struct.pack('<i',0x11ba60-loc-5)
  hooks.append(dict(site=loc,entry=off,kind='call',before=RAW[loc:loc+5].hex()))
if a.roads:
 # Local roads share the guarded installer and existing map/climate prototype.
 for off,loc,name,create in [(wrapper+0x800,0xc772e,'roads_create',True),(wrapper+0xa00,0x2469b7,'roads_tick',False)]:
  if a.installed and create:continue # Installed uniform HUD owns this site.
  roadstate=cave+state+0x300
  if create:
   assert RAW[loc:loc+6]==bytes.fromhex('ff92d0000000')
   prefix='push ebp;mov ebp,esp;push ecx;push dword ptr [ebp+8];call dword ptr [edx+0xd0];'
   selfarg='push dword ptr [ebp-4];';suffix='leave;ret 4;'
  else:
   assert RAW[loc:loc+5]==bytes.fromhex('e89db7ffff')
   prefix=f'call {BASE+0x242159};';selfarg='push esi;';suffix='ret;'
  # EBP belongs to the outer create wrapper. Preserve it before aligning FXSAVE.
  if create:
   body=f'pushfd;pushad;mov esi,[ebp-4];mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push esi;push {roadstate};call {cave+exports[name]};'
  else:
   body=f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push esi;push {roadstate};call {cave+exports[name]};'
  asm=prefix+body+'add esp,8;fxrstor [esp];mov esp,ebp;popad;popfd;'+suffix
  data=bytes(ks.asm(asm,cave+off)[0]);assert len(data)<0x180;code[off:off+len(data)]=data
  for ins in md.disasm(data,cave+off):
   for op in ins.operands:
    if op.type!=CS_OP_IMM:continue
    if op.imm==roadstate:fix.append((ins.address-cave+ins.imm_offset,0,1))
    if ins.mnemonic=='call' and op.imm==BASE+0x242159:fix.append((ins.address-cave+ins.imm_offset,1,-1))
  hooks.append(dict(site=loc,entry=off,kind='call',before=RAW[loc:loc+(6 if create else 5)].hex()))
if a.roads:
 hooks.append(dict(site=0x48e3d0,entry=exports['roads_event'],kind='pointer',before=RAW[0x48e3d0:0x48e3d4].hex()))
 assert RAW[0x48e3d0:0x48e3d4]==struct.pack('<I',BASE+0xd4e76)
if a.bridges:
 # Intercept only the default context pick: completed friendly bridge decks
 # receive ordinary point orders while selection and enemy attacks stay native.
 off=wrapper+0x1400;roadstate=cave+state+0x300
 asm=f'push ecx;push {roadstate};call {cave+exports["bridge_context_pick"]};add esp,8;ret;'
 data=bytes(ks.asm(asm,cave+off)[0]);code[off:off+len(data)]=data
 for ins in md.disasm(data,cave+off):
  for op in ins.operands:
   if op.type==CS_OP_IMM and op.imm==roadstate:fix.append((ins.address-cave+ins.imm_offset,0,1))
 loc=0xd4f5f;assert RAW[loc:loc+5]==b'\xe8'+struct.pack('<i',0x2d8c10-loc-5)
 hooks.append(dict(site=loc,entry=off,kind='call',before=RAW[loc:loc+5].hex()))
 loc=0x2635e4;assert RAW[loc:loc+5]==b'\xe8'+struct.pack('<i',0x263752-loc-5)
 hooks.append(dict(site=loc,entry=exports['bridge_region_route'],kind='call',before=RAW[loc:loc+5].hex()))
 waypoint_sites=[i for i in range(0x2c65ca,0x2c69ee) if RAW[i]==0xe8 and i+5+struct.unpack_from('<i',RAW,i+1)[0]==0x2c6a85]
 assert len(waypoint_sites)==1
 for loc in waypoint_sites:hooks.append(dict(site=loc,entry=exports['bridge_waypoint_position'],kind='call',before=RAW[loc:loc+5].hex()))
 # Keep the normal building UI, confirmation and saved razing state. Only
 # bridge command availability and current upkeep require specialization.
 for target,name in [(0x20583d,'bridge_construction_commands'),(0x205e72,'bridge_raze_start'),(0x205ec2,'bridge_raze_cancel'),(0x20dbcb,'bridge_upkeep_active'),(0x2e4590,'bridge_selection_tick')]:
  sites=[i for i in range(0x44b000) if RAW[i]==0xe8 and i+5+struct.unpack_from('<i',RAW,i+1)[0]==target]
  assert sites,(hex(target),name)
  for loc in sites:hooks.append(dict(site=loc,entry=exports[name],kind='call',before=RAW[loc:loc+5].hex()))
 # Scope construction healing to the native HealEffect call, and periodic
 # healing to its native property pulse. Other healing paths are untouched.
 for loc,name in [(0x1fd835,'bridge_construct_heal'),(0x21bf7b,'bridge_periodic_heal')]:
  assert RAW[loc:loc+5]==b'\xe8'+struct.pack('<i',0x202e47-loc-5)
  hooks.append(dict(site=loc,entry=exports[name],kind='call',before=RAW[loc:loc+5].hex()))
 # Only the bridge growth strip preserves its heading across native VFXModel
 # detachment. Every other effect retains the original virtual method.
 loc=0x50aa5c+0x11c
 assert struct.unpack_from('<I',RAW,loc)[0]==BASE+0x2cedb4
 hooks.append(dict(site=loc,entry=exports['bridge_growth_release'],kind='pointer',before=RAW[loc:loc+4].hex()))
 # All verified calls of CAIStateMove::Activate(actor), including roaming AI.
 actor_move_sites=[i for i in range(0x44b000) if RAW[i]==0xe8 and i+5+struct.unpack_from('<i',RAW,i+1)[0]==0x26f0d1]
 assert actor_move_sites
 for loc in actor_move_sites:hooks.append(dict(site=loc,entry=exports['bridge_move_to_actor'],kind='call',before=RAW[loc:loc+5].hex()))
 attack_activate_sites=[i for i in range(0x44b000) if RAW[i]==0xe8 and i+5+struct.unpack_from('<i',RAW,i+1)[0]==0x27031c]
 assert len(attack_activate_sites)==8
 for loc in attack_activate_sites:hooks.append(dict(site=loc,entry=exports['bridge_attack_activate'],kind='call',before=RAW[loc:loc+5].hex()))
 off=wrapper+0x1b00
 data=bytes(ks.asm(f'push ecx;push {roadstate};call {cave+exports["bridge_attack_tick"]};add esp,8;ret;',cave+off)[0]);code[off:off+len(data)]=data
 for ins in md.disasm(data,cave+off):
  for op in ins.operands:
   if op.type==CS_OP_IMM and op.imm==roadstate:fix.append((ins.address-cave+ins.imm_offset,0,1))
 loc=0x4f4e30;assert RAW[loc:loc+4]==struct.pack('<I',BASE+0x270431)
 hooks.append(dict(site=loc,entry=off,kind='pointer',before=RAW[loc:loc+4].hex()))
 # Individual/summoned units also own UAI Kill/Bombard states. Company-only
 # target filters cannot cover their direct activations or saved active states.
 for target,name,expected in [(0x281899,'bridge_unit_attack_activate',6),(0x281c95,'bridge_unit_bombard_activate',3)]:
  sites=[i for i in range(0x44b000) if RAW[i]==0xe8 and i+5+struct.unpack_from('<i',RAW,i+1)[0]==target]
  assert len(sites)==expected,(hex(target),sites)
  for loc in sites:hooks.append(dict(site=loc,entry=exports[name],kind='call',before=RAW[loc:loc+5].hex()))
 for loc,target,name in [(0x4f6ea4,0x281928,'bridge_unit_attack_tick'),(0x4f6ed0,0x281ec6,'bridge_unit_bombard_tick')]:
  assert RAW[loc:loc+4]==struct.pack('<I',BASE+target)
  hooks.append(dict(site=loc,entry=exports[name],kind='pointer',before=RAW[loc:loc+4].hex()))
 # Native construct actions and summon effects must not materialise a
 # menu/brush prototype. Reuse these four actual actor-creation call sites. The
 # validated bridge queue creates only full length-specific actors directly.
 # Keep human capability/menu checks and saved actor deserialisation native.
 for loc,target,name in [(0x1fd049,0x242fcd,'bridge_builder_spawn_alternate'),(0x1fd050,0x242eee,'bridge_builder_spawn'),(0x28c332,0x242fcd,'bridge_builder_spawn_alternate'),(0x28c339,0x242eee,'bridge_builder_spawn')]:
  assert RAW[loc:loc+5]==b'\xe8'+struct.pack('<i',target-loc-5)
  hooks.append(dict(site=loc,entry=exports[name],kind='call',before=RAW[loc:loc+5].hex()))
 # Reject bridge catalogue prototypes at the actual construct request, before
 # its internal foundation spawn242b2e and work-command submission. This
 # native request has five stack arguments (verified RET20), not four.
 construct_sites=[i for i in range(0x44b000) if RAW[i]==0xe8 and i+5+struct.unpack_from('<i',RAW,i+1)[0]==0x28c365]
 assert construct_sites==[0x289f69],construct_sites
 assert RAW[0x28c65a:0x28c65d]==bytes.fromhex('c21400')
 for loc in construct_sites:hooks.append(dict(site=loc,entry=exports['bridge_construct_request'],kind='call',before=RAW[loc:loc+5].hex()))
 # Runtime movement must see the finished crossings in the saved static
 # island IDs, while actual terrain and object collision remain native.
 # Native island getters preserve flags, ECX/EDX and all floating registers.
 # Destination validators keep live vector temporaries across these calls.
 for offset,name,extra,original,sites in [
  (0x1300,'bridge_collision_island','mov edx,[ebp+8];',0x24a7da,(0x244727,0x244752)),
  (0x1700,'bridge_walk_island','xor edx,edx;',0x24a7da,(0x2238cf,0x223906,0x22392b,0x22393c,0x2239fc,0x223a99)),
  (0x1800,'bridge_company_region','mov edx,[ebp+16];',0x1f5344,(0x273e6c,)),
  (0x1900,'bridge_company_island','mov edx,[ebp+0x58];',0x24a7da,(0x273f13,0x27409c)),
  (0x1a00,'bridge_path_island','mov edx,[ebp+4];',0x24a7da,(0x278e8a,))]:
  island_off=wrapper+offset
  asm=f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];mov ecx,[ebp+24];{extra}call {cave+exports[name]};mov [ebp+28],eax;fxrstor [esp];mov esp,ebp;popad;popfd;ret;'
  data=bytes(ks.asm(asm,cave+island_off)[0]);assert len(data)<0x100;code[island_off:island_off+len(data)]=data
  for island_site in sites:
   assert RAW[island_site:island_site+5]==b'\xe8'+struct.pack('<i',original-island_site-5)
   hooks.append(dict(site=island_site,entry=island_off,kind='call',before=RAW[island_site:island_site+5].hex()))
 loc=0x50e3c8;target=0x2d00af;off=wrapper+0x1200;addr=cave+off;roadstate=cave+state+0x300
 data=bytes(ks.asm(f'push ecx;push {roadstate};call {cave+exports["bridge_decal_tick"]};add esp,8;ret;',addr)[0]);code[off:off+len(data)]=data
 for ins in md.disasm(data,addr):
  for op in ins.operands:
   if op.type==CS_OP_IMM and op.imm==roadstate:fix.append((ins.address-cave+ins.imm_offset,0,1))
 assert RAW[loc:loc+4]==struct.pack('<I',BASE+target)
 hooks.append(dict(site=loc,entry=off,kind='pointer',before=RAW[loc:loc+4].hex()))
 # Native game-only engineer building brush: stock outposts and other previews
 # retain their original methods through the guarded C dispatchers.
 for loc,target,name in [(0x492408,0x11d95d,'bridge_preview_tick'),(0x492428,0xd6a13,'bridge_preview_accept'),(0x492448,0xd6b4f,'bridge_preview_valid')]:
  assert RAW[loc:loc+4]==struct.pack('<I',BASE+target)
  hooks.append(dict(site=loc,entry=exports[name],kind='pointer',before=RAW[loc:loc+4].hex()))
 # Both the order planner and the actual build ability check the worker's
 # roster. Resolving only the planner leaves workers walking to the bank
 # forever: cannot_build still rejects the length-specific native actor.
 for capability_site in (0x1d1434,0x6c459):
  assert RAW[capability_site:capability_site+5]==b'\xe8'+struct.pack('<i',0x2f397-capability_site-5)
  hooks.append(dict(site=capability_site,entry=exports['bridge_can_build'],kind='call',before=RAW[capability_site:capability_site+5].hex()))
 for work_site in (0x26f042,0x26f3d8,0x270f31,0x271b06,0x276e84):
  assert RAW[work_site:work_site+5]==b'\xe8'+struct.pack('<i',0x275a71-work_site-5)
  hooks.append(dict(site=work_site,entry=exports['bridge_work_range'],kind='call',before=RAW[work_site:work_site+5].hex()))
 for auto_site in (0x2731de,0x284479):
  assert RAW[auto_site:auto_site+6]==bytes.fromhex('ff90a4000000')
  hooks.append(dict(site=auto_site,entry=exports['bridge_auto_candidate'],kind='call',before=RAW[auto_site:auto_site+6].hex()))
 # Organization-level automatic target selection also feeds neutral rampage.
 # UI command validation and explicit attack-state checks keep the original.
 for loc in (0x2731f7,0x275eab):
  assert RAW[loc:loc+5]==b'\xe8'+struct.pack('<i',0x216535-loc-5)
  hooks.append(dict(site=loc,entry=exports['bridge_auto_organization'],kind='call',before=RAW[loc:loc+5].hex()))
 auto_site=0x27e975
 assert RAW[auto_site:auto_site+6]==bytes.fromhex('ff926c010000')
 hooks.append(dict(site=auto_site,entry=exports['bridge_auto_collision'],kind='call',before=RAW[auto_site:auto_site+6].hex()))
 # Preserve the native floor result, x87/SSE state, registers and native ABI.
 # Only the C filter's matching saved bridge footprint can raise a land query.
 off=wrapper+0xc00;addr=cave+off;roadstate=cave+state+0x300
 asm=f'''push ecx;push dword ptr [esp+12];push dword ptr [esp+12];call {BASE+0x2424d0};
 sub esp,4;fstp dword ptr [esp];pushfd;pushad;mov ebp,esp;
 sub esp,528;and esp,0xfffffff0;fxsave [esp];
 push dword ptr [ebp+36];push dword ptr [ebp+52];push dword ptr [ebp+48];push dword ptr [ebp+40];push {roadstate};
 call {cave+exports['bridge_floor']};add esp,20;mov [ebp+36],eax;
 fxrstor [esp];mov esp,ebp;popad;popfd;fld dword ptr [esp];add esp,8;ret 8;'''
 data=bytes(ks.asm(asm,addr)[0]);assert len(data)<0x180;code[off:off+len(data)]=data
 for ins in md.disasm(data,addr):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if op.imm==roadstate:fix.append((ins.address-cave+ins.imm_offset,0,1))
   if ins.mnemonic=='call' and op.imm==BASE+0x2424d0:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 # These are verified direct call sites; the native function itself stays intact.
 all_floor_sites=[i for i in range(0x44b000) if RAW[i]==0xe8 and i+5+struct.unpack_from('<i',RAW,i+1)[0]==0x2424d0]
 assert len(all_floor_sites)==57
 # Ground only actors/movers. Terrain and water mesh generation must read
 # the real river bed, otherwise the rendered river grows walls under a deck.
 floor_sites=[0x2033fb,0x203410,0x2131c2,0x213fc7,0x224478,0x23ad9a,0x23e0ed,0x23e895,0x23e8bf,0x23f12d]
 assert set(floor_sites)<=set(all_floor_sites)
 for site_floor in floor_sites:hooks.append(dict(site=site_floor,entry=off,kind='call',before=RAW[site_floor:site_floor+5].hex()))
 # VObjectDynamic recomputes its rendered land height using the view terrain,
 # independently of GThing's saved simulation Z. Cover that native call too.
 visual_off=wrapper+0xe00;visual_addr=cave+visual_off
 asm=f'''push ecx;push dword ptr [esp+12];push dword ptr [esp+12];call {BASE+0x2ea376};
 sub esp,4;fstp dword ptr [esp];pushfd;pushad;mov ebp,esp;
 sub esp,528;and esp,0xfffffff0;fxsave [esp];
 push dword ptr [ebp+4];push dword ptr [ebp+36];push dword ptr [ebp+52];push dword ptr [ebp+48];push dword ptr [ebp+40];push {roadstate};
 call {cave+exports['bridge_visual_floor']};add esp,24;mov [ebp+36],eax;
 fxrstor [esp];mov esp,ebp;popad;popfd;fld dword ptr [esp];add esp,8;ret 8;'''
 data=bytes(ks.asm(asm,visual_addr)[0]);assert len(data)<0x180;code[visual_off:visual_off+len(data)]=data
 for ins in md.disasm(data,visual_addr):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if op.imm==roadstate:fix.append((ins.address-cave+ins.imm_offset,0,1))
   if ins.mnemonic=='call' and op.imm==BASE+0x2ea376:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 for visual_site in (0x2e6fca,0x2e24fd):
  assert RAW[visual_site:visual_site+5]==b'\xe8'+struct.pack('<i',0x2ea376-visual_site-5)
  hooks.append(dict(site=visual_site,entry=visual_off,kind='call',before=RAW[visual_site:visual_site+5].hex()))
 # Destination marker uses the bridge deck height without treating arbitrary
 # caller registers as VObjects (the unit-height wrapper has a different ABI).
 marker_off=wrapper+0x1600;marker_addr=cave+marker_off
 asm=f'''push ecx;push dword ptr [esp+12];push dword ptr [esp+12];call {BASE+0x2ea376};
 sub esp,4;fstp dword ptr [esp];pushfd;pushad;mov ebp,esp;
 sub esp,528;and esp,0xfffffff0;fxsave [esp];
 push dword ptr [ebp+36];push dword ptr [ebp+52];push dword ptr [ebp+48];push dword ptr [ebp+40];push {roadstate};
 call {cave+exports['bridge_marker_floor']};add esp,20;mov [ebp+36],eax;
 fxrstor [esp];mov esp,ebp;popad;popfd;fld dword ptr [esp];add esp,8;ret 8;'''
 data=bytes(ks.asm(asm,marker_addr)[0]);assert len(data)<0x100;code[marker_off:marker_off+len(data)]=data
 for ins in md.disasm(data,marker_addr):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if op.imm==roadstate:fix.append((ins.address-cave+ins.imm_offset,0,1))
   if ins.mnemonic=='call' and op.imm==BASE+0x2ea376:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 marker_sites=[i for i in range(0x2ec00c,0x2ec090) if RAW[i]==0xe8 and i+5+struct.unpack_from('<i',RAW,i+1)[0]==0x2ea376]
 assert len(marker_sites)==1
 for loc in marker_sites:hooks.append(dict(site=loc,entry=marker_off,kind='call',before=RAW[loc:loc+5].hex()))
if a.installed:
 # Add native water polygons, then feather their native alpha before the
 # original bounds/cache update uploads vertex colors. Both wrappers retain
 # all native registers/FPU/SSE and the original callee's stack arguments.
 for water_site,water_target,water_export,water_off,water_arg in [
  (0x1b25de,0x1b29dc,'water_build_blended',wrapper+0x1c00,'build'),
  (0x1b2790,0x398e00,'water_blend_vertices',wrapper+0x1d00,'colors')]:
  assert water_off+0x100<=state
  assert all(abs(water_off-h['entry'])>=0x100 for h in hooks if wrapper<=h['entry']<state)
  assert RAW[water_site:water_site+5]==b'\xe8'+struct.pack('<i',water_target-water_site-5)
  if water_arg=='build':
   asm=f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push dword ptr [ebp+40];push ecx;push {cave+state};call {cave+exports[water_export]};add esp,12;mov [ebp+28],eax;fxrstor [esp];mov esp,ebp;popad;popfd;ret 4;'
  else:
   asm=f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push ebx;push {cave+state};call {cave+exports[water_export]};add esp,8;fxrstor [esp];mov esp,ebp;popad;popfd;jmp {BASE+water_target};'
  data=bytes(ks.asm(asm,cave+water_off)[0]);assert len(data)<0x100;code[water_off:water_off+len(data)]=data
  for ins in md.disasm(data,cave+water_off):
   for op in ins.operands:
    if op.type!=CS_OP_IMM:continue
    if op.imm==cave+state:fix.append((ins.address-cave+ins.imm_offset,0,1))
    if ins.mnemonic=='jmp' and op.imm==BASE+water_target:fix.append((ins.address-cave+ins.imm_offset,1,-1))
  hooks.append(dict(site=water_site,entry=water_off,kind='call',before=RAW[water_site:water_site+5].hex()))
if a.bridges:
 # One native SAI envelope queue call. Keep native ownership/bookkeeping and
 # reserve an AI bridge worker against new single-company travel/build orders.
 loc=0x1f2c0e;target=0x1f2c29;off=wrapper+0x1e00
 assert RAW[loc:loc+5]==b'\xe8'+struct.pack('<i',target-loc-5)
 restore='fxrstor [esp];mov esp,ebp;popad;popfd;'
 asm=f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push dword ptr [ebp+44];push dword ptr [ebp+24];call {cave+exports["bridge_ai_sai_block"]};add esp,8;test eax,eax;jnz blocked;'+restore+f'jmp {BASE+target};blocked:'+restore+'ret 8;'
 data=bytes(ks.asm(asm,cave+off)[0]);assert len(data)<0x100;code[off:off+len(data)]=data
 for ins in md.disasm(data,cave+off):
  for op in ins.operands:
   if op.type==CS_OP_IMM and ins.mnemonic=='jmp' and op.imm==BASE+target:fix.append((ins.address-cave+ins.imm_offset,1,-1))
 hooks.append(dict(site=loc,entry=off,kind='call',before=RAW[loc:loc+5].hex()))
if a.multiplayer:
 for loc in (0xd341e,0xd34c0,0xd3dc7,0x23d34c):
  assert RAW[loc:loc+5]==b'\xe8'+struct.pack('<i',0x22f651-loc-5)
  hooks.append(dict(site=loc,entry=exports['bridge_net_process'],kind='call',before=RAW[loc:loc+5].hex()))
(a.out/'prototype.bin').write_bytes(code)
(a.out/'prototype.json').write_text(json.dumps(dict(size=state+(524288 if a.bridges else 65536 if a.roads else 4096),state=state,uiState=state+256 if a.menu else 0,roadState=state+0x300 if a.roads else 0,bridges=a.bridges,installed=a.installed,multiplayer=a.multiplayer,styles=styles,entry=wrapper,adapter=adapter,hook=site,opcode=0xe8,before=RAW[site:site+5].hex(),fixups=fix,exports=exports,hooks=hooks),indent=2))
print('Built local prototype',len(code),'bytes; state',hex(state))
