"""Add hidden depth-tested deck contours to private model instances."""
from pathlib import Path
import argparse,hashlib,json,sys,time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.out.resolve()
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'outputs/bridge-model-ee2-20261109/deps'));time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N
root=r/'sandbox/rivers-data/Paws/Bridges';report={};art=json.loads((r/'bridge-art.json').read_text())
for path in [*root.glob('*_[xy]_??.nif'),*(v for folder in art['styles'] for v in (root/folder.title()).glob('*_[xy]_??.nif'))]:
 data=N.Data()
 with path.open('rb') as f:data.read(f)
 existing={bytes(b.name) for b in data.get_global_iterator() if isinstance(b,N.NiAVObject)}
 axis,count=path.stem.split('_')[-2:];before=hashlib.sha256(path.read_bytes()).hexdigest()
 for kind in ('selected','focused'):
  name=('PawsBridge'+kind.title()).encode()
  if name in existing:continue
  outline=N.Data()
  with (root/'Selection'/f'{kind}_{axis}_{count}.nif').open('rb') as f:outline.read(f)
  node=outline.roots[0];node.name=name;node.flags=16
  style=path.parent.name.lower() if path.parent!=root else 'core';material=path.stem.split('_')[0]
  key=['core','undead','shadow','human','gauri','drauga','haroun'].index(style)*112+(56 if material=='stone' else 0)+(28 if axis=='y' else 0)+int(count)-5
  node.children[0].name=f'B{key:03X}{"Sel" if kind=="selected" else "Foc"}Quad'.encode()
  data.roots[0].add_child(node)
 with path.open('wb') as f:data.write(f)
 after=hashlib.sha256(path.read_bytes()).hexdigest();report[str(path.relative_to(root))]={'sourceSha256':before,'sha256':after,'hidden':False,'runtimeVisibility':True,'depthTest':True,'depthWrite':True,'selectionPlaneZ':.24}
 if path.parent!=root:
  row=art['styles'][path.parent.name.lower()][path.name];row['sha256']=after;row['depthState']['sha256']=after;row['outline']=report[str(path.relative_to(root))]
 else:
  art['core']['variants'][path.name]['outline']=report[path.name]
  art['core']['variants'][path.name]['sha256']=after
assert len(report)==784
(r/'bridge-art.json').write_text(json.dumps(art,indent=2));(r/'bridge-outline-installed.json').write_text(json.dumps({'passed':True,'variants':report},indent=2))
print('BRIDGE_MODEL_OUTLINES_READY',len(report))
