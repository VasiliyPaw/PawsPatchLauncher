"""Give the private river fixture enough gold for long QA without desertion.

Changes only the first kingdom's named gold stockpile in a copied native save.
Original fixture and all other sections stay byte-identical.
"""
from pathlib import Path
import argparse,struct,zlib,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
root=a.out.resolve();source=root/'sandbox/Userdata/Save/Bridge-ready.RSG';data=source.read_bytes()
assert data[:8]==b'TGCK\x02\0\0\0';count=struct.unpack_from('<I',data,8)[0];assert count==21
directory=len(data)-96*count;rows=[];payload=bytearray(data[:12]);old=None
for i in range(count):
 row=bytearray(data[directory+i*96:directory+(i+1)*96]);name=bytes(row[:64]).decode('utf-16le').split('\0')[0]
 offset,length=struct.unpack_from('<QQ',row,64);part=data[offset:offset+length]
 if name=='KINGDOMS':
  raw=bytearray(zlib.decompress(part));key=b'\x04\0'+ 'gold'.encode('utf-16le');at=raw.index(key)+len(key)
  old=struct.unpack_from('<f',raw,at)[0];assert 400<old<500
  struct.pack_into('<f',raw,at,100000);part=zlib.compress(raw)
 struct.pack_into('<QQ',row,64,len(payload),len(part));payload.extend(part);rows.append(row)
assert old is not None;payload.extend(b''.join(rows));target=source.with_name('Bridge-ready-funded.RSG');target.write_bytes(payload)
report=dict(sourceSha256=hashlib.sha256(data).hexdigest(),targetSha256=hashlib.sha256(payload).hexdigest(),oldGold=old,newGold=100000,unchangedSections=20)
(root/'qa-evidence/funded-fixture.json').write_text(json.dumps(report,indent=2));print(report)
