from context import *
from PIL import Image
import struct,zlib,io,re

def read_rwd(path):
 rows={}
 with Path(path).open('rb')as f:
  assert f.read(12)==b'TGCK'+struct.pack('<II',2,3);f.seek(-288,2);table=f.read();sections={}
  for i in range(3):
   r=table[i*96:(i+1)*96];name=r[:64].decode('utf-16le').split('\0')[0];offset,size,_,__,repeat=struct.unpack_from('<QQIIQ',r,64);assert size==repeat;sections[name]=(offset,size)
  f.seek(sections['Footer'][0]);count=struct.unpack('<I',f.read(4))[0];entries=[]
  for i in range(count):
   n=struct.unpack('<H',f.read(2))[0];name=f.read(n*2).decode('utf-16le');offset,size,flags,index=struct.unpack('<QQII',f.read(24));assert flags==0 and offset+size<=sections['Files'][1];entries.append((name,offset,size))
  assert f.tell()==sections['Footer'][0]+sections['Footer'][1]
  for name,offset,size in entries:
   key=name.lstrip('/').replace('\\','/').lower();assert key not in rows and '..'not in key.split('/');f.seek(sections['Files'][0]+offset);rows[key]=f.read(size)
 return rows

def pack_rwd(path,files):
 rows=sorted(files.items());blobs={};offsets={};stamp=hashlib.sha256(b'PAW-RWD-STAMP-2\0'+struct.pack('<i',len(rows)))
 with path.open('w+b')as out:
  out.write(b'TGCK'+struct.pack('<II',2,3));out.write(struct.pack('<IH',2,2)+'K2'.encode('utf-16le')+struct.pack('<II',0,0));assert out.tell()==30
  for name,data in rows:
   digest=hashlib.sha256(data).hexdigest()
   if digest not in blobs:offsets[digest]=out.tell()-30;out.write(data);blobs[digest]=len(data)
  file_size=out.tell()-30;footer_offset=out.tell();out.write(struct.pack('<I',len(rows)))
  for i,(name,data)in enumerate(rows):
   digest=hashlib.sha256(data).hexdigest();nb=name.encode('utf-16le');out.write(struct.pack('<H',len(nb)//2)+nb+struct.pack('<QQII',offsets[digest],len(data),0,i));key=name.encode('utf-8');stamp.update(struct.pack('<i',len(key))+key+struct.pack('<q',len(data))+data)
  footer_size=out.tell()-footer_offset
  for name,offset,size in [('Header',12,18),('Files',30,file_size),('Footer',footer_offset,footer_size)]:out.write(name.encode('utf-16le').ljust(64,b'\0')+struct.pack('<QQIIQ',offset,size,0,0,size))
  value=zlib.crc32(stamp.digest());out.seek(26);out.write(struct.pack('<I',value))
 assert read_rwd(path)==files
 return dict(path=str(path),sha256=sha(path),size=path.stat().st_size,entries=len(files),uniqueBlobs=len(blobs),stamp=f'{value:08X}',files={n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in rows})

def main():
 old=read(WS/'outputs/ui-hd-20261116/overlay-manifest.json')['files'];previous={r['path'].lower():r for r in old};export=read(PR/'image-export.json')['files'];packs={'paws-hd-ui.rwd':{}};manifest=[];saved={};base_report={}
 out=O/'resources';out.mkdir(exist_ok=True)
 source_baselines=dict(re.findall(r'NormalizeRelativePath\("(skins/[^\"]+)"\)\] = "([A-F0-9]+)"',(S/'src/PawsPatchLauncher/SteamVanillaBaseline.cs').read_text()))
 for name,h in source_baselines.items():
  paths=[Path('G:/PawsWork/QA/Arcane060-20261115/game')/name,Path('G:/PawsWork/QA/Pure050Beta7-20261116/vanilla/game')/name,Path('G:/PawsWork/QA/Pure050Beta7-20261116/immortals/game')/name]
  assert all(sha(p)==h for p in paths),name
  data=read_rwd(paths[0]);packs[name.lower()]=data; base_report[name.lower()]=dict(source=str(paths[0]),sha256=h,originalEntries={n:hashlib.sha256(b).hexdigest().upper()for n,b in data.items()})
 assert len(base_report)==6
 for row in export:
  key=row['path'].lower();prev=previous[key];src=Path(prev['source']);cache=str(src)
  if cache not in saved:
   p=WS/'outputs/ui-hd-20261116/overlay'/prev['path'];data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==prev['sha256'];im=Image.open(src)
   if 'pawuniform'not in key and im.width!=im.height:
    im=im.convert('RGBA');im.thumbnail((512,512),Image.Resampling.LANCZOS);b=io.BytesIO();im.save(b,format='TGA'if p.suffix.lower()=='.tga'else'PNG');data=b.getvalue()
   candidate=Image.open(io.BytesIO(data));assert max(candidate.size)<=512 if 'pawuniform'not in key else candidate.size in[(2048,1024),(512,1024)]
   digest=hashlib.sha256(data).hexdigest().upper();(out/(digest+'.bin')).write_bytes(data);saved[cache]=(data,digest,candidate.size,sha(src))
  data,digest,dims,source_hash=saved[cache]
  parts=key.split('/')
  if parts[0]=='skins':archive='skins/'+parts[1]+'.rwd';entry='/'.join(parts[2:])
  else:archive='paws-hd-ui.rwd';entry='/'.join(parts[1:])
  assert entry not in packs[archive],(archive,entry);packs[archive][entry]=data
  manifest.append(dict(oldPath=row['path'],archivePath=archive,entry=entry,size=len(data),sha256=digest,width=dims[0],height=dims[1],source=str(src),sourceSha256=source_hash))
 assert len(manifest)==708 and len(saved)==236
 destination=O/'packed';destination.mkdir(exist_ok=True);reports={}
 for name,files in packs.items():
  target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);reports[name]=pack_rwd(target,files)
  if name in base_report:
   original=base_report[name]['originalEntries'];assert all(reports[name]['files'][n]['sha256']==h for n,h in original.items());reports[name]['preservedBaseEntries']=len(original)
  print('UI_RWD_PASS',name,reports[name]['entries'],reports[name]['uniqueBlobs'],flush=True)
 write(O/'resource-archives.json',reports);write(O/'base-skin-preservation.json',dict(passed=True,baselines=base_report));write(O/'image-export.json',dict(passed=True,images=708,uniqueSources=len(saved),iconMaximumDimension=512,frameHalf=[2048,1024],frameCenter=[512,1024],aspectRatiosPreserved=True,sourceMastersUnchanged=True,files=manifest));print('COMPACT_RESOURCES_READY',flush=True)
if __name__=='__main__':main()
