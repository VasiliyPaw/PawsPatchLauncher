"""Freeze confirmed production inputs without changing another chat's sources."""
import shutil,subprocess
from context import *
def main():
 OUT.mkdir(exist_ok=False);frozen=OUT/'frozen';frozen.mkdir()
 arcane=Path('C:/PawsArcane051ReleaseQA-20261109');native=arcane/'native-r7';managed=arcane/'helpers-r3/source'
 meta=read(native/'runtime.json');graphics=read(native/'graphics/product.json')
 assert sha(native/'PawsPresentation1372.dll')==meta['sha256']=='7FAE61C67F0FE1D7118F042B22DB68C2BC591A394A994F3EBDC78F175BBF5302'
 assert sha(native/'graphics/d3d9.dll')==graphics['sha256']=='112920FF0CB9A38158A12E9F8875B6B4FBBCE9ADA5C364EF55936EBBE4A83179'
 assert graphics['warmAlwaysDisabled'] and graphics['fixtureNotShipped']
 for folder,rows in [(native,meta['sources']),(native/'graphics',graphics['sources'])]:
  for n,h in rows.items():assert sha(folder/n)==h,n
 for folder in ['cache','cache-build','graphics']:shutil.copytree(native/folder,frozen/'arcane-native'/folder)
 for n in ['runtime.c','runtime.json','find.c','local_find.h','native_contract.h']:shutil.copy2(native/n,frozen/'arcane-native'/n)
 target=frozen/'arcane-managed';target.mkdir()
 for n in ['ResourceCachePatch.cs','ResourceCachePayload.cs','PresentationRuntimePatch.cs','PresentationRuntimePayload.cs']:shutil.copy2(managed/n,target/n)
 assert sha(target/'ResourceCachePayload.cs')==sha(native/'cache-build/ResourceCachePayload.cs')
 pure=PREVIOUS/'ui-native-r3';shutil.copytree(pure,frozen/'pure-ui')
 report=read(PREVIOUS/'beta-helpers-r4/build-report.json')
 for name,row in report.items():
  assert sha(PREVIOUS/'beta-helpers-r4'/name)==row['sha256']
  for p,h in row['sources'].items():assert sha(p)==h,p
 write(frozen/'pure-build-report.json',report)
 manifest={str(p.relative_to(frozen)).replace('\\','/'):sha(p)for p in frozen.rglob('*')if p.is_file()}
 write(OUT/'baseline.json',dict(gitHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),frozen=manifest,patch=PATCH,previousPatch='0.5.0-beta.1',scope=['resource-cache weights and bounded preparation','memory-guarded animation retention','32 MiB VB/IB reuse','per-Find stack eligibility cache'],disabled=['GPU prewarm','prepared-view/view reuse','render registration cache','D3D state cache','old Find index/reject'],installedGameModified=False))
 print('PURE_OPTIMIZATION_INPUTS_FROZEN',len(manifest))
if __name__=='__main__':main()
