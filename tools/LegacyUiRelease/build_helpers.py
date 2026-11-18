from context import *
def main():
 for group,base,oldver,newver in[('arcane',AP,'0.6.0-beta.5',ARC),('pure',PP,'0.5.0-beta.9',PURE)]:
  d=O/group/'helpers';d.mkdir(parents=True,exist_ok=True);reports=read(base/'helpers/build-report.json');mapped={};report={}
  for path,h in{p:h for r in reports.values()for p,h in r['sources'].items()}.items():
   src=Path(path);assert sha(src)==h;data=src.read_bytes()
   if src.name in['25-LargeMapsIdentity.cs','4-PureChannel.cs']:
    assert oldver.encode()in data;data=data.replace(oldver.encode(),newver.encode())
    if group=='pure':data=data.replace(b'1.3.72-pure.21-beta.9',RT.encode())
   dest=d/'inputs'/hashlib.sha256(data).hexdigest().upper()/src.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);mapped[path]=str(dest)
  for n in['paws_player_colors.ini','paws_patch_versions.ini']:
   if(base/'helpers'/n).exists():(d/n).write_bytes((base/'helpers'/n).read_bytes().replace(oldver.encode(),newver.encode()))
  for name,row in reports.items():
   args=[]
   for a in row['args']:
    if a.startswith('/out:'):a='/out:'+str(d/name)
    elif a.startswith('/resource:'):
     p,label=a[10:].rsplit(',',1);a='/resource:'+mapped[p]+','+label
    elif a in mapped:a=mapped[a]
    args.append(a)
   run(args,d/(name+'.build.log'));features=json.loads(run([d/name,'--features']));expected=dict(row['features'],patchVersion=newver)
   if group=='pure':expected['version']=RT
   assert features==expected,(name,features,expected)
   flags=['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']if group=='arcane'else[]
   tests={f:run([d/name,f]).strip()for f in flags};report[name]=dict(sha256=sha(d/name),baselineSha256=row['sha256'],features=features,args=args,sources={mapped[p]:sha(mapped[p])for p in row['sources']},selfTests=tests);print('HELPER_PASS',group,name,flush=True)
  write(d/'build-report.json',report)
if __name__=='__main__':main()
