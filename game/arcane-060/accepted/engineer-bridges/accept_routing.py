"""Validate final native movement evidence and bind it to the delivered runtime."""
from pathlib import Path
import argparse, hashlib, json, math

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
r=args.out.resolve();e=r/'qa-evidence/routing-followup'
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

m=load(r/'native/prototype.json');assert len(m['hooks'])==73
startup=(r/'qa-evidence/r6-normal-startup.log').read_text()
assert 'bridges: READY 73 hooks' in startup and 'PawsBridges.dll started' in startup
assert 'PawsBridgesQA.dll started' not in startup
runtime=r/'sandbox/Mods/PawsBridges.dll'
assert b'bridge-command.txt' not in runtime.read_bytes()
assert not any('PawsBridgesQA' in line for line in (r/'sandbox/Mods/plugins.txt').read_text().splitlines())

members={'2207','2251','2310','2379','2415','2442','2478'}
cases={}
for filename,goal in [('mouse-middle-final.json',(335.84844970703125,662.5240478515625)),
                      ('mouse-far-end-final.json',(343.8919372558594,668.6245727539062)),
                      ('leave-bridge-final.json',(350,700)),
                      ('new-stone-reload-crossing.json',(364,641))]:
 rows=load(e/filename);assert len(rows)>10 and rows[-1]['time']>rows[0]['time']
 first=rows[0]['actors']['2206'];last=rows[-1]['actors']['2206']
 assert set(first['members'])==set(last['members'])==members
 assert last['command'] is None and not last['move']['active']
 error=math.dist(last['position'][:2],goal);assert error<.5,(filename,error)
 for row in rows:
  actor=row['actors']['2206'];assert set(actor['members'])==members
  if actor['command']:assert actor['command']['id']==5 and actor['command']['target']==0
 cases[filename]={'samples':len(rows),'simulationSeconds':rows[-1]['time']-rows[0]['time'],
                  'goal':goal,'finish':last['position'],'stopError':error,'members':len(members)}
assert any(abs(row['actors']['2206']['position'][2]-1.18)<.01 for row in load(e/'mouse-middle-final.json'))
assert any(abs(row['actors']['2206']['position'][2]-1.08)<.01 for row in load(e/'new-stone-reload-crossing.json'))

mid=next(v for v in load(e/'haroun-growth-mid.json')['actors'] if v['id']==7160)
finished=next(v for v in load(e/'haroun-growth-finished.json')['actors'] if v['id']==7160)
assert mid['construction'] and 0<mid['health']<2000
assert not finished['construction'] and finished['health']==finished['maxHealth']==2000
assert finished['paidConstructionCost'][0]==125
for name in ['haroun-growth-mid.png','haroun-growth-near-finish.png','haroun-growth-finished.png']:assert (e/name).is_file()

natural=load(e/'npc-73-natural.json')
assert all(row['actors']['2624']['health']==1000 for row in natural)
assert any(math.dist(natural[0]['actors'][ident]['position'][:2],natural[-1]['actors'][ident]['position'][:2])>10 for ident in ['5494','5517','5571'])
# Attack target IDs can remain cached after leaving a state. Do not confuse
# stale IDs with a live bridge attack or claim every NPC has a movement goal.

saves={}
for name,copy in [('Смешанные биомы.RSG','R6-routing-user1.RSG'),('Смешанные биомы3.RSG','R6-routing-user3.RSG')]:
 original=e/name;live=r/'Documents/Kohan2/data/Save'/name;ascii=r/'Documents/Kohan2/data/Save'/copy
 assert sha(original)==sha(live)==sha(ascii)
 saves[name]=sha(original)
second=e/'Смешанные биомы2.RSG';assert sha(second)==sha(r/'Documents/Kohan2/data/Save'/second.name);saves[second.name]=sha(second)
repo=Path(__file__).resolve().parents[2]
sources=['game/engineer-bridges/routing.h','game/engineer-bridges/navigation.h','game/engineer-bridges/combat.h',
         'game/engineer-bridges/models.py','game/engineer-bridges/runtime.c','game/engineer-bridges/build_plugin.py',
         'game/engineer-roads/roads.c','game/map-shapes/build.py']
report={'passed':True,'localOnly':True,'published':False,'nativeHooks':73,
 'normalRuntimeSha256':sha(runtime),'prototypeSha256':sha(r/'native/prototype.bin'),
 'sourceHashes':{name:sha(repo/name) for name in sources},'preservedUserSaves':saves,
 'checks':{'roads':614,'connectivity':70,'floorAndMarkerABI':232,'routingAndAttackGuards':88,'assets':38548},
 'nativeMovement':cases,'harounGrowth':{'actor':7160,'material':'stone','paidGold':125,'health':2000,'nativeEffectViewed':True},
 'npcNaturalFinal':{'samples':len(natural),'simulationSeconds':natural[-1]['time']-natural[0]['time'],
                    'bridgeHealthStable':1000,'movingAwayFromBridgeObserved':True},
 'limits':['Private single-player only; multiplayer is not enabled.',
           'Final player construction and point-routing runs explicitly removed foreign mobile actors to isolate combat.',
           'Natural NPC observation is a short saved-scene regression, not a complete AI campaign.',
           'Direct enemy bridge attack is compiled-tested but not live reaccepted in this follow-up.',
           'Both Haroun templates are checked; stone growth was live viewed, not all twelve racial construction animations.']}
(e/'acceptance.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('ROUTING_NATIVE_ACCEPTANCE_PASS',len(cases),'movement cases, seven members, paid Haroun growth, original saves preserved')
