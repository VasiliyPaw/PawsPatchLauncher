"""Bind publication to exact package bytes and explicitly scoped native evidence."""
import argparse,zipfile
from context import *
from PrepareRelease070 import validate_package

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pair',type=Path,required=True);a=ap.parse_args()
 evidence={}
 def passed(path):
  path=Path(path);row=read(path);assert row['passed'],str(path);evidence[str(path)]=sha(path);return row
 for name in ['world-native-r2/native-tests.json','beta-transactions-r2/result.json','beta-helpers-r4/composition-test.json','ui-tests-r4/result.json','ui-native-r3/path-tests.json','beta-install-r7/result.json']:passed(OUT/name)
 report=read(OUT/'beta-helpers-r4/build-report.json');prior=read(OUT/'beta-helpers-r3/build-report.json');assert len(report)==4
 for name,row in report.items():
  assert sha(OUT/'beta-helpers-r4'/name)==row['sha256']
  for p,h in row['sources'].items():assert sha(p)==h,p
  old={Path(p).name:h for p,h in prior[name]['sources'].items()};new={Path(p).name:h for p,h in row['sources'].items()}
  assert {k for k in set(old)|set(new)if old.get(k)!=new.get(k)}=={'PawsPurePresentation1372.dll','PurePresentationRuntimePayload.cs'}
  f=row['features'];assert f['patchVersion']=='0.5.0-beta.1' and f['version']=='1.3.72-pure.17-beta.1'
  assert f['largeMapMaximum']==2048 and f['nativeBiomeCount']==3 and f['dynamicDayCycleSeconds']==600
  assert all(f[k] is False for k in ['matchRecoveryEnabled','cityAssistant','automaticMilitia','additionalBuildingSlots','foundationDistribution','fractionalKingdomPoints'])
 for n in ['ui.c','day_clock.h','PurePresentationRuntimePatch.cs']:assert sha(OUT/'ui-native-r2'/n)==sha(OUT/'ui-native-r3'/n)
 qa=Path('G:/PawPure050QA-20261109');large=passed(qa/'vanilla-large-r7/result.json');resume=passed(qa/'immortals-resume-r2/result.json')
 assert large['large'] and resume['checks']['new-random-phase'] and resume['checks']['second-new-match-clock-unique']
 pair=passed(a.pair/'result.json');assert pair['twoPeers'] and pair['checks']['native-peer-checksums'] and pair['checks']['phase-same-on-peers']
 assert {k:v.upper()for k,v in pair['runtimeHashes'].items()}=={k:v['sha256']for k,v in report.items()}
 checks=read(a.pair/'checksums.json');assert checks['common']>=10 and not checks['mismatches']
 packages=read(OUT/'beta-stage-r4/packages.json');assert len(packages)==7;inventory={}
 for p in packages:
  path=OUT/'beta-stage-r4/assets'/p['urls'][-1].rsplit('/',1)[1];assert sha(path)==p['sha256'];validate_package(path,p)
  with zipfile.ZipFile(path)as z:
   names=z.namelist();assert not any(any(x in n.lower()for x in ['rig_input','pure-world.jsonl','reconnect-test.marker','qa_input','private.pem'])for n in names)
   if p['id']=='pure-fixes-runtime':
    assert z.read('payload/paws_presentation.ini')==b'[Runtime]\nstartupReadyEvent=1\n'
    for n,r in report.items():assert hashlib.sha256(z.read('payload/'+n)).hexdigest().upper()==r['sha256']
  inventory[p['id']]=dict(sha256=p['sha256'],size=p['size'],version=p['version'])
 write(OUT/'beta-publication/acceptance.json',dict(passed=True,patchVersion='0.5.0-beta.1',packages=inventory,evidence=evidence,livePair=str(a.pair),nativePeerChecksums=checks,automaticRecovery=False,earlierSingleScope='Prior presentation r2; final r3 changes only trailing-directory validation, separately proven on Win32. Final two-peer run uses exact published helper bytes.',limitations=['Local two-player LAN; no new Internet/VM, three-player, host-migration or historical-film validation','New extended-registry saves require a supporting patch version']))
 print('PURE_BETA_ACCEPTED_EXACT_PACKAGES',len(packages),checks['common'])
if __name__=='__main__':main()
