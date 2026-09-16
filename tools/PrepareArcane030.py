"""Promote accepted Arcane beta.9 to stable 0.3.0; never touch other channels/mods."""
import argparse,copy,hashlib,json,shutil,subprocess,zipfile
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS,RAW,API,key,normalize,fetch,sign
from PrepareRelease070 import read,write,encode,sha,verify,validate_package

REPO=Path(__file__).resolve().parents[1]
VERSION='0.3.0';TAG='patch-'+VERSION
VERSIONS={'pawpatch-core':VERSION,'common-ui':'1.3.72-ui.8','player-colors':VERSION,
          'desync-continue':'1.3.72-r4','powers-shards-original':'1.3.72-powers.2',
          **{'localization-'+c:'1.0.1' for c in ('de','fr','cs','uk')}}
DOWNLOAD='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'

def notes():
    parts=(REPO/'docs'/('release-'+TAG+'.md')).read_text('utf-8').split('\n---\n')
    assert len(parts)==2
    return dict(category='patch',version=VERSION,mods=['arcane-wars'],channel='stable',publishedAt='2026-09-16',
        title=dict(ru="Paw's Patch 0.3.0 — релиз Arcane Wars",en="Paw's Patch 0.3.0 — Arcane Wars release"),
        body={c:t.strip().split('\n',2)[2].strip() for c,t in zip(('ru','en'),parts)})

def guide(beta):
    g=copy.deepcopy(beta);g['version']=VERSION
    for e in g['entries']:
        if e['category']=='beta':e['category']='always'
        for k in ('bodyRu','bodyEn'):
            e[k]=e[k].replace('для беты Arcane Wars','для Arcane Wars').replace('одинаковую бету','одинаковую версию патча')
            e[k]=e[k].replace('Всегда включена в бете','Всегда включена в патче').replace('для Arcane Wars Beta','для Arcane Wars')
            e[k]=e[k].replace('for Arcane Wars Beta','for Arcane Wars').replace('Always enabled in Beta','Always enabled in the patch').replace('matching Beta versions','matching patch versions')
            e[k]=e[k].replace(' Все участники должны обновить бету и использовать совместимые игровые настройки.','')
            e[k]=e[k].replace(' All participants should update Beta and use compatible gameplay settings.','')
        if e['id']=='base':
            e['bodyRu']="Лаунчер устанавливает Arcane Wars как основу и применяет Paw's Patch. Релиз 0.3.0 включает все проверенные изменения беты 0.3.0-beta.9: автоулучшение городов, ускоренную передачу сейвов, проверку совместимости лобби, компактный выбор 48 цветов, исправления вылетов и логов, обновлённые рамки миникарты.\n\nПереключатели компонентов независимы. Для сетевой игры нужны совместимые версии и игровые настройки."
            e['bodyEn']="The launcher installs Arcane Wars as the base mod and applies Paw's Patch. Release 0.3.0 includes all accepted changes from 0.3.0-beta.9: city automation, faster save transfers, lobby compatibility checks, a compact 48-color picker, crash and lair fixes, and updated minimap frames.\n\nComponent switches are independent. Multiplayer requires compatible versions and gameplay settings."
    return g

def prepare(a):
    out=a.out.resolve();assert not (out/'preparation.json').exists(),'Refusing to overwrite a completed stage'
    out.mkdir(parents=True,exist_ok=True)
    before={n:verify(read(REPO/p),key()) for n,p in FEEDS.items()}
    assert before['beta']['patchGuide']['version']=='0.3.0-beta.9'
    assert next(p for p in before['stable']['packages'] if p['id']=='pawpatch-core')['version']=='0.2.1'
    for n,p in FEEDS.items():
        assert normalize(fetch(RAW+p+'?arcane030=baseline'))==normalize((REPO/p).read_bytes())
        dest=out/'previous'/(n+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(REPO/p,dest)
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
    assert private.public_key().public_numbers()==key().public_numbers()
    variants=read(REPO/'game/beta7/variants.json');features={}
    priorfeatures=read(a.beta_stage/'publication/features.json')
    for name in variants:
        f=json.loads(subprocess.check_output([str(a.helpers/name),'--features'],text=True,creationflags=subprocess.CREATE_NO_WINDOW))
        expected=copy.deepcopy(priorfeatures[name]['features']);expected['patchVersion']=VERSION
        assert f==expected,(name,f,expected)
        features[name]=dict(sha256=sha(a.helpers/name),features=f)
    oldstable={p['id']:p for p in before['stable']['packages']};beta={p['id']:p for p in before['beta']['packages']}
    differences={i for i,p in beta.items() if p.get('mods')==['arcane-wars'] and p!=oldstable.get(i)}
    assert differences==set(VERSIONS),differences
    sourcecaches=[a.beta_stage/'publication/assets',a.beta_stage/'test-cache',REPO/'packages']
    assets=[];scope={};copies=[];published={}
    for i,version in VERSIONS.items():
        p=copy.deepcopy(beta[i]);archive=out/'baseline'/(i+'.zip');archive.parent.mkdir(exist_ok=True)
        found=next((q for d in sourcecaches for q in d.glob('*.zip') if q.stat().st_size==p['size'] and sha(q)==p['sha256']),None)
        if found:shutil.copyfile(found,archive)
        else:archive.write_bytes(fetch(p['urls'][0]))
        validate_package(archive,p)
        with zipfile.ZipFile(archive) as z:
            m=json.loads(z.read('module.json'));entries={n.replace('\\','/').lower():n for n in z.namelist()}
            files={f['path'].replace('\\','/'):z.read(entries[('payload/'+f['path'].replace('\\','/')).lower()]) for f in m['files']}
        original=dict(files);changed=[]
        for name in files:
            if name in variants or name=='paws_patch_versions.ini':
                files[name]=(a.helpers/name).read_bytes();changed.append(name)
                if name in variants:copies.append(name)
        assert all(files[n]==b for n,b in original.items() if n not in changed)
        m['version']=version;m['files']=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(files.items())]
        dest=out/'assets'/(i+'-'+version+'.zip');dest.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for n,b in [('module.json',encode(m))]+[('payload/'+n,b) for n,b in sorted(files.items())]:
                info=zipfile.ZipInfo(n,(2026,9,16,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
        p.update(version=version,size=dest.stat().st_size,sha256=sha(dest),urls=[DOWNLOAD+dest.name],experimental=False)
        if i=='common-ui':p['description']=dict(ru='Обязательные исправления, автоулучшение городов, ускоренная передача сейвов и рамки миникарты.',en='Required fixes, city automation, faster save transfers and minimap frames.')
        validate_package(dest,p);published[i]=p
        scope[i]=dict(sourceBetaVersion=beta[i]['version'],sourceBetaSha256=beta[i]['sha256'],identityFiles=changed,preservedPayloadFiles=len(original)-len(changed))
        assets.append(dict(id=i,path=str(dest),size=p['size'],sha256=p['sha256'],url=p['urls'][0]))
    assert set(copies)==set(variants) and len(copies)==11
    feed=copy.deepcopy(before['stable']);feed['packages']=[published.get(p['id'],p) for p in feed['packages']]
    feed['patchGuide']=guide(before['beta']['patchGuide']);feed['playerColorCount']=48
    feed['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ');feed['changelog']=[notes()]+feed['changelog']
    assert [p for p in feed['packages'] if p['id'] not in VERSIONS]==[p for p in before['stable']['packages'] if p['id'] not in VERSIONS]
    for k in before['stable']:
        if k not in ('packages','patchGuide','publishedAt','changelog'):assert feed[k]==before['stable'][k],k
    assert feed['pureRuntimeOptions']==False and feed['launcher']['version']=='0.8.3'
    write(out/'signed/stable.json',sign(feed,private));local=copy.deepcopy(feed)
    for p in local['packages']:
        own=next((x for x in assets if x['id']==p['id']),None)
        if own:p['urls']=[own['path']]
    write(out/'test-feeds/stable.json',sign(local,private))
    history=read(REPO/'feed/changelog.history.json');assert history['stable']==before['stable']['changelog']
    history['stable']=feed['changelog'];write(out/'changelog.history.json',history)
    write(out/'patch-guide.json',feed['patchGuide']);write(out/'features.json',features);write(out/'scope.json',scope)
    write(out/'preparation.json',dict(tag=TAG,assets=assets,before={n:sha(REPO/p) for n,p in FEEDS.items()},
        historyBefore=sha(REPO/'feed/changelog.history.json'),guideBefore=sha(REPO/'feed/patch-guide.json'),notesSha256=sha(REPO/'docs'/('release-'+TAG+'.md'))))
    print('PREPARED: nine Arcane packages; accepted non-identity payloads preserved; pure mods, beta and legacy unchanged',flush=True)

def public(a):
    prep=read(a.out/'preparation.json');r=json.loads(fetch(API+'/releases/tags/'+TAG));assert not r['draft'] and not r['prerelease']
    ref=json.loads(fetch(API+'/git/ref/tags/'+TAG))['object']
    while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
    assert ref['type']=='commit' and ref['sha']==a.commit
    assert json.loads(fetch(API+'/releases/latest'))['tag_name']=='v0.8.3'
    for p in prep['assets']:
        b=fetch(p['url']);assert len(b)==p['size'] and hashlib.sha256(b).hexdigest().upper()==p['sha256'];print('PUBLIC PASS',p['id'],flush=True)
    write(a.out/'public-verification.json',dict(passed=True,commit=a.commit,assets=len(prep['assets'])))

def promote(a):
    out=a.out;prep=read(out/'preparation.json');assert read(out/'public-verification.json')['passed']
    assert read(out.parent/'installation-verification.json')['passed']
    assert sha(REPO/'docs'/('release-'+TAG+'.md'))==prep['notesSha256']
    for n,p in FEEDS.items():
        assert sha(REPO/p)==prep['before'][n]
        assert normalize(fetch(RAW+p+'?arcane030=promotion'))==normalize((REPO/p).read_bytes())
    assert sha(REPO/'feed/changelog.history.json')==prep['historyBefore'] and sha(REPO/'feed/patch-guide.json')==prep['guideBefore']
    verify(read(out/'signed/stable.json'),key())
    target=REPO/'feed/history/stable-before-arcane-030-v2.json';assert not target.exists()
    shutil.copyfile(REPO/'feed/v2/stable.json',target);shutil.copyfile(out/'signed/stable.json',REPO/'feed/v2/stable.json')
    for n in ('changelog.history.json','patch-guide.json'):shutil.copyfile(out/n,REPO/'feed'/n)
    print('PROMOTED LOCALLY: public push/readback pending',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','verify-public','promote']);p.add_argument('--out',type=Path,required=True)
    for x in ('helpers','beta-stage','signing-dir'):p.add_argument('--'+x,type=Path)
    p.add_argument('--commit');a=p.parse_args();{'prepare':prepare,'verify-public':public,'promote':promote}[a.action](a)
