"""Read public CI for exactly the source or catalog commit; no remote writes."""
import argparse
from context import *
p=argparse.ArgumentParser();p.add_argument('phase',choices=['source','catalog']);a=p.parse_args()
commit=read(OUT/('source-publication.json'if a.phase=='source'else'publication.json'))['commit'if a.phase=='source'else'catalogCommit']
rows=json.loads(fetch(API+'/actions/runs?head_sha='+commit+'&per_page=20'))['workflow_runs']
runs=[r for r in rows if r['name']=='Build and test'and r['event']=='push'and r['head_sha']==commit]
if not runs:print('CI_PENDING',a.phase,commit);exit()
r=max(runs,key=lambda r:r['run_number']);result={k:r[k]for k in ['id','head_sha','status','conclusion','html_url']}
write(OUT/(a.phase+'-ci.json'),result)
print('CI_STATUS',a.phase,json.dumps(result),flush=True)
if r['status']=='completed'and r['conclusion']!='success':raise RuntimeError('Required CI failed; inspect '+r['html_url'])
