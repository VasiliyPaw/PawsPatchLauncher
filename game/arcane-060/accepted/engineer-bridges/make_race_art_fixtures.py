"""Private native art fixtures: nation ID and explicit no-fog viewing rules."""
from pathlib import Path
import argparse,hashlib,json,struct,zlib

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();root=a.out.resolve();assert (root/'installed-rivers.marker').exists()
data=source.read_bytes();assert data[:8]==b'TGCK\x02\0\0\0';count=struct.unpack_from('<I',data,8)[0];assert count==21
directory=len(data)-96*count;rows=[]
for i in range(count):
 row=bytearray(data[directory+i*96:directory+(i+1)*96]);name=bytes(row[:64]).decode('utf-16le').split('\0')[0];offset,length=struct.unpack_from('<QQ',row,64)
 assert 12<=offset and offset+length<=directory
 rows.append((row,name,data[offset:offset+length]))
reports={};key=struct.pack('<H',6)+'haroun'.encode('utf-16le')
for race in ['human','gauri','drauga','haroun','shadow','undead']:
 payload=bytearray(data[:12]);table=[];changed=0
 for original,name,part in rows:
  row=bytearray(original)
  if name=='KINGDOMS':
   raw=zlib.decompress(part);assert raw.count(key)==1
   value=struct.pack('<H',len(race))+race.encode('utf-16le');updated=raw.replace(key,value);part=zlib.compress(updated);assert zlib.decompress(part)==updated;changed+=1
  if name in ('MAP_HEADER','RULES'):
   raw=zlib.decompress(part);fog='FogOfWar'.encode('utf-16le')+b'\0'+struct.pack('<II',3,2)
   assert raw.count(fog)==(2 if name=='MAP_HEADER' else 1)
   updated=raw.replace(fog,fog[:-4]+struct.pack('<I',0));part=zlib.compress(updated);assert zlib.decompress(part)==updated;changed+=1
  struct.pack_into('<QQ',row,64,len(payload),len(part));payload.extend(part);table.append(row)
 assert changed==3;payload.extend(b''.join(table));target=root/'Documents/Kohan2/data/Save'/f'R6-art-{race}.RSG';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
 reports[race]={'file':str(target),'sha256':hashlib.sha256(payload).hexdigest(),'unchangedSections':18,'changed':'One nation IDS in KINGDOMS; FogOfWar enum 2 to 0 in MAP_HEADER/RULES for unobstructed art viewing. Same terrain/actors/orders. Not a normal racial campaign.'}
assert source.read_bytes()==data
report={'source':str(source),'sourceSha256':hashlib.sha256(data).hexdigest(),'fixtures':reports,'originalSourceUnchanged':True}
(root/'qa-evidence/r6-race-fixtures.json').write_text(json.dumps(report,indent=2));print('RACE_ART_FIXTURES_READY',len(reports),'original source unchanged')
