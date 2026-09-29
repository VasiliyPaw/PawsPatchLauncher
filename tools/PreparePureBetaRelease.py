"""Publish Pure beta 0.4.0-beta.1 and launcher 0.8.12, preserving other game channels.

Preparation, public verification and catalog promotion are separate stages.
No game installation, launch, Git mutation or upload is performed here.
"""
import argparse, copy, hashlib, io, json, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, API, key, sign, fetch, normalize
from PrepareRelease070 import read, write, sha, verify, validate_package

ROOT = Path(__file__).resolve().parents[1]
VERSION, PATCH, TAG = '0.8.12', '0.4.0-beta.1', 'patch-pure-0.4.0-beta.1'
DOWNLOAD = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'
IDS = {'pure-fixes-data', 'pure-fixes-runtime', 'pure-beta-common', 'pure-ai-improvements', 'pure-lair-recovery', 'pure-independent-hostility'}
IDS |= {'pure-localization-bot-ui-'+lang for lang in ('en','ru','de','fr','cs','uk')}
IDS |= {'pure-'+mode+'-'+part for mode in ('vanilla','immortals') for part in ['rules','hostility']+[f'roaming-{speed}-{extra}' for speed in ('standard','x2','x4') for extra in ('with-new','no-new')]}

def private(a):
    p = serialization.load_pem_private_key(a.private_key.read_bytes(), None)
    assert p.public_key().public_numbers() == key().public_numbers()
    return p

def scoped(before, after):
    if before.get('channel') != 'beta':
        assert before['packages'] == after['packages'], 'Non-beta game packages changed'
        assert before.get('modGuides') == after.get('modGuides'), 'Non-beta guides changed'
    for field in before:
        if field not in {'packages','modGuides','pureRuntimeOptions','launcher','publishedAt','changelog','newsTitle','newsBody'}:
            assert after[field] == before[field], field
    assert [p for p in before['packages'] if p['id'] not in IDS] == [p for p in after['packages'] if p['id'] not in IDS]
    assert [g for g in before.get('modGuides',[]) if g['id'] not in ('vanilla','immortals')] == [g for g in after.get('modGuides',[]) if g['id'] not in ('vanilla','immortals')]

def prepare(a):
    out=a.out; assert not out.exists(), 'Use a fresh publication stage'
    out.mkdir(parents=True); pkey=private(a)
    before={n:verify(read(ROOT/p),key()) for n,p in FEEDS.items()};baseline={}
    for n,p in FEEDS.items():
        assert before[n]['launcher']['version']=='0.8.11'
        assert normalize(fetch(RAW+p+'?purebeta=baseline'))==normalize((ROOT/p).read_bytes()),p
        write(out/'previous'/(n+'.json'),read(ROOT/p));baseline[p]=sha(ROOT/p)
    pure=read(a.build/'packages.json');assets=[]
    assert {p['id'] for p in pure}==IDS
    for p in pure:
        src=Path(p['urls'][0]);validate_package(src,p)
        dest=out/'assets'/src.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(src,dest)
        p['urls']=[DOWNLOAD+TAG+'/'+dest.name]
        assert set(p['mods'])<= {'vanilla','immortals'}
        assert p['id']=='pure-fixes-data' or p['experimental']
        assets.append(dict(id=p['id'],path=str(dest.resolve()),url=p['urls'][0],sha256=p['sha256'],size=p['size']))
    patch=read(ROOT/'docs/release-pure-0.4.0-beta.1.json');launch=read(ROOT/'docs/release-0.8.12.json')
    history=read(ROOT/'feed/changelog.history.json');baseline['feed/changelog.history.json']=sha(ROOT/'feed/changelog.history.json')
    replacements={p['id']:p for p in pure};guides=read(ROOT/'docs/pure-beta-guide-0.4.0-beta.1.json')
    for name,b in before.items():
        f=copy.deepcopy(b)
        notes=[launch,patch] if name=='beta' else [launch]
        if name=='beta':
            f['packages']=[copy.deepcopy(replacements.get(p['id'],p)) for p in f['packages']]
            present={p['id'] for p in f['packages']}
            f['packages'] += [copy.deepcopy(p) for p in pure if p['id'] not in present]
            for guide in f['modGuides']:
                if guide['id'] in ('vanilla','immortals'):
                    old={e['id'] for e in guide['patchGuide']['entries']}
                    assert not old.intersection(e['id'] for e in guides)
                    guide['patchGuide']['version']=PATCH;guide['patchGuide']['entries']+=guides
        else:
            assert f['packages']==b['packages'] and f.get('modGuides')==b.get('modGuides')
        f['changelog']=notes+f['changelog']
        if name in ('stable','beta'):history[name]=notes+history[name]
        f.update(newsTitle=launch['title'],newsBody=launch['body'])
        scoped(b,f);write(out/'payloads'/(name+'.json'),f)
        if name in ('stable','beta'):
            local=copy.deepcopy(f)
            if name=='beta':
                for p in local['packages']:
                    if p['id'] in IDS:p['urls']=[next(x['path'] for x in assets if x['id']==p['id'])]
            write(out/'test-feeds'/(name+'.json'),sign(local,pkey))
    write(out/'changelog.history.json',history)
    write(out/'preparation.json',dict(baseline=baseline,assets=assets,notes={p:sha(ROOT/p) for p in ('docs/release-pure-0.4.0-beta.1.json','docs/release-0.8.12.json','docs/pure-beta-guide-0.4.0-beta.1.json')}))
    print('PREPARED Pure beta only; stable Pure and all Arcane packages unchanged')

def release(tag,commit):
    r=json.loads(fetch(API+'/releases/tags/'+tag));assert not r['draft'] and r['prerelease']==(tag==TAG)
    ref=json.loads(fetch(API+'/git/ref/tags/'+tag))['object']
    while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
    assert ref['type']=='commit' and ref['sha']==commit
    return r

def finalize(a):
    out=a.out;prep=read(out/'preparation.json')
    release(TAG,a.commit);release('v'+VERSION,a.commit)
    assert json.loads(fetch(API+'/releases/latest'))['tag_name']=='v'+VERSION
    artifact=json.loads(fetch(DOWNLOAD+'v'+VERSION+'/launcher-artifact.json'))
    assert artifact['version']==VERSION and artifact['sourceCommit']==a.commit
    if artifact['authenticodeRequired']:assert artifact['authenticodeStatus']=='Valid' and artifact['timestamped']
    else:assert a.allow_unsigned_launcher and artifact['authenticodeStatus']=='NotSigned'
    write(out/'launcher-artifact.json',artifact)
    record=next(f for f in artifact['files'] if f['name']=='PawsPatchLauncher.exe')
    launcher=dict(version=VERSION,size=record['size'],sha256=record['sha256'],urls=[DOWNLOAD+'v'+VERSION+'/PawsPatchLauncher.exe'])
    for p in prep['assets']+[dict(launcher,id='launcher',url=launcher['urls'][0])]:
        data=fetch(p['url']);assert len(data)==p['size'] and hashlib.sha256(data).hexdigest().upper()==p['sha256'].upper()
        print('PUBLIC_BYTES_PASS',p['id'],flush=True)
    archive=next(f for f in artifact['files'] if f['name']=='PawsPatchLauncher-v'+VERSION+'-win-x64.zip')
    data=fetch(DOWNLOAD+'v'+VERSION+'/'+archive['name'])
    assert len(data)==archive['size'] and hashlib.sha256(data).hexdigest().upper()==archive['sha256'].upper()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        expected={f['name'] for f in artifact['files'] if f['name']!=archive['name']}
        assert set(z.namelist())==expected
        for record in artifact['files']:
            if record['name']==archive['name']:continue
            content=z.read(record['name'])
            assert len(content)==record['size'] and hashlib.sha256(content).hexdigest().upper()==record['sha256'].upper()
    print('PUBLIC_BYTES_PASS',archive['name'],flush=True)
    for name in FEEDS:
        f=read(out/'payloads'/(name+'.json'));f.update(launcher=launcher,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        write(out/'signed'/(name+'.json'),sign(f,private(a)))
    write(out/'public-verification.json',dict(passed=True,commit=a.commit,launcher=launcher))

def promote(a):
    out=a.out;prep=read(out/'preparation.json');public=read(out/'public-verification.json')
    assert public['passed'] and read(out.parent/'installation-verification.json')['passed']
    server=read(out.parent/'server-deployment.json')
    assert server['passed'] and server['independentReadback'] and all(server['checks'].values())
    for p,d in {**prep['baseline'],**prep['notes']}.items():assert sha(ROOT/p)==d,p
    for name,path in FEEDS.items():
        assert normalize(fetch(RAW+path+'?purebeta=promote'))==normalize((ROOT/path).read_bytes()),path
        before=verify(read(ROOT/path),key());after=verify(read(out/'signed'/(name+'.json')),key());scoped(before,after)
        assert after['launcher']==public['launcher']
    for name,path in FEEDS.items():shutil.copyfile(out/'signed'/(name+'.json'),ROOT/path)
    shutil.copyfile(out/'changelog.history.json',ROOT/'feed/changelog.history.json')
    print('PROMOTED LOCALLY: push and public readback still required')

def readback(a):
    out=a.out;head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']==head
    root=RAW.replace('/main/','/'+head+'/')
    for name,path in FEEDS.items():
        public=verify(json.loads(fetch(root+path)),key());assert public==verify(read(ROOT/path),key())
        scoped(verify(read(out/'previous'/(name+'.json')),key()),public)
    assert json.loads(fetch(root+'feed/changelog.history.json'))==read(ROOT/'feed/changelog.history.json')
    write(out/'readback.json',dict(passed=True,catalogCommit=head,patch=PATCH,launcher=VERSION))
    print('PUBLICATION_PASS Pure beta 0.4.0-beta.1 / launcher 0.8.12; 4 signed feeds; unchanged Arcane packages; '+head)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','finalize','promote','readback']);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--build',type=Path);p.add_argument('--private-key',type=Path);p.add_argument('--commit');p.add_argument('--allow-unsigned-launcher',action='store_true')
    a=p.parse_args();globals()[a.action](a)
