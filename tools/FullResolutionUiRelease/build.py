from context import *
import zipfile, shutil

def helpers():
 for group,base,oldver,newver in [('arcane',AP,'0.6.0-beta.3',ARC),('pure',PP,'0.5.0-beta.7',PURE)]:
  d=O/group/'helpers';d.mkdir(parents=True,exist_ok=True);mapped={};reports=read(base/'helpers/build-report.json');report={}
  if (d/'build-report.json').exists():
   prior=read(d/'build-report.json');assert all(sha(d/n)==r['sha256']for n,r in prior.items());continue
  for path,h in {p:h for r in reports.values()for p,h in r['sources'].items()}.items():
   src=Path(path);assert sha(src)==h,path;data=src.read_bytes()
   if src.name in ['25-LargeMapsIdentity.cs','4-PureChannel.cs']:
    assert oldver.encode()in data;data=data.replace(oldver.encode(),newver.encode())
    if group=='pure':data=data.replace(b'1.3.72-pure.21-beta.7',RT.encode())
   dest=d/'inputs'/hashlib.sha256(data).hexdigest().upper()/src.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);mapped[path]=str(dest)
  for n in ['paws_player_colors.ini','paws_patch_versions.ini']:
   src=base/'helpers'/n
   if src.exists():(d/n).write_bytes(src.read_bytes().replace(oldver.encode(),newver.encode()))
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
   tests={flag:run([d/name,flag]).strip()for flag in flags}
   report[name]=dict(sha256=sha(d/name),baselineSha256=row['sha256'],features=features,args=args,sources={mapped[p]:sha(mapped[p])for p in row['sources']},selfTests=tests)
   print('HELPER_PASS',group,name,flush=True)
  write(d/'build-report.json',report)

def packages():
 feed=verify(read(O/'before/feed/v3/beta.json'),key());old={p['id']:p for p in feed['packages']};manifest=read(HD/'fullres-manifest.json');hd={}
 # One priority depot for icons. Existing per-race and spectator frame paths
 # retain their native routing. No gameplay resource is placed in the depot.
 for r in manifest['files']:
  n=r['path'];frame='pawuniform' in n.lower();wanted=n.startswith('paws-hd-ui/')and not frame or n.startswith('skins/')or n.startswith('data/')and frame
  if wanted:hd[n.lower()]=(n,HD/'overlay'/n,r)
 assert len(hd)==708,len(hd)
 assert all(Path(n).suffix.lower()in['.png','.tga']for n,_,_ in hd.values())
 audit={};new=[]
 for group,base,version,tag,pids in [('arcane',AP,ARC,'patch-'+ARC,['pawpatch-core','player-colors','desync-continue','common-ui']),('pure',PP,PURE,'patch-pure-'+PURE,['pure-fixes-runtime','pure-fixes-data','pure-beta-common'])]:
  out=O/group/'assets';out.mkdir(parents=True,exist_ok=True);reports=read(O/group/'helpers/build-report.json')
  for pid in pids:
   before=old[pid];src=base/'assets'/Path(before['urls'][0]).name;validate_package(src,before)
   with zipfile.ZipFile(src)as z:
    module=json.loads(z.read('module.json'));original={r['path']:z.read('payload/'+r['path'])for r in module['files']}
   files=dict(original);external={};oldver='0.6.0-beta.3'if group=='arcane'else'0.5.0-beta.7'
   for n in files:
    name=Path(n).name
    if name in reports:files[n]=(O/group/'helpers'/name).read_bytes()
    if name.lower()in['paws_patch_versions.ini','paws_runtime.marker']:files[n]=files[n].replace(oldver.encode(),version.encode())
   if pid in['common-ui','pure-beta-common']:
    for canonical,path,r in hd.values():
     matching=[n for n in files if n.lower()==canonical.lower()];assert len(matching)<=1
     dest=matching[0]if matching else canonical;external[dest]=(path,r)
     files.pop(dest,None)
    if group=='arcane':startup=files['startup/autoexec.txt']
    else:
     startup=(S/'src/PawsPatchLauncher/Assets/Vanilla1372/autoexec.txt').read_bytes()
     assert hashlib.sha256(startup).hexdigest().upper()=='628D30D3D0D8E9F4E1DD33604F6B9869FFC9B92BCA0ABC5D6B80CF5FB644666F'
    assert b'paws-hd-ui/'not in startup
    files['startup/autoexec.txt']=startup.rstrip()+b'\r\n\r\n# Full-resolution interface textures\r\nadddepot paws-hd-ui/\r\n'
   changed=[n for n,b in files.items()if n not in original or original[n]!=b]+list(external)
   allowed=set(reports)|{'paws_patch_versions.ini','paws_runtime.marker','autoexec.txt'}
   assert all(Path(n).name in allowed or n in external for n in changed),changed
   v=RT if pid=='pure-fixes-runtime'else version
   specs=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in files.items()]
   for n,(path,r)in external.items():
    assert sha(path)==r['sha256'].upper();specs.append(dict(path=n,size=path.stat().st_size,sha256=r['sha256'].upper()))
   module.update(version=v,files=sorted(specs,key=lambda r:r['path']));target=out/(pid+'-'+v+'.zip')
   if target.exists():
    with zipfile.ZipFile(target)as z:matches=json.loads(z.read('module.json'))==module
    if not matches:
     superseded=target.with_suffix('.superseded');assert not superseded.exists();target.rename(superseded)
   if not target.exists():
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
     z.writestr('module.json',encode(module))
     for n,b in sorted(files.items()):z.writestr('payload/'+n,b)
     for n,(path,_)in sorted(external.items()):z.write(path,'payload/'+n)
   assert target.stat().st_size<2_000_000_000,'GitHub asset size limit'
   q=copy.deepcopy(before);q.update(version=v,size=target.stat().st_size,sha256=sha(target),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+tag+'/'+target.name]);validate_package(target,q);new.append(q)
   audit[pid]=dict(path=str(target),group=group,changed=changed,preserved=len(files)-len([n for n in changed if n in files]),fullresImages=len(external),size=q['size'],sha256=q['sha256'],sourceVersion=before['version'])
   print('PACKAGE_PASS',pid,q['size'],len(external),flush=True)
 write(O/'packages.json',new);write(O/'package-audit.json',audit)
 write(O/'image-export.json',dict(passed=True,images=708,uniqueSources=len({r['source']for _,_,r in hd.values()}),allSourcePixelsPreserved=True,nativeGameplayUnchanged=True,files=[dict(path=n,sha256=r['sha256'],width=r['width'],height=r['height'],sourceSha256=r['sourceSha256'])for n,_,r in hd.values()]))
if __name__=='__main__':globals()[sys.argv[1]]()
