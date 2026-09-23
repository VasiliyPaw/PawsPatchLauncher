"""Build the beta.2 package set from the signed published baseline and audited sources.

No installed-game writes. Stable, legacy catalogs, launcher and other mods stay
byte-identical. Publication and catalog promotion are separate explicit steps.
"""
import argparse, copy, hashlib, json, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, API, key, normalize, fetch, sign
from PrepareRelease070 import read, write, encode, sha, verify, validate_package
from PrepareSeptember20Release import contents, module, feature

REPO=Path(__file__).resolve().parents[1]
WORK=REPO.parents[1]
VERSION='0.4.0-beta.2'
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
            info=zipfile.ZipInfo(n,(2026,9,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
    p.update(size=path.stat().st_size,sha256=sha(path),urls=[URL+path.name]);validate_package(path,p)
    return p,dict(channel='beta',tag=TAG,id=p['id'],path=str(path),size=p['size'],sha256=p['sha256'],url=p['urls'][0])

def prepare(a):
    stage=a.stage.resolve();out=stage/'publication';assert not (out/'preparation.json').exists()
    out.mkdir(parents=True,exist_ok=True);head=baseline()
    feeds={c:verify(read(REPO/p),key()) for c,p in FEEDS.items()};beta=feeds['beta']
    assert beta['patchGuide']['version']=='0.4.0-beta.1'
    assert feeds['stable']['patchGuide']['version']=='0.3.3'
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
    assert private.public_key().public_numbers()==key().public_numbers()
    for c,p in FEEDS.items():
        dest=out/'previous'/(c+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(REPO/p,dest)
    # Reuse only hash-matching published archives. Never trust a local filename.
    cached={}
    for root in (WORK/'outputs/release-20260920',REPO/'packages'):
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
        for k,v in dict(aiPolicyRevision=31,aiImprovementsSelectable=True,nightmareDifficultyRevision=3,nightmareRequiresAiImprovements=True,foundationDistributionRevision=2,sharedAnimationTargetGuardRevision=1,missingNetworkClientGuardRevision=1).items():assert f[k]==v,(name,k)
    copies=[]
    for payload in files.values():
        for n in list(payload):
            if n in VARIANTS or n=='paws_patch_versions.ini':
                payload[n]=(a.helpers/n).read_bytes()
                if n in VARIANTS:copies.append(n)
    assert len(copies)==11 and set(copies)==set(VARIANTS)
    foundation=REPO/'game/foundation-placement/data'
    for row in read(foundation/'manifest.json'):
        rel=row['path'].lower();blob=(foundation/row['path']).read_bytes()
        assert digest(blob).lower()==row['after'],rel
        old=files['common-ui'].get(rel,files['pawpatch-core'].get(rel))
        assert old is not None and digest(old).lower()==row['before'],rel
        # Common UI contains the effective family/map template and outranks
        # core. Replace both runtime layers, retaining data-only stock options.
        for layer in ('pawpatch-core','common-ui'):
            if rel in files[layer]:files[layer][rel]=blob
    ai=REPO/'game/ai-policy/data'
    for row in read(ai/'manifest.json'):
        rel=row['path'].lower();blob=(ai/row['path']).read_bytes()
        assert digest(blob).lower()==row['after']
        stock=files['pawpatch-core'].get(rel,files['arcane-wars'].get(rel))
        assert stock and digest(stock).lower()==row['before'],rel
        files['ai-improvements'][rel]=blob
    nightmare=a.helpers/'nightmare-data'
    for n in DEFS:
        # Windows preserves case-insensitive filesystem lookup; ZIP names are normalized.
        files['ai-improvements'][n]=(nightmare/n).read_bytes()
    files['common-ui']['data/localization/paws_nightmare.tgi']=(nightmare/'localization/en.tgi').read_bytes()
    for lang in ('ru','uk','cs','de','fr'):
        files['localization-bot-ui-'+lang]['local_ru/localization/paws_nightmare.tgi']=(nightmare/('localization/'+lang+'.tgi')).read_bytes()
    observer=WORK/'outputs/capture-observer-button-r31-20260923'
    for line in (observer/'assets.tsv').read_text('utf-8-sig').splitlines():
        fields=line.split('\t')
        if not fields[0].lower().startswith('data/ui/'):continue
        rel=fields[0];blob=(observer/'payload'/rel).read_bytes();assert digest(blob)==fields[-1]
        files['common-ui'][rel.lower()]=blob
    ui=module('sound_button',REPO/'game/gold-sound-button/prepare.py')
    layout='data/ui/game/game_interface.tgi'
    layout_base=files['common-ui'].get(layout,files['pawpatch-core'].get(layout,files['arcane-wars'].get(layout)))
    assert layout_base is not None,'Missing original Arcane Wars interface'
    files['common-ui'][layout]=ui.add_button(layout_base,(REPO/'game/gold-sound-button/button.tgi').read_text('utf-8'))
    files['common-ui']['data/ui/game/pawgoldsound.png']=(REPO/'game/gold-sound-button/PawGoldSound.png').read_bytes()
    # Compare generated layout with the accepted installation, without using it as input.
    accepted=read(WORK/'outputs/ai-city-plans-button-r5-20260923/installation.json')
    expected=next(r for r in accepted['files'] if r['path'].lower()==layout)['after']
    accepted_layout=(WORK/'outputs/ai-city-plans-button-r5-20260923/payload'/layout).read_bytes()
    assert digest(accepted_layout)==expected.upper(),'Accepted layout fixture changed'
    def definitions(blob):
        encoding='utf-16' if blob[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig'
        return [line.rstrip() for line in blob.decode(encoding).splitlines()
                if line.strip() and not line.lstrip().startswith(';;')]
    # The accepted local iteration normalized CRLF and retained an outdated
    # size comment. Require every non-comment definition to match exactly.
    assert definitions(files['common-ui'][layout])==definitions(accepted_layout),'Sound button differs from accepted layout'
    write(out/'layout-verification.json',dict(passed=True,acceptedSha256=expected,
          releaseSha256=digest(files['common-ui'][layout]),definitionsIdentical=True))
    assets=[];scope={};replacements={}
    packages={p['id']:p for p in beta['packages']}
    for i,payload in files.items():
        if payload==originals[i]:continue
        replacements[i],asset=emit(out,packages[i],payload);assets.append(asset)
        scope[i]=[n for n,b in payload.items() if b!=originals[i].get(n)]
    final=copy.deepcopy(beta)
    final['packages']=[replacements.get(p['id'],p) for p in beta['packages']]
    assert [p for p in final['packages'] if p.get('mods')!=['arcane-wars']]==[p for p in beta['packages'] if p.get('mods')!=['arcane-wars']]
    text=read(REPO/'docs/release-20260923.json')
    note=dict(category='patch',version=VERSION,publishedAt='2026-09-23',mods=['arcane-wars'],channel='beta',title={c:'Paw’s Patch '+VERSION for c in text['body']},body=text['body'])
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
    assert read(out/'public-verification.json')['passed']
    for p,h in prep['before'].items():assert sha(REPO/p)==h,'Catalog changed: '+p
    verify(read(out/'final/beta.json'),key())
    for src,dst in [('beta.json','feed/v2/beta.json'),('changelog.history.json','feed/changelog.history.json'),('patch-guide-beta.json','feed/patch-guide-beta.json')]:shutil.copyfile(out/'final'/src,REPO/dst)
    print('PROMOTED beta',VERSION)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--helpers',type=Path);p.add_argument('--signing-dir',type=Path);p.add_argument('--promote',action='store_true');a=p.parse_args()
    if a.promote:promote(a)
    else:prepare(a)
