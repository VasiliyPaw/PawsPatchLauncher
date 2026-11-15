"""Validate captured native terrain and placement; never control a live game."""
import argparse, json, collections, math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);a=p.parse_args()
j=json.loads(a.snapshot.read_text())[0];w=j['map']['width'];h=j['map']['height']
cells=j['terrain']['cells'];labels=[-1]*len(cells);groups=[]
for start,(_,flags) in enumerate(cells):
 if labels[start]>=0 or flags&0x100:continue
 index=len(groups);q=[start];labels[start]=index
 for i in q:
  for k in (i-1 if i%w else -1,i+1 if i%w+1<w else -1,i-w,i+w):
   if 0<=k<len(cells) and labels[k]<0 and not cells[k][1]&0x100:
    labels[k]=index;q.append(k)
 groups.append(len(q))
largest=max(range(len(groups)),key=lambda k:groups[k]);important=[]
for actor in j['actors']:
 name=actor['ids']
 if not (name=='start_loc' or name.startswith(('marker_','lair_','tech_lair_','artifact_')) or '_center_' in name or '_settlementcamp' in name):continue
 x=int(actor['x']/2);y=int(actor['y']/2)
 # Static structures block their own footprint. Test a reachable perimeter
 # within 8 cells and record the exact nearest distance, instead of treating
 # their occupied center as a terrain failure.
 distance=min((math.hypot(dx,dy) for dy in range(-8,9) for dx in range(-8,9)
  if 0<=x+dx<w and 0<=y+dy<h and labels[(y+dy)*w+x+dx]==largest),default=None)
 important.append(dict(ids=name,x=actor['x'],y=actor['y'],distance_cells=distance))
result=dict(map=j['map'],seed=j.get('probe',[0]*6)[5],largest_walkable=groups[largest],
 walkable_total=sum(groups),components=sorted(groups,reverse=True),important=important,
 all_important_reachable=all(o['distance_cells'] is not None for o in important),
 terrain_sha256=j['terrain']['sha256'],heights=j.get('heights'))
a.snapshot.with_suffix('.check.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('important','components')},indent=2))
print('Important objects:',len(important),'components:',sorted(groups,reverse=True)[:20])
assert result['all_important_reachable']
