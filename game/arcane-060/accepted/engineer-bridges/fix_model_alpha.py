"""Update only imported alpha-pass flags in an existing private model set."""
from pathlib import Path
import argparse,sys,time,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--models',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.models/'deps'));time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N
root=a.out/'sandbox/probe-data';manifest=json.loads((root/'bridge-model-manifest.json').read_text());changed=0
for name,row in manifest.items():
 path=root/'Paws/Bridges'/name;data=N.Data()
 with path.open('rb') as f:data.read(f)
 touched=False
 for b in data.blocks:
  if isinstance(b,N.NiAlphaProperty) and int(b.flags)&1:b.flags=int(b.flags)&~1;touched=True
 if touched:
  with path.open('wb') as f:data.write(f)
  changed+=1
 row['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
(root/'bridge-model-manifest.json').write_text(json.dumps(manifest,indent=2))
print('BRIDGE_ALPHA_PASS_UPDATED',changed)
