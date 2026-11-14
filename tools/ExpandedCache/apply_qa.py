"""Update only three explicitly owned existing QA games, preserving old bytes."""
import os,shutil,subprocess,json
from pathlib import Path
from build import OUT,REPO,WS,BASE,read,write,sha,run,once
TARGETS=[('arcane',Path('G:/PawGraphicsQA-20261113/game')),('arcane',Path('G:/PawBufferPublishQA-20261113/arcane-r6/game')),('pure',Path('G:/PawBufferPublishQA-20261113/pure-r6/game'))]
def main():
 assert read(OUT/'checks/result.json')['passed'] and read(OUT/'native-tests.json')['passed']
 inventory=[]
 for kind,game in TARGETS:
  assert game.resolve().drive=='G:' and (game/'.paw-live-matrix.json').is_file() and (game/'k2.exe').is_file()
  active=subprocess.check_output(['powershell.exe','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='k2.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"],text=True).strip()
  processes=json.loads(active)if active else []
  if isinstance(processes,dict):processes=[processes]
  assert not any(p.get('ExecutablePath')and Path(p['ExecutablePath']).resolve()==(game/'k2.exe').resolve()for p in processes),'Owned QA game must be closed'
  assert all(p.get('ExecutablePath')for p in processes),'Cannot identify an active game safely'
  source=OUT/(kind+'-helpers');files={name:source/name for name in read(source/'build-report.json')}
  files['data/UVars_k2.tgi']=OUT/'overlay/data/UVars_k2.tgi'
  files['d3d9.dll']=WS/'outputs/buffer-ownership-release-20261113/arcane-installer-fixture/game/d3d9.dll'
  if not files['d3d9.dll'].is_file():files['d3d9.dll']=Path('G:/PawGraphicsQA-20261113/product-graphics/d3d9.dll')
  assert sha(files['d3d9.dll'])=='3B596B4A9435A8BDCD183906CAABE9CB60706FCE56783D42E8C66C52DA43944E'
  records=[]
  for rel,src in files.items():
   target=game/rel;backup=OUT/'qa-before'/game.parent.name/rel
   if target.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
   before=sha(target)if target.exists()else None;target.parent.mkdir(exist_ok=True)
   temp=target.with_name(target.name+'.expanded-new');temp.write_bytes(src.read_bytes());os.replace(temp,target)
   assert sha(target)==sha(src);records.append(dict(path=rel,before=before,after=sha(target),backup=str(backup)))
  write(game/'expanded-cache-local.json',dict(candidateOnly=True,policy=read(OUT/'policy.json'),source=str(OUT),kind=kind))
  inventory.append(dict(game=str(game),kind=kind,files=records))
 write(OUT/'qa-deployment.json',inventory);print('EXISTING_QA_COPIES_UPDATED',len(inventory))

if __name__=='__main__':main()
