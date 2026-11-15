from pathlib import Path
import os,json,hashlib,zipfile,struct,io,collections,time,concurrent.futures as futures
from PIL import Image
P=Path(__file__).resolve().parent;WS=P.parents[1];O=WS/'outputs/arcane060-lossless-20261115';Q=Path('G:/PawsWork/QA/Arcane060Lossless-20261115');BASE=WS/'outputs/arcane-060-beta-release-20261115'
os.environ['TEMP']=os.environ['TMP']=str(P/'Temp')
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def chunks(raw):
 assert raw[:8]==b'\x89PNG\r\n\x1a\n';pos=8;rows=[]
 while pos<len(raw):
  n=struct.unpack_from('>I',raw,pos)[0];kind=raw[pos+4:pos+8];data=raw[pos+8:pos+8+n];rows.append((kind.decode('ascii'),data));pos+=n+12
 assert pos==len(raw)and rows[-1][0]=='IEND';return rows
def describe(raw):
 cs=chunks(raw)
 with Image.open(io.BytesIO(raw))as im:
  im.load();rgba=im.convert('RGBA');pixels=rgba.tobytes();size=im.size;mode=im.mode
 return dict(sha256=sha(raw),size=len(raw),width=size[0],height=size[1],mode=mode,rgbaSha256=sha(pixels),ihdr=cs[0][1].hex(),nonIdatSha256=sha(b''.join(k.encode()+struct.pack('>I',len(b))+b for k,b in cs if k!='IDAT')),chunks=[k for k,b in cs])
def item(row,raw):
 result=describe(raw);assert result['sha256'].upper()==row['sha256'].upper()and result['size']==row['size'];p=Q/'candidate/payload'/row['path'];p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert sha(p.read_bytes())==result['sha256'],'Candidate already altered; use verify instead'
 else:p.write_bytes(raw)
 result.update(path=row['path']);return result
def audit():
 records=[];pending=set();started=time.monotonic();ps=json.loads((BASE/'packages.json').read_text());texture=[p for p in ps if p['id'].startswith('arcane-biome-textures-')]
 with futures.ThreadPoolExecutor(max_workers=8)as pool:
  for q in texture:
   with zipfile.ZipFile(BASE/'assets'/(q['id']+'-'+q['version']+'.zip'))as z:
    manifest=json.loads(z.read('module.json'))
    for row in manifest['files']:
     pending.add(pool.submit(item,row,z.read('payload/'+row['path'])))
     if len(pending)>=64:
      done,pending=futures.wait(pending,return_when=futures.FIRST_COMPLETED)
      records.extend(f.result()for f in done)
   print('AUDIT_PACKAGE',q['id'],'processed',len(records),flush=True)
  records.extend(f.result()for f in futures.as_completed(pending))
 records.sort(key=lambda r:r['path']);write(O/'original-files.json',records);dups={}
 for field in ['sha256','rgbaSha256']:
  groups=collections.defaultdict(list)
  for r in records:groups[(r['width'],r['height'],r[field])].append(r)
  repeated=[v for v in groups.values()if len(v)>1];dups[field]=dict(groups=len(repeated),extraFiles=sum(len(v)-1 for v in repeated),extraBytes=sum(sum(r['size']for r in v[1:])for v in repeated),items=[[r['path']for r in v]for v in repeated])
 write(O/'duplicates.json',dups);summary=dict(files=len(records),rawBytes=sum(r['size']for r in records),archiveBytes=sum(p['size']for p in texture),seconds=round(time.monotonic()-started,2),modes=dict(collections.Counter(r['mode']for r in records)),dimensions=dict(collections.Counter(str((r['width'],r['height']))for r in records)),byteDuplicateExtras=dups['sha256']['extraFiles'],pixelDuplicateExtras=dups['rgbaSha256']['extraFiles'],duplicateBytes=dups['sha256']['extraBytes']);write(O/'audit.json',summary);print('AUDIT_COMPLETE',json.dumps(summary),flush=True)
if __name__=='__main__':audit()
