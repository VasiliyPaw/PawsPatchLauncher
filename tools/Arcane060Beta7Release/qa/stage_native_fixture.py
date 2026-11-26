"""Assemble an owned native QA fixture from the real verified four-module install.

This is explicit test-fixture assembly, not a full upgrade of the retired
24-module fixture. Keep its original state/Originals and all unrelated records.
"""
from pathlib import Path
import json,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from context import WS,O,read,write,sha

GAME=Path('G:/PawsWork/QA/ArcaneFix-20261125/game')
CHANGED={'pawpatch-core','common-ui','player-colors','desync-continue'}

def safe(root,rel):
 p=root/rel
 assert p.resolve().is_relative_to(root.resolve()) and p.resolve().drive.upper()=='G:'
 for parent in (p,*p.parents):
  if parent.exists():assert not parent.lstat().st_file_attributes & 0x400,str(parent)
 return p

def main():
 sys.path.insert(0,str(WS/'work/arcane-bridge-terrain-fixes-20261125/qa-tools'));import control
 assert not control.own()
 qa=read(O/'qa/result.json');assert qa['passed']
 fixture=Path(qa['fixture']);safe(fixture,'.pawpatch/state.json')
 state=read(fixture/'.pawpatch/state.json');assert set(state['modules'])==CHANGED
 original_path=O/'native-save/state-original-beta6.json'
 assert not original_path.exists(),'Never replace the baseline snapshot'
 original=(GAME/'.pawpatch/state.json').read_bytes();old=json.loads(original)
 assert old['modules']['pawpatch-core']['version']=='0.6.0-beta.6'
 original_path.write_bytes(original)
 winners={}
 for key,module in sorted(state['modules'].items(),key=lambda p:(p[1]['priority'],p[0].lower())):
  assert module['version']=='0.6.0-beta.7' and module['enabled']
  for rel in module.get('remove',[]):winners[rel.replace('\\','/').lower()]=None
  for row in module['files']:winners[row['path'].replace('\\','/').lower()]=row
 copied=removed=0
 for rel,row in winners.items():
  target=safe(GAME,rel)
  if row is None:
   if target.exists():assert target.is_file();target.unlink();removed+=1
   continue
  source=safe(fixture,rel)
  assert source.stat().st_size==row['size'] and sha(source)==row['sha256'].upper(),rel
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  assert sha(target)==row['sha256'].upper(),rel
  copied+=1
 for key in CHANGED:
  replacement=state['modules'][key]
  replacement['enabled']=old['modules'][key]['enabled']
  old['modules'][key]=replacement
 assert {k:v for k,v in old['modules'].items()if k not in CHANGED}=={k:v for k,v in json.loads(original)['modules'].items()if k not in CHANGED}
 assert old['originals']==json.loads(original)['originals']
 write(O/'native-save/state-final-assembled.json',old)
 (GAME/'.pawpatch/state.json').write_bytes((O/'native-save/state-final-assembled.json').read_bytes())
 plugins=GAME/'Mods/plugins.txt';text=plugins.read_text('utf-8-sig')
 if 'PawsNetworkQA.dll' not in text:text=text.rstrip()+'\nPawsNetworkQA.dll\n'
 plugins.write_text(text,encoding='utf-8')
 write(O/'native-save/fixture-assembly.json',dict(passed=True,scope='Native-QA fixture assembled from verified four beta7 modules',realPrivateUpgrade=False,genericFixture=str(fixture),genericStateSHA256=sha(fixture/'.pawpatch/state.json'),originalStateSHA256=sha(original_path),finalStateSHA256=sha(O/'native-save/state-final-assembled.json'),copiedWinningFiles=copied,removedWinningPaths=removed,otherModuleRecordsPreserved=True,originalsPreserved=True,qaObserverNotPublished=True))
 print('NATIVE_FIXTURE_ASSEMBLED',copied,removed,flush=True)

if __name__=='__main__':main()
