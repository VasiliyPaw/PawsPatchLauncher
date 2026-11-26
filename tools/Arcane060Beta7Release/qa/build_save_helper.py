"""Private save-test carrier, using the production custom-color feature set."""
from pathlib import Path
import sys,json,re,hashlib,subprocess,zipfile,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from context import WS,O,env,sha,read,write
Q=Path('G:/PawsWork/QA/ArcaneFix-20261125');game=Q/'game'
source=WS/'work/arcane-bridge-terrain-fixes-20261125/helper-inputs'
def main():
 # Restore only the two official color-support files into this private fixture.
 # The historical ZIP is a read-only input; executable inputs/output stay on G:.
 color_zip=WS/'outputs/ui-revert-release-20261118/arcane/assets/player-colors-0.6.0-beta.6.zip'
 assert sha(color_zip)=='609AE57B4B2C1C410990D50A352BC4C7627A4AB51668CD381A11260F280CBDE3'
 data_pins={}
 with zipfile.ZipFile(color_zip)as z:
  manifest=json.loads(z.read('module.json'))
  for entry in manifest['files']:
   n=entry['path']
   if n not in ['paws_player_colors.ini','data/ui/menus/pcolors.tgi']:continue
   raw=z.read('payload/'+n);assert hashlib.sha256(raw).hexdigest().upper()==entry['sha256'].upper()
   dst=game/n;backup=O/'native-save/inputs/color-files-before'/n
   if dst.exists()and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,backup)
   dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw);data_pins[n]=sha(dst)
 assert len(data_pins)==2
 name='k2_paws_lobby_colors_mp_nohostility_1372.exe';row=read(source/'helpers/build-report.json')[name];mapping=read(source/'origin-map.json')
 for original,digest in row['sources'].items():assert sha(source/mapping[original])==digest.upper()
 startup=next(k for k in mapping if k.endswith('PawRuntimeStartup.cs'));raw=(source/mapping[startup]).read_text()
 arrays=re.search(r'string\[\] names=\{([^}]+)\};string\[\] hashes=\{([^}]+)\}',raw);assert arrays
 names=re.findall(r'"([^"]+)"',arrays[1]);pins={n:sha(game/'Mods'/n)for n in names};assert len(pins)==10
 replacement='string[] names={'+arrays[1]+'};string[] hashes={'+','.join('"'+pins[n]+'"'for n in names)+'}'
 raw=raw[:arrays.start()]+replacement+raw[arrays.end():];patched=O/'native-save/color-QA.PawRuntimeStartup.cs';patched.parent.mkdir(parents=True,exist_ok=True);patched.write_text(raw,encoding='utf-8')
 args=['C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe']
 for a in row['args'][1:]:
  if a.startswith('/out:'):a='/out:'+str(game/'TestInstalledRuntime.exe')
  elif a in mapping:a=str(patched)if a==startup else str(source/mapping[a])
  elif a.startswith('/resource:'):
   original,label=a[10:].rsplit(',',1);a='/resource:'+str(source/mapping[original])+','+label
  args.append(a)
 subprocess.run(args,check=True,env=env(),cwd=Q)
 assert (game/'paws_player_colors.ini').is_file()
 write(O/'native-save/color-helper-build.json',dict(productionFeatureCarrier=name,productionSourceHashesVerified=True,onlyPrivateDllPinsChanged=True,officialColorData=data_pins,pins=pins,helperSha256=sha(game/'TestInstalledRuntime.exe'),startupSha256=sha(patched)))
 print('PRIVATE_COLOR_CARRIER_BUILT',name)
if __name__=='__main__':main()
