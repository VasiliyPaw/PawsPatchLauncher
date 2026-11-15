"""Verify the actual installed-candidate bridge definitions and reviewed assets."""
from pathlib import Path
import argparse,hashlib,io,json,re,sys,time
import numpy as np
from models import definitions, bridge_balance

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--style',choices=['shadow','undead','human','gauri','drauga','haroun']);p.add_argument('--sample',action='store_true');a=p.parse_args()
root=a.out.resolve();art=json.loads((root/'bridge-art.json').read_text());checks=0
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'outputs/bridge-model-ee2-20261109/deps'))
time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

for language in ('en','ru','uk','de','fr','cs'):
 text=definitions(language,art['styles'])
 blocks=re.split(r'\[Thing Template=PawsBridge(?:Haroun)?\]',text)[1:]
 ids=[re.search(r'IDS = (\w+)',b)[1] for b in blocks]
 assert len(ids)==len(set(ids))==115+114*len(art['styles']);checks+=1
 if 'haroun' in art['styles']:
  base=text.split('[Template PawsBridgeHaroun Template=K2Structure]')[1].split('[Thing')[0]
  assert 'VFX_IDS = normal_construction_raise_vfx' in base
  assert text.count('VFX_IDS = paws_bridge_haroun_growth_')==224 and text.count('VFX_IDS = paws_bridge_haroun_finish_')==112
  assert text.count('[WhenLeave Template=FXC_StopVFX]')==112
  assert 'construction_smoke_vfx' not in base and 'paws_bridge_construction_raise_vfx' not in base;checks+=2
 for block,ident in zip(blocks,ids):
  if ident=='paws_bridge_site':continue
  wood='_wood_' in ident
  style=next((s for s in art['styles'] if ident.startswith('paws_bridge_'+s+'_')),'')
  hp,gold,resource,amount=bridge_balance(style,'wood' if wood else 'stone')
  assert re.search(r'health = '+str(hp)+r'\b',block);checks+=1
  assert re.search(r'\[Cost\]\s+gold = '+str(gold)+r'\b',block);checks+=1
  assert re.search(r'\[Upkeep\]\s+'+resource+r' = '+str(amount)+r'\b',block);checks+=1
  description=re.search(r'description = "([^"]*)"',block)[1]
  assert not any(c.isdigit() for c in description);checks+=1
  if not ident.endswith('_site'):
   material,axis,count=ident.rsplit('_',3)[-3:];length=(int(count)-1)*2
   assert 'rect_width = '+str(length if axis=='x' else 6)+'\n' in block;checks+=1
   assert 'rect_height = '+str(6 if axis=='x' else length)+'\n' in block;checks+=1

base=root/'sandbox/rivers-data/Paws/Bridges';nif_models=0;hashed_models=0
for style,manifest in [('',art['core']['variants']),*art['styles'].items()]:
 if a.style and style!=a.style:continue
 folder=base/(style.title() if style else '')
 for name,row in manifest.items():
  path=folder/name;assert sha(path)==row['sha256'];checks+=1;hashed_models+=1
  if a.sample and int(path.stem.split('_')[-1]) not in (5,13,32):continue
  nif_models+=1
  model=N.Data();model.read(io.BytesIO(path.read_bytes()));assert model.version==0x0A010000;checks+=1
  if (root/'bridge-outline-installed.json').exists():
   for kind in ('Selected','Focused'):
    frames=[b for b in model.blocks if isinstance(b,N.NiNode) and bytes(b.name)==('PawsBridge'+kind).encode()]
    assert len(frames)==1 and frames[0] in model.roots[0].children and int(frames[0].flags)==16;checks+=1
    assert len(frames[0].children)==1 and isinstance(frames[0].children[0],N.NiTriShape);checks+=1
    mesh=frames[0].children[0];assert mesh.data.num_vertices==32 and mesh.data.num_triangles==32;checks+=1
    assert all(abs(v.z-.24)<1e-5 for v in mesh.data.vertices);checks+=1
  depths=[b for b in model.blocks if isinstance(b,N.NiZBufferProperty)]
  assert depths and all(int(b.flags)&3==3 and int(b.function)==3 for b in depths);checks+=1
  boxes=[b for b in model.blocks if isinstance(b,N.NiTriBasedGeom) and bytes(b.name)==b'SelectionBox']
  assert len(boxes)==1 and int(boxes[0].flags)==17;checks+=1
  box=boxes[0];assert box in model.roots[0].children;checks+=1
  material,axis,count=path.stem.split('_');length=(int(count)-1)*2
  vertices=np.array([[v.x,v.y,v.z,1.] for v in box.data.vertices])@np.array(box.get_transform().as_list())
  assert np.allclose(np.ptp(vertices[:,:3],axis=0),[length if axis=='x' else 6,6 if axis=='x' else length,.3],atol=1e-4);checks+=1
  assert abs(vertices[:,2].min()-(.1 if material=='wood' else 0)+.12)<1e-4;checks+=1
  for b in model.blocks:
   if isinstance(b,N.NiSourceTexture) and b.use_external:
    file=bytes(b.file_name).decode().replace('\\','/').split('/')[-1]
    assert (folder/file).is_file(),(path,file);checks+=1
  if style:assert row['visualRadiusEstimate']>=length/2;checks+=1
 for name,row in art['sources'].get(style,{}).get('textures',{}).items():
  assert sha(folder/name)==row['sha256'];checks+=1

report={'passed':True,'checks':checks,'models':hashed_models,'nifModels':nif_models,'sampledGeometry':a.sample,'definitions':115+114*len(art['styles']),'languages':6,'styles':[a.style] if a.style else list(art['styles'])}
(root/f'qa-evidence/{"r7" if a.sample else "r5"}-assets{"-"+a.style if a.style else ""}.json').write_text(json.dumps(report,indent=2))
print(checks,'PASS: prices, upkeep, six languages, race assets, textures and precise hidden selection boxes')
