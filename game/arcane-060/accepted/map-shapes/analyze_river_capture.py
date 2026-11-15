"""Independently check native captured river cells and absolute bed vertices."""
from pathlib import Path
import argparse,json,collections
import numpy as np

p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
s=json.loads(a.capture.read_text())[-1];w=s['map']['width'];h=s['map']['height']
plan=np.frombuffer(a.capture.with_suffix('.plan.bin').read_bytes(),dtype=np.uint8).reshape(h,w)>0
cells=s['terrain']['cells'];flags=np.array([c[1] for c in cells]).reshape(h,w)
dry=plan&(((flags&0x70)!=0x20)|((flags&0x100)==0))
hm=s['heights'];assert hm['shift']==1 and hm['pad']==1 and hm['width']==w+1 and hm['height']==h+1
heights=np.frombuffer(a.capture.with_suffix('.heights.bin').read_bytes(),dtype='<f4').reshape(h+1,w+1)
affected=np.zeros((h+1,w+1),dtype=bool)
for dy,dx in [(0,0),(0,1),(1,0),(1,1)]:affected[dy:dy+h,dx:dx+w]|=plan
above=affected&(heights>0.0001)
biomes=collections.Counter(c[0].split('_')[2] if c[0].startswith('paws_river_') else c[0].split('_')[0] for i,c in enumerate(cells) if plan.flat[i])
report=dict(seed=s['probe'][5],width=w*2,height=h*2,rivers=s['probe'][16],riverCells=int(plan.sum()),
 dryOrWalkableRiverCells=int(dry.sum()),aboveWaterRiverVertices=int(above.sum()),checkedBedVertices=int(affected.sum()),
 highestRiverVertex=float(heights[affected].max()),biomes=dict(biomes),generatorResult=s['probe'][8],generatorPhase=s['probe'][13])
assert report['riverCells']==s['probe'][17] and report['generatorResult']==0 and report['generatorPhase']==5
assert not report['dryOrWalkableRiverCells'] and not report['aboveWaterRiverVertices'],report
a.capture.with_suffix('.analysis.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
