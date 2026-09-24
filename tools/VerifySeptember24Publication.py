"""Read back beta.3 release bytes and signed catalogs; no publication writes."""
import argparse, hashlib, json
from pathlib import Path
from PrepareRelease081 import API, RAW, FEEDS, fetch, key, normalize
from PrepareRelease070 import read, write, verify

p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--catalog',action='store_true');a=p.parse_args()
out=a.stage.resolve()/'publication';repo=Path(__file__).resolve().parents[1]
prep=read(out/'preparation.json')
if a.catalog:
    proof=[]
    for channel,path in FEEDS.items():
        blob=fetch(RAW.replace('/main/','/'+a.commit+'/')+path)
        feed=verify(json.loads(blob),key())
        assert normalize(blob)==normalize((repo/path).read_bytes()),'Published catalog differs: '+path
        assert feed['launcher']['version']=='0.8.6'
        if channel=='beta':assert feed['patchGuide']['version']=='0.4.0-beta.3'
        else:assert normalize(blob)==normalize((out/'previous'/(channel+'.json')).read_bytes()),'Unrelated channel changed'
        proof.append(dict(channel=channel,sha256=hashlib.sha256(blob).hexdigest(),signatureValid=True))
    for path in ['feed/changelog.history.json','feed/patch-guide-beta.json']:
        assert normalize(fetch(RAW.replace('/main/','/'+a.commit+'/')+path))==normalize((repo/path).read_bytes())
    write(out/'catalog-readback.json',dict(passed=True,commit=a.commit,catalogs=proof))
    print('PUBLIC_CATALOGS_PASS',len(proof))
else:
    def get(path):return json.loads(fetch(API+path))
    tag='patch-0.4.0-beta.3';release=get('/releases/tags/'+tag)
    assert not release['draft'] and release['prerelease']
    ref=get('/git/ref/tags/'+tag)['object']
    for _ in range(4):
        if ref['type']!='tag':break
        ref=get('/git/tags/'+ref['sha'])['object']
    assert ref['type']=='commit' and ref['sha']==a.commit,'Release source mismatch'
    remote={asset['name']:asset for asset in release['assets']}
    assert set(remote)=={Path(row['path']).name for row in prep['assets']},'Unexpected release asset set'
    proof=[]
    for row in prep['assets']:
        asset=remote[Path(row['path']).name];blob=fetch(row['url'])
        assert len(blob)==row['size']==asset['size']
        assert hashlib.sha256(blob).hexdigest().upper()==row['sha256']
        assert asset['digest']=='sha256:'+row['sha256'].lower()
        proof.append(dict(id=row['id'],channel='beta',sha256=row['sha256'],size=len(blob)))
    write(out/'public-verification.json',dict(passed=True,sourceCommit=a.commit,release=release['html_url'],assets=proof))
    print('PUBLIC_PATCH_ASSETS_PASS',len(proof))
