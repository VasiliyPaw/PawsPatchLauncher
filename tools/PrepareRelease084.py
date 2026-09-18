"""Promote accepted Arcane 0.3.1 and publish launcher 0.8.4 through guarded stages."""
import argparse, copy, hashlib, json, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, API, key, normalize, fetch, sign
from PrepareRelease070 import read, write, encode, sha, verify, validate_package
from PrepareArcane030 import guide

REPO = Path(__file__).resolve().parents[1]
VERSION = '0.8.4'
PATCH = '0.3.1'
TAG = 'patch-' + PATCH
DOWNLOAD = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'
VERSIONS = {'pawpatch-core': PATCH, 'common-ui': '1.3.72-ui.9',
            'player-colors': PATCH, 'desync-continue': '1.3.72-r5'}


def private(a):
    k = serialization.load_pem_private_key((a.signing_dir / 'pawpatch-signing-private.pem').read_bytes(), None)
    assert k.public_key().public_numbers() == key().public_numbers()
    return k


def notes(version, patch=False):
    filename = 'release-' + ('patch-' if patch else '') + version + '.md'
    parts = (REPO / 'docs' / filename).read_text('utf-8').split('\n---\n')
    assert len(parts) == 2
    title = ("Paw's Patch " if patch else "Paw's Launcher ") + version
    n = dict(category='patch' if patch else 'launcher', version=version,
             mods=['arcane-wars'] if patch else [], publishedAt='2026-09-18',
             title=dict(ru=title, en=title),
             body={c:t.strip().split('\n',2)[2].strip() for c,t in zip(('ru','en'),parts)})
    if patch: n['channel'] = 'stable'
    return n


def prepare(a):
    out = a.out.resolve()
    assert not (out/'preparation.json').exists(), 'Completed stage already exists'
    out.mkdir(parents=True, exist_ok=True)
    k = private(a)
    before = {n:verify(read(REPO/p),key()) for n,p in FEEDS.items()}
    assert before['stable']['patchGuide']['version'] == '0.3.0'
    assert before['beta']['patchGuide']['version'] == '0.3.1-beta.1'
    for n,p in FEEDS.items():
        assert before[n]['launcher']['version'] == '0.8.3'
        assert normalize(fetch(RAW+p+'?release084=baseline')) == normalize((REPO/p).read_bytes())
        target = out/'previous'/(n+'.json'); target.parent.mkdir(exist_ok=True)
        shutil.copyfile(REPO/p,target)
    variants = read(REPO/'game/beta7/variants.json')
    prior = read(a.beta_stage/'publication/features.json')
    features = {}
    for name in variants:
        f = json.loads(subprocess.check_output([str(a.helpers/name),'--features'],text=True,creationflags=subprocess.CREATE_NO_WINDOW))
        expected = copy.deepcopy(prior[name]['features']); expected['patchVersion'] = PATCH
        assert f == expected, (name, f, expected)
        features[name] = dict(sha256=sha(a.helpers/name),features=f)
    # Runtime payloads must remain byte-identical to the user-accepted beta.
    payloads = []
    for folder in ('native','lair-native','camera-native'):
        for source in (a.beta_stage/'helpers'/folder).glob('*'):
            if source.suffix not in ('.bin','.cs'): continue
            target = a.helpers/folder/source.name
            assert target.exists() and sha(target) == sha(source), str(target)
            payloads.append(str(target.relative_to(a.helpers)))
    assert payloads
    stable = {p['id']:p for p in before['stable']['packages']}
    beta = {p['id']:p for p in before['beta']['packages']}
    differences = {i for i,p in beta.items() if p.get('mods') == ['arcane-wars'] and p != stable.get(i)}
    assert set(VERSIONS) <= differences
    caches = [a.beta_stage/'publication/assets',a.beta_stage/'test-cache',
              out.parent.parent/'release-arcane-030/publication/assets',REPO/'packages']
    # Search existing validated artifacts only; no modification of these caches.
    index = {}
    for directory in caches:
        for path in directory.glob('*.zip'): index.setdefault(path.stat().st_size,[]).append(path)
    def archive(p, label):
        target = out/'baseline'/(label+'.zip'); target.parent.mkdir(exist_ok=True)
        found = next((x for x in index.get(p['size'],[]) if sha(x)==p['sha256']),None)
        if found: shutil.copyfile(found,target)
        else: target.write_bytes(fetch(p['urls'][0]))
        validate_package(target,p)
        return target
    # Stable already contains the other beta changes. Verify payload manifests,
    # rather than needlessly republishing identical data with a new version.
    equivalent = {}
    for ident in sorted(differences-set(VERSIONS)):
        manifests = []
        for channel,p in [('stable',stable[ident]),('beta',beta[ident])]:
            with zipfile.ZipFile(archive(p,ident+'-'+channel)) as z: m=json.loads(z.read('module.json'))
            m.pop('version')
            for entry in m['files']: entry['path']=entry['path'].replace('\\','/').lower()
            m['files'].sort(key=lambda entry:entry['path'])
            manifests.append(m)
        assert manifests[0] == manifests[1], 'Unpromoted payload difference: '+ident
        equivalent[ident] = 'identical payloads; stable version retained'
    published = {}; assets = []; scope = {}; copies = []
    for ident,version in VERSIONS.items():
        p = copy.deepcopy(beta[ident])
        with zipfile.ZipFile(archive(p,ident)) as z:
            m = json.loads(z.read('module.json'))
            files = {f['path']:z.read('payload/'+f['path']) for f in m['files']}
        original = dict(files); changed = []
        for name in files:
            if name in variants or name == 'paws_patch_versions.ini':
                files[name] = (a.helpers/name).read_bytes(); changed.append(name)
                if name in variants: copies.append(name)
        assert all(files[n]==v for n,v in original.items() if n not in changed)
        m['version'] = version
        m['files'] = [dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(files.items())]
        target = out/'assets'/(ident+'-'+version+'.zip'); target.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in [('module.json',encode(m))]+[('payload/'+n,b) for n,b in sorted(files.items())]:
                entry=zipfile.ZipInfo(name,(2026,9,18,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o100644<<16
                z.writestr(entry,data)
        p.update(version=version,size=target.stat().st_size,sha256=sha(target),urls=[DOWNLOAD+TAG+'/'+target.name],experimental=False)
        # Retain the already published stable, player-facing package descriptions.
        p['description'] = stable[ident]['description']
        validate_package(target,p);published[ident]=p
        assets.append(dict(id=ident,path=str(target),size=p['size'],sha256=p['sha256'],url=p['urls'][0]))
        scope[ident]=dict(sourceBetaVersion=beta[ident]['version'],identityFiles=changed,preservedPayloadFiles=len(original)-len(changed))
    assert set(copies)==set(variants) and len(copies)==11
    launch = notes(VERSION); patch = notes(PATCH,True)
    history = read(REPO/'feed/changelog.history.json')
    for name,f in before.items():
        f = copy.deepcopy(f)
        if name == 'stable':
            f['packages'] = [published.get(p['id'],p) for p in f['packages']]
            g = guide(before['beta']['patchGuide']);g['version']=PATCH
            for e in g['entries']:
                if e['id']=='base':
                    e['bodyRu']="Лаунчер устанавливает Arcane Wars как основу и применяет Paw's Patch: автоулучшение городов, ускоренную передачу сейвов, проверку совместимости лобби, компактный выбор 48 цветов, исправления вылетов и логов, обновлённые рамки миникарты и отдаление камеры до 2."
                    e['bodyEn']="The launcher installs Arcane Wars and applies Paw's Patch: city automation, faster save transfers, lobby compatibility checks, a compact 48-color picker, crash and lair fixes, updated minimap frames and a camera zoom-out limit of 2."
            f['patchGuide'] = g
            f['changelog'] = [patch]+f['changelog']
            write(out/'patch-guide.json',g)
        f['changelog'] = [launch]+f['changelog']
        f.update(newsTitle=launch['title'],newsBody=launch['body'])
        if name in ('stable','beta'):
            assert history[name]==before[name]['changelog']
            history[name]=f['changelog']
        if name!='stable': assert f['packages']==before[name]['packages']
        else: assert [p for p in f['packages'] if p['id'] not in VERSIONS]==[p for p in before[name]['packages'] if p['id'] not in VERSIONS]
        for field in before[name]:
            if field not in ('packages','patchGuide','changelog','newsTitle','newsBody'): assert f[field]==before[name][field],field
        write(out/'payloads'/(name+'.json'),f)
        if name in ('stable','beta'):
            local = copy.deepcopy(f)
            if name=='stable':
                for p in local['packages']:
                    item=next((x for x in assets if x['id']==p['id']),None)
                    if item:p['urls']=[item['path']]
            write(out/'test-feeds'/(name+'.json'),sign(local,k))
    write(out/'changelog.history.json',history)
    write(out/'features.json',features)
    write(out/'scope.json',dict(packages=scope,alreadyStable=equivalent,identicalNativePayloads=payloads))
    write(out/'preparation.json',dict(assets=assets,before={n:sha(REPO/p) for n,p in FEEDS.items()},
        historyBefore=sha(REPO/'feed/changelog.history.json'),guideBefore=sha(REPO/'feed/patch-guide.json'),
        notesBefore={n:sha(REPO/'docs'/n) for n in ('release-0.8.4.md','release-patch-0.3.1.md')}))
    print('PREPARED: four Arcane packages, accepted runtime preserved; other gameplay packages unchanged',flush=True)


def finalize(a):
    out=a.out;prep=read(out/'preparation.json');artifact=read(a.launcher.parent/'launcher-artifact.json')
    assert artifact['version']==VERSION and artifact['sourceCommit']==a.commit
    item=next(x for x in artifact['files'] if x['name']=='PawsPatchLauncher.exe')
    assert sha(a.launcher)==item['sha256'] and a.launcher.stat().st_size==item['size']
    launcher=dict(version=VERSION,sha256=item['sha256'],size=item['size'],urls=[DOWNLOAD+'v'+VERSION+'/PawsPatchLauncher.exe'])
    for n in FEEDS:
        f=read(out/'payloads'/(n+'.json'));f.update(launcher=launcher,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        write(out/'signed'/(n+'.json'),sign(f,private(a)))
    write(out/'release-plan.json',dict(sourceCommit=a.commit,launcher=launcher,assets=prep['assets']))
    print('SIGNED: four catalogs bound to exact CI artifact')


def public(a):
    out=a.out;plan=read(out/'release-plan.json')
    for tag in ('v'+VERSION,TAG):
        r=json.loads(fetch(API+'/releases/tags/'+tag));assert not r['draft'] and not r['prerelease']
        ref=json.loads(fetch(API+'/git/ref/tags/'+tag))['object']
        while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
        assert ref['type']=='commit' and ref['sha']==plan['sourceCommit']
    assert json.loads(fetch(API+'/releases/latest'))['tag_name']=='v'+VERSION
    for p in plan['assets']+[dict(plan['launcher'],id='launcher',url=plan['launcher']['urls'][0])]:
        data=fetch(p['url']);assert len(data)==p['size'] and hashlib.sha256(data).hexdigest().upper()==p['sha256'].upper()
        print('PUBLIC PASS',p['id'],flush=True)
    write(out/'public-verification.json',dict(passAll=True,sourceCommit=plan['sourceCommit'],assets=len(plan['assets'])+1))


def promote(a):
    out=a.out;prep=read(out/'preparation.json')
    assert read(out/'public-verification.json')['passAll'] and read(out.parent/'installation-verification.json')['passed']
    for name,h in prep['notesBefore'].items():assert sha(REPO/'docs'/name)==h
    for n,p in FEEDS.items():
        assert sha(REPO/p)==prep['before'][n]
        assert normalize(fetch(RAW+p+'?release084=promotion'))==normalize((REPO/p).read_bytes())
        verify(read(out/'signed'/(n+'.json')),key())
        assert not (REPO/'feed/history'/('before-launcher-084-'+n+'.json')).exists()
    assert sha(REPO/'feed/changelog.history.json')==prep['historyBefore']
    assert sha(REPO/'feed/patch-guide.json')==prep['guideBefore']
    for n,p in FEEDS.items():
        shutil.copyfile(REPO/p,REPO/'feed/history'/('before-launcher-084-'+n+'.json'))
        shutil.copyfile(out/'signed'/(n+'.json'),REPO/p)
    for name in ('changelog.history.json','patch-guide.json'):shutil.copyfile(out/name,REPO/'feed'/name)
    print('PROMOTED LOCALLY; push and canonical public readback required')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','finalize','verify-public','promote']);p.add_argument('--out',type=Path,required=True)
    for n in ('helpers','beta-stage','signing-dir','launcher'):p.add_argument('--'+n,type=Path)
    p.add_argument('--commit');a=p.parse_args()
    {'prepare':prepare,'finalize':finalize,'verify-public':public,'promote':promote}[a.action](a)
