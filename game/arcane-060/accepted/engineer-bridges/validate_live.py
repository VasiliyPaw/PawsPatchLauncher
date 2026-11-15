"""Validate retained native observations; no attachment, commands or game writes."""
from pathlib import Path
import argparse,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.out;e=root/'qa-evidence'
def read(name):return json.loads((e/name).read_text())
def company(row):return next(x for x in row['actors'] if x['id']==432)
def amount(row,nation,resource):
 kingdom=next(k for k in row['kingdoms'] if k['nation']==nation)
 return kingdom['upkeep'][row['resources'].index(resource)]
members=set(range(433,440));traces={}
for name,side,center in [('wood-crossing.json','right',95),('wood-after-restart-crossing.json','left',95),('stone-crossing.json','right',111)]:
 rows=read(name);last=company(rows[-1])['elements'];assert {u['id'] for u in last}==members
 assert all(u['x']>122 if side=='right' else u['x']<110 for u in last)
 wet=[u for row in rows for u in company(row)['elements'] if 110<=u['x']<=122]
 assert {u['id'] for u in wet}==members
 assert all(abs(u['z']-2.08)<.001 and abs(u['y']-center)<3 for u in wet)
 traces[name]=dict(members=7,deckHeight=2.08,waterSamples=len(wet),destination=side)
wood=read('wood-built.json');restored=read('wood-restored-stone-built.json');both=read('both-after-final-restart.json')
assert wood['completed']>=1 and wood['built']==1 and not wood['failed']
assert amount(wood,'haroun','wood')==amount(restored,'haroun','wood')==amount(both,'haroun','wood')==10
assert amount(restored,'drauga','stone')==amount(both,'drauga','stone')==10
assert amount(both,'haroun','stone')==6 and amount(both,'drauga','wood')==0
bridges=[x for x in both['actors'] if x['name'].startswith('paws_bridge_')]
assert sorted(x['name'] for x in bridges)==['paws_bridge_stone_x_13','paws_bridge_wood_x_13']
assert all(abs(x['z']-2.08)<.001 and x['economy'] for x in bridges)
baseline=read('ready-world-baseline.json');built_world=read('both-world-before-restart.json');loaded_world=read('both-world-after-final-restart.json')
assert baseline['heights']==built_world['heights']==loaded_world['heights']
assert not baseline['bridgeCells'] and len(built_world['bridgeCells'])==len(loaded_world['bridgeCells'])==36
for snapshot in (built_world,loaded_world):
 assert all(not(c['flags']&0x100) and c['waterBody'] for c in snapshot['bridgeCells'])
def terrain_contract(snapshot):return [(c['x'],c['y'],c['flags']&0x331) for c in snapshot['bridgeCells']]
assert terrain_contract(built_world)==terrain_contract(loaded_world)
files=['PawsBridgesTest.exe','native/prototype.bin','native/prototype.json','sandbox/Mods/PawsBridges.dll','sandbox/Userdata/Save/Bridges-models-built.RSG','bridges-in-game.png']
report=dict(date='2026-11-09',scope='Private stock 1.3.72 SP model prototype; no publication or installation changes',
 automated=dict(nativeJobs=176,floorAbi=56,assets=1840,generator=256,menu=312,total=2640),
 live=dict(woodBuiltThroughEngineerJob=True,stoneNativeObjectAndEconomy=True,woodUpkeep=10,stoneUpkeep=10,
 upkeepAppliedOnceAfterRestart=True,modelActorsAndDeckHeightPersist=True,terrainBaseAndDeformationUnchanged=True,
 animatedWaterBodiesPresent=True,passableBridgeCells=36,crossings=traces),
 limitations=['Single-player only; straight narrow crossings and nearby bank heights.',
 'No demolition, destruction, repair, AI building, multiplayer or replay commands.',
 'Finished objects/terrain/upkeep persist; unfinished jobs are cancelled on load.',
 'Live engineer job used the retained Haroun-owned human-engineer fixture; six worker IDs/race routing also have emitted-code checks.',
 'Stone object/economy used the QA native factory for a real Drauga kingdom; a full manual job for each remaining race was not played.'],
 files={str(f):hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files})
(root/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BRIDGES_LIVE_PASS',json.dumps(report['live'],ensure_ascii=False))
