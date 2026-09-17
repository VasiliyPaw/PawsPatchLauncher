"""Stage a term-only localization revision with unchanged patch/launcher versions.

Reuses verified released packages. Existing assets are immutable; every corrected
archive gets a new filename. Package versions remain unchanged and the launcher
detects the revision by archive SHA-256. No executable/gameplay payload is edited.
"""
import argparse, copy, hashlib, json, re, shutil, zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import key, sign, fetch, normalize, RAW
from PrepareRelease070 import read, write, encode, sha, verify, validate_package
from PrepareSplitLanguages import dec
from PrepareEuropeanModLanguages import table

REPO=Path(__file__).resolve().parents[1]
REVISION='text-20260917.1'
DOWNLOAD='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-0.3.0/'
FEEDS={c:'feed/v2/'+c+'.json' for c in ('stable','beta')}
TERM=read(REPO/'game/localization/apparition-term.json')

def language(path):
    if path.lower().startswith('data/'):return 'en'
    m=re.match(r'Local_(?:aw_)?(ru|de|fr|cs|uk)/',path,re.I)
    assert m,path
    return m[1].lower()

def prepare(a):
    out=a.out;out.mkdir(parents=True,exist_ok=True)
    assert not (out/'preparation.json').exists(),'Use a fresh output directory'
    feeds={c:verify(read(REPO/p),key()) for c,p in FEEDS.items()}
    for c,p in FEEDS.items():
        assert normalize(fetch(RAW+p+'?apparition=baseline'))==normalize((REPO/p).read_bytes()),'Public feed changed'
        dest=out/'previous'/(c+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(REPO/p,dest)
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
    assert private.public_key().public_numbers()==key().public_numbers()
    inventory=read(a.inventory);replacements={};assets=[];audited=[]
    expected={p['sha256'] for f in feeds.values() for p in f['packages'] if p['id'].startswith(('aw-localization-','localization-','pawpatch-data-')) or p['id']=='pawpatch-core'}
    assert expected=={x['package']['sha256'] for x in inventory},'Incomplete package inventory'
    for item in inventory:
        p=item['package'];source=Path(item['source']);validate_package(source,p)
        with zipfile.ZipFile(source) as z:
            content={n:z.read(n) for n in z.namelist()}
        module=json.loads(content['module.json']);original=copy.deepcopy(content);changes=[]
        for f in module['files']:
            path=f['path'].replace('\\','/');member='payload/'+path
            if not path.lower().endswith('/strings_data_k2.tgi'):continue
            before=table(content[member])
            if TERM['key'] not in before:continue
            code=language(path);value=TERM['values'][code]
            # The English source uses the mod author's misspelling. It still
            # names the same creature and is hash-guarded by released helpers.
            # This revision corrects mistranslations, leaving the source intact.
            if code=='en':continue
            assert before[TERM['key']] in (value,TERM['previous'][code]),(path,before[TERM['key']])
            if before[TERM['key']]==value:continue
            raw=content[member];text=dec(raw)
            pattern=r'(?m)^(\s*'+re.escape(TERM['key'])+r'\s*=\s*")([^"\r\n]*)(")'
            fixed,count=re.subn(pattern,lambda m:m[1]+value+m[3],text)
            assert count==1,(p['id'],path,count)
            if raw.startswith(b'\xff\xfe'):changed=b'\xff\xfe'+fixed.encode('utf-16-le')
            elif raw.startswith(b'\xfe\xff'):changed=b'\xfe\xff'+fixed.encode('utf-16-be')
            elif raw.startswith(b'\xef\xbb\xbf'):changed=b'\xef\xbb\xbf'+fixed.encode('utf-8')
            else:
                try:raw.decode('utf-8');changed=fixed.encode('utf-8')
                except UnicodeDecodeError:changed=fixed.encode('cp1251')
            after=table(changed)
            assert after==dict(before,**{TERM['key']:value})
            if p['id']=='localization-ru':
                # Released helpers guard Local_ru's original table hash.
                # Mount the corrected table last through the existing locale
                # mechanism; leave the protected original byte-identical.
                overlay='Local_aw_ru_hotfix/Localization/strings_data_K2.tgi'
                assert 'payload/'+overlay not in content
                content['payload/'+overlay]=changed
                startup='startup/autoexec_ru.txt';old_startup=content['payload/'+startup]
                assert old_startup.rstrip().endswith(b'addlocaledepot Local_ru/')
                content['payload/'+startup]=old_startup.rstrip()+b'\r\naddlocaledepot Local_aw_ru_hotfix/\r\n'
                changes.append(dict(path=overlay,sourcePath=path,language=code,before=before[TERM['key']],after=value))
            else:
                content[member]=changed
                changes.append(dict(path=path,language=code,before=before[TERM['key']],after=value))
        if changes:
            files={f['path'].replace('\\','/'):f for f in module['files']}
            for member,data in content.items():
                if not member.startswith('payload/'):continue
                path=member[8:]
                files[path]=dict(files.get(path,{}),path=path,size=len(data),sha256=hashlib.sha256(data).hexdigest().upper())
            module['files']=list(files.values())
            content['module.json']=encode(module)
            dest=out/'assets'/(p['id']+'-'+p['version']+'.'+REVISION+'.zip');dest.parent.mkdir(exist_ok=True)
            with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                for name,data in content.items():z.writestr(name,data)
            changed_names={n for n in content if content[n]!=original.get(n)}
            allowed={'module.json',*('payload/'+c['path'] for c in changes)}
            if p['id']=='localization-ru':
                allowed.add('payload/startup/autoexec_ru.txt')
                assert content['payload/Local_ru/Localization/strings_data_K2.tgi']==original['payload/Local_ru/Localization/strings_data_K2.tgi']
            assert changed_names==allowed
            assert module['version']==p['version'] and module['id']==p['id']
            q=dict(p,size=dest.stat().st_size,sha256=sha(dest),urls=[DOWNLOAD+dest.name])
            validate_package(dest,q);replacements[p['sha256']]=q
            assets.append(dict(path=str(dest.resolve()),sourceSha256=p['sha256'],package=q,changes=changes,preservedPayloadFiles=len(module['files'])-len(changes)))
        audited.append(dict(id=p['id'],version=p['version'],changed=bool(changes)))
    assert len(assets)==10 and len(inventory)==21,(len(assets),len(inventory))
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    for c,previous in feeds.items():
        final=copy.deepcopy(previous)
        for p in final['packages']:
            if p['sha256'] in replacements:
                q=replacements[p['sha256']]
                for field in ('size','sha256','urls'):p[field]=q[field]
        final['publishedAt']=stamp
        assert [(p['id'],p['version']) for p in previous['packages']]==[(p['id'],p['version']) for p in final['packages']]
        assert {k:v for k,v in previous.items() if k not in ('packages','publishedAt')}=={k:v for k,v in final.items() if k not in ('packages','publishedAt')}
        write(out/'signed'/(c+'.json'),sign(final,private))
        local=copy.deepcopy(final)
        paths={x['package']['sha256']:x['path'] for x in assets}
        for p in local['packages']:
            if p['sha256'] in paths:p['urls']=[paths[p['sha256']]]
        write(out/'test-feeds'/(c+'.json'),sign(local,private))
    write(out/'preparation.json',dict(revision=REVISION,assets=assets,audited=audited,before={c:sha(REPO/p) for c,p in FEEDS.items()},term=TERM,patchVersionsUnchanged=True,launcherVersionUnchanged=True,gameplayAndExecutablesUnchanged=True))
    print('STAGED',len(assets),'text-only archives; 21 packages audited; all patch/launcher versions unchanged')

def public(a):
    prep=read(a.out/'preparation.json')
    for asset in prep['assets']:
        p=asset['package'];raw=fetch(p['urls'][0])
        assert len(raw)==p['size'] and hashlib.sha256(raw).hexdigest().upper()==p['sha256']
        print('PUBLIC PASS',p['id'],p['version'],flush=True)
    write(a.out/'public-verification.json',dict(passed=True,assets=len(prep['assets'])))

def promote(a):
    prep=read(a.out/'preparation.json');assert read(a.out/'public-verification.json')['passed']
    assert read(a.out/'installation-verification.json')['passed']
    for c,p in FEEDS.items():
        assert sha(REPO/p)==prep['before'][c]
        assert normalize(fetch(RAW+p+'?apparition=promotion'))==normalize((REPO/p).read_bytes())
        verify(read(a.out/'signed'/(c+'.json')),key())
    for c,p in FEEDS.items():
        dest=REPO/'feed/history'/(c+'-before-apparition-text-20260917.json')
        assert not dest.exists();shutil.copyfile(REPO/p,dest)
        shutil.copyfile(a.out/'signed'/(c+'.json'),REPO/p)
    print('PROMOTED locally; push and public catalog readback remain')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','verify-public','promote'))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--inventory',type=Path);p.add_argument('--signing-dir',type=Path)
    a=p.parse_args();{'prepare':prepare,'verify-public':public,'promote':promote}[a.action](a)
