"""Export selected launcher sources over committed HEAD; preserve the checkout."""
import argparse,hashlib,io,json,subprocess,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
 raw=subprocess.check_output(['git','archive','--format=zip',head],cwd=REPO)
 with zipfile.ZipFile(io.BytesIO(raw)) as z:z.extractall(out)
 manifest=json.loads(a.manifest.read_text());proof=[]
 for row in manifest['intended']:
  name=row['path'];source=REPO/name;target=out/name
  assert target.resolve().is_relative_to(out)
  if row['action']=='delete':
   assert not source.exists();target.unlink(missing_ok=True);proof.append(dict(path=name,deleted=True));continue
  expected=row.get('candidateSha256',row['sha256']);assert sha(source)==expected,(name,sha(source),expected)
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());proof.append(dict(path=name,sha256=sha(target)))
 (out/'selected-source-proof.json').write_text(json.dumps(dict(base=head,selected=proof,excludedDirtyFiles=True),indent=2))
 print('CLEAN_SELECTED_LAUNCHER_EXPORTED',len(proof),head,out,flush=True)
if __name__=='__main__':main()
