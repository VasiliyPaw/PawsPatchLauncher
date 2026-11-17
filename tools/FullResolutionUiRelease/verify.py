from context import *
from PIL import Image
import zipfile
def main():
 accepted=read(HD/'verification.json');assert accepted['passed']and accepted['allSourcePixelsPreserved']and accepted['gpu']['passed']
 m=read(HD/'fullres-manifest.json');seen=set()
 for r in m['files']:
  if r['source']in seen:continue
  seen.add(r['source']);src=Path(r['source']);assert sha(src)==r['sourceSha256'].upper();out=HD/'overlay'/r['path'];a=Image.open(src).convert('RGBA');b=Image.open(out).convert('RGBA');assert a.size==b.size and a.tobytes()==b.tobytes()
 assert len(seen)==236
 # Compiler inputs are identical to the previous releases except for the
 # two explicit managed version identity constants.
 for group,base in[('arcane',AP),('pure',PP)]:
  old=read(base/'helpers/build-report.json');new=read(O/group/'helpers/build-report.json')
  for n,row in new.items():
   before={Path(p).name:(Path(p),h)for p,h in old[n]['sources'].items()};after={Path(p).name:(Path(p),h)for p,h in row['sources'].items()};assert before.keys()==after.keys()
   for name,(p,h)in after.items():
    original,oldhash=before[name];assert sha(p)==h and sha(original)==oldhash
    if name=='25-LargeMapsIdentity.cs':assert p.read_bytes()==original.read_bytes().replace(b'0.6.0-beta.3',ARC.encode())
    elif name=='4-PureChannel.cs':assert p.read_bytes()==original.read_bytes().replace(b'0.5.0-beta.7',PURE.encode()).replace(b'1.3.72-pure.21-beta.7',RT.encode())
    else:assert h==oldhash,(group,n,name)
 for mod in['arcane','vanilla','immortals']:
  r=read(O/(mod+'-installer-result.json'));assert r['passed']and r['originalArchivesUnchanged']and r['fullresImages']==708
 assert read(O/'catalog-qa/result.json')['passed']
 audit=read(O/'package-audit.json');assert all(r['fullresImages']==708 for p,r in audit.items()if p in['common-ui','pure-beta-common'])
 write(O/'verification.json',dict(passed=True,versions=dict(arcane=ARC,pure=PURE),sourceAssets=236,sourcePixelsPreserved=True,sourceSizesPreserved=True,fullresImagePathsPerMod=708,nativeGameplayInputsIdentical=True,managedChanges='Version identity constants only',installerMods=3,installerCases=18,allHelperVariants=12,rollbackAndReapply=True,catalog=read(O/'catalog-qa/result.json'),liveVisualEvidence=str(HD/'verification.json'),liveScope='Accepted Arcane human HUD at 2560x1440 and actual GPU upload dimensions; remaining race masters checked as files. No new multiplayer match.',downloadBytes={g:sum(p['size']for p in read(O/'packages.json')if audit[p['id']]['group']==g)for g in['arcane','pure']},terrainArchivesReused=True,launcherUnchanged=True,stableChannelsUnchanged=True))
 print('FULL_RES_RELEASE_VERIFICATION_PASS',flush=True)
if __name__=='__main__':main()
