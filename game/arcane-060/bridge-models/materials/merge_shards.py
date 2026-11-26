"""Merge disjoint checked results after both shard workers have closed."""
from pathlib import Path
import json
from generate import HERE,OUTPUT,sha,atomic
def main():
 inputs=json.loads((HERE/'inputs-manifest.json').read_text(encoding='utf-8'))
 baseline=json.loads((HERE/'dispatch-checkpoint.json').read_text(encoding='utf-8'))
 current=json.loads((HERE/'checkpoint.json').read_text(encoding='utf-8'))
 assert current==baseline,'The frozen dispatch baseline must not be written by workers'
 combined=dict(baseline['models']);drivers=[]
 for index in [0,1]:
  state=json.loads((HERE/f'shard-{index}.json').read_text(encoding='utf-8'))
  assert state['pins']['dispatch']==sha(HERE/'dispatch-checkpoint.json')
  assert state['pins']['core']==sha(HERE/'generate.py')and state['pins']['script']==sha(HERE/'generate_shard.py')
  assert set(state['models'])==set(state['assigned'])
  assert not(set(combined)&set(state['models']))
  combined.update(state['models']);drivers.append({'file':f'shard-{index}.json','sha256':sha(HERE/f'shard-{index}.json')})
 assert set(combined)==set(inputs['models'])and len(combined)==672
 for rel,row in combined.items():assert row['invariantsExact']and sha(OUTPUT/rel)==row['sha256']
 current['models']=combined;current['parallelScheduling']={'driverSha256':sha(HERE/'generate_shard.py'),'mergeSha256':sha(Path(__file__)),'dispatchSha256':sha(HERE/'dispatch-checkpoint.json'),'states':drivers}
 atomic(HERE/'checkpoint.json',current);print('MERGED_VERIFIED_MODELS',len(combined),flush=True)
if __name__=='__main__':main()
