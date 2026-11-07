"""Stage signed URL-only repair of the existing Arcane beta.2 catalogs."""
import argparse,copy,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import key,sign,fetch,RAW,normalize
from PrepareRelease070 import verify,encode
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--private-key',type=Path,required=True);a=ap.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 private=serialization.load_pem_private_key(a.private_key.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 revision=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT,text=True).split()[0]
 remote=RAW.replace('/main/','/'+revision+'/');changes=[]
 for path in ('feed/v3/beta.json','feed/v2/beta.json'):
  raw=(ROOT/path).read_bytes();assert normalize(fetch(remote+path))==normalize(raw)
  before=verify(json.loads(raw),key());after=copy.deepcopy(before);count=0
  for p in after['packages']:
   if p.get('mods')!=['arcane-wars'] or p['version']!='0.5.0-beta.2':continue
   url='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-'+p['version']+'/'+p['id']+'-'+p['version']+'.zip'
   assert p.get('url')==url and p['urls']!=[url],p['id']
   changes.append(dict(feed=path,id=p['id'],oldUrls=p['urls'],urls=[url],size=p['size'],sha256=p['sha256']))
   p['urls']=[url];p.pop('url',None);count+=1
  assert count==10
  after['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
  for rel,value in [('before/'+path,raw),('signed/'+path,encode(sign(after,private)))]:
   p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
 (out/'repair.json').write_bytes(encode(dict(sourceCommit=revision,changes=changes)))
 print('SIGNED_URL_REPAIR_STAGED',len(changes),'records; no upload or install')
if __name__=='__main__':main()
