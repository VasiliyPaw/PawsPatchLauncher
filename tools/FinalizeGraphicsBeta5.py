"""Verify public Beta 5 artifacts and stage canonical beta feeds; never uploads."""
import argparse, base64, copy, hashlib, json, re, shutil, urllib.request
from pathlib import Path
import PreparePatchChannels078 as base
from FinalizeMaintenance0712 import audit_package
from PrepareGraphicsBeta5 import TAG, VERSION, VERSIONS

API='https://api.github.com/repos/VasiliyPaw/PawsPatchLauncher'
RAW='https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/'
def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'PawsPatchGraphicsBetaAudit','Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=45) as response:return response.read()
def normalized(data):return data.replace(b'\r\n',b'\n')
def payload(data):return json.loads(base64.b64decode(json.loads(data)['payload'],validate=True))

def main(args):
    out=args.candidate.resolve();prepared=base.read(out/'preparation.json');plan=base.read(out/'release-plan.json')
    assert re.fullmatch('[0-9a-f]{40}',args.commit)
    assert plan['tag']==TAG and plan['version']==VERSION and plan['prerelease'] and not plan['launcherIncluded']
    assert base.sha(base.REPO/'docs'/('release-'+TAG+'.md'))==plan['notesSha256']
    assert len(plan['assets'])==2
    release=json.loads(fetch(API+'/releases/tags/'+TAG))
    assert release['prerelease'] and not release['draft'] and release['tag_name']==TAG
    tag=json.loads(fetch(API+'/git/ref/tags/'+TAG))['object']
    for _ in range(8):
        if tag['type']!='tag':break
        tag=json.loads(fetch(API+'/git/tags/'+tag['sha']))['object']
    assert tag['type']=='commit' and tag['sha']==args.commit
    assert json.loads(fetch(API+'/releases/latest'))['tag_name']=='v0.7.12'
    assets={a['name']:a for a in release['assets']};verified=[]
    for item in plan['assets']:
        audit_package(Path(item['path']),item)
        public=assets[item['name']]
        assert public['browser_download_url']==base.DOWNLOADS+TAG+'/'+item['name']
        assert public['size']==item['size'] and public['digest'].lower()=='sha256:'+item['sha256'].lower()
        data=fetch(public['browser_download_url'])
        assert len(data)==item['size'] and base.sha_bytes(data)==item['sha256']
        verified.append(dict(name=item['name'],size=len(data),sha256=base.sha_bytes(data)))
        print('PUBLIC ASSET VERIFIED',item['name'],len(data),flush=True)
    replacements={a['packageId']:a for a in plan['assets']}
    assert set(replacements)==set(VERSIONS)
    for schema in base.SCHEMAS:
        for channel in base.CHANNELS:
            rel='feed/'+('v2/' if schema=='v2' else '')+channel+'.json'
            current=base.REPO/rel;before=current.read_bytes()
            assert base.sha(current)==prepared['before'][schema+'/'+channel]
            assert normalized(fetch(RAW+rel+'?graphics-beta5=baseline'))==normalized(before),'Public feed moved'
            assert normalized((out/'previous'/schema/(channel+'.signed.json')).read_bytes())==normalized(before)
            if channel=='stable':continue
            candidate=out/'feeds'/schema/'beta.production.signed.json'
            base.command([args.dotnet,base.REPO/'tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll','verify',candidate,args.public_key])
            after=payload(candidate.read_bytes());old=payload(before)
            assert after==base.read(candidate.with_name('beta.production.payload.json'))
            assert {k:v for k,v in after.items() if k not in ('publishedAt','packages','changelog')}=={k:v for k,v in old.items() if k not in ('publishedAt','packages','changelog')}
            assert after['changelog'][1:]==old['changelog']
            entry=after['changelog'][0]
            assert entry['category']=='patch' and entry['version']==VERSION and entry['mods']==['arcane-wars']
            expected=copy.deepcopy(old['packages'])
            for p in expected:
                if p['id'] in replacements:
                    a=replacements[p['id']]
                    for key in ('version','size','sha256'):p[key]=a[key]
                    p['urls']=[base.DOWNLOADS+TAG+'/'+a['name']]
            assert after['packages']==expected
    history=base.read(out/'changelog.history.json');previous=base.read(base.REPO/'feed/changelog.history.json')
    assert base.sha(base.REPO/'feed/changelog.history.json')==prepared['historyBefore']
    assert history['stable']==previous['stable'] and history['beta'][1:]==previous['beta']
    assert history['beta']==base.read(out/'feeds/v2/beta.production.payload.json')['changelog']
    if args.promote:
        for schema in base.SCHEMAS:
            rel='feed/'+('v2/' if schema=='v2' else '')+'beta.json'
            assert base.sha(base.REPO/rel)==prepared['before'][schema+'/beta']
            backup=base.REPO/'feed/history'/('beta-before-graphics-beta5-'+schema+'.json')
            assert not backup.exists()
            shutil.copyfile(base.REPO/rel,backup)
            shutil.copyfile(out/'feeds'/schema/'beta.production.signed.json',base.REPO/rel)
        shutil.copyfile(out/'changelog.history.json',base.REPO/'feed/changelog.history.json')
    base.write(out/'public-verification.json',dict(tag=TAG,sourceCommit=args.commit,assets=verified,locallyPromoted=args.promote))
    print('BETA 5 PUBLIC VERIFIED'+('; canonical beta feeds promoted locally, push/readback still required' if args.promote else ''))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('candidate',type=Path);p.add_argument('commit')
    p.add_argument('--dotnet',type=Path,required=True);p.add_argument('--public-key',type=Path,required=True)
    p.add_argument('--promote',action='store_true')
    main(p.parse_args())
