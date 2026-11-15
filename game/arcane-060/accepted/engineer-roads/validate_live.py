"""Verify retained read-only snapshots of the drag-road native experiment."""
import argparse,json,hashlib,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.out
def rows(name):return json.loads((root/(name+'.json')).read_text())
before=rows('before-road')[0];saved=rows('before-save')[0];loaded=rows('after-load')[0]
assert saved['terrain']==loaded['terrain']
assert saved['heights']==loaded['heights'] and before['heights']==saved['heights']
assert before['base_heights_sha256']==saved['base_heights_sha256']==loaded['base_heights_sha256']
pairs=list(zip(before['terrain']['cells'],saved['terrain']['cells']))
changed=sum(b!=s for b,s in pairs);blocked_changed=sum(b!=s for b,s in pairs if b[1]&0x100)
assert changed>0 and blocked_changed==0
build=rows('drag-build');job=build[0]['roads']['jobs'][0]
footprint=set();width=before['map']['width']
for point in job['points'][:job['count']]:
 x=point&65535;y=point>>16
 footprint.update(yy*width+xx for yy in range(y-1,y+2) for xx in range(x-1,x+2))
actual={i for i,(b,s) in enumerate(pairs) if b!=s}
assert actual==footprint
assert build[-1]['roads']['header'][7]==0 and not build[-1]['roads']['jobs']
assert len({r['roads']['header'][6] for r in build})>1
ordinary=rows('cancelled-road');counts={r['roads']['header'][6] for r in ordinary}
assert len(counts)==1 and all(not r['roads']['jobs'] for r in ordinary)
positions=[next(c for c in r['actors'] if c['id']==432) for r in ordinary]
distance=math.hypot(positions[-1]['x']-positions[0]['x'],positions[-1]['y']-positions[0]['y'])
assert distance>1
speeds=sorted({round(c['company_speed'],2) for r in build+ordinary for c in r['actors'] if c['id']==432})
assert 2.25 in speeds and 2.85 in speeds
assert not loaded['roads']['jobs']
assert ordinary[-1]['terrain']['counts']['paws_engineer_road01']>loaded['terrain']['counts']['paws_engineer_road01']
files=['PawsRoadsTest.exe','native/prototype.bin','native/prototype.json','sandbox/Userdata/Save/Engineers-ready.RSG','sandbox/Userdata/Save/Drag-road-built.RSG','road-in-game.png']
report=dict(date='2026-10-12',scope='Local single-player drag-road prototype; no production install or publication',
 automated=dict(road=82,assets=43,generator=256,menu=312,total=693),
 live=dict(engineerCompanyId=432,plannedPoints=job['count'],changedTerrainCells=changed,
  changedCellsExactlyMatchPlan=True,gradualConstruction=True,changedBlockedCells=blocked_changed,
  heightsUnchanged=True,saveLoadTerrainExact=True,saveLoadHeightExact=True,companySpeeds=speeds,
  ordinaryMovementDistance=distance,ordinaryMovementPaintCount=list(counts)[0],constructionAfterReload=True),
 limitations=['Single-player only; no bridge construction, AI road planning, multiplayer/replay support, costs or work animation.',
  'Straight segments only; completed terrain persists, active tasks do not.',
  'Prototype supports maps up to 1024 world units; live fixture is 192 by 192.',
  'Active-task cancellation is covered by compiled tests; short live segments completed before the sampled right-click.',
  'Native texture was visually checked in temperate climate only.'],
 files={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files})
(root/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['live'],indent=2))
