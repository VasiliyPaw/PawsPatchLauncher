from context import *
import shutil,re

def main():
 D=O/'helpers/source';D.mkdir(parents=True,exist_ok=True);resources=O/'helpers/resources';resources.mkdir(exist_ok=True)
 shutil.copy2(B2/'helpers/paws_player_colors.ini',O/'helpers/paws_player_colors.ini')
 reports=read(B2/'helpers/build-report.json');accepted=read(CAND/'verification.json');assert accepted['status']=='local-visibility-scoped-candidate-not-published';assert accepted['productionSha256']==sha(CWORK/'build/PawsCaptureKnowledge.dll')
 for f in(B2/'helpers/source').glob('*.cs'):shutil.copy2(f,D/f.name)
 f=D/'25-LargeMapsIdentity.cs';s=f.read_text();assert '0.6.0-beta.2'in s;f.write_text(s.replace('0.6.0-beta.2',VERSION))
 f=D/'PawRuntimeStartup.cs';s=f.read_text();pattern=r'string\[\] names=\{([^}]+)\};string\[\] hashes=\{([^}]+)\};';m=re.search(pattern,s);assert m
 names=re.findall(r'"([^"]+)"',m[1]);hashes=re.findall(r'"([^"]+)"',m[2]);assert len(names)==9 and len(hashes)==9;names.append('PawsCaptureKnowledge.dll');hashes.append(accepted['productionSha256']);replacement='string[] names={'+','.join('"'+n+'"'for n in names)+'};string[] hashes={'+','.join('"'+h+'"'for h in hashes)+'};';s=s[:m.start()]+replacement+s[m.end():];f.write_text(s)
 result={}
 for name,row in reports.items():
  target=O/'helpers'/name;args=[]
  for arg in row['args']:
   if arg.startswith('/out:'):arg='/out:'+str(target)
   elif arg.lower().endswith('.cs'):arg=str(D/Path(arg).name)
   elif arg.startswith('/resource:'):
    src,label=arg[10:].rsplit(',',1);src=Path(src);assert sha(src)==row['sources'][str(src)];dest=resources/(sha(src)[:16]+'-'+label+'.bin')
    if not dest.exists():shutil.copy2(src,dest)
    arg='/resource:'+str(dest)+','+label
   args.append(arg)
  run(args,O/'helpers'/(name+'.build.log'));features=json.loads(run([target,'--features']));expected=dict(row['features']);expected['patchVersion']=VERSION;assert features==expected,(name,'feature drift')
  tests={flag:run([target,flag]).strip()for flag in ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']}
  sources=[Path(a)for a in args if a.lower().endswith('.cs')]+[Path(a[10:].rsplit(',',1)[0])for a in args if a.startswith('/resource:')]
  result[name]=dict(sha256=sha(target),baselineSha256=row['sha256'],features=features,args=args,sources={str(f):sha(f)for f in sources},selfTests=tests)
  print('BETA3_HELPER_PASS',name,flush=True)
 shutil.copy2(B2/'helpers/paws_player_colors.ini',O/'helpers/paws_player_colors.ini');write(O/'helpers/build-report.json',result);write(O/'helpers/native-contract.json',dict(names=names,hashes=hashes,requiresCaptureKnowledge=True))
if __name__=='__main__':main()
