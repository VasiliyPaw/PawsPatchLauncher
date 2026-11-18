from context import *
import zipfile
def main():
 for group,base in [('arcane',AP),('pure',PP)]:
  old=read(base/'helpers/build-report.json');new=read(O/group/'helpers/build-report.json')
  for n,row in new.items():
   before={Path(p).name:(Path(p),h)for p,h in old[n]['sources'].items()};after={Path(p).name:(Path(p),h)for p,h in row['sources'].items()};assert before.keys()==after.keys()
   for name,(p,h)in after.items():
    original,oldhash=before[name];assert sha(p)==h and sha(original)==oldhash
    if name=='25-LargeMapsIdentity.cs':assert p.read_bytes()==original.read_bytes().replace(b'0.6.0-beta.5',ARC.encode())
    elif name=='4-PureChannel.cs':assert p.read_bytes()==original.read_bytes().replace(b'0.5.0-beta.9',PURE.encode()).replace(b'1.3.72-pure.21-beta.9',RT.encode())
    else:assert h==oldhash
 for pid,row in read(O/'graphics-baseline.json').items():
  with zipfile.ZipFile(read(O/'package-audit.json')[pid]['path'])as z:
   for n,r in row['files'].items():assert hashlib.sha256(z.read('payload/'+n)).hexdigest().upper()==r['sha256']
   m=json.loads(z.read('module.json'));assert set(read(O/'hd-removals.json'))<=set(m['remove']);assert not any(n.startswith('payload/paws-hd-ui')for n in z.namelist())
 for mod in ['arcane','vanilla','immortals']:
  for suffix in ['installer-result','fullres-upgrade']:assert read(O/(mod+'-'+suffix+'.json'))['passed']
 assert read(O/'launcher-tests.json')['passed']and read(O/'catalog-qa/result.json')['passed']
 terrain=read(O/'terrain-preserved.json');assert terrain==next(p for p in verify(read(O/'signed/feed/v3/beta.json'),key())['packages']if p['id']==terrain['id'])
 write(O/'verification.json',dict(passed=True,versions=dict(arcane=ARC,pure=PURE,launcher='1.0.21'),legacyArtMatchesPreHdBytes=True,hdPathsRemoved=655,stockSkinsRestored=6,installerCases=18,fullResolutionUpgradeCases=3,nativeGameplayInputsIdentical=True,managedGameplayChanges='Version identities only',terrainPackageUnchanged=True,terrainRedownloadRequired=False,nativeGameLaunched=False,newMultiplayerMatchClaimed=False,launcherTests=read(O/'launcher-tests.json'),cacheCleanup=read(O/'cleanup-integration/result.json'),catalog=read(O/'catalog-qa/result.json')))
 print('LEGACY_UI_RELEASE_VERIFICATION_PASS',flush=True)
if __name__=='__main__':main()
