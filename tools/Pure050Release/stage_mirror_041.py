"""Read back commit-pinned mirrors and sign only their Pure URL replacement."""
import argparse,subprocess
from context import *
from publish_041 import STAGE,KEY,FEEDS,IDS,scoped
from PrepareRelease081 import fetch,key,sign,RAW
from PrepareRelease070 import verify,validate_package
from cryptography.hazmat.primitives import serialization
def main():
 p=argparse.ArgumentParser();p.add_argument('commit');a=p.parse_args();assert len(a.commit)==40 and all(c in '0123456789abcdef'for c in a.commit)
 assert subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=REPO,text=True).split()[0]==a.commit
 packages=read(OUT/'stable-stage/packages.json');proof={}
 for package in packages:
  original=package['urls'][-1];name=original.rsplit('/',1)[1];primary=RAW.replace('/main/','/'+a.commit+'/')+'feed/assets/pure-0.4.1/'+name;data=fetch(primary);assert len(data)==package['size']and hashlib.sha256(data).hexdigest().upper()==package['sha256'];path=STAGE/'public-assets'/name;path.parent.mkdir(exist_ok=True);path.write_bytes(data);validate_package(path,package);package['urls']=[primary,original];proof[package['id']]=dict(sha256=package['sha256'],primary=primary,size=len(data));print('PURE_IMMUTABLE_MIRROR_PASS',package['id'],flush=True)
 replacements={p['id']:p for p in packages};private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 for rel in FEEDS:
  before=verify(read(STAGE/'before'/rel),key());after=verify(read(STAGE/'signed'/rel),key())
  if 'modGuides'not in after:continue
  for package in after['packages']:
   if package['id']in IDS:package['urls']=replacements[package['id']]['urls']
  scoped(before,after);write(STAGE/'signed'/rel,sign(after,private))
 write(OUT/'stable-stage/packages.json',packages);prep=read(STAGE/'preparation.json');prep.update(packages=packages,mirrorCommit=a.commit);write(STAGE/'preparation.json',prep);write(STAGE/'public-assets.json',proof)
 print('PURE_MIRROR_STAGE_READY',a.commit)
if __name__=='__main__':main()
