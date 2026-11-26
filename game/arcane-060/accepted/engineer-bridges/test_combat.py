"""Prepared compiled-ABI regressions for bridge acquisition and prototypes.
Run only after the shared slot is released and the payload is rebuilt.
"""
from pathlib import Path
scope={'__file__':str(Path(__file__).with_name('test_ai.py')),'__name__':'bridge_fixture'}
exec(compile(Path(scope['__file__']).read_text().split('\nfor image,cave in ')[0],scope['__file__'],'exec'),scope)
Fixture=scope['Fixture'];BASE=scope['BASE'];m=scope['m'];checks=[]
def check(name,value):
 assert value,name
 checks.append(name)
# These verified native byte facts establish ABI/offsets independently of mocks.
# They come from the pinned 1.3.72 RAW image used by the actual hook builder.
for offset,expected in [(2592720, '8b41048b4004c3'), (2628008, '8b4e10'), (2629341, '8b5310'), (2630334, '8b4214894110'), (2370467, '8b4704'), (2371560, '8b4f04'), (2627850, 'c20800'), (2628981, 'c20800'), (2371435, 'c20400'), (2372106, 'c20400'), (2672218, 'c21400')]:
 check('pinned native ABI '+hex(offset),scope['RAW'][offset:offset+len(bytes.fromhex(expected))]==bytes.fromhex(expected))
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 f=Fixture(image,cave);u=f.u;events=[];suffix=hex(image)
 source=f.other;target=f.danger;mind=0x20710000;cmd=0x20711000;kill=0x20712000;bombard=0x20713000;context=0x20715000
 f.w(source+0x70,mind);f.w(source+0x7c,0);f.w(source+0x80,0);f.w(mind+4,source);f.w(mind+0x20,0)
 for state in [kill,bombard]:f.w(state+4,mind);f.w(state+0x10,300)
 f.make_actor(target,300,f.enemy,100,100)
 def native(uc,at,size,_):
  sp=uc.reg_read(scope['UC_X86_REG_ESP']);obj=uc.reg_read(scope['UC_X86_REG_ECX']);off=at-image;clean=0;ret=41
  if off in [0x281899,0x281c95]:events.append(('activate',off,obj,f.r(sp+4),f.r(sp+8)));clean=8
  elif off in [0x281915,0x281e76]:events.append(('deactivate',off,obj));f.w(obj+12,0);f.w(obj+16,0)
  elif off in [0x281928,0x281ec6]:events.append(('tick',off,obj))
  elif off in [0x242eee,0x242fcd]:events.append(('create',off,obj,f.r(sp+4)));clean=4;ret=43
  elif off==0x28c365:events.append(('construct-request',obj,tuple(f.r(sp+4+i*4)for i in range(5))));clean=20;ret=44
  elif off==0x2f397:events.append(('capability',obj,f.r(sp+4)));clean=4;ret=1
  uc.reg_write(scope['UC_X86_REG_EAX'],ret);uc.reg_write(scope['UC_X86_REG_ESP'],sp+4+clean);uc.reg_write(scope['UC_X86_REG_EIP'],f.r(sp))
 for off in [0x281899,0x281c95,0x281915,0x281e76,0x281928,0x281ec6,0x242eee,0x242fcd,0x2f397,0x28c365]:u.hook_add(scope['UC_HOOK_CODE'],native,begin=image+off,end=image+off)
 def order(actor,target_id):
  ai=f.r(actor+0x70);f.w(ai+0x20,cmd);f.w(cmd+8,f.definition('attack'));f.w(f.r(cmd+8)+12,0);f.w(cmd+12,1);f.w(cmd+16,target_id)
 for definition in ['paws_bridge_site','paws_bridge_wood_site','paws_bridge_stone_site',*[f'paws_bridge_{race}_{material}_site'for race in ['undead','shadow','human','gauri','drauga','haroun']for material in ['wood','stone']],'paws_bridge_drauga_wood_y_15','paws_bridge_human_stone_x_32']:
  f.w(target+4,f.definition(definition));check('bridge target '+definition+' '+suffix,f.call('bridge_combat_target_check',[target])==1)
 f.w(target+4,f.definition('normal_outpost'));check('ordinary structure classification '+suffix,f.call('bridge_combat_target_check',[target])==0)
 for definition in ['paws_bridge_drauga_wood_site','paws_bridge_human_stone_y_16']:
  f.w(target+4,f.definition(definition));f.w(mind+0x20,0);f.w(source+0x80,0)
  for export,state,original,stop,tick in [('bridge_unit_attack_activate',kill,0x281899,0x281915,'bridge_unit_attack_tick'),('bridge_unit_bombard_activate',bombard,0x281c95,0x281e76,'bridge_unit_bombard_tick')]:
   before=len(events);check('ungrouped automatic activation rejected '+definition+' '+export+' '+suffix,f.call(export,[0,target],selfptr=state)==0 and len(events)==before)
   f.w(state+12,2);f.w(state+16,300);f.call(tick,[],selfptr=state)
   check('saved automatic state fully deactivated '+export+' '+suffix,events[-1]==('deactivate',stop,state) and f.r(state+12)==0 and f.r(state+16)==0)
   order(source,300);check('explicit own unit order retained '+export+' '+suffix,f.call(export,[2,target],selfptr=state)==41 and events[-1]==('activate',original,state,2,target))
   f.w(state+12,2);f.w(state+16,300);f.call(tick,[],selfptr=state);check('explicit saved unit state retained '+export+' '+suffix,events[-1][0]=='tick' and f.r(state+12)==2)
   order(source,999);before=len(events);check('different explicit target does not authorize bridge '+export+' '+suffix,f.call(export,[0,target],selfptr=state)==0 and len(events)==before)
   f.w(mind+0x20,0);element=0x20714000;f.w(source+0x80,element);f.w(element+16,f.army);order(f.army,300)
   check('parent company explicit order retained '+export+' '+suffix,f.call(export,[2,target],selfptr=state)==41)
   f.w(source+0x80,0);f.w(f.r(f.army+0x70)+0x20,0);f.w(target+4,f.definition('ordinary_enemy'));before=len(events)
   check('ordinary enemies and retaliation remain native '+export+' '+suffix,f.call(export,[0,target],selfptr=state)==41 and len(events)==before+1)
   f.w(target+4,f.definition(definition))
 # The real native construct request must be stopped BEFORE its foundation
 # spawn, preserving its fifth argument, callee cleanup and ordinary forwarding.
 for definition in ['paws_bridge_site','paws_bridge_drauga_wood_site','paws_bridge_haroun_stone_site']:
  request=[f.definition(definition),f.kingdom,context+32,context+40,context+48];before=len(events)
  check('early prototype request rejected before foundation/work '+definition+' '+suffix,f.call('bridge_construct_request',request,selfptr=f.world)==0 and len(events)==before)
  check('rejected construct request preserves RET20 ABI '+suffix,u.reg_read(scope['UC_X86_REG_ESP'])==0x3000f018)
 for definition in ['paws_bridge_drauga_wood_y_15','human_outpost']:
  request=[f.definition(definition),f.kingdom,context+32,context+40,context+48]
  check('ordinary/full-count construct request forwards all five args '+definition+' '+suffix,f.call('bridge_construct_request',request,selfptr=f.world)==44 and events[-1]==('construct-request',f.world,tuple(request)))
  check('forwarded construct request preserves RET20 ABI '+suffix,u.reg_read(scope['UC_X86_REG_ESP'])==0x3000f018)
 check('verified early construct entry installed '+suffix,any(h['site']==0x289f69 and h['entry']==m['exports']['bridge_construct_request']for h in m['hooks']))
 # The guard runs at commit, not at the human capability/menu check.
 for export,original in [('bridge_builder_spawn',0x242eee),('bridge_builder_spawn_alternate',0x242fcd)]:
  f.w(context+4,f.definition('paws_bridge_drauga_wood_site'));before=len(events)
  check('prototype spawn rejected without native creation/payment '+export+' '+suffix,f.call(export,[context],selfptr=f.world)==0 and len(events)==before)
  check('human catalogue capability preserved '+export+' '+suffix,f.call('bridge_can_build',[context+4],selfptr=0x20716000)==1)
  for definition in ['paws_bridge_drauga_wood_y_15','human_outpost','normal_summoned_creature']:
   f.w(context+4,f.definition(definition));check('real actor forwarded '+definition+' '+export+' '+suffix,f.call(export,[context],selfptr=f.world)==43 and events[-1]==('create',original,f.world,context))
 for loc,export in [(0x1fd049,'bridge_builder_spawn_alternate'),(0x1fd050,'bridge_builder_spawn'),(0x28c332,'bridge_builder_spawn_alternate'),(0x28c339,'bridge_builder_spawn'),(0x4f6ea4,'bridge_unit_attack_tick'),(0x4f6ed0,'bridge_unit_bombard_tick')]:
  check('native hook installed '+hex(loc)+' '+suffix,any(h['site']==loc and h['entry']==m['exports'][export]for h in m['hooks']))
# Work follows its own native state (RTTI UAIStateRepair), not Kill/Bombard.
# Keep the compiled hook manifest off these activation and lifecycle sites.
for location in [0x284e0a,0x4f6f28,0x4f6f34,0x4f6f38]:
 check('typed native repair/construction remains unhooked '+hex(location),not any(h['site']==location for h in m['hooks']))
for location,target in [(0x4f6f28,0x282988),(0x4f6f34,0x282913),(0x4f6f38,0x282971)]:
 check('pinned separate native work state '+hex(location),scope['struct'].unpack_from('<I',scope['RAW'],location)[0]==BASE+target)
print('BRIDGE_COMBAT_PASS',len(checks),'compiled policy/ABI checks across two relocations')
(scope['args'].out/'combat-result.json').write_text(scope['json'].dumps({'passed':True,'checks':checks,'liveGame':False,'networkPeers':False},indent=2))
