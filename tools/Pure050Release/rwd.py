"""Read-only archive entries; no game installation or archive mutation."""
import struct
from pathlib import Path
def entries(path,suffix='.tgi'):
 result={}
 with Path(path).open('rb') as f:
  header=f.read(16);assert header[:4]==b'TGCK';count=struct.unpack_from('<I',header,8)[0];assert 0<count<64;f.seek(-96*count,2);table=f.read();sections={}
  for i in range(count):
   row=table[i*96:(i+1)*96];sections[row[:64].decode('utf-16le').split('\0')[0]]=struct.unpack_from('<QQ',row,64)
  f.seek(sections['Footer'][0]);n=struct.unpack('<I',f.read(4))[0];items=[]
  for i in range(n):
   size=struct.unpack('<H',f.read(2))[0];name=f.read(size*2).decode('utf-16le');offset,length,_,index=struct.unpack('<QQII',f.read(24))
   if name.lower().endswith(suffix):items.append((name.lstrip('/').replace('\\','/').lower(),offset,length))
  for name,offset,length in items:f.seek(sections['Files'][0]+offset);result['data/'+name]=f.read(length)
 return result
def decode(raw):
 if raw.startswith((b'\xff\xfe',b'\xfe\xff')):return raw.decode('utf-16').replace('\r','')
 try:return raw.decode('utf-8-sig').replace('\r','')
 except UnicodeDecodeError:return raw.decode('cp1252').replace('\r','')
