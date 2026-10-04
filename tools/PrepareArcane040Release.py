"""Promote the accepted Arcane beta to stable; preserve both Pure channels.

Stages immutable archives and signed catalogs. Publishing assets and pushing the
catalog commit remain explicit steps. Never writes to the installed game.
"""
import argparse, copy, hashlib, json, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, API, key, sign, fetch, normalize
from PrepareRelease070 import read, write, encode, sha, verify, validate_package
from PrepareSeptember20Release import contents, feature

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parents[1]
VERSION = '0.4.0'
TAG = 'patch-' + VERSION
LAUNCHER = '0.8.13'
DOWNLOAD = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'
TRACKED = [*FEEDS.values(), 'feed/changelog.history.json', 'feed/patch-guide-beta.json']
VARIANTS = read(ROOT/'game/beta7/variants.json')


def private(a):
    k = serialization.load_pem_private_key(a.private_key.read_bytes(), None)
    assert k.public_key().public_numbers() == key().public_numbers()
    return k


def arcane(p):
    return p.get('mods') == ['arcane-wars']


def scope(before, after, legacy=False):
    if legacy:
        allowed = {'launcher', 'changelog', 'newsTitle', 'newsBody', 'publishedAt'}
        assert {k:v for k,v in before.items() if k not in allowed} == {k:v for k,v in after.items() if k not in allowed}
    else:
        assert [p for p in before['packages'] if not arcane(p)] == [p for p in after['packages'] if not arcane(p)]
        allowed = {'launcher', 'changelog', 'newsTitle', 'newsBody', 'publishedAt', 'packages', 'patchGuide'}
        assert {k:v for k,v in before.items() if k not in allowed} == {k:v for k,v in after.items() if k not in allowed}
        assert all(not p.get('experimental') and 'beta' not in p['version'].lower() for p in after['packages'] if arcane(p))
        assert after['patchGuide']['version'] == VERSION
        assert all(e['category'] != 'beta' for e in after['patchGuide']['entries'])


def prepare(a):
    stage=a.stage.resolve(); out=stage/'publication'
    assert not (out/'preparation.json').exists(), 'Use a fresh publication directory'
    log=(stage.parent/(stage.name+'-build.log')).read_text('utf-8-sig')
    assert 'Built eight quiet helpers. No game launched.' in log, 'Native build incomplete'
    assert read(stage/'helpers/ai-native/peer-parity.json')['passed']
    assert read(stage/'server-deployment.json')['passed'], 'Production migration not verified'
    head=json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']
    before={n:verify(read(ROOT/p),key()) for n,p in FEEDS.items()}
    for p in TRACKED:
        assert normalize(fetch(RAW.replace('/main/','/'+head+'/')+p)) == normalize((ROOT/p).read_bytes()), 'Public baseline moved: '+p
    assert before['stable']['patchGuide']['version']=='0.3.3'
    assert before['beta']['patchGuide']['version']=='0.4.0-beta.10'
    prior=read(WORK/'outputs/release-20260929-beta10/publication/features.json')
    features={}
    for n in VARIANTS:
        f=feature(stage/'helpers'/n); expected=copy.deepcopy(prior[n]);expected['patchVersion']=VERSION
        assert f==expected, ('Feature drift',n,f,expected)
        assert (stage/'helpers/ai-native/ai-policy.bin').read_bytes().hex().encode('utf-16le') in (stage/'helpers'/n).read_bytes()
        features[n]=f
        for channel in ('stable','beta'):
            dest=stage/(channel+'-helpers')/n;dest.parent.mkdir(exist_ok=True);shutil.copyfile(stage/'helpers'/n,dest)
    for n,p in FEEDS.items():
        dest=out/'previous'/(n+'.json');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
    packages={p['sha256']:p for f in before.values() for p in f['packages']}
    sizes={p['size'] for p in packages.values()}; cache={}
    for root in (WORK/'outputs',ROOT/'packages'):
        for path in root.rglob('*.zip'):
            size=path.stat().st_size
            if size in sizes: cache.setdefault(size,[]).append(path)
    resolved={}; hashed={}
    for digest,p in packages.items():
        path=None
        for candidate in cache.get(p['size'],[]):
            if candidate not in hashed:hashed[candidate]=sha(candidate)
            if hashed[candidate]==digest:path=candidate;break
        if path is None:
            path=stage/'downloads'/(digest+'.zip');path.parent.mkdir(exist_ok=True)
            if not path.exists():path.write_bytes(fetch(p['urls'][0]))
        validate_package(path,p);resolved[digest]=str(path.resolve())
    beta=before['beta']; stable_by_id={p['id']:p for p in before['stable']['packages']}
    promoted=[];assets=[];changes={};seen=set()
    for p in beta['packages']:
        if not arcane(p):continue
        original=contents(Path(resolved[p['sha256']]),p);payload=dict(original)
        for n in payload:
            if n in VARIANTS or n=='paws_patch_versions.ini':
                payload[n]=(stage/'helpers'/n).read_bytes()
                if n in VARIANTS:seen.add(n)
        changed=[n for n in payload if payload[n]!=original[n]]
        assert all(n in VARIANTS or n=='paws_patch_versions.ini' for n in changed)
        q=copy.deepcopy(p)
        if changed or p!=stable_by_id.get(p['id']):
            q['version']=VERSION;q['experimental']=False
            manifest=dict(id=q['id'],version=VERSION,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(payload.items())],remove=[])
            path=out/'assets'/(q['id']+'-'+VERSION+'.zip');path.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                for n,b in [('module.json',encode(manifest))]+[('payload/'+n,b) for n,b in sorted(payload.items())]:
                    info=zipfile.ZipInfo(n,(2026,10,4,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
            q.update(size=path.stat().st_size,sha256=sha(path),urls=[DOWNLOAD+TAG+'/'+path.name]);validate_package(path,q)
            resolved[q['sha256']]=str(path.resolve())
            assets.append(dict(id=q['id'],path=str(path.resolve()),size=q['size'],sha256=q['sha256'],url=q['urls'][0]))
            changes[q['id']]=dict(changedPayload=changed,preservedFiles=len(payload)-len(changed),betaSha256=p['sha256'])
        promoted.append(q)
        if p['id']=='common-ui':
            for root in ('data','local_base_ru','local_ru'):
                name=root+'/localization/hotkeys/hotkeys_favorites.txt'
                dest=stage/'hotkeys'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload[name])
    assert seen==set(VARIANTS)
    guide=copy.deepcopy(beta['patchGuide']);guide['version']=VERSION
    for e in guide['entries']:
        if e['category']=='beta':e['category']='always'
        for field in ('bodyRu','bodyEn'):
            e[field]=e[field].replace('для беты Arcane Wars','для Arcane Wars').replace('в бете','в патче').replace('EXE беты','EXE патча').replace('одинаковую бету','одинаковую версию патча').replace('обновить бету','обновить патч').replace('Arcane Wars Beta','Arcane Wars').replace('every beta EXE','every patch EXE').replace('in Beta','in the patch').replace('matching Beta versions','matching patch versions').replace('update Beta','update the patch')
        if e['id']=='base':
            e['bodyRu']="Лаунчер устанавливает Arcane Wars как основу и применяет Paw’s Patch 0.4.0. Возможности прежней беты теперь доступны в релизном канале. Настройки компонентов применяются перед запуском игры."
            e['bodyEn']="The launcher installs Arcane Wars as the base mod and applies Paw’s Patch 0.4.0. Former beta features are now available in the stable channel. Component settings are applied before starting the game."
    bodies=read(ROOT/'docs/release-patch-0.4.0.json')
    note=dict(category='patch',version=VERSION,publishedAt='2026-10-04',mods=['arcane-wars'],channel='stable',title={c:'Paw’s Patch '+VERSION for c in bodies},body=bodies)
    for channel in ('stable','beta'):
        f=copy.deepcopy(before[channel]); replacements={p['id']:p for p in promoted}
        f['packages']=[replacements[p['id']] if arcane(p) else p for p in f['packages']]
        known={p['id'] for p in f['packages']};f['packages'] += [p for p in promoted if p['id'] not in known]
        f.update(patchGuide=guide,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),changelog=[note]+f['changelog'],newsTitle=note['title'],newsBody=note['body'])
        scope(before[channel],f)
        write(out/'signed'/(channel+'.json'),sign(f,private(a)))
        local=copy.deepcopy(f)
        for p in local['packages']:p['urls']=[resolved[p['sha256']]]
        write(out/'test-feeds'/(channel+'.json'),sign(local,private(a)))
    write(out/'features.json',features);write(out/'scope.json',changes)
    write(out/'preparation.json',dict(baselineCommit=head,assets=assets,before={p:sha(ROOT/p) for p in TRACKED},note=note))
    print('ARCANE_040_STAGED',len(assets),'archives; Pure channels preserved',flush=True)


def finalize(a):
    out=a.stage/'publication'; proof=read(out/'preparation.json')
    assert read(a.stage/'installation-verification.json')['passed']
    launcher_proof=read(a.launcher_stage/'preparation.json')
    assert launcher_proof['version']==LAUNCHER and launcher_proof['commit']==a.commit
    for p,h in proof['before'].items():assert sha(ROOT/p)==h,'Baseline changed: '+p
    history=read(a.launcher_stage/'changelog.history.json')
    for n,p in FEEDS.items():
        launch=verify(read(a.launcher_stage/'signed'/(n+'.json')),key())
        f=verify(read(out/'signed'/(n+'.json')),key()) if n in ('stable','beta') else verify(read(ROOT/p),key())
        f['launcher']=launch['launcher'];f['publishedAt']=launch['publishedAt']
        f['changelog']=[read(ROOT/'docs/release-0.8.13.json')]+f['changelog']
        if n in ('stable','beta'):history[n]=[proof['note']]+history[n]
        else:f['newsTitle']=launch['newsTitle'];f['newsBody']=launch['newsBody']
        scope(verify(read(ROOT/p),key()),f,n.startswith('legacy'))
        write(out/'final'/(n+'.json'),sign(f,private(a)))
    write(out/'final/changelog.history.json',history)
    write(out/'final/patch-guide-beta.json',verify(read(out/'final/beta.json'),key())['patchGuide'])
    write(out/'finalization.json',dict(commit=a.commit,launcher=launcher_proof['launcher']))
    print('ARCANE_040_FINALIZED four signed catalogs')


def public(a):
    out=a.stage/'publication';proof=read(out/'preparation.json')
    r=json.loads(fetch(API+'/releases/tags/'+TAG));assert not r['draft'] and not r['prerelease']
    ref=json.loads(fetch(API+'/git/ref/tags/'+TAG))['object']
    while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
    assert ref['type']=='commit' and ref['sha']==a.commit
    remote={x['name']:x for x in r['assets']}
    for row in proof['assets']:
        data=fetch(row['url']);asset=remote[Path(row['path']).name]
        assert len(data)==row['size']==asset['size']
        assert hashlib.sha256(data).hexdigest().upper()==row['sha256']
        assert asset['digest']=='sha256:'+row['sha256'].lower()
    write(out/'public-verification.json',dict(passed=True,commit=a.commit,assets=len(proof['assets'])))
    print('ARCANE_040_PUBLIC_ASSETS_PASS',len(proof['assets']))


def promote(a):
    out=a.stage/'publication';proof=read(out/'preparation.json')
    assert read(out/'public-verification.json')['passed']
    assert read(a.stage/'installation-verification.json')['passed']
    assert read(a.stage/'server-deployment.json')['passed']
    for p,h in proof['before'].items():
        assert sha(ROOT/p)==h
        assert normalize(fetch(RAW+p))==normalize((ROOT/p).read_bytes()),'Public baseline moved'
    for n,p in FEEDS.items():
        f=verify(read(out/'final'/(n+'.json')),key())
        scope(verify(read(ROOT/p),key()),f,n.startswith('legacy'))
        assert f['launcher']['version']==LAUNCHER
        shutil.copyfile(out/'final'/(n+'.json'),ROOT/p)
    for n in ('changelog.history.json','patch-guide-beta.json'):shutil.copyfile(out/'final'/n,ROOT/'feed'/n)
    print('ARCANE_040_PROMOTED_LOCALLY; push and readback required')


def readback(a):
    out=a.stage/'publication'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']==head
    for n,p in FEEDS.items():
        f=verify(json.loads(fetch(RAW.replace('/main/','/'+head+'/')+p)),key())
        assert f==verify(read(ROOT/p),key())
        scope(verify(read(out/'previous'/(n+'.json')),key()),f,n.startswith('legacy'))
        assert f['launcher']['version']==LAUNCHER
    for p in TRACKED[4:]:assert normalize(fetch(RAW.replace('/main/','/'+head+'/')+p))==normalize((ROOT/p).read_bytes())
    write(out/'catalog-readback.json',dict(passed=True,commit=head,patch=VERSION,launcher=LAUNCHER))
    print('ARCANE_040_PUBLIC_CATALOGS_PASS',head)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','finalize','public','promote','readback'])
    p.add_argument('--stage',required=True,type=Path);p.add_argument('--private-key',type=Path)
    p.add_argument('--launcher-stage',type=Path);p.add_argument('--commit');a=p.parse_args()
    a.stage=a.stage.resolve();globals()[a.action](a)
