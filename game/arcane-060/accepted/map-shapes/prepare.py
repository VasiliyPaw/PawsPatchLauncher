"""Isolated stage-two map profiles. Existing installed profiles are not edited."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from PrepareSplitLanguages import rwd_files,dec
p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
subprocess.run([sys.executable,'-B',str(ROOT/'game/terrain-prototype/prepare.py'),'--game',str(a.game),'--out',str(a.out)],check=True)
out=a.out.resolve()
assert (out/'terrain-prototype.marker').is_file() and out!=a.game.resolve()
# Stage one properties are intentionally absent: this stage changes generation only.
for name in ['Terrain/Temperate/temperate_road.tgi','Properties/properties_terrains.tgi','RandomMap/rmc_paws_terrain_probe.tgi']:
 (out/'probe-data'/name).unlink(missing_ok=True)
fs=rwd_files((a.game/'Data.rwd').read_bytes())
source=dec(fs['RandomMap/rmc_temperate03.tgi']).replace('\r','')
# Keep native vegetation, major kingdoms, camps, resources and their sliders.
# Only native blocking blobs and height noise are replaced by the shape pass.
source=re.sub(r'\s*\[TerrainBlob Template=Temp(?:MountainTerrainBlob\d*|LakeTerrainBlob)\]','',source)
source=re.sub(r'\s*\[TerrainNoise Template=TempNoisePhase\w+\]','',source)
for ident,title,description in [
 ('pangaea','Pangaea','One connected continent, coastal bays and an outer sea.'),
 ('mediterranean','Mediterranean','A central inland sea with broad connected shores.'),
 ('rivers','Rivers','Winding rivers with three broad prebuilt crossings.')]:
 t=source.replace('IDS = rmc_temperate03','IDS = paws_shape_'+ident)
 t=t.replace('"#rmc_temperate03_name"','"Paw - '+title+'"').replace('"#rmc_temperate03_description"','"'+description+' Local test, temperate climate."')
 # Separate IDs get separate native settings and seed/save metadata.
 at=t.rfind('}')
 t=t[:at]+'''\n [MapSize]
 width = 768
 height = 768
 recommended_kingdoms_min = 2
 recommended_kingdoms_max = 8
 [MapSize]
 width = 1024
 height = 1024
 recommended_kingdoms_min = 2
 recommended_kingdoms_max = 8
'''+t[at:]
 (out/'probe-data/RandomMap'/('rmc_paws_'+ident+'.tgi')).write_text(t,encoding='utf-16')
manifest={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in out.rglob('*') if f.is_file() and f.name!='manifest.json'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Three private profiles prepared:',out)
