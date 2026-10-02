"""Stage and publish catalogs for the Pure beta.2 AI compatibility update.

Only two Pure beta packages change. Publication of immutable assets is separate.
Stable, legacy feeds, Arcane packages and the launcher are preserved byte-for-byte.
"""
import argparse, copy, hashlib, json, shutil, subprocess, sys, zipfile, io
from pathlib import Path
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, API, key, sign, fetch, normalize
from PrepareRelease070 import read, write, sha, verify, validate_package

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'game/pure-fixes'))
import build

VERSION = '0.4.0-beta.2'
TAG = 'patch-pure-' + VERSION
RUNTIME = '1.3.72-pure.13-beta.2'
IDS = {'pure-fixes-runtime', 'pure-fixes-data'}
DOWNLOAD = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/' + TAG + '/'

def private(a):
    result = serialization.load_pem_private_key(a.private_key.read_bytes(), None)
    assert result.public_key().public_numbers() == key().public_numbers()
    return result

def scoped(before, after):
    assert before['launcher'] == after['launcher']
    assert [p for p in before['packages'] if p['id'] not in IDS] == [p for p in after['packages'] if p['id'] not in IDS]
    assert {p['id'] for p in before['packages']} == {p['id'] for p in after['packages']}
    for p in after['packages']:
        if p['id'] in IDS: assert set(p['mods']) == {'vanilla','immortals'}
    guides = copy.deepcopy(after['modGuides'])
    for old, new in zip(before['modGuides'], guides):
        if old['id'] in ('vanilla','immortals'):
            assert new['patchGuide']['version'] == VERSION
            new['patchGuide']['version'] = old['patchGuide']['version']
    assert guides == before['modGuides']
    for field in before:
        if field not in {'packages','modGuides','changelog','publishedAt'}: assert before[field] == after[field], field

def prepare(a):
    out=a.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    baseline={}
    for name,path in FEEDS.items():
        assert normalize(fetch(RAW+path+'?pure-ai=baseline')) == normalize((ROOT/path).read_bytes()), path
        baseline[path]=sha(ROOT/path)
        shutil.copyfile(ROOT/path,out/(name+'-before.json'))
    baseline['feed/changelog.history.json']=sha(ROOT/'feed/changelog.history.json')
    assert json.loads(fetch(RAW+'feed/changelog.history.json?pure-ai=baseline')) == read(ROOT/'feed/changelog.history.json')
    before=verify(read(ROOT/FEEDS['beta']),key()); after=copy.deepcopy(before); assets=[]
    for package in after['packages']:
        if package['id'] not in IDS: continue
        original=copy.deepcopy(package)
        if package['id']=='pure-fixes-runtime':
            files={p.name:p.read_bytes() for p in a.helpers.glob('k2_paws_*.exe')}
            assert len(files)==4
            features=read(a.helpers/'features.json')
            for name,data in files.items():
                assert hashlib.sha256(data).hexdigest().upper()==features[name]['sha256']
                f=features[name]['features']; assert f['aiPolicyProfile']=='pure' and f['aiPolicyCompatibilityRevision']==1
                assert f['patchVersion']==VERSION
            version=RUNTIME
        else:
            raw=fetch(original['urls'][0])
            assert len(raw)==original['size'] and hashlib.sha256(raw).hexdigest().upper()==original['sha256'].upper()
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                files={n[8:]:z.read(n) for n in z.namelist() if n.startswith('payload/')}
            version=VERSION
        fresh=build.package(out,package['id'],version,files,package['executableIndependent'],package['priority'],package['name'],package['description'])
        path=Path(fresh['urls'][0]); validate_package(path,fresh)
        # Retain every existing selector/dependency and change only artifact identity.
        for field in ('version','size','sha256'):package[field]=fresh[field]
        package['urls']=[DOWNLOAD+path.name]
        assets.append(dict(id=package['id'],path=str(path),url=package['urls'][0],size=package['size'],sha256=package['sha256']))
    assert len(assets)==2
    for guide in after['modGuides']:
        if guide['id'] in ('vanilla','immortals'):guide['patchGuide']['version']=VERSION
    notes=read(ROOT/'docs/release-pure-0.4.0-beta.2.json')
    after['changelog']=[notes]+after['changelog']; after['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    scoped(before,after);write(out/'payload.json',after)
    history=read(ROOT/'feed/changelog.history.json');history['beta']=[notes]+history['beta'];write(out/'history.json',history)
    local=copy.deepcopy(after)
    for p in local['packages']:
        if p['id'] in IDS:p['urls']=[next(x['path'] for x in assets if x['id']==p['id'])]
    write(out/'beta.json',sign(local,private(a)));shutil.copyfile(ROOT/FEEDS['stable'],out/'stable.json')
    (out/'public.pem').write_bytes(key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
    write(out/'preparation.json',dict(baseline=baseline,assets=assets,notesSha=sha(ROOT/'docs/release-pure-0.4.0-beta.2.json')))
    print('PURE_AI_RELEASE_PREPARED',out)

def promote(a):
    out=a.out;prep=read(out/'preparation.json')
    assert read(a.launch_results/'summary.json')['complete']
    launches=[json.loads(line) for line in (a.launch_results/'launches.jsonl').read_text().splitlines() if line.strip()]
    current={r['id'] for r in launches if 'pure-fixes-runtime@'+RUNTIME in r['modules'] and r['phase']=='menu'}
    assert {mode+'-pure-beta-'+lang for mode in ('vanilla','immortals') for lang in ('en','ru','de','fr','cs','uk')} <= current
    tests=read(out.parent/'native-tests.json');assert tests and all(t['exitCode']==0 for t in tests)
    release=json.loads(fetch(API+'/releases/tags/'+TAG));assert not release['draft'] and release['prerelease']
    ref=json.loads(fetch(API+'/git/ref/tags/'+TAG))['object']
    while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
    assert ref['type']=='commit' and ref['sha']==a.commit
    for asset in prep['assets']:
        data=fetch(asset['url']);assert len(data)==asset['size'] and hashlib.sha256(data).hexdigest().upper()==asset['sha256']
        print('PUBLIC_BYTES_PASS',asset['id'])
    for path,digest in prep['baseline'].items():
        assert sha(ROOT/path)==digest,path
        assert normalize(fetch(RAW+path+'?pure-ai=promote'))==normalize((ROOT/path).read_bytes()),path
    assert sha(ROOT/'docs/release-pure-0.4.0-beta.2.json')==prep['notesSha']
    after=read(out/'payload.json');scoped(verify(read(out/'beta-before.json'),key()),after)
    write(ROOT/FEEDS['beta'],sign(after,private(a)));write(ROOT/'feed/changelog.history.json',read(out/'history.json'))
    write(out/'public-verification.json',dict(passed=True,sourceCommit=a.commit,tag=TAG))
    print('PROMOTED beta v2 and history only; push and readback required')

def readback(a):
    out=a.out;head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']==head
    prefix=RAW.replace('/main/','/'+head+'/')
    for name,path in FEEDS.items():
        data=fetch(prefix+path);assert normalize(data)==normalize((ROOT/path).read_bytes())
        if name=='beta':scoped(verify(read(out/'beta-before.json'),key()),verify(json.loads(data),key()))
        else:assert normalize(data)==normalize((out/(name+'-before.json')).read_bytes())
    assert json.loads(fetch(prefix+'feed/changelog.history.json'))==read(ROOT/'feed/changelog.history.json')
    write(out/'readback.json',dict(passed=True,catalogCommit=head,patch=VERSION))
    print('PUBLICATION_PASS',VERSION,head)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','promote','readback'])
    p.add_argument('--out',type=Path,required=True);p.add_argument('--helpers',type=Path);p.add_argument('--private-key',type=Path)
    p.add_argument('--commit');p.add_argument('--launch-results',type=Path)
    a=p.parse_args();globals()[a.action](a)
