"""Rebake only the transverse scale of already prepared native bridge meshes."""
from pathlib import Path
import argparse,hashlib,json,sys,time,numpy as np
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--width',type=float,default=6);a=p.parse_args()
sys.path.insert(0,str(a.models/'deps'));time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N
root=a.out/'sandbox/probe-data';manifest=json.loads((root/'bridge-model-manifest.json').read_text())
for name,row in manifest.items():
 if row['width']==a.width:continue
 scale=a.width/row['width'];axis=1 if '_x_' in name else 0;file=root/'Paws/Bridges'/name;data=N.Data()
 with file.open('rb') as f:data.read(f)
 for mesh in data.blocks:
  if not isinstance(mesh,N.NiTriBasedGeom):continue
  for vertex in mesh.data.vertices:
   if axis:vertex.y*=scale
   else:vertex.x*=scale
  if mesh.data.has_normals:
   for normal in mesh.data.normals:
    v=np.array([normal.x,normal.y,normal.z]);v[axis]/=scale;v/=max(np.linalg.norm(v),1e-12);normal.x,normal.y,normal.z=map(float,v)
  mesh.data.update_center_radius()
 with file.open('wb') as f:data.write(f)
 row['width']=a.width;row['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
(root/'bridge-model-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('BRIDGE_MODEL_WIDTH',a.width,len(manifest))
