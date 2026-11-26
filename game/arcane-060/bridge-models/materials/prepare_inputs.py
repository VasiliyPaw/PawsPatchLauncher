"""Freeze only current racial model/texture inputs on physical G:, read-only source."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
SOURCE=Path('G:/PawsWork/QA/ArcaneFix-20261125/game/rivers-data/Paws/Bridges')
OLD=HERE.parent/'bridge-natural-look-20261125'
RACES=['Human','Gauri','Drauga','Haroun','Shadow','Undead']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 assert str(HERE.resolve()).lower().startswith('g:\\'), 'Output must physically reside on G:'
 manifest=HERE/'inputs-manifest.json';assert not manifest.exists(),'Never replace a frozen input manifest'
 expected={f'{kind}_{axis}_{count:02}.nif'for kind in ['wood','stone']for axis in ['x','y']for count in range(5,33)}
 approved={}
 for name in ['candidate-manifest.json','candidate-manifest-16.json']:
  for row in json.loads((OLD/name).read_text(encoding='utf-8'))['models']:
   relative=row['race']+'/'+Path(row['before']).name
   approved[relative]=row
 rows={};models=[]
 for race in RACES:
  assert {p.name for p in (SOURCE/race).glob('*.nif')}==expected,(race,'Unexpected model universe')
  for p in sorted((SOURCE/race).glob('*')):
   if not p.is_file()or p.suffix.lower()not in ['.nif','.tga']:continue
   rel=(Path(race)/p.name).as_posix();before=sha(p)
   if rel in approved:assert before==approved[rel]['sourceSha256'],('Approved input drift',rel)
   out=HERE/'inputs'/rel;out.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(p,out)
   assert before==sha(out)==sha(p),('Snapshot drift',rel)
   rows[rel]={'sha256':before,'bytes':out.stat().st_size}
   if p.suffix.lower()=='.nif':models.append(rel)
 assert len(models)==672 and len(approved)==24
 value={'sourceRoot':str(SOURCE),'models':models,'files':rows,'sourceReadOnly':True,'approvedReferences':approved,'genericModelsExcluded':True}
 manifest.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'frozenModels':len(models),'frozenFiles':len(rows),'approvedReferences':len(approved),'inputManifestSha256':sha(manifest)}),flush=True)
if __name__=='__main__':main()
