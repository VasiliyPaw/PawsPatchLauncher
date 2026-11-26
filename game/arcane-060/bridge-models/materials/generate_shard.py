"""Optional scheduling only: disjoint models, exact same pinned core.process().

Never run without a separately agreed two-worker window and a frozen dispatch
checkpoint containing all24 approved reference checks. No shared state writes.
"""
from pathlib import Path
import argparse,json,os,time,threading,_thread,uuid,traceback,shutil
import generate as core
HERE=core.HERE
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--index',type=int,choices=[0,1],required=True);parser.add_argument('--seconds',type=int,default=180);parser.add_argument('--max-models',type=int,default=672);args=parser.parse_args()
 assert 20<=args.seconds<=180
 inputs=json.loads((HERE/'inputs-manifest.json').read_text(encoding='utf-8'))
 baseline=json.loads((HERE/'dispatch-checkpoint.json').read_text(encoding='utf-8'))
 assert set(inputs['approvedReferences'])<=set(baseline['models'])
 pins={'dispatch':core.sha(HERE/'dispatch-checkpoint.json'),'inputs':core.sha(HERE/'inputs-manifest.json'),
       'core':core.sha(HERE/'generate.py'),'helper':core.sha(core.HELPER),'script':core.sha(Path(__file__)),
       'acceleratorSource':core.sha(HERE/'ao_trace.c'),'originalScript':core.sha(core.OLD/'build_candidate.py')}
 assert baseline['pins']['script']==pins['core']and baseline['pins']['inputs']==pins['inputs']and baseline['pins']['helper']==pins['helper']
 assigned=sorted(set(inputs['models'])-set(baseline['models']))[args.index::2]
 state_path=HERE/f'shard-{args.index}.json'
 state=json.loads(state_path.read_text())if state_path.exists()else{'models':{},'pins':pins,'assigned':assigned}
 assert state['pins']==pins and state['assigned']==assigned
 for rel,row in state['models'].items():assert rel in assigned and core.sha(core.OUTPUT/rel)==row['sha256']
 core.TEMP=HERE/f'temp-shard-{args.index}';core.TEMP.mkdir(exist_ok=True)
 started=time.monotonic();processed=0;status='complete';error=None;batch_id=uuid.uuid4().hex
 timer=threading.Timer(args.seconds,_thread.interrupt_main);timer.daemon=True;timer.start()
 try:
  for relative in assigned:
   if relative in state['models']:continue
   if processed>=args.max_models or time.monotonic()-started>args.seconds-15:status='checkpoint';break
   row=core.process(relative,inputs,min(20,max(1,args.seconds-(time.monotonic()-started)-2)))
   state['models'][relative]=row;processed+=1;core.atomic(state_path,state)
   print(json.dumps({'shard':args.index,'done':len(state['models']),'assigned':len(assigned),'model':relative,'seconds':row['seconds']}),flush=True)
 except KeyboardInterrupt:status='checkpoint'
 except BaseException as exc:status='failed';error=repr(exc);traceback.print_exc()
 finally:
  timer.cancel()
  if core.active_child is not None:
   if core.active_child.poll()is None:core.active_child.kill()
   core.active_child.wait();core.active_child=None
  receipt={'status':status,'error':error,'shard':args.index,'done':len(state['models']),'assigned':len(assigned),
           'processed':processed,'elapsedSeconds':round(time.monotonic()-started,3),'pid':os.getpid(),
           'parentPeakBytes':core.parent_peak_bytes(),'allTraceChildrenClosed':True,'pins':pins}
  if status=='failed':
   dest=HERE/'failures'/batch_id;dest.mkdir(parents=True)
   for p in [core.TEMP/'trace-input.bin',core.TEMP/'trace-output.bin',Path(__file__),HERE/'generate.py',HERE/'ao_trace.c',core.HELPER]:
    if p.is_file():shutil.copy2(p,dest/p.name)
  core.atomic(HERE/'batches'/(batch_id+'.json'),receipt);core.atomic(HERE/f'last-shard-{args.index}.json',receipt);print(json.dumps(receipt),flush=True)
 if status=='failed':raise SystemExit(1)
if __name__=='__main__':main()
