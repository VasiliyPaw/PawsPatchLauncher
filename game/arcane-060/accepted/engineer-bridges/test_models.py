"""Check native bridge definitions, fixed upkeep, model dependencies and locales."""
from pathlib import Path
import argparse,re,json,hashlib,sys,time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--models',type=Path,required=True);a=p.parse_args()
checks=0
for lang in ('en','ru','de','fr','cs','uk'):
 root=a.out/'locales'/lang
 ui=(root/'UI/Game/game_interface.tgi').read_text(encoding='utf-16')
 assert '[PawBridgeButton' not in ui and ui.count('[PawRoadButton')==1;checks+=1
 terrain=(root/'Terrain/Temperate/temperate_road.tgi').read_text(encoding='utf-16')
 bridge=terrain[terrain.index('IDS = paws_engineer_bridge'):]
 assert 'land = true' in bridge and 'water = true' in bridge and 'WaterFrames%04d.dds' in bridge;checks+=1
 actors=(root/'Special/Things/thing_visibilityactors.tgi').read_text(encoding='utf-16')
 ids=re.findall(r'(?m)^\s*IDS = (paws_bridge_\w+)',actors)
 assert len(ids)==len(set(ids))==115;checks+=1
 for worker in ['Units/Human/engineer.tgi','Units/Haroun/caretaker.tgi','Units/Gauri/forge.tgi','Units/Drauga/crafter.tgi','Units/Shadow/nightbringer.tgi','Units/Undead/boneweaver.tgi']:
  text=(root/worker).read_text(encoding='utf-16')
  assert text.count('actor_ids = paws_bridge_wood_site')==text.count('actor_ids = paws_bridge_stone_site')==1;checks+=1
 assert 'paws_bridge_construction_raise_vfx' in actors and 'location = BASE' in actors;checks+=1
 effect=(root/'Effects/construction.tgi').read_text(encoding='utf-16').split('IDS = paws_bridge_construction_raise_vfx')[1]
 assert 'apply_swaying = false' in effect and 'apply_shaking = false' in effect;checks+=1
 for material,resource in [('wood','wood'),('stone','stone')]:
  for n in range(5,33):
   for axis in ('x','y'):
    ident=f'paws_bridge_{material}_{axis}_{n:02}'
    block=actors[actors.index('IDS = '+ident):].split('[Thing Template=PawsBridge]',1)[0]
    assert f'[Upkeep]\n  {resource} = 10' in block and '[Cost]' not in block;checks+=1
    assert f'health = {1000 if material=="wood" else 2000}' in block;checks+=1
manifest=json.loads((a.out/'sandbox/probe-data/bridge-model-manifest.json').read_text())
assert len(manifest)==112;checks+=1
for name,row in manifest.items():
 path=a.out/'sandbox/probe-data/Paws/Bridges'/name
 assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'];checks+=1
 assert row['width']==6 and row['length'] in range(8,63,2);checks+=1
sys.path.insert(0,str(a.models/'deps'));time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N
import numpy as np
for material in ('wood','stone'):
 for axis in ('x','y'):
  for n in (5,13,32):
   path=a.out/f'sandbox/probe-data/Paws/Bridges/{material}_{axis}_{n:02}.nif'
   data=N.Data()
   with path.open('rb') as f:data.read(f)
   assert data.version==0x0A010000;checks+=1
   assert {b.name for b in data.blocks if isinstance(b,N.NiNode)}>={b'BASE',b'Final'};checks+=1
   for b in data.blocks:
    if isinstance(b,N.NiAlphaProperty):assert not (int(b.flags)&1) and int(b.flags)&0x200;checks+=1
    if isinstance(b,N.NiSourceTexture):assert (path.parent/b.file_name.decode()).exists();checks+=1
    if not isinstance(b,N.NiTriBasedGeom):continue
    points=np.array([[v.x,v.y,v.z] for v in b.data.vertices])
    assert np.isfinite(points).all();checks+=1
    assert np.max(np.abs(points[:,0 if axis=='x' else 1]))<=(n-1)+1e-3;checks+=1
assert (a.out/'sandbox/Userdata/Save/Bridge-ready.RSG').read_bytes()==(Path(__file__).parent/'fixtures/Bridge-ready.RSG').read_bytes();checks+=1
print('BRIDGE_ASSETS_PASS',checks,'checks: all actor variants/locales, upkeep, dependency hashes and sampled NIF geometry')
