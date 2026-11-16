from pathlib import Path
import argparse,subprocess,hashlib,json,os
p=argparse.ArgumentParser();p.add_argument('--cc',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--tests',action='store_true');a=p.parse_args()
assert a.out.resolve().drive.upper()=='G:', 'Project builds must remain on G:'
a.out.mkdir(parents=True,exist_ok=True);temp=a.out/'Temp';temp.mkdir(exist_ok=True);env=os.environ.copy();env.update(TEMP=str(temp),TMP=str(temp));src=Path(__file__).with_name('capture_knowledge.c');report={}
for name,defines in [('PawsCaptureKnowledge.dll',[])]+([('PawsCaptureKnowledgeTest.dll',['-DCAPTURE_KNOWLEDGE_TEST'])]if a.tests else []):
 target=a.out/name;cmd=[str(a.cc),'-shared','-Wall','-Werror',*defines,str(src),'-o',str(target),'-lkernel32'];subprocess.run(cmd,check=True,env=env);report[name]={'sha256':hashlib.sha256(target.read_bytes()).hexdigest().upper(),'sourceSha256':hashlib.sha256(src.read_bytes()).hexdigest().upper(),'command':cmd}
(a.out/'build-report.json').write_text(json.dumps(report,indent=2));print('BUILD_PASS')
