from context import *
import zipfile,re,shutil
OLD_ARC=WS/'outputs/arcane060-beta3-release-20261116/assets/common-ui-0.6.0-beta.3.zip';OLD_PURE=WS/'outputs/pure050-beta7-release-20261116/assets/pure-beta-common-0.5.0-beta.7.zip'
def unpack(path):
 with zipfile.ZipFile(path)as z:
  m=json.loads(z.read('module.json'));return m,{r['path']:z.read('payload/'+r['path'])for r in m['files']}
def stock_skins():
 root=Path('G:/PawsWork/QA/Arcane060-20261115/game');state=read(root/'.pawpatch/state.json');originals={n.replace('\\','/').lower():r for n,r in state['originals'].items()};expected=dict(re.findall(r'NormalizeRelativePath\("(skins/[^\"]+)"\)\] = "([A-F0-9]+)"',(S/'src/PawsPatchLauncher/SteamVanillaBaseline.cs').read_text()));out={};report={};folder=O/'stock-skins';folder.mkdir(exist_ok=True)
 for n,h in expected.items():
  r=originals[n.lower()];assert r['existed']and r['sha256'].upper()==h;p=root/'.pawpatch/originals'/r['backupRelativePath'];assert sha(p)==h;dest=folder/Path(n).name;shutil.copy2(p,dest);out[n]=dest.read_bytes();report[n]=dict(path=str(dest),sha256=h,size=dest.stat().st_size)
 assert len(out)==6;write(O/'stock-skins.json',report);return out
def main():
 f=verify(read(O/'before/feed/v3/beta.json'),key());old={p['id']:p for p in f['packages']};skins=stock_skins();known_hd=read(HD/'fullres-manifest.json')['files'];remove=sorted({r['path']for r in known_hd if r['path'].startswith('paws-hd-ui/')}|{'paws-hd-ui.rwd'});assert len(remove)==655;new=[];audit={};graphics={}
 for group,base,version,tag,pids in[('arcane',AP,ARC,'patch-'+ARC,['pawpatch-core','player-colors','desync-continue','common-ui']),('pure',PP,PURE,'patch-pure-'+PURE,['pure-fixes-runtime','pure-fixes-data','pure-beta-common'])]:
  out=O/group/'assets';out.mkdir(parents=True,exist_ok=True);helpers=read(O/group/'helpers/build-report.json');oldver='0.6.0-beta.5'if group=='arcane'else'0.5.0-beta.9'
  for pid in pids:
   before=old[pid];path=base/'assets'/Path(before['urls'][0]).name;validate_package(path,before);m,current=unpack(path);files=dict(current);baseline={};new_removals=[]
   if pid in['common-ui','pure-beta-common']:
    m,baseline=unpack(OLD_ARC if group=='arcane'else OLD_PURE);files=dict(baseline);files.update(skins)
    if group=='pure':files['startup/autoexec.txt']=(S/'src/PawsPatchLauncher/Assets/Vanilla1372/autoexec.txt').read_bytes()
    assert b'paws-hd-ui'not in files['startup/autoexec.txt'];m['remove']=sorted(set(m.get('remove',[]))|set(remove));new_removals=remove
   for n in files:
    name=Path(n).name
    if name in helpers:files[n]=(O/group/'helpers'/name).read_bytes()
    if name.lower()in['paws_patch_versions.ini','paws_runtime.marker']:
     for v in[oldver,'0.6.0-beta.3'if group=='arcane'else'0.5.0-beta.7']:files[n]=files[n].replace(v.encode(),version.encode())
   if baseline:
    images={n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in baseline.items()if Path(n).suffix.lower()in['.png','.tga']};assert len(images)>=63
    assert all(files[n]==baseline[n]for n in images);graphics[pid]=dict(sourceArchive=str(OLD_ARC if group=='arcane'else OLD_PURE),files=images)
   changed=[n for n,b in files.items()if n not in current or b!=current[n]];dropped=sorted(set(current)-set(files));allowed=set(helpers)|{'paws_patch_versions.ini','paws_runtime.marker','autoexec.txt'}
   if not baseline:assert all(Path(n).name in allowed for n in changed)and not dropped
   else:assert all(n.lower()=='paws-hd-ui.rwd'or n.lower()in {k.lower()for k in skins}for n in dropped),dropped
   v=RT if pid=='pure-fixes-runtime'else version;m.update(version=v,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())]);dest=out/(pid+'-'+v+'.zip')
   with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
    z.writestr('module.json',encode(m))
    for n,b in sorted(files.items()):z.writestr('payload/'+n,b)
   q=copy.deepcopy(before);q.update(version=v,size=dest.stat().st_size,sha256=sha(dest),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+tag+'/'+dest.name]);validate_package(dest,q);new.append(q);audit[pid]=dict(path=str(dest),group=group,size=q['size'],sha256=q['sha256'],changed=changed,dropped=dropped,removedHdPaths=len(new_removals),oldGraphicsRestored=bool(baseline),stockSkinArchives=6 if baseline else 0);print('OLD_UI_PACKAGE_PASS',pid,q['size'],flush=True)
 write(O/'packages.json',new);write(O/'package-audit.json',audit);write(O/'graphics-baseline.json',graphics);write(O/'hd-removals.json',remove);write(O/'terrain-preserved.json',next(p for p in f['packages']if p['id']=='arcane-biome-textures'))
if __name__=='__main__':main()
