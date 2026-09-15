"""Promote the accepted 0.8.1 language candidate without changing payload files.

Stages immutable packages, signs catalogs, and verifies public bytes before local
catalog promotion. Uploading and pushing are separate explicit operations.
Legacy feeds retain their game packages for launchers older than the v2 schema.
"""
import argparse, base64, copy, json, re, shutil, subprocess, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from PrepareRelease070 import read, write, encode, sha, verify, validate_package

REPO = Path(__file__).resolve().parents[1]
VERSION = '0.8.1'
TAG = 'v' + VERSION
DOWNLOAD = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/' + TAG + '/'
RAW = 'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/'
API = 'https://api.github.com/repos/VasiliyPaw/PawsPatchLauncher'
FEEDS = {'stable':'feed/v2/stable.json', 'beta':'feed/v2/beta.json',
         'legacy-stable':'feed/stable.json', 'legacy-beta':'feed/beta.json'}

def key():
    return serialization.load_pem_public_key(read(REPO/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'].encode())

def normalize(raw): return raw.replace(b'\r\n', b'\n')

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent':'PawsRelease081', 'Cache-Control':'no-cache'})
    with urllib.request.urlopen(request, timeout=90) as response: return response.read()

def sign(feed, private):
    payload = encode(feed)
    r, s = utils.decode_dss_signature(private.sign(payload, ec.ECDSA(hashes.SHA256())))
    result = dict(keyId='pawpatch-prod-2026', payload=base64.b64encode(payload).decode(),
                  signature=base64.b64encode(r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode())
    assert verify(result, key()) == feed
    return result

def prepare(a):
    out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    assert not (out/'preparation.json').exists(), 'Use a fresh staging directory'
    old={name:verify(read(REPO/path),key()) for name,path in FEEDS.items()}
    accepted={c:verify(read(a.feeds/(c+'.json')),key()) for c in ('stable','beta')}
    for name,path in FEEDS.items():
        before=(REPO/path).read_bytes()
        assert normalize(fetch(RAW+path+'?release081=baseline'))==normalize(before), 'Public feed moved: '+path
        target=out/'previous'/(name+'.json'); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(before)
    history=read(REPO/'feed/changelog.history.json')
    write(out/'previous/history.json',history)
    sections=(REPO/'docs/release-0.8.1.md').read_text('utf-8').split('\n---\n')
    entry=dict(category='launcher',version=VERSION,publishedAt='2026-09-15',
        title=dict(ru="Paw's Launcher 0.8.1 — языки игры и удобство чата",en="Paw's Launcher 0.8.1 — game languages and chat improvements"),
        body={c:s.split('\n',2)[2].strip() for c,s in zip(('ru','en'),(sections[0],sections[1].lstrip()))})
    known={p['sha256'].upper():p for f in old.values() for p in f['packages']}
    assets={}; replacements={}; payload_count=0
    for channel,test in accepted.items():
        previous=old[channel]
        assert previous['launcher']['version']=='0.8.0'
        assert test['game']==previous['game'] and test['modGames']==previous['modGames']
        assert len(test['packages'])==59 and len({p['id'] for p in test['packages']})==59
        assert {p['id'] for p in previous['packages']} <= {p['id'] for p in test['packages']}
        for p in test['packages']:
            original=p['sha256'].upper()
            if original not in replacements:
                if original in known:
                    q=known[original]
                    assert p['id']==q['id'] and p['version']==q['version'] and p['size']==q['size']
                    replacements[original]={k:copy.deepcopy(q[k]) for k in ('version','size','sha256','urls')}
                else:
                    source=Path(p['urls'][0]); assert source.is_file(),p['id']
                    payload_count+=validate_package(source,p)
                    # Release labels change only module.json. All tested payload bytes
                    # remain identical, including native helpers and their core identity.
                    # Core versions are intentionally retained: beta helpers require the
                    # exact beta.7 identifier. The immutable URL/hash identifies this
                    # multilingual revision; no old release asset is replaced.
                    version=re.sub(r'-preview\..*$', '', p['version'])
                    dest=out/'assets'/(p['id']+'-'+version+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
                    assert not dest.exists(),dest
                    if version==p['version']:shutil.copyfile(source,dest)
                    else:
                        with zipfile.ZipFile(source) as zin,zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as zout:
                            for item in zin.infolist():
                                data=zin.read(item.filename)
                                if item.filename=='module.json':
                                    module=json.loads(data);module['version']=version;data=encode(module)
                                zout.writestr(item.filename,data)
                        with zipfile.ZipFile(source) as zin,zipfile.ZipFile(dest) as zout:
                            assert zin.namelist()==zout.namelist()
                            assert all(zin.read(n)==zout.read(n) for n in zin.namelist() if n!='module.json')
                    q=dict(version=version,size=dest.stat().st_size,sha256=sha(dest),urls=[DOWNLOAD+dest.name])
                    validate_package(dest,dict(p,**q))
                    replacements[original]=q
                    assets[dest.name]=dict(id=p['id'],path=str(dest),sourceSha256=original,**q)
            p.update(copy.deepcopy(replacements[original]))
        # Preserve current public metadata/history, bringing in only accepted
        # language-aware guides and package choices from the test feed.
        final=copy.deepcopy(previous)
        for field in ('packages','patchGuide','modGuides'):final[field]=copy.deepcopy(test[field])
        final['changelog']=[entry]+previous['changelog']
        final['newsTitle']=entry['title'];final['newsBody']=entry['body']
        write(out/'payloads'/(channel+'.json'),final)
        legacy=copy.deepcopy(old['legacy-'+channel]);legacy['changelog']=[entry]+legacy['changelog']
        legacy['newsTitle']=entry['title'];legacy['newsBody']=entry['body']
        write(out/'payloads'/('legacy-'+channel+'.json'),legacy)
        history[channel]=final['changelog']
    write(out/'changelog.history.json',history)
    write(out/'preparation.json',dict(version=VERSION,assets=list(assets.values()),payloadFiles=payload_count,
        before={n:sha(out/'previous'/(n+'.json')) for n in FEEDS},historyBefore=sha(REPO/'feed/changelog.history.json'),
        notesSha256=sha(REPO/'docs/release-0.8.1.md')))
    print('STAGED',len(assets),'immutable archives;',payload_count,'payload files validated',flush=True)

def finalize(a):
    out=a.out.resolve();prepared=read(out/'preparation.json')
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),password=None)
    assert private.public_key().public_numbers()==key().public_numbers()
    artifact=read(a.launcher.parent/'launcher-artifact.json')
    assert artifact['version']==VERSION and re.fullmatch('[0-9a-f]{40}',artifact['sourceCommit'])
    record=next(f for f in artifact['files'] if f['name']=='PawsPatchLauncher.exe')
    assert sha(a.launcher)==record['sha256'] and a.launcher.stat().st_size==record['size']
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    launcher=dict(version=VERSION,size=record['size'],sha256=record['sha256'],urls=[DOWNLOAD+'PawsPatchLauncher.exe'])
    paths={asset['sha256']:asset['path'] for asset in prepared['assets']}
    for name in FEEDS:
        final=read(out/'payloads'/(name+'.json'));final.update(launcher=launcher,publishedAt=stamp)
        assert all(all(u.startswith('https://') for u in p['urls']) for p in final['packages'])
        if name.startswith('legacy-'):
            before=verify(read(out/'previous'/(name+'.json')),key())
            ignored={'launcher','publishedAt','changelog','newsTitle','newsBody'}
            assert {k:v for k,v in before.items() if k not in ignored}=={k:v for k,v in final.items() if k not in ignored}
        write(out/'signed'/(name+'.json'),sign(final,private))
        if not name.startswith('legacy-'):
            local=copy.deepcopy(final)
            for p in local['packages']:
                if p['sha256'] in paths:p['urls']=[paths[p['sha256']]]
            write(out/'validation-feeds'/(name+'.json'),sign(local,private))
    config=read(REPO/'src/PawsPatchLauncher/launcher.config.json')
    config['feedUrls']=[str(out/'validation-feeds/stable.json')]
    config['betaFeedUrls']=[str(out/'validation-feeds/beta.json')]
    write(out/'validation.config.json',config)
    write(out/'release-plan.json',dict(version=VERSION,sourceCommit=artifact['sourceCommit'],launcher=launcher,assets=prepared['assets']))
    print('SIGNED 4 production catalogs; legacy gameplay preserved; source',artifact['sourceCommit'],flush=True)

def promote(a):
    out=a.out.resolve();prepared=read(out/'preparation.json');plan=read(out/'release-plan.json')
    assert sha(REPO/'docs/release-0.8.1.md')==prepared['notesSha256']
    assert (out/'public-assets-verification.log').read_text('utf-8').strip().splitlines()[-1].startswith('PUBLICATION PASS ')
    release=json.loads(fetch(API+'/releases/tags/'+TAG));assert not release['draft'] and not release['prerelease']
    assert json.loads(fetch(API+'/releases/latest'))['tag_name']==TAG
    tag=json.loads(fetch(API+'/git/ref/tags/'+TAG))['object']
    while tag['type']=='tag':tag=json.loads(fetch(API+'/git/tags/'+tag['sha']))['object']
    assert tag['type']=='commit' and tag['sha']==plan['sourceCommit']
    assets={p['name']:p for p in release['assets']}
    for p in prepared['assets']+[dict(plan['launcher'],path='PawsPatchLauncher.exe')]:
        asset=assets[Path(p['path']).name]
        assert asset['size']==p['size'] and asset['digest'].lower()=='sha256:'+p['sha256'].lower()
    for name,path in FEEDS.items():
        assert sha(REPO/path)==prepared['before'][name]
        assert normalize(fetch(RAW+path+'?release081=promotion'))==normalize((REPO/path).read_bytes()),'Public feed moved'
        verify(read(out/'signed'/(name+'.json')),key())
    assert sha(REPO/'feed/changelog.history.json')==prepared['historyBefore']
    guides={'stable':'patch-guide.json','beta':'patch-guide-beta.json'}
    for channel,filename in guides.items():
        assert read(REPO/'feed'/filename)==verify(read(out/'previous'/(channel+'.json')),key())['patchGuide']
    for name,path in FEEDS.items():
        backup=REPO/'feed/history'/('before-launcher-081-'+name+'.json');assert not backup.exists()
        shutil.copyfile(REPO/path,backup);shutil.copyfile(out/'signed'/(name+'.json'),REPO/path)
    shutil.copyfile(out/'changelog.history.json',REPO/'feed/changelog.history.json')
    for channel,filename in guides.items():
        write(REPO/'feed'/filename,verify(read(out/'signed'/(channel+'.json')),key())['patchGuide'])
    print('PROMOTED LOCALLY: 4 catalogs; push and public readback still required',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','finalize','promote'])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--feeds',type=Path)
    parser.add_argument('--launcher',type=Path)
    parser.add_argument('--signing-dir',type=Path)
    args=parser.parse_args()
    {'prepare':prepare,'finalize':finalize,'promote':promote}[args.action](args)
