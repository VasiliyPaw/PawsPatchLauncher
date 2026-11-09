"""Bind the exact three packages to native, installer and two-mode live evidence."""
import zipfile
from context import *
from PrepareRelease070 import validate_package
def main():
 evidence={}
 def passed(path):
  path=Path(path);row=read(path);assert row.get('passed',row.get('accepted')) is True,path;evidence[str(path)]=sha(path);return row
 for n in ['cache-tests/result.json','find-tests/result.json','ui-tests/result.json','composition-tests-r2/result.json','graphics-tests/result.json','installer-r5/result.json']:passed(OUT/n)
 assert 'graphics ownership/rollback mismatch'in(OUT/'installer-r5/Program.cs').read_text();evidence['installerProgram']=sha(OUT/'installer-r5/Program.cs')
 base=Path('G:/PawPure050OptQA-20261109');pair=passed(base/'vanilla-pair-r3/result.json');resume=passed(base/'immortals-resume-r1/result.json')
 report=read(OUT/'helpers-r1/build-report.json');expected={n:r['sha256']for n,r in report.items()};assert len(expected)==4
 for row in [pair,resume]:assert {n:h.upper()for n,h in row['runtimeHashes'].items()}==expected
 for n,r in report.items():
  assert sha(OUT/'helpers-r1'/n)==r['sha256'];assert r['features']['patchVersion']==PATCH and r['features']['version']==RUNTIME
  assert not any(r['features'][k]for k in ['matchRecoveryEnabled','cityAssistant','automaticMilitia','additionalBuildingSlots','foundationDistribution','fractionalKingdomPoints','gpuPrewarm'])
  for p,h in r['sources'].items():assert sha(p)==h,p
 crc=read(base/'vanilla-pair-r3/checksums.json');assert crc['common']>=10 and not crc['mismatches']
 assert resume['checks']['save-phase-preserved']and resume['checks']['new-random-phase']and resume['checks']['second-new-match-clock-unique']
 probes={}
 for label,path in [('vanilla',base/'vanilla-pair-r3/host-optimization.json'),('immortals-loaded',base/'immortals-resume-r1/loaded-optimization.json'),('immortals-second',base/'immortals-resume-r1/second-optimization.json')]:
  r=read(path);assert r['animationPercent']==80 and r['resource']['animationPolicy']==1 and r['resource']['callback']!=0 and r['resource']['failures']==0
  assert r['buffers']['mode']==1 and r['buffers']['hits']>0 and r['buffers']['bytes']<=32*1024*1024 and r['buffers']['held']<=512;assert r['findHookTarget']!=0;probes[label]=r;evidence[str(path)]=sha(path)
 packages=read(OUT/'stage-r3/packages.json');assert len(packages)==3;inventory={}
 for p in packages:
  path=OUT/'stage-r3/assets'/p['urls'][-1].rsplit('/',1)[1];assert sha(path)==p['sha256'];validate_package(path,p)
  with zipfile.ZipFile(path)as z:
   names=z.namelist();assert not any(any(s in n.lower()for s in ['rig_input','avifil32','reconnect-test.marker','d3d9-fixture','private.pem'])for n in names)
   if p['id']=='pure-beta-common':assert hashlib.sha256(z.read('payload/d3d9.dll')).hexdigest().upper()=='112920FF0CB9A38158A12E9F8875B6B4FBBCE9ADA5C364EF55936EBBE4A83179'
   if p['id']=='pure-fixes-runtime':
    assert 'payload/d3d9.dll'not in names
    for n,h in expected.items():assert hashlib.sha256(z.read('payload/'+n)).hexdigest().upper()==h
  inventory[p['id']]=dict(version=p['version'],size=p['size'],sha256=p['sha256'])
 audit=read(OUT/'stage-r3/audit.json');assert audit['dataPayloadUnchanged']and audit['commonChanged']==['d3d9.dll']and audit['worldAndLocalizationUnchanged']
 receipt=dict(passed=True,patchVersion=PATCH,packages=inventory,helperHashes=expected,nativePeerChecksums=crc,optimizationSnapshots=probes,evidence=evidence,automaticRecovery=False,limitations=['Functional compatibility, no isolated Pure FPS or frame-time A/B claim','Local two-player Vanilla LAN; Immortals actual-save reload and second match','No new Internet, other-PC/GPU or many-hour large-army acceptance'])
 write(OUT/'publication/acceptance.json',receipt);public=dict(receipt);public.pop('evidence');write(REPO/'docs/verification-pure-050-optimizations-20261109.json',public);print('PURE_OPTIMIZATION_PORT_ACCEPTED',len(packages),crc['common'])
if __name__=='__main__':main()
