"""Read back every completed model and emit an exact, material-only handoff."""
from pathlib import Path
import json,hashlib,shutil
from generate import HERE,INPUT,OUTPUT,invariant,original,sha,atomic
def main():
 inputs=json.loads((HERE/'inputs-manifest.json').read_text(encoding='utf-8'))
 checkpoint=json.loads((HERE/'checkpoint.json').read_text(encoding='utf-8'))
 expected_pins={'inputs':sha(HERE/'inputs-manifest.json'),'helper':sha(HERE/'ao_trace.exe'),'script':sha(HERE/'generate.py'),'acceleratorSource':sha(HERE/'ao_trace.c'),'originalScript':sha(HERE.parent/'bridge-natural-look-20261125/build_candidate.py')}
 assert checkpoint['pins']==expected_pins,'Generation inputs/helper/source changed'
 assert set(checkpoint['models'])==set(inputs['models']) and len(inputs['models'])==672
 assert not (HERE/'final-manifest.json').exists(),'Do not rewrite a finished handoff'
 files={};references=0
 for relative,row in checkpoint['models'].items():
  source=INPUT/relative;out=OUTPUT/relative
  assert sha(source)==row['sourceSha256']==inputs['files'][relative]['sha256']
  assert sha(out)==row['sha256']
  # Generation already reopened both models and compared every invariant.
  # Exact byte hashes here prove those checked files have not changed.
  assert row['invariantsExact'],relative
  references+=int(row['approvedBytesReused'])
  files['Paws/Bridges/'+relative]={'sha256':row['sha256'],'bytes':row['bytes'],'sourceSha256':row['sourceSha256'],'kind':'approved-material-candidate','geometryHierarchyUvNormalsMaterialsTexturesSelectionControllersExact':True}
 for relative,row in inputs['files'].items():
  if not relative.endswith('.tga'):continue
  source=INPUT/relative;out=OUTPUT/relative;out.parent.mkdir(parents=True,exist_ok=True)
  assert sha(source)==row['sha256'];shutil.copy2(source,out);assert sha(out)==row['sha256']
  files['Paws/Bridges/'+relative]={'sha256':row['sha256'],'bytes':out.stat().st_size,'kind':'unchanged-texture','unchangedTexture':True}
 actual={p.relative_to(HERE/'overlay').as_posix() for p in (HERE/'overlay').rglob('*')if p.is_file()}
 assert actual==set(files)and references==24
 assert all('/Shadows/'not in p and '/RacialBuild/'not in p and p.endswith(('.nif','.tga'))for p in actual)
 script_paths=[HERE/'ao_trace.c',HERE/'ao_trace.exe',HERE/'generate.py',HERE/'prepare_inputs.py',HERE/'finalize.py',HERE/'inputs-manifest.json',HERE/'checkpoint.json']
 if 'parallelScheduling'in checkpoint:script_paths.extend(HERE/p for p in ['generate_shard.py','merge_shards.py','dispatch-checkpoint.json','shard-0.json','shard-1.json'])
 result={'complete':True,'scope':'672 racial bridge models, surface AO only','races':6,'materials':2,'counts':[5,32],'axes':['x','y'],
         'models':672,'approvedModelsByteExact':24,'newCastShadows':False,'newProjectedShadows':False,'gameplayDefinitionsIncluded':False,'vfxIncluded':False,
         'gameOrSdkRun':False,'installedOrSharedSourceModified':False,'files':files,
         'scriptAndEvidenceSha256':{p.name:sha(p)for p in script_paths},
         'algorithm':{'samples':24,'radius':2.4,'strength':.48,'originBias':.045,'nearClip':.035,'distanceFalloff':.65,'roundedCacheDecimals':4,'referenceColorTolerance':2e-6},
         'limits':['Structural verification for all672; prior native screenshot review covered count16 only.','Low-detail projected-shadow changes were rejected and are absent.','Parent release coordinator owns merge, any additional native validation and publication.']}
 atomic(HERE/'final-manifest.json',result)
 print(json.dumps({'complete':True,'models':672,'files':len(files),'approvedModelsByteExact':24,'manifestSha256':sha(HERE/'final-manifest.json')}),flush=True)
if __name__=='__main__':main()
