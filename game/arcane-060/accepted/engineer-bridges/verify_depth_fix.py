"""Prove all racial art differs only at explicit depth-comparison uint32s."""
from pathlib import Path
import argparse,hashlib,json,struct

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=a.out.resolve();inputs=json.loads((r/'bridge-art-inputs.json').read_text());art=json.loads((r/'bridge-art.json').read_text())
old=json.loads((r/'qa-evidence/r5-art-before-depth.json').read_text());checks=0;properties=0;corrected=0
assert art['core']==old['core'];checks+=1
for style,rows in art['styles'].items():
 for name,row in rows.items():
  source=Path(inputs[style+'Selection'])/name if style+'Selection' in inputs else Path(inputs[style])/'Paws/Bridges'/style.title()/name
  original=source.read_bytes();actual=(r/'sandbox/rivers-data/Paws/Bridges'/style.title()/name).read_bytes()
  assert hashlib.sha256(original).hexdigest()==row['sourceArtSha256'];checks+=1
  depth=row['depthState'];expected=bytearray(original)
  for offset in depth['comparisonOffsets']:struct.pack_into('<I',expected,offset,3)
  assert actual==bytes(expected) and len(actual)==len(original);checks+=1
  assert hashlib.sha256(actual).hexdigest()==row['sha256']==depth['sha256'];checks+=1
  assert depth['comparison']=='LESS_EQUAL' and depth['depthWrite'] and depth['depthTest'];checks+=1
  properties+=depth['properties'];corrected+=depth['corrected']
report=dict(passed=True,checks=checks,models=sum(map(len,art['styles'].values())),properties=properties,corrected=corrected,
            onlyDepthComparisonFieldsChanged=True,geometryTexturesMaterialsAndSelectionUnchanged=True)
(r/'qa-evidence/r5-depth-bytes.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
