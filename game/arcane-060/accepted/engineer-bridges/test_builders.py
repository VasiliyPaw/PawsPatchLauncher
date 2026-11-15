"""Verify native settler content and bridge work eligibility in emitted assets."""
import argparse,json,re,sys
from pathlib import Path
from builders import end_block
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.out
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from PrepareSplitLanguages import dec

def units(text):
 result={}
 for match in re.finditer(r'(?im)^\s*\[(?:Unit|Thing)\b[^\]]*\]\s*\{',text):
  block=text[match.start():end_block(text,match.start())];ident=re.search(r'(?im)^\s*IDS\s*=\s*(\w+)',block)
  if ident:result[ident[1]]=block
 return result
def flat(text):return text.replace('\r','').replace('\n','')

report=json.loads((root/'pioneer-builders.json').read_text());checks=0;seen=set()
styles=list(json.loads((root/'bridge-art.json').read_text())['styles']) if (root/'bridge-art.json').exists() else []
for file,ids in report.items():
 before=units(dec((root/'sandbox/data'/file).read_bytes()));after=units((root/'sandbox/rivers-data'/file).read_text(encoding='utf-16'))
 assert before.keys()==after.keys();checks+=1
 for ident,block in after.items():
  if ident not in ids:assert flat(block)==flat(before[ident]);checks+=1;continue
  style=next((race for race in styles if '/'+race.title()+'/' in file),'')
  prefix='paws_bridge_'+(style+'_' if style else '')
  seen.add(ident);assert block.count('actor_ids = '+prefix+'wood_site')==block.count('actor_ids = '+prefix+'stone_site')==1;checks+=1
  assert re.search(r'\[Ability\s+Template=K2ConstructLocal(?:Settlement)?\]',block);checks+=1
  assert '[Ability Template=K2RepairLocal]' in block;checks+=1
  if '[Ability Template=K2RepairLocal]' not in before[ident]:assert 'targets = +constructable -cannot_build -under_construction +own -enemy -upgrading -settlement_center' in block;checks+=1
  # Existing settlement construction remains byte-for-byte in the unit.
  original=before[ident]
  for match in re.finditer(r'\[Ability\s+Template=K2ConstructLocalSettlement\]',original):
   assert flat(original[match.start():end_block(original,match.start())]) in flat(block);checks+=1
  old_build=re.findall(r'actor_ids\s*=\s*(\w+)',original)
  assert all(re.search(r'actor_ids\s*=\s*'+re.escape(value)+r'\b',block) for value in old_build);checks+=1
assert {'nightbringer','boneweaver'}<=seen;checks+=1
assert not any(re.search(r'(?:^|_)(?:pioneer|pilgrim|founder|settler)$',ident,re.I) for ident in seen);checks+=1
for file,ids in report.items():
 before=units(dec((root/'sandbox/data'/file).read_bytes()))
 for ident in ids:
  assert re.search(r'actor_ids\s*=\s*\w+_outpost\b',before[ident],re.I),ident;checks+=1
print('PIONEER_BUILDERS_PASS',checks,'checks;',len(seen),'settler variants, both bridge menus, construction/repair, original company and settlement content preserved')
