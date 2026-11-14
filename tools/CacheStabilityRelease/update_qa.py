"""Update the same three closed QA copies, without launching any game."""
import shutil,zipfile
from context import *
print(run([sys.executable,REPO/'tools/ExpandedCache/apply_qa.py']),flush=True)
sys.path.insert(0,str(REPO/'tools/ExpandedCache'))
from apply_qa import TARGETS
records=[]
for kind,game in TARGETS:
 state=read(game/'.pawpatch/state.json');changes=[]
 for ident,a in read(OUT/'package-audit.json').items():
  if a['kind']!=kind:continue
  with zipfile.ZipFile(a['archive'])as z:
   module=read(OUT/'packages.json');entry=next(p for p in module if p['id']==ident)
   m=json.loads(z.read('module.json'))
   for name in a['changed']:
    dest=game/name;dest.parent.mkdir(parents=True,exist_ok=True)
    backup=OUT/'qa-before'/game.parent.name/name
    if dest.exists()and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup)
    temp=dest.with_name(dest.name+'.cache-release-new');temp.write_bytes(z.read('payload/'+name));os.replace(temp,dest);changes.append(name)
  if ident in state['modules']:
   state['modules'][ident].update(version=entry['version'],archiveSha256=entry['sha256'],files=m['files'])
 write(game/'.pawpatch/state.json',state)
 if str(game)==r'G:\PawGraphicsQA-20261113\game':
  # Existing Start-Expanded-Cache.ps1 requires the private-profile wrapper.
  n='k2_paws_lobby_colors_mp_1372_experimental.exe';dest=game/n;t=game/(n+'.qa-new');t.write_bytes((OUT/'qa-helper'/n).read_bytes());os.replace(t,dest)
 records.append(dict(game=str(game),kind=kind,version=VERSIONS[kind],changed=changes,gameLaunched=False,privateWrapper=kind=='arcane'and game.parent.name=='PawGraphicsQA-20261113'))
write(OUT/'qa-updated.json',records);print('EXISTING_THREE_QA_COPIES_UPDATED_NO_LAUNCH')
