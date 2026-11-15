"""Clone the user's active launcher installation into a private river test.

Installed files stay unchanged. Feature overrides use its existing Userdata
depot, retaining original launcher guard inputs and all enabled module data.
"""
from pathlib import Path
import argparse,shutil,os,json,hashlib,sys
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'game/lobby-colors'),str(REPO/'game/engineer-bridges')]
from PrepareSplitLanguages import rwd_files,dec
from compact_menu import span
from models import definitions,construction_effect
from art import apply_art
from builders import patch_pioneers
from rivers_data import rule_definition,shape_rule,installed_ui,river_terrain
p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--bridges',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
game=a.game.resolve();bridges=a.bridges.resolve();out=a.out.resolve();sandbox=out/'sandbox'
assert game!=sandbox and game not in out.parents and (bridges/'sandbox/terrain-prototype.marker').is_file()
assert not out.exists() or (out/'installed-rivers.marker').is_file()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
if not out.exists():
 out.mkdir();(out/'installed-rivers.marker').write_text('Private installed Arcane rivers and bridges\n');sandbox.mkdir()
 state=json.loads((game/'.pawpatch/state.json').read_text());paths=set()
 for module in state['modules'].values():
  if module.get('enabled'):
   for f in module.get('files',[]):paths.add(f['path'])
 for name in ['k2.exe','BinkW32.dll','mss32.dll','steam_api.dll','DbgHelp.dll','GdiPlus.dll','UnicoWS.dll','avifil32.dll','d3d9.dll','D3DX9_43.dll','D3DCompiler_43.dll','steam_appid.txt','paws_presentation.ini','paws_game_text.ini','paws_player_colors.ini','paws_launch_versions.ini','paws_patch_versions.ini']:
  if (game/name).is_file():paths.add(name)
 for folder in ['startup','mss','Mods']:
  for f in (game/folder).rglob('*'):
   if f.is_file() and f.suffix.lower() not in ('.log','.dmp'):paths.add(f.relative_to(game).as_posix())
 baseline={}
 for i,relative in enumerate(sorted(paths)):
  src=game/relative
  if not src.is_file():raise FileNotFoundError(src)
  dst=sandbox/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);baseline[relative]=sha(src)
  if i%3000==0:print('COPIED',i,'of',len(paths),flush=True)
 for name in ['Data.rwd','Music.rwd']:
  src=bridges/'sandbox'/name;assert src.stat().st_size==(game/name).stat().st_size and sha(src)==sha(game/name);os.link(src,sandbox/name);baseline[name]=sha(src)
 (sandbox/'.pawpatch').mkdir(exist_ok=True);shutil.copy2(game/'.pawpatch/state.json',sandbox/'.pawpatch/state.json')
 for name in ['terrain-prototype.marker','reconnect-test.marker','installed-runtime.marker']:(sandbox/name).write_text('Private installed river fixture\n')
 (sandbox/'Userdata/User').mkdir(parents=True);shutil.copy2(bridges/'sandbox/Userdata/User/UVars.tgi',sandbox/'Userdata/User/UVars.tgi')
 (out/'Documents').mkdir();(out/'AppData').mkdir();(out/'qa-evidence').mkdir();(out/'native').mkdir()
 (out/'installed-baseline.json').write_text(json.dumps(dict(game=str(game),modules={k:dict(version=v['version'],enabled=v.get('enabled')) for k,v in state['modules'].items()},files=baseline),indent=2))
 print('INSTALLED_BASELINE_COPIED',len(paths),flush=True)
 # Preserve accepted model geometry/materials exactly.
 shutil.copytree(bridges/'sandbox/probe-data/Paws',sandbox/'Userdata/Paws')
 shutil.copy2(bridges/'sandbox/probe-data/bridge-model-manifest.json',out/'bridge-model-manifest.json')
files=rwd_files((sandbox/'Data.rwd').read_bytes())
shutil.copy2(bridges/'sandbox/shfolder.dll',sandbox/'shfolder.dll')
private_user=out/'Documents/Kohan2/data/User';private_user.mkdir(parents=True,exist_ok=True)
if not (private_user/'UVars.tgi').exists():shutil.copy2(bridges/'sandbox/Userdata/User/UVars.tgi',private_user/'UVars.tgi')
def original(name):
 file=sandbox/'data'/name
 return dec(file.read_bytes()) if file.is_file() else dec(files[name])
language='ru';root=sandbox/'rivers-data'
root.mkdir(exist_ok=True)
if not (root/'Paws').exists():shutil.copytree(bridges/'sandbox/probe-data/Paws',root/'Paws')
styles=apply_art(out,root)
startup=sandbox/'startup/autoexec.txt';text=startup.read_text(encoding='utf-8-sig')
if 'adddepot rivers-data/' not in text:startup.write_text(text+'\n# Private rivers and bridges overlay\nadddepot rivers-data/\n',encoding='utf-8')
def write(name,text):
 path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-16')
write('Game/world_rules_k2.tgi',original('Game/world_rules_k2.tgi')+rule_definition(language)+shape_rule(language))
svars=original('Game/SVars.tgi');at=svars.index('{')+1
write('Game/SVars.tgi',svars[:at]+'\n int PawsRivers = 17\n int PawsMapShape = 0\n'+svars[at:])
write('UI/Shared/random_map_dialog.tgi',installed_ui(original('UI/Shared/random_map_dialog.tgi'),language,span))
write('Special/Things/thing_visibilityactors.tgi',original('Special/Things/thing_visibilityactors.tgi')+'\n'+definitions(language,styles))
(root/'Properties/properties_intrinsic.tgi').unlink(missing_ok=True)
for name in ['Units/Human/engineer.tgi','Units/Haroun/caretaker.tgi','Units/Gauri/forge.tgi','Units/Drauga/crafter.tgi','Units/Shadow/nightbringer.tgi','Units/Undead/boneweaver.tgi']:
 text=original(name);at=text.index('[BuildActor]');write(name,text[:at]+'[BuildActor]\n actor_ids = paws_bridge_wood_site\n [BuildActor]\n actor_ids = paws_bridge_stone_site\n '+text[at:])
pioneers={}
previous_pioneers=out/'pioneer-builders.json'
if previous_pioneers.exists():
 for name in json.loads(previous_pioneers.read_text()):
  if name not in ['Units/Shadow/nightbringer.tgi','Units/Undead/boneweaver.tgi']:(root/name).unlink(missing_ok=True)
for race in ('Human','Haroun','Gauri','Drauga','Shadow','Undead'):
 for path in sorted((sandbox/'data/Units'/race).glob('*.tgi')):
  name=path.relative_to(sandbox/'data').as_posix();text,changed=patch_pioneers(original(name))
  if changed:write(name,text);pioneers[name]=changed
for style in styles:
 for path in (root/'Units'/style.title()).glob('*.tgi'):
  text=path.read_text(encoding='utf-16')
  text=text.replace('paws_bridge_wood_site','paws_bridge_'+style+'_wood_site').replace('paws_bridge_stone_site','paws_bridge_'+style+'_stone_site')
  path.write_text(text,encoding='utf-16')
(out/'pioneer-builders.json').write_text(json.dumps(pioneers,indent=2))
for biome in ['temperate','arctic','desert','cursed']:write('Terrain/'+biome.title()+'/paws_river.tgi',river_terrain(biome))
write('Effects/construction.tgi',original('Effects/construction.tgi')+construction_effect())
text=(bridges/'sandbox/probe-data/Terrain/Temperate/temperate_road.tgi').read_text(encoding='utf-16');at=text.index('IDS = paws_engineer_bridge');at=text.rfind('[Terrain',0,at)
write('Terrain/Temperate/temperate_road.tgi',original('Terrain/Temperate/temperate_road.tgi')+'\n'+text[at:])
# No separate river RMC/profile: every installed climate, including mixed
# biomes, uses these independent shape and river-count rules.
(out/'overrides.json').write_text(json.dumps({str(p.relative_to(root)):sha(p) for p in root.rglob('*.tgi')},indent=2))
print('INSTALLED_RIVER_BASE_READY',out)
