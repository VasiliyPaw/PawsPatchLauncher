"""Stage, verify and promote Arcane 0.3.2-beta.1. Upload and Git push are separate steps."""
import argparse,copy,hashlib,json,shutil,subprocess,zipfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS,RAW,API,key,normalize,fetch,sign
from PrepareRelease070 import read,write,encode,sha,verify,validate_package

REPO=Path(__file__).resolve().parents[1]
VERSION='0.3.2-beta.1';TAG='patch-'+VERSION
VERSIONS={'pawpatch-core':VERSION,'common-ui':'1.3.72-ui.10-beta.1','player-colors':VERSION,'desync-continue':'1.3.72-r6-beta.1'}
RACES=('Human','Gauri','Drauga','Haroun','Undead','Shadow')
VARIANTS=('UI/Game/ControlPanel','UI/800/Game/ControlPanel','UI/1280/Game/ControlPanel')
FRAMES={f'skins/{r}/{v}/Background.tga' for r in RACES for v in VARIANTS}
DOWNLOAD='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'

def notes():
    texts=(REPO/'docs'/('release-'+TAG+'.md')).read_text('utf-8').split('\n---\n')
    assert len(texts)==2
    return dict(category='patch',version=VERSION,mods=['arcane-wars'],channel='beta',publishedAt='2026-09-18',
        title=dict(ru="Paw's Patch "+VERSION+' — палитра из 39 цветов',en="Paw's Patch "+VERSION+' — 39-color palette'),
        body={c:t.strip().split('\n',2)[2].strip() for c,t in zip(('ru','en'),texts)})

def payload(path,p):
    validate_package(path,p)
    with zipfile.ZipFile(path) as z:
        m=json.loads(z.read('module.json'));return m,{f['path']:z.read('payload/'+f['path']) for f in m['files']}

def prepare(a):
    out=a.out.resolve();assert not (out/'preparation.json').exists();out.mkdir(parents=True,exist_ok=True)
    before={n:verify(read(REPO/p),key()) for n,p in FEEDS.items()}
    assert before['beta']['patchGuide']['version']=='0.3.1-beta.2'
    head=json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']
    live=RAW.replace('/main/','/'+head+'/')
    for n,p in FEEDS.items():
        assert normalize(fetch(live+p))==normalize((REPO/p).read_bytes())
        dest=out/'previous'/(n+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(REPO/p,dest)
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
    assert private.public_key().public_numbers()==key().public_numbers()
    variants=read(REPO/'game/beta7/variants.json');features={}
    for name,defines in variants.items():
        f=json.loads(subprocess.check_output([str(a.helpers/name),'--features'],text=True,creationflags=subprocess.CREATE_NO_WINDOW))
        assert f['patchVersion']==VERSION and f['lairWoundedDefendersRevision']==3
        assert f['gameplayCameraRevision']==1 and f['gameplayCameraZoomMaximum']==2 and f['gameplayCameraFarPlane']==1024
        assert f['cityPolicyRevision']==23 and f['lobbyCompatibility'] and f['fastSaveTransfer']
        assert not any('minimap' in k.lower() or 'resolution' in k.lower() for k in f)
        for field,flag in [('colors','PAW_COLORS'),('bypass','SYNC_CONTINUE'),('hostility','HERD_RELATIONS_ONLY')]:assert f[field]==(flag in defines)
        features[name]=dict(sha256=sha(a.helpers/name),features=f)
    source={p['id']:p for p in before['beta']['packages']};packages=copy.deepcopy(before['beta']['packages'])
    assets=[];scope={};copies=[]
    for p in packages:
        if p['id'] not in VERSIONS:continue
        old=source[p['id']];archive=a.baseline/(p['id']+'.zip');m,original=payload(archive,old);files=dict(original);allowed=set()
        assert not m.get('remove')
        for name in files:
            if name in variants:files[name]=(a.helpers/name).read_bytes();allowed.add(name);copies.append(name)
            elif name in ('paws_patch_versions.ini','paws_player_colors.ini'):files[name]=(a.helpers/name).read_bytes();allowed.add(name)
        if p['id']=='common-ui':assert FRAMES.issubset(files), 'Accepted frames must remain present'
        assert set(files)==set(original), 'No data files added or removed'
        allowed={n for n in allowed if files[n]!=original[n]}
        assert {n for n in files if files[n]!=original[n]}==allowed
        m['version']=VERSIONS[p['id']];m['files']=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(files.items())]
        dest=out/'assets'/(p['id']+'-'+m['version']+'.zip');dest.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for n,b in [('module.json',encode(m))]+[('payload/'+n,b) for n,b in sorted(files.items())]:
                info=zipfile.ZipInfo(n,(2026,9,18,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
        if p['id']=='player-colors':
            p['description']={k:v.replace('48','39') for k,v in p['description'].items()}
        p.update(version=m['version'],size=dest.stat().st_size,sha256=sha(dest),urls=[DOWNLOAD+dest.name]);validate_package(dest,p)
        scope[p['id']]=dict(changed=sorted(allowed),preservedFiles=len(original)-len(allowed-set(FRAMES)),newFiles=sorted(set(files)-set(original)))
        assets.append(dict(id=p['id'],path=str(dest),size=p['size'],sha256=p['sha256'],url=p['urls'][0]))
    assert set(copies)==set(variants) and len(copies)==11,Counter(copies)
    feed=copy.deepcopy(before['beta']);feed['packages']=packages;entry=notes();feed['changelog']=[entry]+[n for n in feed['changelog'] if not(n.get('category')=='patch' and n.get('version')=='0.3.1-beta.2' and n.get('mods')==['arcane-wars'])]
    feed['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ');feed['patchGuide']['version']=VERSION
    feed['playerColorCount']=39
    colors=next(e for e in feed['patchGuide']['entries'] if e['id']=='colors')
    colors['bodyRu']='39 цветов и вариант «Случайно». Список открывается стрелкой рядом со значком цвета. Удалены девять выбранных похожих оттенков; цвета в старых сохранениях сохраняются.\n\nВ новой игре цвет следует за участником при смене места. Хост может менять цвета всех участников, клиент — только свой. В сохранениях цвета принадлежат королевствам и доступны только для просмотра.'
    colors['bodyEn']='39 colors plus Random. Open the list with the arrow beside the color badge. Nine selected similar shades have been removed; existing saved-game colors are preserved.\n\nIn new games, colors follow participants between seats. Hosts may change all participant colors; clients only their own. Saved-game colors belong to kingdoms and are read-only.'
    assert [p for p in feed['packages'] if p['id'] not in VERSIONS]==[p for p in before['beta']['packages'] if p['id'] not in VERSIONS]
    for field in before['beta']:
        if field not in ('packages','changelog','publishedAt','patchGuide','playerColorCount'):assert feed[field]==before['beta'][field],field
    write(out/'signed/beta.json',sign(feed,private))
    local=copy.deepcopy(feed)
    for p in local['packages']:
        own=next((x for x in assets if x['id']==p['id']),None)
        if own:p['urls']=[own['path']]
    write(out/'test-feeds/beta.json',sign(local,private));shutil.copyfile(REPO/'feed/v2/stable.json',out/'test-feeds/stable.json')
    write(out/'features.json',features);write(out/'scope.json',scope)
    history=read(REPO/'feed/changelog.history.json');assert history['beta']==before['beta']['changelog'];history['beta']=feed['changelog'];write(out/'changelog.history.json',history)
    write(out/'patch-guide-beta.json',feed['patchGuide'])
    write(out/'preparation.json',dict(tag=TAG,assets=assets,before={n:sha(REPO/p) for n,p in FEEDS.items()},
        historyBefore=sha(REPO/'feed/changelog.history.json'),guideBefore=sha(REPO/'feed/patch-guide-beta.json'),notesSha256=sha(REPO/'docs'/('release-'+TAG+'.md'))))
    print('PREPARED: four packages, 11 copies of eight helpers, 39-color palette, save-only retired shades; other data and 18 accepted textures preserved; only v2 Arcane beta changes',flush=True)

def public(a):
    out=a.out;prep=read(out/'preparation.json');r=json.loads(fetch(API+'/releases/tags/'+TAG));assert not r['draft'] and r['prerelease']
    ref=json.loads(fetch(API+'/git/ref/tags/'+TAG))['object']
    while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
    assert ref['type']=='commit' and ref['sha']==a.commit
    assert json.loads(fetch(API+'/releases/latest'))['tag_name']=='v0.8.4'
    for p in prep['assets']:
        b=fetch(p['url']);assert len(b)==p['size'] and hashlib.sha256(b).hexdigest().upper()==p['sha256'];print('PUBLIC PASS',p['id'],len(b),flush=True)
    write(out/'public-verification.json',dict(passed=True,commit=a.commit,assets=len(prep['assets'])))

def promote(a):
    out=a.out;prep=read(out/'preparation.json');assert read(out/'public-verification.json')['passed']
    assert read(out.parent/'installation-verification.json')['passed']
    assert read(out.parent/'helpers/camera-native/test-results.json')['passed']
    assert read(out.parent/'palette-verification/participant-tests.json')['passed']
    assert read(out.parent/'palette-verification/popup-width-tests.json')['passed']
    assert sha(REPO/'docs'/('release-'+TAG+'.md'))==prep['notesSha256']
    head=json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']
    live=RAW.replace('/main/','/'+head+'/')
    for n,p in FEEDS.items():
        assert sha(REPO/p)==prep['before'][n]
        assert normalize(fetch(live+p))==normalize((REPO/p).read_bytes())
    assert sha(REPO/'feed/changelog.history.json')==prep['historyBefore'] and sha(REPO/'feed/patch-guide-beta.json')==prep['guideBefore']
    verify(read(out/'signed/beta.json'),key())
    target=REPO/'feed/history/beta-before-arcane-032-beta1-v2.json';assert not target.exists()
    shutil.copyfile(REPO/'feed/v2/beta.json',target);shutil.copyfile(out/'signed/beta.json',REPO/'feed/v2/beta.json')
    for n in ('changelog.history.json','patch-guide-beta.json'):shutil.copyfile(out/n,REPO/'feed'/n)
    print('PROMOTED LOCALLY: public push/readback pending',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','verify-public','promote']);p.add_argument('--out',type=Path,required=True)
    for x in ('helpers','baseline','signing-dir'):p.add_argument('--'+x,type=Path)
    p.add_argument('--commit');a=p.parse_args();{'prepare':prepare,'verify-public':public,'promote':promote}[a.action](a)
