from pathlib import Path
import os,sys,json,hashlib,subprocess,copy,base64,urllib.request,tarfile
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec,utils
P=Path(__file__).resolve().parent; WS=P.parents[1]; O=WS/'outputs/arcane060-beta7-release-20261126'; S=P/'source'; REPO=WS/'work/launcher-104-release'
V='0.6.0-beta.7'; TAG='patch-'+V
API='https://api.github.com/repos/VasiliyPaw/PawsPatchLauncher'; RAW='https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/'
KEY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work/PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem')
FILES=[f'feed/{p}{c}.json'for p in['v3/','v2/','']for c in['stable','beta']]+['feed/changelog.history.json','feed/patch-guide-beta.json']
def encode(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,x):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(x))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()
def env():
 e=os.environ.copy();e.update(DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',TEMP=str(P/'Temp'),TMP=str(P/'Temp'),DOTNET_CLI_HOME=str(P/'dotnet-home'),NUGET_PACKAGES=str(WS/'work/arcane060-beta3-release-20261116/nuget'),NUGET_HTTP_CACHE_PATH=str(P/'nuget-http'),NUGET_SCRATCH=str(P/'nuget-scratch'),DOTNET_CLI_TELEMETRY_OPTOUT='1');return e
def run(args,cwd=REPO,log=None):
 r=subprocess.run(list(map(str,args)),cwd=cwd,env=env(),capture_output=True,text=True,encoding='utf-8',errors='replace')
 if log:Path(log).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
 assert r.returncode==0,(list(map(str,args[:3])),r.returncode,r.stdout[-3000:],r.stderr[-3000:]);return r.stdout.strip()
def git(*a):return run(['git',*a])
def key():return serialization.load_pem_public_key(read(S/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'].encode())
def verify(a):
 b=base64.b64decode(a['payload'],validate=True); sig=base64.b64decode(a['signature'],validate=True);assert len(sig)==64
 key().verify(utils.encode_dss_signature(int.from_bytes(sig[:32],'big'),int.from_bytes(sig[32:],'big')),b,ec.ECDSA(hashes.SHA256()));return json.loads(b)
def sign(x):
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers();b=encode(x);r,s=utils.decode_dss_signature(private.sign(b,ec.ECDSA(hashes.SHA256())));a=dict(keyId='pawpatch-prod-2026',payload=base64.b64encode(b).decode(),signature=base64.b64encode(r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode());assert verify(a)==x;return a
def unchanged():
 b=read(P/'baseline.json');assert git('rev-parse','HEAD')==b['localHead'];assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(P/'staged-before.patch').read_bytes()
def snapshot():
 git('fetch','--no-tags','origin','main');head=git('rev-parse','FETCH_HEAD')
 for rel in FILES:
  dest=O/'before'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(subprocess.check_output(['git','show',head+':'+rel],cwd=REPO))
 write(O/'catalog-baseline.json',dict(publicHead=head));return head
def baseline():
 assert not (P/'baseline.json').exists();head=snapshot();assert not S.exists()
 with (P/'public-source.tar').open('wb')as f:subprocess.run(['git','archive',head],cwd=REPO,env=env(),stdout=f,check=True)
 S.mkdir()
 with tarfile.open(P/'public-source.tar')as t:t.extractall(S,filter='data')
 (P/'staged-before.patch').write_bytes(subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO));write(P/'baseline.json',dict(publicHead=head,localHead=git('rev-parse','HEAD')))
 f=verify(read(O/'before/feed/v3/beta.json'));assert next(p for p in f['packages']if p['id']=='pawpatch-core')['version']=='0.6.0-beta.6'
 write(O/'baseline-summary.json',dict(head=head,launcher=f['launcher']['version'],packages={p['id']:dict(version=p['version'],size=p['size'],sha256=p['sha256'],urls=p['urls'])for p in f['packages']if p['id']in['pawpatch-core','common-ui','player-colors','desync-continue','arcane-biome-textures']},verifiedSignatures=6))
 for r in FILES[:6]:verify(read(O/'before'/r))
 print('BASELINE_VERIFIED',head,f['launcher']['version'],flush=True)
if __name__=='__main__':baseline()
