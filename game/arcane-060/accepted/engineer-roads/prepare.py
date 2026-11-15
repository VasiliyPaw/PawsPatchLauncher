"""Prepare only a separate road prototype; retain stage 3 shape/climate menu."""
import argparse,sys,subprocess,hashlib,json,shutil
from pathlib import Path
from texts import LANGS,LABELS,TIPS
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'game/gold-sound-button')]
from PrepareSplitLanguages import rwd_files,dec
from prepare import add_button

def main():
 p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--fixture',type=Path);p.add_argument('--fixture-profile',type=Path);a=p.parse_args()
 if bool(a.fixture)!=bool(a.fixture_profile):p.error('Both --fixture and --fixture-profile are required for the optional saved test map')
 subprocess.run([sys.executable,'-B',str(ROOT/'game/map-shapes/prepare_menu.py'),'--game',str(a.game),'--out',str(a.out)],check=True)
 files=rwd_files((a.game/'Data.rwd').read_bytes())
 dest=a.out/'sandbox/Userdata/Save/Engineers-ready.RSG';dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(Path(__file__).with_name('fixtures')/'Engineers-ready.RSG',dest)
 if a.fixture:
  dest=a.out/'sandbox/Userdata/Save/Road-test.RSG';dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(a.fixture,dest)
  shutil.copy2(a.fixture_profile,a.out/'sandbox/probe-data/RandomMap/rmc_paws_terrain_probe.tgi')
 for lang,labels,tip in zip(LANGS,LABELS,TIPS):
  root=a.out/'locales'/lang
  button='''[PawRoadButton Template=SharedPushButtonWidgetBase]
 {
  tooltip_name = "'''+labels[1]+'''"
  tooltip = "'''+tip+'''"
  [View]
  {
   L = 158r
   T = 223b
   R = 6r
   B = 195b
  }
  [Client Template=LabelWidget]
  {
   [View Template=NoVE]
   {
    L = 2
    T = 3
    R = 2r
    B = 3b
   }
   [Label Template=SharedSmallCenteredLabelVE]
   text = "'''+labels[0]+'''"
  }
 }
'''
  dest=root/'UI/Game/game_interface.tgi';dest.parent.mkdir(parents=True,exist_ok=True)
  dest.write_bytes(add_button(files['UI/Game/game_interface.tgi'],button))
  # Dedicated terrain definition; stock dirt roads retain their original rules.
  road = """[Terrain Template=Terrain]
{
 IDS = paws_engineer_road
 name = "Engineer road"
 base_priority = 176
 terrain_group = dirt
 doodad_frequency = 0
 primary_doodad_frequency = 0
 [Property]
 property_ids = paws_road_speed
 [Variation]
 {
  IDS = paws_engineer_road01
  name = "Engineer road"
  texture = /Terrain/PawsRoad/PawsCobble.tga
  texture_width = 8
  texture_height = 8
  terrain_color = .55,.52,.46
  weight = 1
 }
}
"""
  # The engine loads the explicit terrain file list; a new filename is not scanned.
  # Append a separate definition to an already registered file, retaining stock roads.
  dest=root/'Terrain/Temperate/temperate_road.tgi';dest.parent.mkdir(parents=True,exist_ok=True)
  dest.write_text(dec(files['Terrain/Temperate/temperate_road.tgi'])+'\n'+road,encoding='utf-16')
  dest=root/'Terrain/PawsRoad/PawsCobble.tga';dest.parent.mkdir(parents=True,exist_ok=True)
  shutil.copy2(Path(__file__).with_name('assets')/'PawsCobble.tga',dest)
  old=dest.with_name('paws_engineer_road.tgi')
  if old.exists():old.unlink()
  props=dec(files['Properties/properties_terrains.tgi'])+'''
[Property Template=TerrainProperty]
{
 IDS = paws_road_speed
 name = "Road +20%"
 icon = /Properties/%s/PropertyIcons/IconPropertyTrailblazing.png
 [Modifier Template=MultiplyModifier]
 attribute = SPEED_MAX
 amount = +.20
}
'''
  dest=root/'Properties/properties_terrains.tgi';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(props,encoding='utf-16')
 manifest={str(f.relative_to(a.out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.out/'locales').rglob('*') if f.is_file()}
 (a.out/'menu-manifest.json').write_text(json.dumps(manifest,indent=2))
 print('Prepared engineer-road sandbox',a.out)
if __name__=='__main__':main()
