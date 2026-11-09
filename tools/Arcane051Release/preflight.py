"""Read live signed catalogs and preserve all existing dirty source work."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];OUT=REPO/'outputs/arcane-051-release-20261109'
sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import fetch,key,RAW
from PrepareRelease070 import verify
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(exist_ok=False);backup=OUT/'preserved-work';backup.mkdir()
 for name,args in [('status.txt',['status','--short']),('head.txt',['rev-parse','HEAD']),('head.diff',['diff','HEAD','--binary']),('staged.diff',['diff','--cached','--binary']),('unstaged.diff',['diff','--binary'])]:(backup/name).write_bytes(subprocess.check_output(['git',*args],cwd=REPO))
 changed=subprocess.check_output(['git','diff','--name-only','-z','HEAD'],cwd=REPO).decode().split('\0')
 untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z','--','src','game','tools','docs','supabase','tests'],cwd=REPO).decode().split('\0');manifest={}
 for name in sorted(set(changed+untracked)):
  if not name or '__pycache__'in Path(name).parts or name.endswith('.pyc'):continue
  p=REPO/name
  if not p.is_file():manifest[name]=dict(deleted=True);continue
  target=backup/'files'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);manifest[name]=dict(sha256=sha(p),bytes=p.stat().st_size)
 for label,p in [('installed-exe',Path('D:/SteamLibrary/steamapps/common/Kohan II/k2.exe')),('save-one',Path('C:/Users/Paw/Documents/Kohan2/data/Save/Случайно.RSG')),('save-two',Path('C:/Users/Paw/Documents/Kohan2/data/Save/Случайно2.RSG'))]:manifest[label]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
 (backup/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
 head=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=REPO,text=True).split()[0];live={}
 for prefix in ['v3/','v2/','']:
  for channel in ['stable','beta']:
   name='feed/'+prefix+channel+'.json';b=fetch(RAW.replace('/main/','/'+head+'/')+name);d=verify(json.loads(b),key());target=OUT/'before'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
   assert b.replace(b'\r\n',b'\n')==(REPO/name).read_bytes().replace(b'\r\n',b'\n'),'Local catalog differs from public: '+name
   (target.parent/(channel+'.payload.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2));live[name]=dict(launcher=d['launcher']['version'],guide=d.get('patchGuide',{}).get('version'),packages={p['id']:p['version']for p in d['packages']if p['id']in['pawpatch-core','common-ui','player-colors','desync-continue','ai-improvements']})
 for name in ['feed/changelog.history.json','feed/patch-guide.json','feed/patch-guide-beta.json']:
  b=fetch(RAW.replace('/main/','/'+head+'/')+name);target=OUT/'before'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
  assert b.replace(b'\r\n',b'\n')==(REPO/name).read_bytes().replace(b'\r\n',b'\n'),name
 (OUT/'baseline.json').write_text(json.dumps(dict(publicHead=head,catalogs=live,preservedFiles=len(manifest)),indent=2));print(json.dumps(dict(publicHead=head,catalogs=live,preservedFiles=len(manifest)),indent=2))
if __name__=='__main__':main()
