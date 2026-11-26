"""Stage exact production DLL/helper pairs in the owned, stopped save fixture."""
from pathlib import Path
import sys,json,hashlib,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from context import WS,O,read,write,sha
Q=Path('G:/PawsWork/QA/ArcaneFix-20261125');GAME=Q/'game'
OLD=WS/'outputs/ui-revert-release-20261118/arcane/assets'
HELPER='k2_paws_lobby_colors_mp_nohostility_1372.exe'
def main():
 label=sys.argv[1];assert label in['baseline','final'];assert Q.resolve().drive.upper()=='G:'
 sys.path.insert(0,str(WS/'work/arcane-bridge-terrain-fixes-20261125/qa-tools'));import control
 assert not control.own()
 state_path=O/('native-save/state-original-beta6.json'if label=='baseline'else'native-save/state-final-assembled.json')
 state_bytes=state_path.read_bytes();state=json.loads(state_bytes)
 assert state['modules']['pawpatch-core']['version']==('0.6.0-beta.6'if label=='baseline'else'0.6.0-beta.7')
 files={}
 def member(archive,name):
  with zipfile.ZipFile(archive)as z:
   m=json.loads(z.read('module.json'));r=next(r for r in m['files']if r['path']==name);b=z.read('payload/'+name)
   assert len(b)==r['size']and hashlib.sha256(b).hexdigest().upper()==r['sha256'].upper();return b
 core=OLD/'pawpatch-core-0.6.0-beta.6.zip';colors=OLD/'player-colors-0.6.0-beta.6.zip'
 assert sha(core)=='2D266518EDEEBF35F78946DC76EC4856DEDE5013E931C93ED3D4D581DB06BC4F'
 assert sha(colors)=='609AE57B4B2C1C410990D50A352BC4C7627A4AB51668CD381A11260F280CBDE3'
 if label=='baseline':
  for n in ['Mods/PawsBridges.dll','Mods/PawsWaterBiomes.dll','paws_runtime.marker']:files[n]=member(core,n)
  files['TestInstalledRuntime.exe']=member(colors,HELPER)
  files['paws_patch_versions.ini']=member(OLD/'common-ui-0.6.0-beta.6.zip','paws_patch_versions.ini')
 else:
  for n in ['Mods/PawsBridges.dll','Mods/PawsWaterBiomes.dll','paws_runtime.marker']:files[n]=member(O/'assets/pawpatch-core-0.6.0-beta.7.zip',n)
  files['TestInstalledRuntime.exe']=(O/'helpers'/HELPER).read_bytes();assert hashlib.sha256(files['TestInstalledRuntime.exe']).hexdigest().upper()==read(O/'helpers/build-report.json')['helpers'][HELPER]['sha256']
  files['paws_patch_versions.ini']=member(O/'assets/common-ui-0.6.0-beta.7.zip','paws_patch_versions.ini')
 for n in ['paws_player_colors.ini','data/ui/menus/pcolors.tgi']:files[n]=member(colors,n)
 pins={}
 for n,b in files.items():
  p=GAME/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);pins[n]=sha(p)
 (GAME/'.pawpatch/state.json').write_bytes(state_bytes)
 write(O/'native-save'/('production-pair-'+label+'.json'),dict(label=label,helperVariant=HELPER,exactProductionPairs=True,compilerInvoked=False,files=pins,stateFixtureSnapshot=str(state_path),stateSHA256=sha(state_path)))
 print('EXACT_PRODUCTION_PAIR_STAGED',label)
if __name__=='__main__':main()
