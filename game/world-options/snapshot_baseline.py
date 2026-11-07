"""Preserve pinned accepted helper inputs before updating generated payloads."""
import argparse,hashlib,json,shutil
from pathlib import Path
def main():
 ap=argparse.ArgumentParser();ap.add_argument('report',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);source=out/'inputs';source.mkdir();report=json.loads(a.report.read_text());mapping={}
 for row in report.values():
  for name,digest in row['sources'].items():
   p=Path(name);assert hashlib.sha256(p.read_bytes()).hexdigest().upper()==digest.upper(),name
   target=source/digest[:16]/p.name;target.parent.mkdir(exist_ok=True)
   if not target.exists():shutil.copy2(p,target)
   mapping[name]=str(target)
 for row in report.values():
  row['sources']={mapping[p]:h for p,h in row['sources'].items()}
  args=[]
  for arg in row['args']:
   if arg in mapping:arg=mapping[arg]
   elif arg.startswith('/resource:'):
    p,label=arg[10:].rsplit(',',1);arg='/resource:'+mapping[p]+','+label
   args.append(arg)
  row['args']=args
 for name in ('paws_patch_versions.ini','paws_player_colors.ini'):shutil.copy2(a.report.parent/name,out/name)
 (out/'build-report.json').write_text(json.dumps(report,indent=2));print('ACCEPTED_BASELINE_PRESERVED',len(mapping),'inputs')
if __name__=='__main__':main()
