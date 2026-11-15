"""Make a private native-save fixture with a Drauga-owned human engineer company.

Only the same-length nation IDs in lobby metadata and kingdom serialization
change. Terrain, all native actors, orders and the original fixture stay intact.
"""
from pathlib import Path
import argparse,hashlib,json,struct,zlib
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
root=a.out.resolve();source=root/'sandbox/Userdata/Save/Bridge-ready.RSG';data=source.read_bytes()
assert data[:8]==b'TGCK\x02\x00\x00\x00'
count=struct.unpack_from('<I',data,8)[0];assert count==21
directory=len(data)-96*count;rows=[];payload=bytearray(data[:12]);changes={}
for i in range(count):
 row=bytearray(data[directory+i*96:directory+(i+1)*96]);name=bytes(row[:64]).decode('utf-16le').split('\0')[0]
 offset,length=struct.unpack_from('<QQ',row,64);part=data[offset:offset+length]
 assert 12<=offset<directory and offset+length<=directory
 if name in ('MAP_HEADER','KINGDOMS'):
  raw=zlib.decompress(part);old='haroun'.encode('utf-16le');new='drauga'.encode('utf-16le')
  occurrences=raw.count(old);assert occurrences==(2 if name=='MAP_HEADER' else 1)
  changed=raw.replace(old,new);assert len(changed)==len(raw)
  part=zlib.compress(changed);assert zlib.decompress(part)==changed;changes[name]=occurrences
 struct.pack_into('<QQ',row,64,len(payload),len(part));payload.extend(part);rows.append(row)
payload.extend(b''.join(rows));target=source.with_name('Bridge-ready-stone.RSG');target.write_bytes(payload)
report={'source':str(source),'sourceSha256':hashlib.sha256(data).hexdigest(),'target':str(target),'targetSha256':hashlib.sha256(payload).hexdigest(),'changedNationIds':changes,'unchangedSections':count-len(changes)}
(root/'qa-evidence/stone-fixture.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
