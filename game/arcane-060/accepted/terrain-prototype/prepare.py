"""Prepare a private copy; never installs into the user's game or documents."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from PrepareSplitLanguages import rwd_files,dec
p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
out=a.out.resolve();game=a.game.resolve()
assert out!=game and game not in out.parents
out.mkdir(parents=True,exist_ok=True)
marker=out/'terrain-prototype.marker'
if any(out.iterdir()) and not marker.exists():raise RuntimeError('Output must be empty or a previous terrain sandbox')
marker.write_text('Local single-player terrain prototype\n')
(out/'steam_appid.txt').write_text('97130\n',encoding='ascii')
expected='1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45'
assert hashlib.sha256((game/'k2.exe').read_bytes()).hexdigest().upper()==expected
for name in ['k2.exe','Data.rwd','Music.rwd','BinkW32.dll','mss32.dll','steam_api.dll','DbgHelp.dll','GdiPlus.dll','UnicoWS.dll']:
 if not (out/name).exists():shutil.copy2(game/name,out/name)
shutil.copytree(game/'mss',out/'mss',dirs_exist_ok=True)
(out/'startup').mkdir(exist_ok=True)
(out/'startup/autoexec.txt').write_text('adddepot data.rwd\nadddepot music.rwd\nadddepot probe-data/\nadddepot Userdata/ 1\n',encoding='ascii')
for folder in ['Userdata/User','probe-data/Terrain/Temperate','probe-data/Properties','probe-data/RandomMap']:(out/folder).mkdir(parents=True,exist_ok=True)
# The Steam 1.3.72 executable expects autosave controls absent from Data.rwd.
# Keep only this required stock-compatible UI layout in the private depot.
options=game/'data/UI/Shared/options_dialog.tgi'
if not options.is_file():raise RuntimeError('The 1.3.72 options_dialog.tgi is required')
(out/'probe-data/UI/Shared').mkdir(parents=True,exist_ok=True)
shutil.copy2(options,out/'probe-data/UI/Shared/options_dialog.tgi')
uvars=out/'Userdata/User/UVars.tgi'
if not uvars.exists():uvars.write_text('''[Vars]
{
 int ResolutionX = 1280
 int ResolutionY = 720
 flag ResolutionWindowed = true
 flag ResolutionCoopFullscreenMode = false
 flag FirstRun = false
 flag ViewShowElapsedGameTime = true
 float FrameRateLimit = 60
 float AudioMainVolume = 0.2
 float AudioMusicVolume = 0
}
''',encoding='utf-16')
files=rwd_files((game/'Data.rwd').read_bytes())
road=dec(files['Terrain/Temperate/temperate_road.tgi']).replace('\r','')
assert road.count('[Variation]')==2
road=road.replace('[Variation]','[Property]\n property_ids = paws_probe_road_speed\n\n [Variation]',1)
(out/'probe-data/Terrain/Temperate/temperate_road.tgi').write_text(road,encoding='utf-16')
props=dec(files['Properties/properties_terrains.tgi']).replace('\r','')+'''
[Property Template=TerrainProperty]
{
 IDS = paws_probe_road_speed
 name = "Test road +20%"
 icon = /Properties/%s/PropertyIcons/IconPropertyTrailblazing.png
 [Modifier Template=MultiplyModifier]
 attribute = SPEED_MAX
 amount = +.20
}
'''
(out/'probe-data/Properties/properties_terrains.tgi').write_text(props,encoding='utf-16')
(out/'probe-data/RandomMap/rmc_paws_terrain_probe.tgi').write_text('''[RMC template=K2RMC]
{
 IDS = rmc_paws_terrain_probe
 name = "Paw's Terrain Test"
 description = "Local flat terrain test. Use the separate probe window."
 biome = temperate
 [MapSize]
 width = 256
 height = 256
 recommended_kingdoms_min = 2
 recommended_kingdoms_max = 2
 [TerrainBlob template=RMCTerrainBlob]
 {
  range = 1,1
  show_ui = false
  terrain_ids = temperate_grass
  paint_first_variation_only = true
  blob_size = 16,64
  consistency = 0.6
  proximity = 0.6
  fuzzy_factor = 0.6
 }
 [ActorGroup template=StartSettlement]
 apply_to_all_major_kingdoms = true
}
''',encoding='utf-16')
manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Prepared isolated sandbox:',out)
