from audit import *
import zlib
VERSION='0.6.0-lossless.preview.1'
def file_sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pack_rwd(path,groups):
 rows=sorted([r for group in groups for r in group],key=lambda r:r['path'].lower());byhash={r['sha256']:group[0]for group in groups for r in group};offsets={};lengths={};h=hashlib.sha256(b'PAW-RWD-STAMP-2\0'+struct.pack('<i',len(rows)))
 with path.open('w+b')as out:
  out.write(b'TGCK'+struct.pack('<II',2,3));out.write(struct.pack('<IH',2,2)+'K2'.encode('utf-16le')+struct.pack('<II',0,0));assert out.tell()==30
  for group in groups:
   r=group[0];data=(Q/'candidate/payload'/r['path']).read_bytes();assert sha(data)==r['sha256'];offsets[r['sha256']]=out.tell()-30;lengths[r['sha256']]=len(data);out.write(data)
  file_size=out.tell()-30;footer_offset=out.tell();out.write(struct.pack('<I',len(rows)))
  for i,r in enumerate(rows):
   name=r['path'].removeprefix('rivers-data/').lower();nb=name.encode('utf-16le');out.write(struct.pack('<H',len(nb)//2)+nb+struct.pack('<QQII',offsets[r['sha256']],r['size'],0,i))
   data=(Q/'candidate/payload'/byhash[r['sha256']]['path']).read_bytes();key=name.encode('utf-8');h.update(struct.pack('<i',len(key))+key+struct.pack('<q',len(data))+data)
  footer_size=out.tell()-footer_offset
  for name,offset,size in [('Header',12,18),('Files',30,file_size),('Footer',footer_offset,footer_size)]:out.write(name.encode('utf-16le').ljust(64,b'\0')+struct.pack('<QQIIQ',offset,size,0,0,size))
  stamp=zlib.crc32(h.digest());out.seek(26);out.write(struct.pack('<I',stamp))
 return dict(path=str(path),sha256=file_sha(path),size=path.stat().st_size,entries=len(rows),uniqueBlobs=len(groups),stamp=f'{stamp:08X}',deduplicatedBytes=sum(r['size']for r in rows)-file_size)
def verify_rwd(path,expected):
 # Independent bounded table parser, checking each alias by its actual offset.
 with path.open('rb')as f:
  assert f.read(12)==b'TGCK'+struct.pack('<II',2,3);f.seek(-288,2);table=f.read();sections={}
  for i in range(3):
   row=table[i*96:(i+1)*96];name=row[:64].decode('utf-16le').split('\0')[0];offset,size,_,__,repeat=struct.unpack_from('<QQIIQ',row,64);assert repeat==size;sections[name]=(offset,size)
  f.seek(sections['Footer'][0]);count=struct.unpack('<I',f.read(4))[0];assert count==len(expected);entries=[]
  for i in range(count):
   n=struct.unpack('<H',f.read(2))[0];name=f.read(n*2).decode('utf-16le');offset,size,flags,index=struct.unpack('<QQII',f.read(24));assert flags==0 and index==i;entries.append((name,offset,size))
  assert f.tell()==sections['Footer'][0]+sections['Footer'][1]
  for name,offset,size in entries:
   r=expected[name];assert size==r['size']and offset+size<=sections['Files'][1];f.seek(sections['Files'][0]+offset);assert sha(f.read(size))==r['sha256']
 return count
def main():
 records=json.loads((O/'optimized-files.json').read_text());groups=collections.defaultdict(list)
 for r in records:groups[r['sha256']].append(r)
 parts=[];part=[];size=0
 for group in sorted(groups.values(),key=lambda v:v[0]['path']):
  n=group[0]['size']
  if part and size+n>220*1024*1024:parts.append(part);part=[];size=0
  part.append(group);size+=n
 if part:parts.append(part)
 out=Q/'packed';out.mkdir(exist_ok=True);assets=O/'candidate-packages';assets.mkdir(exist_ok=True);report=[]
 for i,part in enumerate(parts,1):
  filename=f'paws-biome-textures-{i:02}.rwd';path=out/filename;row=pack_rwd(path,part);expected={r['path'].removeprefix('rivers-data/').lower():r for group in part for r in group};assert verify_rwd(path,expected)==row['entries']
  module=dict(schemaVersion=1,id=f'arcane-biome-textures-{i:02}',version=VERSION,files=[dict(path=filename,size=row['size'],sha256=row['sha256'].upper())],remove=[])
  archive=assets/(module['id']+'-'+VERSION+'.zip')
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:z.writestr('module.json',json.dumps(module,indent=2));z.write(path,'payload/'+filename)
  row.update(archive=str(archive),archiveSize=archive.stat().st_size,archiveSha256=file_sha(archive),verifiedNames=len(expected));report.append(row);print('PACKED_AND_VERIFIED',filename,row['entries'],row['size'],row['archiveSize'],flush=True)
 write(O/'packed.json',report);before=json.loads((O/'audit.json').read_text());summary=dict(passed=True,allNamesPreserved=sum(r['entries']for r in report)==22464,allPixelComparisons=22464,parts=len(report),originalTextureDownload=before['archiveBytes'],candidateTextureDownload=sum(r['archiveSize']for r in report),originalOtherPackages=100414548,candidateWholeUpdate=sum(r['archiveSize']for r in report)+100414548,originalWholeUpdate=before['archiveBytes']+100414548,originalTexturePayload=before['rawBytes'],optimizedLoosePayload=sum(r['size']for r in records),deduplicatedArchivePayload=sum(r['size']for r in report),rwdAliases=True,published=False)
 write(O/'packing-result.json',summary);print('LOSSLESS_PACKING_COMPLETE',json.dumps(summary),flush=True)
if __name__=='__main__':main()
