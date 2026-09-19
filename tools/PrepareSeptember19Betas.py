"""Stage scoped Arcane company recovery and pure palette/frame betas.

Publication and catalog promotion are explicit separate operations. Neither
staging nor verification modifies the installed game or opens a game process.
"""
import argparse, copy, hashlib, json, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, API, key, normalize, fetch, sign
from PrepareRelease070 import read, write, encode, sha, verify, validate_package

REPO=Path(__file__).resolve().parents[1]
AW='0.3.2-beta.2'; PURE='0.3.0-beta.2'
TAGS={'arcane':'patch-'+AW,'pure':'patch-pure-'+PURE}
VERSIONS={'pawpatch-core':AW,'common-ui':'1.3.72-ui.11-beta.2',
          'player-colors':AW,'desync-continue':'1.3.72-r7-beta.2'}
PURE_IDS={'pure-fixes-data','pure-fixes-runtime','pure-player-colors'}
DOWNLOAD='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'
FRAMES={f'skins/{r}/{v}/background.tga' for r in ('human','gauri','drauga','haroun','undead','shadow')
        for v in ('ui/game/controlpanel','ui/800/game/controlpanel','ui/1280/game/controlpanel')}

def payload(path,p):
    validate_package(path,p)
    with zipfile.ZipFile(path) as z:
        m=json.loads(z.read('module.json'))
        assert not m.get('remove')
        return m,{f['path']:z.read('payload/'+f['path']) for f in m['files']}

def notes(group):
    version=AW if group=='arcane' else PURE
    filename='release-patch-'+AW+'.md' if group=='arcane' else 'release-pure-'+PURE+'.md'
    sections=(REPO/'docs'/filename).read_text('utf-8').split('\n---\n');assert len(sections)==2
    return dict(category='patch',version=version,mods=['arcane-wars'] if group=='arcane' else ['vanilla','immortals'],
                channel='beta',publishedAt='2026-09-19',
                title={c:s.strip().split('\n')[0].removeprefix('# ') for c,s in zip(('ru','en'),sections)},
                body={c:s.strip().split('\n',2)[2].strip() for c,s in zip(('ru','en'),sections)})

def current_matches():
    head=json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']
    base=RAW.replace('/main/','/'+head+'/')
    for p in [*FEEDS.values(),'feed/changelog.history.json','feed/patch-guide-beta.json']:
        assert normalize(fetch(base+p))==normalize((REPO/p).read_bytes()),'Public baseline moved: '+p
    return head

def prepare(a):
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);assert not (out/'preparation.json').exists()
    head=current_matches();before={n:verify(read(REPO/p),key()) for n,p in FEEDS.items()}
    feed=copy.deepcopy(before['beta']);assert feed['patchGuide']['version']=='0.3.2-beta.1'
    assert feed['launcher']['version']=='0.8.5' and feed['playerColorCount']==39
    for n,p in FEEDS.items():
        dest=out/'previous'/(n+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(REPO/p,dest)
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
    assert private.public_key().public_numbers()==key().public_numbers()
    variants=read(REPO/'game/beta7/variants.json');features={}
    for name,defines in variants.items():
        f=json.loads(subprocess.check_output([str(a.helpers/name),'--features'],text=True,creationflags=subprocess.CREATE_NO_WINDOW))
        assert f['patchVersion']==AW and f['companyPositionRecoveryRevision']==1
        assert f['lairWoundedDefendersRevision']==3 and f['gameplayCameraZoomMaximum']==2
        assert f['cityPolicyRevision']==23 and f['lobbyCompatibility'] and f['fastSaveTransfer']
        for field,flag in [('colors','PAW_COLORS'),('bypass','SYNC_CONTINUE'),('hostility','HERD_RELATIONS_ONLY')]:assert f[field]==(flag in defines)
        features[name]=dict(sha256=sha(a.helpers/name),features=f)
    baseline=out/'baseline';baseline.mkdir();original={}
    for p in feed['packages']:
        if p['id'] not in set(VERSIONS)|PURE_IDS:continue
        path=baseline/(p['id']+'.zip');path.write_bytes(fetch(p['urls'][0]));original[p['id']]=payload(path,p)
    assets=[];scope={};copies=[]
    for p in feed['packages']:
        if p['id'] not in VERSIONS:continue
        m,old=original[p['id']];files=dict(old);changed=[]
        for name in files:
            if name in variants:
                files[name]=(a.helpers/name).read_bytes();changed.append(name);copies.append(name)
            elif name=='paws_patch_versions.ini':files[name]=(a.helpers/name).read_bytes();changed.append(name)
        assert {n for n in files if files[n]!=old[n]}==set(changed)
        m['version']=VERSIONS[p['id']]
        m['files']=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(files.items())]
        dest=out/'assets'/TAGS['arcane']/(p['id']+'-'+m['version']+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(dest,'w') as z:
            for n,b in [('module.json',encode(m))]+[('payload/'+n,b) for n,b in sorted(files.items())]:
                info=zipfile.ZipInfo(n,(2026,9,19,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
        p.update(version=m['version'],size=dest.stat().st_size,sha256=sha(dest),urls=[DOWNLOAD+TAGS['arcane']+'/'+dest.name]);validate_package(dest,p)
        scope[p['id']]=dict(changed=changed,preservedFiles=len(old)-len(changed),newFiles=[])
        assets.append(dict(group='arcane',tag=TAGS['arcane'],id=p['id'],path=str(dest),size=p['size'],sha256=p['sha256'],url=p['urls'][0]))
    assert set(copies)==set(variants) and len(copies)==11
    pure=read(a.pure/'packages.json')['beta'];assert {p['id'] for p in pure}==PURE_IDS
    for new in pure:
        src=Path(new['urls'][0]);m,files=payload(src,new);old=original[new['id']][1]
        if new['id']=='pure-fixes-data':
            assert set(files)-set(old)==FRAMES and all(files[n]==b for n,b in old.items())
            accepted={n.lower():b for n,b in original['common-ui'][1].items()}
            assert all(files[n]==accepted[n.lower()] for n in FRAMES)
        elif new['id']=='pure-player-colors':
            assert set(files)==set(old)
            assert files['Data/UI/Menus/pcolors.tgi']==old['Data/UI/Menus/pcolors.tgi']
            assert files['paws_player_colors.ini']==(REPO/'game/beta7/paws_player_colors.ini').read_bytes()
        else:
            assert set(files)==set(old) and len(files)==4
            for name in files:
                f=json.loads(subprocess.check_output([str(a.pure/'beta'/name),'--features'],text=True,creationflags=subprocess.CREATE_NO_WINDOW))
                assert f['patchVersion']==PURE and not f['hostility'] and not f['cityAssistant']
                assert 'companyPositionRecoveryRevision' not in f
        dest=out/'assets'/TAGS['pure']/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
        p=next(p for p in feed['packages'] if p['id']==new['id'])
        for field in ('version','size','sha256','description'):p[field]=copy.deepcopy(new[field])
        p['urls']=[DOWNLOAD+TAGS['pure']+'/'+dest.name];validate_package(dest,p)
        scope[p['id']]=dict(changed=[n for n in old if files[n]!=old[n]],newFiles=sorted(set(files)-set(old)))
        assets.append(dict(group='pure',tag=TAGS['pure'],id=p['id'],path=str(dest),size=p['size'],sha256=p['sha256'],url=p['urls'][0]))
    entries=[notes('arcane'),notes('pure')];feed['changelog']=entries+feed['changelog']
    feed['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    feed['patchGuide']['version']=AW
    feed['patchGuide']['entries'].insert(0,dict(id='company-position-recovery',category='always',
        titleRu='Движение рот',titleEn='Company movement',
        bodyRu='Восстанавливает движение роты, если её значок и позиция зависли отдельно от бойцов. Работает и при загрузке сохранений.',
        bodyEn='Restores company movement when its banner and position get stuck apart from its troops. Also works when loading saved games.'))
    frame=copy.deepcopy(next(e for e in feed['patchGuide']['entries'] if e['id']=='minimap-frames'))
    color=next(e for e in feed['patchGuide']['entries'] if e['id']=='colors')
    for g in feed['modGuides']:
        if g['id'] not in ('vanilla','immortals'):continue
        doc=g['patchGuide'];assert doc['version']=='0.3.0-beta.1';doc['version']=PURE
        for e in doc['entries']:
            if e['id']=='colors':
                e['bodyRu']=color['bodyRu'];e['bodyEn']=color['bodyEn']
        doc['entries'].append(copy.deepcopy(frame))
        # Keep descriptions and mode rules; only the beta palette count changes.
        for section in g['sections']:
            for field in ('title','body'):
                if field in section:section[field]={lang:txt.replace('48','39') for lang,txt in section[field].items()}
    changed=set(VERSIONS)|PURE_IDS
    assert [p for p in feed['packages'] if p['id'] not in changed]==[p for p in before['beta']['packages'] if p['id'] not in changed]
    for field in before['beta']:
        if field not in ('packages','patchGuide','modGuides','changelog','publishedAt'):assert feed[field]==before['beta'][field],field
    write(out/'signed/beta.json',sign(feed,private));local=copy.deepcopy(feed)
    for p in local['packages']:
        own=next((x for x in assets if x['id']==p['id']),None)
        if own:p['urls']=[own['path']]
    write(out/'test-feeds/beta.json',sign(local,private));shutil.copyfile(REPO/'feed/v2/stable.json',out/'test-feeds/stable.json')
    history=read(REPO/'feed/changelog.history.json');assert history['beta']==before['beta']['changelog'];history['beta']=feed['changelog']
    write(out/'changelog.history.json',history);write(out/'patch-guide-beta.json',feed['patchGuide'])
    write(out/'features.json',features);write(out/'scope.json',scope)
    write(out/'preparation.json',dict(baselineCommit=head,tags=TAGS,assets=assets,before={n:sha(REPO/p) for n,p in FEEDS.items()},
        historyBefore=sha(REPO/'feed/changelog.history.json'),guideBefore=sha(REPO/'feed/patch-guide-beta.json'),
        notes={g:notes(g) for g in TAGS}))
    print('PREPARED: seven beta packages; stable, launcher and legacy feeds unchanged')

def public(a):
    prep=read(a.out/'preparation.json')
    for tag in TAGS.values():
        r=json.loads(fetch(API+'/releases/tags/'+tag));assert not r['draft'] and r['prerelease']
        ref=json.loads(fetch(API+'/git/ref/tags/'+tag))['object']
        while ref['type']=='tag':ref=json.loads(fetch(API+'/git/tags/'+ref['sha']))['object']
        assert ref['type']=='commit' and ref['sha']==a.commit
    assert json.loads(fetch(API+'/releases/latest'))['tag_name']=='v0.8.5'
    for p in prep['assets']:
        data=fetch(p['url']);assert len(data)==p['size'] and hashlib.sha256(data).hexdigest().upper()==p['sha256']
        print('PUBLIC PASS',p['id'],flush=True)
    write(a.out/'public-verification.json',dict(passed=True,commit=a.commit,assets=len(prep['assets'])))

def promote(a):
    prep=read(a.out/'preparation.json');assert read(a.out/'public-verification.json')['passed']
    assert read(a.out.parent/'installation-verification.json')['passed']
    assert read(a.out.parent/'release-acceptance.json')['passed']
    assert read(a.out.parent/'helpers/company-native/test-results.json')['passed']
    assert all(notes(g)==prep['notes'][g] for g in TAGS),'Release notes changed after staging'
    current_matches()
    for n,p in FEEDS.items():assert sha(REPO/p)==prep['before'][n]
    assert sha(REPO/'feed/changelog.history.json')==prep['historyBefore']
    assert sha(REPO/'feed/patch-guide-beta.json')==prep['guideBefore']
    verify(read(a.out/'signed/beta.json'),key())
    backup=REPO/'feed/history/beta-before-september19-betas-v2.json';assert not backup.exists()
    shutil.copyfile(REPO/'feed/v2/beta.json',backup)
    shutil.copyfile(a.out/'signed/beta.json',REPO/'feed/v2/beta.json')
    for n in ('changelog.history.json','patch-guide-beta.json'):shutil.copyfile(a.out/n,REPO/'feed'/n)
    print('PROMOTED LOCALLY; push and public readback pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','verify-public','promote']);p.add_argument('--out',type=Path,required=True)
    for name in ('helpers','pure','signing-dir'):p.add_argument('--'+name,type=Path)
    p.add_argument('--commit');a=p.parse_args();{'prepare':prepare,'verify-public':public,'promote':promote}[a.action](a)
