"""Stage 0.7.0 catalogs and immutable packages. Promotion is a separate operation.

Requires cryptography. Never uploads, changes a game installation, or prints keys.
The v1 catalogs retain their gameplay to protect users who defer the EXE update.
"""
import argparse, base64, copy, hashlib, json, shutil, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

REPO = Path(__file__).resolve().parents[1]
ROOT = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v0.7.0/'
VERSIONS = {'aw-player-colors':'1.0.0', 'immortals':'2.1.0', 'game-localization-en':'1.0.0',
            'immortals-text-fixes':'1.0.0', 'pure-fixes-data':'0.1.0'}

def read(path): return json.loads(Path(path).read_text('utf-8-sig'))
def encode(obj): return (json.dumps(obj, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
def write(path, obj): path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(encode(obj))
def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest().upper()
def verify(envelope, key):
    payload=base64.b64decode(envelope['payload'], validate=True); sig=base64.b64decode(envelope['signature'], validate=True)
    assert len(sig)==64
    key.verify(utils.encode_dss_signature(int.from_bytes(sig[:32],'big'),int.from_bytes(sig[32:],'big')),payload,ec.ECDSA(hashes.SHA256()))
    return json.loads(payload)
def validate_package(path, package):
    assert path.stat().st_size==package['size'] and sha(path)==package['sha256'].upper(),path
    with zipfile.ZipFile(path) as z:
        module=json.loads(z.read('module.json'))
        assert module['id']==package['id'] and module['version']==package['version']
        seen=set()
        for f in module['files']:
            p=f['path'].replace('\\','/'); assert not p.startswith('/') and '..' not in p.split('/') and ':' not in p and p.lower() not in seen
            seen.add(p.lower()); data=z.read('payload/'+p)
            assert len(data)==f['size'] and hashlib.sha256(data).hexdigest().upper()==f['sha256'].upper(),p
        return len(module['files'])

def prepare(args):
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    assert not (out/'preparation.json').exists(), 'Use a fresh staging directory.'
    public=serialization.load_pem_public_key(read(REPO/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'].encode())
    test=serialization.load_pem_public_key(read(args.test_config)['publicKeyPem'].encode())
    old={c:verify(read(REPO/f'feed/{c}.json'),public) for c in ('stable','beta')}
    known={p['sha256'].upper():p for f in old.values() for p in f['packages']}
    audited={c:verify(read(args.feeds/(c+'.json')),test) for c in old}
    notes=(REPO/'docs/release-0.7.0.md').read_text('utf-8').replace('**','').replace('\n- ','\n• ').split('\n---\n')
    entry=dict(category='launcher',version='0.7.0',publishedAt='2026-09-13',
        title=dict(ru="Paw's Launcher 0.7.0 — моды, установка и чаты",en="Paw's Launcher 0.7.0 — mods, installations and chat"),
        body=dict(ru=notes[0].split('\n',2)[2].strip(),en=notes[1].split('# English',1)[1].strip()))
    replacements={}; assets={}; verified={}; history={}
    for c,feed in audited.items():
        assert old[c]['launcher']['version']=='0.6.4' and feed['game']==old[c]['game']
        shutil.copy2(REPO/f'feed/{c}.json',out/f'previous-{c}.json')
        for p in feed['packages']:
            original=p['sha256'].upper()
            if original not in verified: verified[original]=validate_package(Path(p['urls'][0]),p)
            if original not in replacements:
                q=copy.deepcopy(p); source=Path(p['urls'][0]); q['version']=VERSIONS.get(p['id'],p['version'])
                if original in known and q['version']==p['version']:
                    assert known[original]['id']==q['id'] and known[original]['version']==q['version']
                    q['urls']=known[original]['urls']
                else:
                    target=out/'packages'/f"{q['id']}-{q['version']}.zip"; target.parent.mkdir(exist_ok=True)
                    if q['version']!=p['version']:
                        with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dest:
                            for info in src.infolist():
                                data=src.read(info.filename)
                                if info.filename=='module.json':
                                    module=json.loads(data); module['version']=q['version']; data=encode(module)
                                dest.writestr(info,data)
                    else: shutil.copy2(source,target)
                    q.update(size=target.stat().st_size,sha256=sha(target),urls=[ROOT+target.name])
                    assert validate_package(target,q)==verified[original]
                    assets[target.name]={'path':str(target),'size':q['size'],'sha256':q['sha256']}
                replacements[original]=q
            # Keep channel-specific display/required/dependency metadata.
            q=replacements[original]
            for field in ('version','size','sha256','urls'): p[field]=q[field]
        feed['changelog']=[entry]+[e for e in feed['changelog'] if not(e.get('category')=='launcher' and '-local.' in e.get('version',''))]
        for e in feed['changelog']:
            if e.get('category')=='patch' and e.get('mods') in (['vanilla'],['immortals']) and e.get('version')=='0.1.0': e['publishedAt']='2026-09-13'
        history[c]=feed['changelog']
        feed.update(newsTitle=entry['title'],newsBody=entry['body'])
        write(out/f'{c}.payload.json',feed)
        legacy=copy.deepcopy(old[c]);legacy.update(changelog=[entry]+old[c]['changelog'],newsTitle=entry['title'],newsBody=entry['body'])
        write(out/f'legacy-{c}.payload.json',legacy)
    write(out/'changelog.history.json',history)
    write(out/'preparation.json',dict(version='0.7.0',auditedArchives=len(verified),payloadFiles=sum(verified.values()),assets=list(assets.values()),
        previousHashes={c:sha(out/f'previous-{c}.json') for c in old}))
    print(f'STAGED: {len(assets)} new immutable archives; {len(verified)} audited archives; {sum(verified.values())} payload files. No upload or promotion.')

def finalize(args):
    out=args.out.resolve();prepared=read(out/'preparation.json');assert args.launcher.is_file()
    key=serialization.load_pem_private_key((args.signing_dir/'pawpatch-signing-private.pem').read_bytes(),password=None)
    public=serialization.load_pem_public_key(read(REPO/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'].encode())
    assert key.public_key().public_numbers()==public.public_numbers()
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    release=dict(version='0.7.0',size=args.launcher.stat().st_size,sha256=sha(args.launcher),urls=[ROOT+'PawsPatchLauncher.exe'])
    for name in ('stable','beta','legacy-stable','legacy-beta'):
        feed=read(out/(name+'.payload.json'));feed.update(launcher=release,publishedAt=stamp)
        if name.startswith('legacy-'):
            before=verify(read(out/('previous-'+feed['channel']+'.json')),public)
            exclude={'launcher','publishedAt','changelog','newsTitle','newsBody'}
            assert {k:v for k,v in feed.items() if k not in exclude}=={k:v for k,v in before.items() if k not in exclude}
        for p in feed['packages']: assert all(u.startswith('https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/') for u in p['urls'])
        payload=encode(feed);r,s=utils.decode_dss_signature(key.sign(payload,ec.ECDSA(hashes.SHA256())))
        signed=dict(keyId='pawpatch-prod-2026',payload=base64.b64encode(payload).decode(),signature=base64.b64encode(r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode())
        assert verify(signed,public)==feed
        write(out/'signed'/(name+'.json'),signed)
    print('SIGNED: 4 catalogs, including unchanged legacy game packages; launcher '+release['sha256'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','finalize']);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--feeds',type=Path);parser.add_argument('--test-config',type=Path);parser.add_argument('--launcher',type=Path);parser.add_argument('--signing-dir',type=Path)
    args=parser.parse_args()
    (prepare if args.action=='prepare' else finalize)(args)
