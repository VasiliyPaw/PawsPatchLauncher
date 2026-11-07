"""Bounded sequential owned tests on an independent local port; retains failures."""
import argparse,json,subprocess,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,required=True)
    ap.add_argument('--cases',required=True);ap.add_argument('--revision',default='r1');a=ap.parse_args()
    here=Path(__file__).resolve().parent;summary=[]
    for case in a.cases.split(','):
        root=Path('G:/PawHotJoinLab-20261107-edge-'+case+'-'+a.revision)
        cmd=[sys.executable,str(here/'experiment.py'),'--out',str(root),'--mode','coordinated','--scenario','return','--leave-mode','menu','--automatic','--witness','--edge-case',case,'--port',str(a.port),'--observe','65']
        if case.startswith('timeout-'):cmd+=['--test-capture-timeout','12000']
        if case=='batch-loss':cmd+=['--simultaneous','observer']
        if case=='observer-host':
            cmd[cmd.index('--scenario')+1]='visitor';cmd.remove('--witness')
        code=subprocess.run(cmd,timeout=1200).returncode
        valid=subprocess.run([sys.executable,str(here/'validate_run.py'),str(root)],timeout=90).returncode if (root/'result.json').exists() else None
        summary.append(dict(case=case,root=str(root),driverExit=code,validatorExit=valid))
        Path('G:/PawHotJoinAnalysis-20261106/local-edge-suite-'+str(a.port)+'.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
