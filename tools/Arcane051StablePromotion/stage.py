import concurrent.futures,copy,zipfile
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
from common import *
def arcane(p):return p.get('mods')==['arcane-wars']
def main():
    stable=read(OUT/'before/feed/v3/stable.payload.json');beta=read(OUT/'before/feed/v3/beta.payload.json')
    assert beta['patchGuide']['version']==BETA and stable['patchGuide']['version']=='0.5.0'
    current={p['id']:p for p in stable['packages']};wanted=[p for p in beta['packages'] if arcane(p) and p!=current.get(p['id'])];assert len(wanted)==17
    helpers=read(OUT/'helpers/build-report.json');assert len(helpers)==8
    accepted=OUT/'accepted-assets';accepted.mkdir(exist_ok=True);assets=OUT/'assets';assets.mkdir(exist_ok=True)
    def download(p):
        path=accepted/(p['id']+'.zip')
        if not path.exists():path.write_bytes(fetch(p['urls'][0]))
        validate_package(path,p);return p['id'],path
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:resolved=dict(pool.map(download,wanted))
    replacements={};scope={};seen=set()
    for p in wanted:
        with zipfile.ZipFile(resolved[p['id']]) as z:
            module=json.loads(z.read('module.json'));original={f['path']:z.read('payload/'+f['path']) for f in module['files']};payload=dict(original)
            for name in payload:
                leaf=Path(name).name
                if leaf in helpers:
                    assert hashlib.sha256(payload[name]).hexdigest().upper()==helpers[leaf]['baselineSha256'];payload[name]=(OUT/'helpers'/leaf).read_bytes();seen.add(leaf)
                elif leaf=='paws_patch_versions.ini':
                    assert BETA.encode() in payload[name];payload[name]=payload[name].replace(BETA.encode(),VERSION.encode())
            changed=[n for n in payload if payload[n]!=original[n]]
            assert all(Path(n).name in helpers or Path(n).name=='paws_patch_versions.ini' for n in changed)
            module['version']=VERSION
            for f in module['files']:f.update(size=len(payload[f['path']]),sha256=hashlib.sha256(payload[f['path']]).hexdigest().upper())
            dest=assets/(p['id']+'-'+VERSION+'.zip')
            with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
                for info in z.infolist():
                    data=encode(module) if info.filename=='module.json' else payload.get(info.filename.removeprefix('payload/'),z.read(info.filename)) if info.filename.startswith('payload/') else z.read(info.filename)
                    out.writestr(info,data)
        q=copy.deepcopy(p);q.update(version=VERSION,experimental=False,size=dest.stat().st_size,sha256=sha(dest),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'+dest.name]);validate_package(dest,q);replacements[q['id']]=q
        scope[q['id']]=dict(sourceVersion=p['version'],sourceSha256=p['sha256'],changedPayload=changed,preservedFiles=len(payload)-len(changed),archive=str(dest))
        print('PACKAGE_PASS',q['id'],'changed payload',len(changed),flush=True)
    assert seen==set(helpers)
    notes=[e for e in beta['changelog'] if e.get('category')=='patch' and e.get('mods')==['arcane-wars'] and e['version'].startswith('0.5.1-beta.')]
    assert any(e['version']==BETA for e in notes)
    # The first beta's rendering experiment was explicitly disabled by beta.5.
    bodies={lang:'\n'.join(dict.fromkeys(line for e in notes for i,line in enumerate(e['body'].get(lang,e['body']['en']).splitlines()) if line.strip() and not(e['version']=='0.5.1-beta.1' and i==0))) for lang in ['ru','en','de','fr','cs','uk']}
    entry=dict(category='patch',mods=['arcane-wars'],channel='stable',version=VERSION,publishedAt='2026-11-15',title={lang:'Paw’s Patch '+VERSION+' — Arcane Wars' for lang in bodies},body=bodies)
    write(OUT/'release-patch-0.5.1.json',entry)
    (OUT/'notes.md').write_text('\n\n'.join(entry['title'][lang]+'\n\n'+body for lang,body in bodies.items())+'\n',encoding='utf-8')
    guide=copy.deepcopy(beta['patchGuide']);guide['version']=VERSION
    for e in guide['entries']:
        if e['category']=='beta':e['category']='always'
        if e['id']=='base':
            for field in ['bodyRu','bodyEn']:e[field]=e[field].replace('Paw’s Patch 0.4.0','Paw’s Patch '+VERSION)
    private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
    changedpaths=[]
    for prefix in ['v3','v2']:
        rel=f'feed/{prefix}/stable.json';a=verify(read(OUT/'before'/rel),key());source=verify(read(OUT/'before'/f'feed/{prefix}/beta.json'),key());b=copy.deepcopy(a)
        target={p['id']:copy.deepcopy(replacements.get(p['id'],p)) for p in source['packages'] if arcane(p)}
        b['packages']=[target[p['id']] if arcane(p) else p for p in a['packages']];known={p['id'] for p in b['packages']};b['packages'] += [p for name,p in target.items() if name not in known]
        b.update(patchGuide=guide,changelog=[entry]+a['changelog'],newsTitle=entry['title'],newsBody=entry['body'],publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        assert b['launcher']==a['launcher'] and b['game']==a['game'] and b.get('modGames')==a.get('modGames') and b.get('modGuides')==a.get('modGuides')
        assert [p for p in a['packages'] if not arcane(p)]==[p for p in b['packages'] if not arcane(p)]
        assert all(not p.get('experimental') and 'beta' not in p['version'] for p in b['packages'] if arcane(p))
        write(OUT/'signed'/rel,sign(b,private));changedpaths.append(rel)
        local=copy.deepcopy(b)
        for p in local['packages']:
            if p['id'] in scope:p['urls']=[scope[p['id']]['archive']]
        write(OUT/'local-feeds'/f'{prefix}-stable.json',sign(local,private))
    history=read(OUT/'before/feed/changelog.history.json');history['stable']=[entry]+history['stable'];write(OUT/'signed/feed/changelog.history.json',history);write(OUT/'signed/feed/patch-guide.json',guide);changedpaths+=['feed/changelog.history.json','feed/patch-guide.json']
    for rel in read(OUT/'baseline.json')['feeds']:
        if rel not in changedpaths:
            dest=OUT/'signed'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((OUT/'before'/rel).read_bytes())
    write(OUT/'preparation.json',dict(version=VERSION,beta=BETA,publicHead=read(OUT/'baseline.json')['publicHead'],changed=changedpaths,assets=[dict(id=i,path=v['archive'],sha256=sha(v['archive']),size=Path(v['archive']).stat().st_size) for i,v in scope.items()],scope=scope,helperVariants=len(helpers),selfTests=40,installedGameModified=False))
    (OUT/'public.pem').write_text(read(REPO/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'])
    print('STAGED: 17 packages, signed v2/v3 stable catalogs; beta/Pure/launcher retained',flush=True)
if __name__=='__main__':main()
