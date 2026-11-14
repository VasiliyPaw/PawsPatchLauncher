import copy,shutil,sys,urllib.error,urllib.request,zipfile
from common import *
SCRIPTS=['common.py','build_helpers.py','stage.py','verify.py','publish.py','ResourceChecks.cs']
def unchanged():
    assert git('rev-parse','HEAD')=='413c669265632585def6d02af40a008218a9fafb','Shared checkout moved'
    assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(OUT/'shared-index-before.patch').read_bytes(),'Shared staging moved'
def gate():
    unchanged();p=read(OUT/'preparation.json');assert p['version']==VERSION and len(p['assets'])==17
    assert read(OUT/'installation-tested-packages.json')['assets']==p['assets'],'Installed package bytes changed after acceptance'
    assert read(OUT/'catalog-result.json')['passed'] and read(OUT/'catalog-result.json')['selections']==55296
    assert read(OUT/'installer-result.json')['passed'] and read(OUT/'installer-result.json')['cases']==12
    assert 'NATIVE_RESOURCES_UNCHANGED_PASS 8 helpers; 96 embedded resources' in (OUT/'resources-check.log').read_text()
    for name,row in read(OUT/'helpers/build-report.json').items():
        assert sha(OUT/'helpers'/name)==row['sha256'] and row['features']['patchVersion']==VERSION and len(row['selfTests'])==5
        assert all(sha(path)==digest for path,digest in row['sources'].items())
    for a in p['assets']:validate_package(Path(a['path']),dict(a,version=VERSION))
    for rel in p['changed'][:2]:
        f=verify(read(OUT/'signed'/rel),key());a=verify(read(OUT/'before'/rel),key())
        assert f['patchGuide']['version']==VERSION and f['launcher']==a['launcher'] and f.get('modGuides')==a.get('modGuides')
        assert [p for p in f['packages'] if p.get('mods')!=['arcane-wars']]==[p for p in a['packages'] if p.get('mods')!=['arcane-wars']]
    return p
def bundle():
    gate();files={};reports=read(OUT/'helpers/build-report.json')
    for row in reports.values():
        for path,digest in row['sources'].items():
            path=Path(path);assert path.suffix.lower() not in ['.rwd','.rsg','.pem'] and (path.suffix.lower()!='.exe' or path.name=='PawsGraphicsRecorder.exe');files['inputs/'+digest+'/'+path.name]=path.read_bytes()
    files['build-report.json']=(OUT/'helpers/build-report.json').read_bytes()
    for name in ['paws_player_colors.ini','paws_patch_versions.ini']:files[name]=(OUT/'helpers'/name).read_bytes()
    for name in SCRIPTS:files['promotion-tools/'+name]=(Path(__file__).parent/name).read_bytes()
    files['README.txt']=b'Arcane Wars 0.5.1 stable: exact accepted 0.5.1-beta.5 helper inputs; only patch identity changes. No game EXE, RWD, saves, profiles or signing keys. Remap build-report compiler arguments by sources SHA-256 to inputs/<sha>/<filename>, redirect /out to an owned G: folder, retain resource names and put both INIs next to the helpers. Compiler is ordinary Windows .NET Framework x86 csc. The promotion tools use a pinned workspace and recorded baseline; their publication actions require explicit authorization and the production signing key. No live game was launched for this promotion.\n'
    files['manifest.json']=encode({name:dict(size=len(data),sha256=hashlib.sha256(data).hexdigest().upper()) for name,data in files.items()})
    path=OUT/('arcane-'+VERSION+'-build-inputs.zip')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,11,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
    write(OUT/'bundle.json',dict(path=str(path),sha256=sha(path),size=path.stat().st_size,files=len(files)));print('BUILD_INPUTS_BUNDLED',len(files),flush=True)
def commit_files(parent,root,paths,message,label):
    assert head()==parent,'Public main moved; rebase preparation before publication'
    e=env();e['GIT_INDEX_FILE']=str(OUT/(label+'-private-index'));assert not Path(e['GIT_INDEX_FILE']).exists()
    def command(*args):return subprocess.check_output(['git',*args],cwd=REPO,env=e,text=True).strip()
    command('read-tree',parent);command('--work-tree='+str(root),'add','--',*paths);tree=command('write-tree')
    body=OUT/(label+'-commit.txt');body.write_text(message+'\n',encoding='utf-8');commit=command('commit-tree',tree,'-p',parent,'-F',str(body))
    assert set(command('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines())==set(paths)
    assert head()==parent;command('push','origin',commit+':refs/heads/main');unchanged();return commit
def source():
    prep=gate();bundle();base=prep['publicHead'];assert head()==base
    root=OUT/'source-publication';root.mkdir(exist_ok=False);paths=[]
    def add(rel,data):
        assert subprocess.run(['git','cat-file','-e',base+':'+rel],cwd=REPO,capture_output=True).returncode!=0,'Refusing to replace existing public source path'
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);paths.append(rel)
    for name in SCRIPTS:add('tools/Arcane051StablePromotion/'+name,(Path(__file__).parent/name).read_bytes())
    add('docs/release-patch-0.5.1.json',(OUT/'release-patch-0.5.1.json').read_bytes())
    add('docs/verification-arcane-stable-0.5.1-20261115.md',(OUT/'verification.md').read_bytes())
    commit=commit_files(base,root,paths,'Prepare Arcane Wars 0.5.1 stable from accepted beta.5','source')
    write(OUT/'source-publication.json',dict(commit=commit,files=paths,sha256={rel:sha(root/rel) for rel in paths}));print('SOURCE_PUBLIC',commit,flush=True)
def credential_request(path):
    credential=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',cwd=REPO,text=True,capture_output=True,check=True,env=env())
    token=os.environ.get('GH_TOKEN') or dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line).get('password');assert token
    req=urllib.request.Request(API+path,headers={'Authorization':'Bearer '+token,'User-Agent':'PawsArcaneStablePromotion','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
def ci(phase):
    commit=read(OUT/('source-publication.json' if phase=='source' else 'publication.json'))['commit' if phase=='source' else 'catalogCommit']
    rows=credential_request('/actions/runs?head_sha='+commit+'&per_page=25')['workflow_runs'];rows=[r for r in rows if r['name']=='Build and test' and r['head_sha']==commit and r['event']=='push']
    if not rows:print('CI_PENDING',phase);return
    r=max(rows,key=lambda r:r['run_number']);result={k:r[k] for k in ['id','head_sha','status','conclusion','html_url']};write(OUT/(phase+'-ci.json'),result);print(json.dumps(result),flush=True)
    if r['status']=='completed' and r['conclusion']!='success':raise RuntimeError('Required CI failed: '+r['html_url'])
def release():
    prep=gate();source=read(OUT/'source-publication.json');commit=source['commit'];assert head()==commit
    assert read(OUT/'source-ci.json')['head_sha']==commit and read(OUT/'source-ci.json')['conclusion']=='success'
    assert all(sha(OUT/'source-publication'/p)==h for p,h in source['sha256'].items())
    bundle=read(OUT/'bundle.json');assert sha(bundle['path'])==bundle['sha256']
    paths=[a['path'] for a in prep['assets']]+[bundle['path']]
    print(run([sys.executable,REPO/'tools/PublishLauncherRelease.py',VERSION,commit,OUT/'notes.md',*paths,'--tag',TAG,'--name','Paw’s Patch '+VERSION+' — Arcane Wars'],OUT/'upload.log'),flush=True)
    r=credential_request('/releases/tags/'+TAG);assert not r['draft'] and not r['prerelease'];remote={a['name']:a for a in r['assets']};checks={}
    def check(path):
        path=Path(path);a=remote[path.name];data=fetch(a['browser_download_url']);assert len(data)==path.stat().st_size and hashlib.sha256(data).hexdigest().upper()==sha(path) and a['digest']=='sha256:'+sha(path).lower();return path.name,dict(size=len(data),sha256=sha(path))
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:checks=dict(pool.map(check,paths))
    assert credential_request('/releases/latest')['tag_name']=='v1.0.18'
    write(OUT/'public-assets.json',dict(passed=True,url=r['html_url'],tag=TAG,sourceCommit=commit,assets=checks));print('PUBLIC_ASSETS_VERIFIED',len(checks),r['html_url'],flush=True)
def promote():
    prep=gate();assert read(OUT/'public-assets.json')['passed'];commit=read(OUT/'source-publication.json')['commit'];assert head()==commit
    for rel in read(OUT/'baseline.json')['feeds']:assert normalize(fetch(RAW.replace('/main/','/'+commit+'/')+rel))==normalize((OUT/'before'/rel).read_bytes()),rel
    catalog=commit_files(commit,OUT/'signed',prep['changed'],'Publish signed Arcane Wars 0.5.1 stable catalogs','catalog')
    write(OUT/'publication.json',dict(sourceCommit=commit,catalogCommit=catalog,version=VERSION,betaRetained=BETA,release=read(OUT/'public-assets.json')['url'],installedGameModified=False));print('STABLE_CATALOGS_PUBLIC',catalog,flush=True)
def readback():
    prep=read(OUT/'preparation.json');proof=read(OUT/'publication.json');commit=proof['catalogCommit'];assert head()==commit
    for rel in read(OUT/'baseline.json')['feeds']:
        data=fetch(RAW.replace('/main/','/'+commit+'/')+rel);assert normalize(data)==normalize((OUT/'signed'/rel).read_bytes()),rel
        if rel.startswith(('feed/v2/','feed/v3/')):verify(json.loads(data),key())
        if rel not in prep['changed']:assert normalize(data)==normalize((OUT/'before'/rel).read_bytes()),rel
    for prefix in ['v2','v3']:
        f=verify(json.loads(fetch(RAW+f'feed/{prefix}/stable.json?arcane051='+commit)),key());assert f==verify(read(OUT/'signed'/f'feed/{prefix}/stable.json'),key()),'Canonical feed has not propagated yet'
    assert credential_request('/releases/latest')['tag_name']=='v1.0.18';r=credential_request('/releases/tags/'+TAG);assert not r['prerelease'] and not r['draft']
    assert credential_request('/releases/tags/patch-'+BETA)['prerelease'];unchanged()
    proof.update(passed=True,packages=17,helpers=8,selfTests=40,catalogSelections=55296,installationCases=12,gamesLaunched=False);write(OUT/'readback.json',proof);print('PUBLIC_STABLE_READBACK_PASS',json.dumps(proof),flush=True)
if __name__=='__main__':
    action=sys.argv[1]
    if action.startswith('ci-'):ci(action[3:])
    else:globals()[action]()
