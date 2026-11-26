"""Run from the extracted immutable build-inputs asset on physical G:."""
from pathlib import Path
import os,sys,json,subprocess,hashlib
root=Path(__file__).resolve().parent
assert root.drive.upper()=='G:','Restore the build inputs to physical G: before replay.'
mapping=json.loads((root/'origin-map.json').read_text());reports=json.loads((root/'helpers/build-report.json').read_text())
out=root/'rebuilt';out.mkdir(exist_ok=True);temp=root/'Temp';temp.mkdir(exist_ok=True)
environment=os.environ.copy();environment.update(DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false',TEMP=str(temp),TMP=str(temp))
compiler=Path(sys.argv[1])if len(sys.argv)>1 else Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
for name,row in reports.items():
 for original,digest in row['sources'].items():
  source=root/mapping[original];assert hashlib.sha256(source.read_bytes()).hexdigest().upper()==digest.upper()
 args=[str(compiler)]
 for a in row['args'][1:]:
  if a.startswith('/out:'):a='/out:'+str(out/name)
  elif a in mapping:a=str(root/mapping[a])
  elif a.startswith('/resource:'):
   source,label=a[10:].rsplit(',',1);a='/resource:'+str(root/mapping[source])+','+label
  args.append(a)
 subprocess.run(args,env=environment,check=True);print(name,hashlib.sha256((out/name).read_bytes()).hexdigest())
