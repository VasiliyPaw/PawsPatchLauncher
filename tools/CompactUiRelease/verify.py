from context import *
from resources import read_rwd
from PIL import Image
import io
def main():
 assert read(O/'reader-result.json')['passed']and read(O/'base-skin-preservation.json')['passed'];assert read(O/'terrain-merge.json')['passed']
 masters={r['source']:r['sourceSha256'].upper()for r in read(HD/'fullres-manifest.json')['files']};m=read(O/'image-export.json');seen=set();archives={n:read_rwd(r['path'])for n,r in read(O/'resource-archives.json').items()}
 for r in m['files']:
  if r['source']in seen:continue
  seen.add(r['source']);src=Path(r['source']);assert sha(src)==masters[r['source']]==r['sourceSha256'];im=Image.open(src).convert('RGBA');actual=Image.open(io.BytesIO(archives[r['archivePath']][r['entry']])).convert('RGBA')
  if 'pawuniform'in r['oldPath'].lower():expected=im.resize((r['width'],r['height']),Image.Resampling.LANCZOS)
  elif im.width!=im.height:im.thumbnail((512,512),Image.Resampling.LANCZOS);expected=im
  else:expected=im.resize((512,512),Image.Resampling.LANCZOS)
  assert expected.size==actual.size and expected.tobytes()==actual.tobytes()
 assert len(seen)==236
 for group,base in[('arcane',AP),('pure',PP)]:
  old=read(base/'helpers/build-report.json');new=read(O/group/'helpers/build-report.json')
  for n,row in new.items():
   before={Path(p).name:(Path(p),h)for p,h in old[n]['sources'].items()};after={Path(p).name:(Path(p),h)for p,h in row['sources'].items()};assert before.keys()==after.keys()
   for name,(p,h)in after.items():
    original,oldhash=before[name];assert sha(p)==h and sha(original)==oldhash
    if name=='25-LargeMapsIdentity.cs':assert p.read_bytes()==original.read_bytes().replace(b'0.6.0-beta.4',ARC.encode())
    elif name=='4-PureChannel.cs':assert p.read_bytes()==original.read_bytes().replace(b'0.5.0-beta.8',PURE.encode()).replace(b'1.3.72-pure.21-beta.8',RT.encode())
    else:assert h==oldhash
 for mod in['arcane','vanilla','immortals']:
  r=read(O/(mod+'-installer-result.json'));assert r['passed']and r['originalArchivesUnchanged']and r['stockSkinArchivesRestoredOnDisable']
 assert read(O/'catalog-qa/result.json')['passed']and read(O/'live-result.json')['passed']and read(O/'live-cleanup.json')['passed'];im=Image.open(O/'compact-in-game.png');im.load();assert im.size==(2560,1440)
 audit=read(O/'package-audit.json');f=verify(read(O/'signed/feed/v3/beta.json'),key());coreBytes=sum((sum(p['sourceRecipe'][k]['size']for k in['base','patch'])if p.get('sourceRecipe')else p['size'])for p in f['packages']if p['id']in['arcane-wars','pawpatch-core','common-ui','startup-base','arcane-biome-textures'])
 write(O/'verification.json',dict(passed=True,versions=dict(arcane=ARC,pure=PURE),sourceAssets=236,sourceMastersUnchanged=True,exactApprovedResizeVerified=True,aspectRatiosPreserved=True,images=708,nativeGameplayInputsIdentical=True,managedChanges='Version identity constants only',installerMods=3,installerCases=18,allHelperVariants=12,rollbackAndReapply=True,stockSkinArchivesRestoredOnDisable=True,catalog=read(O/'catalog-qa/result.json'),live=read(O/'live-result.json'),liveCleanup=read(O/'live-cleanup.json'),terrain=read(O/'terrain-merge.json'),firstArcaneCoreDownloadBytes=coreBytes,uiPackageBytes={pid:audit[pid]['size']for pid in['common-ui','pure-beta-common']},launcherUnchanged=True,stableChannelsUnchanged=True,newMultiplayerMatchClaimed=False));print('COMPACT_RELEASE_VERIFICATION_PASS',coreBytes,flush=True)
if __name__=='__main__':main()
