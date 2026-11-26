from context import *
from packages import validate,FIX
import zipfile
def main():
 helper=read(O/'helpers/build-report.json');assert helper['passed']and helper['helperCount']==8 and helper['helperFeatureChecks']==8 and helper['selfTestChecks']==40
 assert read(O/'helpers/closure.json')['ownCount']==0 and read(O/'native-all-closure.json')['allOwnedClosed']
 native=read(FIX/'final-native-v2/manifest.json');assert native['hookCount']==109 and native['overlapCheckPassed']and native['multiplayer'];assert native['sha256'].upper()==sha(FIX/'final-native-v2/sandbox/Mods/PawsBridges.dll')
 materials=read(O/'materials/manifest.json');assert materials['models']==672 and not materials['newProjectedShadows']and not materials['gameplayDefinitionsIncluded']
 checks=read(O/'checks-before-package.json');qa=read(O/'qa/result.json');assert qa['passed']
 save=read(O/'native-save/comparison.json');assert save['passed']and save['allSevenExactIDsPresentInBoth']and not save['differences']
 assert read(O/'native-save/final-all-closure.json')['allOwnedClosed']
 fixture=read(O/'native-save/fixture-assembly.json');assert fixture['passed']and fixture['realPrivateUpgrade']is False
 for label in ['baseline','final']:
  assert read(O/('native-save/production-pair-'+label+'.json'))['exactProductionPairs']
  assert read(O/('native-save/'+label+'-post-ready.json'))['status']=='POST_USER_READY_RECORDED'
 pairs={p['id']:p for p in read(O/'packages.json')};assert set(pairs)=={'pawpatch-core','common-ui','player-colors','desync-continue'}
 count=0
 for p in pairs.values():
  path=Path(read(O/'package-audit.json')[p['id']]['path']);count+=validate(path,p)
  receipt=qa['packageAssets']['new:'+p['id']];assert receipt['sha256'].upper()==p['sha256'].upper()and receipt['signedSha256'].upper()==p['sha256'].upper()and receipt['size']==p['size']
 assert qa['helperHashes']=={n:r['sha256']for n,r in helper['helpers'].items()}
 with zipfile.ZipFile(read(O/'package-audit.json')['pawpatch-core']['path'])as z:
  names=set(z.namelist());assert not any(any(x in n.lower()for x in ['networkqa','testinstalled','private-not-published','save/','profile/','no-fog'])for n in names)
  assert hashlib.sha256(z.read('payload/Mods/PawsBridges.dll')).hexdigest().upper()==native['sha256'].upper()
  assert hashlib.sha256(z.read('payload/Mods/PawsWaterBiomes.dll')).hexdigest().upper()==sha(FIX/'water/PawsWaterBiomes.dll')
  for n,r in materials['files'].items():assert hashlib.sha256(z.read('payload/rivers-data/'+n)).hexdigest().lower()==r['sha256'].lower()
  assert len([n for n in names if n.startswith('payload/rivers-data/Paws/Bridges/RacialBuild/shadow/work_')and n.endswith('.nif')])==56
 # Byte-level preservation of stock artwork and its cleanup rules.
 from packages import OLD
 with zipfile.ZipFile(OLD/'common-ui-0.6.0-beta.6.zip')as a,zipfile.ZipFile(read(O/'package-audit.json')['common-ui']['path'])as b:
  ma=json.loads(a.read('module.json'));mb=json.loads(b.read('module.json'));assert ma.get('remove')==mb.get('remove')and len(mb['remove'])==1132
  artwork=[r['path']for r in ma['files']if Path(r['path']).suffix.lower()in['.tga','.png','.rwd']]
  for n in artwork:assert a.read('payload/'+n)==b.read('payload/'+n)
 for rel in FILES[:6]:
  a=verify(read(O/'before'/rel));b=verify(read(O/'signed'/rel))
  if rel not in['feed/v2/beta.json','feed/v3/beta.json']:assert (O/'before'/rel).read_bytes()==(O/'signed'/rel).read_bytes()
  else:
   for k in['launcher','game','modGames','modGuides']:assert a[k]==b[k]
   assert next(p for p in a['packages']if p['id']=='arcane-biome-textures')==next(p for p in b['packages']if p['id']=='arcane-biome-textures')
   assert [p for p in a['packages']if p['id']not in pairs]==[p for p in b['packages']if p['id']not in pairs]
 unchanged()
 checks.update(passed=True,version=V,productionHooks=109,packagePayloadFiles=count,helperFeatureChecks=8,helperSelfTests=40,materialModels=672,materialApprovedReferencesExact=24,newProjectedShadows=False,stockArtworkByteExact=len(artwork),hdRemovalRulesPreserved=1132,terrainPackageUnchanged=True,terrainRedownloadRequired=False,unrelatedModsAndStableUnchanged=True,qa=qa,nativeSave=dict(passed=True,exactProductionPairs=True,sameInitialWorldTime=save['sameInitialWorldTime'],allSevenExactIdsPreserved=True,bridgeCounts=save['allBridgeCounts'],differenceCount=0,postReadySmokePassed=True,allOwnedClosed=True,scope='Existing saved actor retention; no new live multiplayer match or full 24-module private upgrade claimed.'))
 write(O/'verification.json',checks);print('ARCANE_BETA7_RELEASE_GATE_PASS',count,flush=True)
if __name__=='__main__':main()
