"""Check the explicit native terrain load path and all prepared locales."""
import argparse, sys, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from PrepareSplitLanguages import rwd_files, dec
from texts import LANGS
p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
stock=dec(rwd_files((a.game/'Data.rwd').read_bytes())['Terrain/Temperate/temperate_road.tgi'])
checks=0
for lang in LANGS:
 root=a.out/'locales'/lang
 road=(root/'Terrain/Temperate/temperate_road.tgi').read_bytes().decode('utf-16').replace('\r','')
 assert road.startswith(stock.replace('\r',''));checks+=1
 assert road.count('IDS = paws_engineer_road\n')==1 and road.count('IDS = paws_engineer_road01')==1;checks+=1
 assert road.count('name = "Engineer road"')==2;checks+=1
 assert 'property_ids = paws_road_speed' in road;checks+=1
 texture=(root/'Terrain/PawsRoad/PawsCobble.tga').read_bytes()
 assert struct.unpack_from('<HH',texture,12)==(256,256) and texture[16]==24;checks+=1
 assert 'texture = /Terrain/PawsRoad/PawsCobble.tga' in road;checks+=1
 props=(root/'Properties/properties_terrains.tgi').read_text(encoding='utf-16')
 assert 'IDS = paws_road_speed' in props and 'amount = +.20' in props;checks+=1
assert (a.out/'sandbox/Userdata/Save/Engineers-ready.RSG').read_bytes()==(Path(__file__).with_name('fixtures')/'Engineers-ready.RSG').read_bytes();checks+=1
print(checks,'PASS: loaded terrain file, stock roads retained, named definitions, texture, speed property and native fixture')
