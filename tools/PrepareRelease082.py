"""Promote all accepted beta.8 test payloads and the CI-built launcher 0.8.2.

No publication is performed here. Prepare, finalize, verify-public and promote
are separate steps. Legacy catalogs retain their older gameplay schema.
"""
import argparse, copy, hashlib, json, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, API, key, normalize, fetch, sign
from PrepareRelease070 import read, write, encode, sha, verify, validate_package

REPO = Path(__file__).resolve().parents[1]
VERSION = '0.8.2'
PATCH = '0.3.0-beta.8'
TAG = 'patch-'+PATCH
DOWNLOAD = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'
CHANGED = {'pawpatch-core': PATCH, 'player-colors': PATCH,
           'common-ui': '1.3.72-ui.7-beta.8',
           **{'localization-'+c: '1.0.1-beta.8' for c in ('de','fr','cs','uk')}}

def notes_entry(filename, version, patch=False):
    parts=(REPO/'docs'/filename).read_text('utf-8').split('\n---\n')
    bodies={c:s.strip().split('\n',2)[2].strip() for c,s in zip(('ru','en'),parts)}
    entry=dict(category='patch' if patch else 'launcher',version=version,publishedAt='2026-09-16',
        title=dict(ru="Paw's Patch "+version+' — города и цвета' if patch else "Paw's Launcher "+version+' — интерфейс и чат',
                   en="Paw's Patch "+version+' — cities and colors' if patch else "Paw's Launcher "+version+' — interface and chat'),body=bodies)
    if patch:entry.update(mod='arcane-wars',channel='beta')
    return entry

def package_files(path, package):
    validate_package(path,package)
    with zipfile.ZipFile(path) as z:
        manifest=json.loads(z.read('module.json'))
        return manifest,{f['path']:z.read('payload/'+f['path']) for f in manifest['files']}

def prepare(a):
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before={n:verify(read(REPO/p),key()) for n,p in FEEDS.items()}
    testkey=serialization.load_pem_public_key(read(a.feeds/'launcher.config.json')['publicKeyPem'].encode())
    accepted=verify(read(a.feeds/'beta.json'),testkey)
    assert accepted['patchGuide']['version']=='0.3.0-beta.8-test.10'
    assert accepted['playerColorCount']==48
    for n,p in FEEDS.items():
        assert before[n]['launcher']['version']=='0.8.1'
        assert normalize(fetch(RAW+p+'?release082=baseline'))==normalize((REPO/p).read_bytes()),p
        target=out/'previous'/(n+'.json');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((REPO/p).read_bytes())
    prior={p['id']:p for p in before['beta']['packages']}
    assert len(accepted['packages'])==len(prior)==59
    assert {p['id'] for p in accepted['packages'] if p!=prior[p['id']]}==set(CHANGED)
    ignored={'publishedAt','changelog','patchGuide','playerColorCount','packages'}
    assert {k:v for k,v in accepted.items() if k not in ignored}=={k:v for k,v in before['beta'].items() if k not in ignored}
    variants=read(REPO/'game/beta7/variants.json');features={}
    for name in variants:
        f=json.loads(subprocess.check_output([str(a.helpers/name),'--features'],text=True))
        assert f['patchVersion']==PATCH and f['cityPolicyRevision']==23 and f['lobbyCompatibility']
        features[name]=dict(sha256=sha(a.helpers/name),features=f)
    assets=[];scope={};packages=copy.deepcopy(accepted['packages']);helper_copies=[]
    for p in packages:
        if p['id'] not in CHANGED:continue
        original=Path(p['urls'][0]);manifest,files=package_files(original,p)
        accepted_hashes={n:hashlib.sha256(b).hexdigest().upper() for n,b in files.items()}
        old=prior[p['id']];oldpath=out/'baseline-packages'/(p['id']+'.zip');oldpath.parent.mkdir(exist_ok=True)
        oldpath.write_bytes(fetch(old['urls'][0]));_,oldfiles=package_files(oldpath,old)
        promoted=[]
        for name in files:
            if name in variants or name=='paws_patch_versions.ini':
                files[name]=(a.helpers/name).read_bytes();promoted.append(name)
                if name in variants:helper_copies.append(name)
        version=CHANGED[p['id']];manifest['version']=version
        manifest['files']=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(files.items())]
        assert not manifest.get('remove')
        path=out/'assets'/(p['id']+'-'+version+'.zip');path.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for n,b in [('module.json',encode(manifest))]+[('payload/'+n,b) for n,b in sorted(files.items())]:
                info=zipfile.ZipInfo(n,(2026,9,16,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
        p.update(version=version,size=path.stat().st_size,sha256=sha(path),urls=[DOWNLOAD+TAG+'/'+path.name])
        validate_package(path,p)
        _,final=package_files(path,p)
        assert set(final)==set(accepted_hashes)
        assert all(hashlib.sha256(final[n]).hexdigest().upper()==h for n,h in accepted_hashes.items() if n not in promoted)
        assert set(final)==set(oldfiles)
        scope[p['id']]=dict(acceptedArchive=sha(original),publicBefore=old['sha256'],promotionOnly=promoted,
            changedSincePublic=[n for n in final if final[n]!=oldfiles[n]],
            preservedAcceptedFiles=len(final)-len(promoted))
        assets.append(dict(id=p['id'],path=str(path),size=p['size'],sha256=p['sha256'],url=p['urls'][0]))
    assert set(helper_copies)==set(variants) and len(helper_copies)==9
    launch=notes_entry('release-0.8.2.md',VERSION);patch=notes_entry('release-'+TAG+'.md',PATCH,True)
    history=read(REPO/'feed/changelog.history.json')
    for n,old in before.items():
        f=copy.deepcopy(old);f['changelog']=[launch]+old['changelog'];f.update(newsTitle=launch['title'],newsBody=launch['body'])
        if n=='beta':
            f.update(packages=packages,patchGuide=copy.deepcopy(accepted['patchGuide']),playerColorCount=48)
            f['patchGuide']['version']=PATCH;f['changelog']=[launch,patch]+old['changelog']
        if not n.startswith('legacy-'):history[n]=f['changelog']
        write(out/'payloads'/(n+'.json'),f)
    write(out/'changelog.history.json',history);write(out/'scope.json',scope);write(out/'features.json',features)
    write(out/'preparation.json',dict(assets=assets,before={n:sha(REPO/p) for n,p in FEEDS.items()},
        historyBefore=sha(REPO/'feed/changelog.history.json'),notes={n:sha(REPO/'docs'/n) for n in ('release-0.8.2.md','release-'+TAG+'.md')}))
    print('PREPARED: all 7 changed packages; 9 helper copies; accepted non-identity payload bytes preserved',flush=True)

def finalize(a):
    out=a.out.resolve();prep=read(out/'preparation.json')
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),password=None)
    assert private.public_key().public_numbers()==key().public_numbers()
    artifact=read(a.launcher.parent/'launcher-artifact.json');assert artifact['version']==VERSION
    exe=next(f for f in artifact['files'] if f['name']=='PawsPatchLauncher.exe')
    assert sha(a.launcher)==exe['sha256'] and a.launcher.stat().st_size==exe['size']
    launcher=dict(version=VERSION,size=exe['size'],sha256=exe['sha256'],urls=[DOWNLOAD+'v'+VERSION+'/PawsPatchLauncher.exe'])
    paths={}
    for p in prep['assets']:
        local=out/'validation-feeds/packages'/Path(p['path']).name
        local.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p['path'],local)
        paths[p['id']]=str(local)
    for n in FEEDS:
        f=read(out/'payloads'/(n+'.json'));f.update(launcher=launcher,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        assert all(u.startswith('https://') for p in f['packages'] for u in p['urls'])
        write(out/'signed'/(n+'.json'),sign(f,private))
        if n in ('stable','beta'):
            local=copy.deepcopy(f)
            if n=='beta':
                for p in local['packages']:
                    if p['id'] in paths:p['urls']=[paths[p['id']]]
            write(out/'validation-feeds'/(n+'.json'),sign(local,private))
    config=read(REPO/'src/PawsPatchLauncher/launcher.config.json')
    config.update(feedUrls=[str(out/'validation-feeds/stable.json')],betaFeedUrls=[str(out/'validation-feeds/beta.json')])
    write(out/'validation-feeds/launcher.config.json',config)
    write(out/'release-plan.json',dict(sourceCommit=artifact['sourceCommit'],launcher=launcher,assets=prep['assets']))
    print('SIGNED: 4 catalogs; stable and legacy gameplay unchanged',flush=True)

def public(a):
    out=a.out.resolve();plan=read(out/'release-plan.json')
    release=json.loads(fetch(API+'/releases/tags/v'+VERSION));assert not release['draft'] and not release['prerelease']
    beta=json.loads(fetch(API+'/releases/tags/'+TAG));assert not beta['draft'] and beta['prerelease']
    for tag in ('v'+VERSION,TAG):
        ref=json.loads(fetch(API+'/git/ref/tags/'+tag))['object']
        while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
        assert ref['type']=='commit' and ref['sha']==plan['sourceCommit']
    for p in plan['assets']+[dict(plan['launcher'],url=plan['launcher']['urls'][0],id='launcher')]:
        data=fetch(p['url']);assert len(data)==p['size'] and hashlib.sha256(data).hexdigest().upper()==p['sha256'].upper()
        print('PUBLIC PASS',p['id'],len(data),flush=True)
    write(out/'public-verification.json',dict(passAll=True,sourceCommit=plan['sourceCommit'],assets=len(plan['assets'])+1))

def promote(a):
    out=a.out.resolve();prep=read(out/'preparation.json');assert read(out/'public-verification.json')['passAll']
    for n,h in prep['notes'].items():assert sha(REPO/'docs'/n)==h
    for n,p in FEEDS.items():
        assert sha(REPO/p)==prep['before'][n]
        assert normalize(fetch(RAW+p+'?release082=promotion'))==normalize((REPO/p).read_bytes())
        verify(read(out/'signed'/(n+'.json')),key())
    assert sha(REPO/'feed/changelog.history.json')==prep['historyBefore']
    for n,p in FEEDS.items():
        backup=REPO/'feed/history'/('before-launcher-082-'+n+'.json');assert not backup.exists()
        shutil.copyfile(REPO/p,backup);shutil.copyfile(out/'signed'/(n+'.json'),REPO/p)
    shutil.copyfile(out/'changelog.history.json',REPO/'feed/changelog.history.json')
    write(REPO/'feed/patch-guide-beta.json',verify(read(out/'signed/beta.json'),key())['patchGuide'])
    print('PROMOTED LOCALLY: push and remote readback required',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','finalize','verify-public','promote'])
    p.add_argument('--out',type=Path,required=True)
    for x in ('feeds','helpers','launcher','signing-dir'):p.add_argument('--'+x,type=Path)
    a=p.parse_args();{'prepare':prepare,'finalize':finalize,'verify-public':public,'promote':promote}[a.action](a)
