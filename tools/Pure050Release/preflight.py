"""Freeze public Pure beta inputs before rebuilding; never installs or publishes."""
import shutil,subprocess
from context import *
from PrepareRelease081 import fetch,key,RAW
from PrepareRelease070 import verify,validate_package
def main():
 OUT.mkdir(exist_ok=False)
 head=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=REPO,text=True).split()[0]
 before={}
 for prefix in ['v3/','v2/','']:
  for channel in ['stable','beta']:
   rel='feed/'+prefix+channel+'.json';data=fetch(RAW.replace('/main/','/'+head+'/')+rel);envelope=json.loads(data);payload=verify(envelope,key());p=OUT/'before'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);write(p.with_suffix('.payload.json'),payload);before[rel]=payload
 beta=before['feed/v3/beta.json'];assert next(p for p in beta['packages'] if p['id']=='pure-fixes-data')['version']=='0.4.1-beta.12'
 assets=OUT/'accepted-assets';assets.mkdir()
 wanted={'pure-fixes-data','pure-fixes-runtime','pure-beta-common','pure-vanilla-rules','pure-immortals-rules','immortals'}
 for row in beta['packages']:
  if row['id'] not in wanted:continue
  target=assets/row['urls'][0].rsplit('/',1)[1];target.write_bytes(fetch(row['urls'][0]));validate_package(target,row);print('PUBLIC_INPUT_VERIFIED',row['id'],flush=True)
 pinned={};reports={}
 for name,row in read(BASE/'build-report.json').items():
  assert sha(BASE/name)==row['sha256'];build=read(BASE/(name+'.build.json'));args=[]
  for source,digest in build['sources'].items():
   assert sha(source)==digest,source;target=OUT/'accepted-inputs'/Path(source).name;target.parent.mkdir(exist_ok=True)
   if target.exists():assert sha(target)==digest
   else:shutil.copy2(source,target)
   pinned[source]=str(target)
  for resource,data in build['resources'].items():
   source=data['path'];assert sha(source)==data['sha256'],source;target=OUT/'accepted-resources'/Path(source).name;target.parent.mkdir(exist_ok=True)
   if target.exists():assert sha(target)==data['sha256']
   else:shutil.copy2(source,target)
   pinned[source]=str(target)
  for arg in build['args']:
   if arg in pinned:arg=pinned[arg]
   elif arg.startswith('/resource:'):
    source,label=arg[10:].rsplit(',',1);arg='/resource:'+pinned[source]+','+label
   args.append(arg)
  reports[name]=dict(args=args,acceptedSha256=row['sha256'],features=row['features'])
 write(OUT/'accepted-build.json',reports)
 write(OUT/'baseline.json',dict(publicHead=head,sourceFiles={str(Path(v).relative_to(OUT)):sha(v) for v in pinned.values()},acceptedPackages=[p for p in beta['packages'] if p['id'] in wanted]))
 for name,command in [('status.txt',['status','--short']),('dirty.patch',['diff','HEAD','--binary']),('staged.patch',['diff','--cached','--binary'])]:
  (OUT/name).write_bytes(subprocess.check_output(['git',*command],cwd=REPO))
 print('PURE_INPUTS_FROZEN',len(pinned),len(reports),head)
if __name__=='__main__':main()
