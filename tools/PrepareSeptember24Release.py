"""Build the beta.3 package set from the signed published baseline and audited sources.

No installed-game writes. Stable, legacy catalogs, launcher and other mods stay
byte-identical. Publication and catalog promotion are separate explicit steps.
"""
import argparse, copy, hashlib, json, re, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, API, key, normalize, fetch, sign
from PrepareRelease070 import read, write, encode, sha, verify, validate_package
from PrepareSeptember20Release import contents, module, feature

REPO=Path(__file__).resolve().parents[1]
WORK=REPO.parents[1]
VERSION='0.4.0-beta.3'
TAG='patch-'+VERSION
URL='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'
VARIANTS=read(REPO/'game/beta7/variants.json')
DEFS=('data/game/handicaps_paws_nightmare.tgi','data/properties/paws_handicap_nightmare.tgi')

def digest(b):return hashlib.sha256(b).hexdigest().upper()

def baseline():
    head=json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']
    for name in [*FEEDS.values(),'feed/changelog.history.json','feed/patch-guide-beta.json']:
        assert normalize(fetch(RAW.replace('/main/','/'+head+'/')+name))==normalize((REPO/name).read_bytes()),'Public baseline changed: '+name
    return head

def emit(out,p,files):
    p=copy.deepcopy(p);p['version']=VERSION
    manifest=dict(id=p['id'],version=VERSION,files=[dict(path=n,size=len(b),sha256=digest(b)) for n,b in sorted(files.items())],remove=[])
    path=out/'assets'/TAG/(p['id']+'-'+VERSION+'.zip');path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in [('module.json',encode(manifest))]+[('payload/'+n,b) for n,b in sorted(files.items())]:
            info=zipfile.ZipInfo(n,(2026,9,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
    p.update(size=path.stat().st_size,sha256=sha(path),urls=[URL+path.name]);validate_package(path,p)
    return p,dict(channel='beta',tag=TAG,id=p['id'],path=str(path),size=p['size'],sha256=p['sha256'],url=p['urls'][0])

def prepare(a):
    stage=a.stage.resolve();out=stage/'publication';assert not (out/'preparation.json').exists()
    build_bytes=(stage/'build.log').read_bytes()
    build_log=build_bytes.decode('utf-16' if build_bytes[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig')
    assert 'Built eight quiet helpers. No game launched.' in build_log,'Full helper build has not passed'
    out.mkdir(parents=True,exist_ok=True);head=baseline()
    feeds={c:verify(read(REPO/p),key()) for c,p in FEEDS.items()};beta=feeds['beta']
    assert beta['patchGuide']['version']=='0.4.0-beta.2'
    assert feeds['stable']['patchGuide']['version']=='0.3.3'
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
    assert private.public_key().public_numbers()==key().public_numbers()
    for c,p in FEEDS.items():
        dest=out/'previous'/(c+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(REPO/p,dest)
    # Reuse only hash-matching published archives. Never trust a local filename.
    cached={}
    for root in (WORK/'outputs/release-20260923',WORK/'outputs/release-20260920',REPO/'packages'):
        for p in root.rglob('*.zip'):cached.setdefault(p.stat().st_size,[]).append(p)
    originals={};resolved={}
    all_packages={p['sha256']:p for f in (feeds['stable'],beta) for p in f['packages']}
    for p in all_packages.values():
        source=next((q for q in cached.get(p['size'],[]) if sha(q)==p['sha256']),None)
        if source is None:
            source=stage/'downloads'/(p['sha256']+'.zip');source.parent.mkdir(exist_ok=True)
            if not source.exists():source.write_bytes(fetch(p['urls'][0]))
        validate_package(source,p);resolved[p['sha256']]=str(source.resolve())
    for p in beta['packages']:
        if p.get('mods')==['arcane-wars']:originals[p['id']]=contents(Path(resolved[p['sha256']]),p)
    files=copy.deepcopy(originals)
    features={name:dict(sha256=sha(a.helpers/name),features=feature(a.helpers/name)) for name in VARIANTS}
    for name,row in features.items():
        f=row['features'];assert f['patchVersion']==VERSION
        for k,v in dict(aiPolicyRevision=35,aiImprovementsSelectable=True,nightmareDifficultyRevision=3,nightmareRequiresAiImprovements=True,foundationDistributionRevision=2,sharedAnimationTargetGuardRevision=1,missingNetworkClientGuardRevision=1).items():assert f[k]==v,(name,k)
    copies=[]
    for payload in files.values():
        for n in list(payload):
            if n in VARIANTS or n=='paws_patch_versions.ini':
                payload[n]=(a.helpers/n).read_bytes()
                if n in VARIANTS:copies.append(n)
    assert len(copies)==11 and set(copies)==set(VARIANTS)
    # Existing map distribution and AI profiles are inherited byte-for-byte.
    # Only the 0.75-KP balance definition gains the Gauri kingdom prerequisite.
    requirements=module('arcane_requirements',REPO/'game/arcane-unit-requirements/prepare.py')
    from GameplayPresentationData import decode
    unit='data/units/gauri/aw_maelstrom_destroyer.tgi'
    requirement_layers=[]
    for layer,payload in files.items():
        if unit in payload and re.search(r'Kingdom_points_consumed\s*=\s*0\.75\s',decode(payload[unit])[0],re.I):
            payload[unit]=requirements.patch(payload[unit]);requirement_layers.append(layer)
    assert 'aw-siege-balance' in requirement_layers
    lobby=module('bot_lobby_ui',REPO/'game/bot-lobby/prepare_ui.py')
    tooltips=module('bot_tooltips',REPO/'game/bot-lobby/prepare_tooltips.py')
    for language in tooltips.TEXT:
        layer='common-ui' if language=='en' else 'localization-bot-ui-'+language
        for name in ('pcolors','staging'):
            rel='data/ui/menus/'+name+'.tgi';raw=files[layer][rel]
            text=decode(raw)[0]
            for kind in ('Race','Faction','Difficulty'):
                for suffix in ('Label',''):
                    start,end=lobby.span(text,'PawBots'+kind+suffix);text=text[:start]+text[end:]
            start,end=lobby.span(text,'Slots');block=text[start:end]
            block,count=re.subn(r'B\s*=\s*\+365\b','B = +405',block,count=1)
            assert count==1,(language,name,'old client geometry')
            raw=(text[:start]+block+text[end:]).encode('utf-16')
            files[layer][rel]=lobby.transform(raw,language)
        sources=['pawpatch-core'] if language=='en' else ['localization-'+language,'aw-localization-'+language,'pawpatch-data-'+language]
        catalogs={}
        for source in sources:
            for rel,raw in files[source].items():
                # Every helper verifies the same English family table, even
                # when the UI is localized. Localized depots override labels.
                if rel.endswith('/localization/strings_data_k2.tgi') and (language=='en' or not rel.startswith('data/')):
                    catalogs[rel]=tooltips.transform(raw,language)
        assert catalogs,language
        files[layer].update(catalogs)
    nightmare=a.helpers/'nightmare-data'
    for n in DEFS:
        # Windows preserves case-insensitive filesystem lookup; ZIP names are normalized.
        files['ai-improvements'][n]=(nightmare/n).read_bytes()
    files['common-ui']['data/localization/paws_nightmare.tgi']=(nightmare/'localization/en.tgi').read_bytes()
    for lang in ('ru','uk','cs','de','fr'):
        files['localization-bot-ui-'+lang]['local_ru/localization/paws_nightmare.tgi']=(nightmare/('localization/'+lang+'.tgi')).read_bytes()
    ui=module('sound_button',REPO/'game/gold-sound-button/prepare.py')
    layout='data/ui/game/game_interface.tgi'
    layout_base=files['common-ui'].get(layout,files['pawpatch-core'].get(layout,files['arcane-wars'].get(layout)))
    assert layout_base is not None,'Missing original Arcane Wars interface'
    files['common-ui'][layout]=ui.add_button(layout_base,(REPO/'game/gold-sound-button/button.tgi').read_text('utf-8'))
    files['common-ui']['data/ui/game/pawgoldsound.png']=(REPO/'game/gold-sound-button/PawGoldSound.png').read_bytes()
    files['common-ui']['data/audio/paws_gold_button.tgi']=(REPO/'game/gold-sound-button/audio.tgi').read_bytes()
    layout_text=decode(files['common-ui'][layout])[0]
    assert 'L = 44r' in layout_text and 'T = 251.333333b' in layout_text
    assert 'set_sound = paws_gold_button_select' in layout_text
    assert 'control_flags = NULL' in files['common-ui']['data/audio/paws_gold_button.tgi'].decode('utf-8')
    write(out/'layout-verification.json',dict(passed=True,frameAt2560x1440=[100,100],
          releaseSha256=digest(files['common-ui'][layout]),simultaneousSounds=64))
    assets=[];scope={};replacements={}
    packages={p['id']:p for p in beta['packages']}
    for i,payload in files.items():
        if payload==originals[i]:continue
        replacements[i],asset=emit(out,packages[i],payload);assets.append(asset)
        scope[i]=[n for n,b in payload.items() if b!=originals[i].get(n)]
    final=copy.deepcopy(beta)
    final['packages']=[replacements.get(p['id'],p) for p in beta['packages']]
    assert [p for p in final['packages'] if p.get('mods')!=['arcane-wars']]==[p for p in beta['packages'] if p.get('mods')!=['arcane-wars']]
    text=read(REPO/'docs/release-20260924.json')
    note=dict(category='patch',version=VERSION,publishedAt='2026-09-24',mods=['arcane-wars'],channel='beta',title={c:'Paw’s Patch '+VERSION for c in text['body']},body=text['body'])
    final['changelog']=[note]+final['changelog'];final['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    final['patchGuide']['version']=VERSION
    additions=text['guide'];final['patchGuide']['entries']=[e for e in final['patchGuide']['entries'] if e['id'] not in {x['id'] for x in additions}]+additions
    write(out/'final/beta.json',sign(final,private))
    history=read(REPO/'feed/changelog.history.json');history['beta']=final['changelog']
    write(out/'final/changelog.history.json',history);write(out/'final/patch-guide-beta.json',final['patchGuide'])
    for channel in ('stable','beta'):
        test=copy.deepcopy(final if channel=='beta' else feeds[channel])
        for p in test['packages']:
            own=next((x for x in assets if x['sha256']==p['sha256']),None)
            p['urls']=[own['path'] if own else resolved[p['sha256']]]
        write(out/'test-feeds'/(channel+'.json'),sign(test,private))
    write(out/'features.json',features);write(out/'scope.json',scope)
    write(out/'preparation.json',dict(baselineCommit=head,assets=assets,before={p:sha(REPO/p) for p in [*FEEDS.values(),'feed/changelog.history.json','feed/patch-guide-beta.json']},version=VERSION))
    print('STAGED',len(assets),'beta packages; stable and launcher unchanged')

def promote(a):
    out=a.stage/'publication';prep=read(out/'preparation.json')
    assert read(a.stage/'installation-verification.json')['passed']
    assert read(out/'data-verification.json')['passed']
    assert read(a.stage/'native-r35-equivalence.json')['passed']
    assert read(out/'public-verification.json')['passed']
    for p,h in prep['before'].items():assert sha(REPO/p)==h,'Catalog changed: '+p
    verify(read(out/'final/beta.json'),key())
    for src,dst in [('beta.json','feed/v2/beta.json'),('changelog.history.json','feed/changelog.history.json'),('patch-guide-beta.json','feed/patch-guide-beta.json')]:shutil.copyfile(out/'final'/src,REPO/dst)
    print('PROMOTED beta',VERSION)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--helpers',type=Path);p.add_argument('--signing-dir',type=Path);p.add_argument('--promote',action='store_true');a=p.parse_args()
    if a.promote:promote(a)
    else:prepare(a)
