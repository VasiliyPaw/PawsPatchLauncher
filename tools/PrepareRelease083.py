"""Stage scoped pure channels and launcher 0.8.3; publish only through explicit release steps."""
import argparse,copy,hashlib,json,re,shutil
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS,RAW,API,key,normalize,fetch,sign
from PrepareRelease070 import read,write,sha,verify,validate_package
from PurePatch083Text import TEXTS
REPO=Path(__file__).resolve().parents[1]
VERSION='0.8.3'
VERSIONS={'stable':'0.2.0','beta':'0.3.0-beta.1'}
TAGS={c:'patch-pure-'+v for c,v in VERSIONS.items()}
DOWNLOAD='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'

def private(a):
    k=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
    assert k.public_key().public_numbers()==key().public_numbers();return k

def notes(filename,version,mods=None):
    sections=(REPO/'docs'/filename).read_text('utf-8').split('\n---\n')
    assert len(sections)==2
    bodies={c:s.strip().split('\n',2)[2].strip() for c,s in zip(('ru','en'),sections)}
    return dict(category='patch' if mods else 'launcher',version=version,mods=mods or [],publishedAt='2026-09-16',
        title={'ru':"Paw's Patch "+version+' — Vanilla и Immortals' if mods else "Paw's Launcher 0.8.3",
               'en':"Paw's Patch "+version+' — Vanilla and Immortals' if mods else "Paw's Launcher 0.8.3"},body=bodies)

def prepare(a):
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);k=private(a)
    before={n:verify(read(REPO/p),key()) for n,p in FEEDS.items()}
    source=read(a.build/'packages.json');assets=[];changed={}
    for n,p in FEEDS.items():
        assert before[n]['launcher']['version']=='0.8.2'
        assert normalize(fetch(RAW+p+'?pure083=baseline'))==normalize((REPO/p).read_bytes())
        t=out/'previous'/(n+'.json');t.parent.mkdir(exist_ok=True);shutil.copyfile(REPO/p,t)
    launch=notes('release-0.8.3.md',VERSION)
    history=read(REPO/'feed/changelog.history.json')
    desync=(REPO/'src/PawsPatchLauncher/PatchGuide.cs').read_text('utf-8')
    desync_bodies=[json.loads('"'+re.search('DesyncHelp'+c+r' = "(.*?)";',desync)[1]+'"') for c in ('Ru','En')]
    for channel in VERSIONS:
        replacements=copy.deepcopy(source[channel]);changed[channel]=[]
        for p in replacements:
            path=Path(p['urls'][0]);validate_package(path,p)
            dest=out/'releases'/TAGS[channel]/path.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
            p['urls']=[DOWNLOAD+TAGS[channel]+'/'+dest.name]
            assets.append(dict(channel=channel,tag=TAGS[channel],id=p['id'],version=p['version'],path=str(dest),url=p['urls'][0],sha256=p['sha256'],size=p['size']))
        f=copy.deepcopy(before[channel]);ids={p['id'] for p in replacements}
        f['packages']=[p for p in f['packages'] if p['id'] not in ids]+replacements
        f['pureRuntimeOptions']=channel=='beta'
        patch=notes('release-pure-'+VERSIONS[channel]+'.md',VERSIONS[channel],['vanilla','immortals'])
        f['changelog']=[launch,patch]+f['changelog']
        f.update(newsTitle=launch['title'],newsBody=launch['body'])
        for g in f['modGuides']:
            if g['id'] not in ('vanilla','immortals'):continue
            doc=copy.deepcopy(next(x for x in before['beta']['modGuides'] if x['id']==g['id'])['patchGuide'])
            doc['version']=VERSIONS[channel]
            for e in doc['entries']:
                e['category']='always'
                if e['id']=='base':e['bodyRu']=e['bodyRu'].replace('Русский язык выбирается независимо от патча.','Язык игры выбирается независимо от патча.')
                ident={'terrain':'terrain','fast-save-transfer':'transfer'}.get(e['id'])
                if ident:e.update(bodyRu=TEXTS[ident][0],bodyEn=TEXTS[ident][1])
            if channel=='beta':
                doc['entries'] += [dict(id='colors',category='optional',titleRu='Расширенные цвета игроков',titleEn='Extended player colors',bodyRu=TEXTS['colors'][0],bodyEn=TEXTS['colors'][1]),
                    dict(id='desync',category='optional',titleRu='Игнорирование рассинхронов',titleEn='Ignore desyncs',bodyRu=desync_bodies[0],bodyEn=desync_bodies[1])]
            g['patchGuide']=doc
        # No Arcane Wars payload, requirement, guide or localization changes.
        assert [p for p in f['packages'] if p['id'] not in ids]==[p for p in before[channel]['packages'] if p['id'] not in ids]
        assert f['patchGuide']==before[channel]['patchGuide'] and f['game']==before[channel]['game'] and f['modGames']==before[channel]['modGames']
        write(out/'payloads'/(channel+'.json'),f);history[channel]=f['changelog']
        local=copy.deepcopy(f)
        for p in local['packages']:
            own=next((x for x in assets if x['channel']==channel and x['id']==p['id']),None)
            if own:p['urls']=[own['path']]
        write(out/'test-feeds'/(channel+'.json'),sign(local,k))
    for n in ('legacy-stable','legacy-beta'):
        f=copy.deepcopy(before[n]);f['changelog']=[launch]+f['changelog'];f.update(newsTitle=launch['title'],newsBody=launch['body']);write(out/'payloads'/(n+'.json'),f)
    config=read(REPO/'src/PawsPatchLauncher/launcher.config.json')
    config.update(feedUrls=[str(out/'test-feeds/stable.json')],betaFeedUrls=[str(out/'test-feeds/beta.json')])
    write(out/'test-feeds/launcher.config.json',config)
    write(out/'changelog.history.json',history)
    write(out/'preparation.json',dict(assets=assets,before={n:sha(REPO/p) for n,p in FEEDS.items()},historyBefore=sha(REPO/'feed/changelog.history.json')))
    print('PREPARED: stable 0.2.0, beta 0.3.0-beta.1; Arcane Wars and legacy gameplay unchanged')

def finalize(a):
    out=a.out.resolve();prep=read(out/'preparation.json');artifact=read(a.launcher.parent/'launcher-artifact.json');assert artifact['version']==VERSION
    item=next(x for x in artifact['files'] if x['name']=='PawsPatchLauncher.exe')
    assert sha(a.launcher)==item['sha256'] and a.launcher.stat().st_size==item['size']
    launcher=dict(version=VERSION,sha256=item['sha256'],size=item['size'],urls=[DOWNLOAD+'v'+VERSION+'/PawsPatchLauncher.exe'])
    k=private(a)
    for n in FEEDS:
        f=read(out/'payloads'/(n+'.json'));f.update(launcher=launcher,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        write(out/'signed'/(n+'.json'),sign(f,k))
    write(out/'release-plan.json',dict(sourceCommit=artifact['sourceCommit'],launcher=launcher,assets=prep['assets']))
    print('SIGNED: four catalogs bound to exact CI artifact')

def public(a):
    out=a.out.resolve();plan=read(out/'release-plan.json')
    for tag in ('v'+VERSION,*TAGS.values()):
        r=json.loads(fetch(API+'/releases/tags/'+tag));assert not r['draft'] and r['prerelease']==(tag==TAGS['beta'])
        ref=json.loads(fetch(API+'/git/ref/tags/'+tag))['object']
        while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
        assert ref['type']=='commit' and ref['sha']==plan['sourceCommit']
    for p in plan['assets']+[dict(plan['launcher'],url=plan['launcher']['urls'][0],id='launcher')]:
        data=fetch(p['url']);assert len(data)==p['size'] and hashlib.sha256(data).hexdigest().upper()==p['sha256'].upper();print('PUBLIC PASS',p['id'],flush=True)
    write(out/'public-verification.json',dict(passAll=True,sourceCommit=plan['sourceCommit'],assets=len(plan['assets'])+1))

def promote(a):
    out=a.out.resolve();prep=read(out/'preparation.json');assert read(out/'public-verification.json')['passAll']
    for n,p in FEEDS.items():
        assert sha(REPO/p)==prep['before'][n]
        assert normalize(fetch(RAW+p+'?pure083=promotion'))==normalize((REPO/p).read_bytes())
        verify(read(out/'signed'/(n+'.json')),key())
    assert sha(REPO/'feed/changelog.history.json')==prep['historyBefore']
    for n,p in FEEDS.items():
        backup=REPO/'feed/history'/('before-launcher-083-'+n+'.json');assert not backup.exists()
        shutil.copyfile(REPO/p,backup);shutil.copyfile(out/'signed'/(n+'.json'),REPO/p)
    shutil.copyfile(out/'changelog.history.json',REPO/'feed/changelog.history.json')
    print('PROMOTED LOCALLY; push and ordinary public URL readback required')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','finalize','verify-public','promote']);p.add_argument('--out',type=Path,required=True)
    for n in ('build','signing-dir','launcher'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();{'prepare':prepare,'finalize':finalize,'verify-public':public,'promote':promote}[a.action](a)
