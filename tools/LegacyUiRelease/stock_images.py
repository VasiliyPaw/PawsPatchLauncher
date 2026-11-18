from context import *
import struct,zipfile,io
from PIL import Image
def entries(path,wanted):
 result={}
 with Path(path).open('rb')as f:
  assert f.read(12)==b'TGCK'+struct.pack('<II',2,3);f.seek(-288,2);sections={}
  for i in range(3):
   row=f.read(96);sections[row[:64].decode('utf-16le').split('\0')[0]]=struct.unpack_from('<QQ',row,64)
  f.seek(sections['Footer'][0]);count=struct.unpack('<I',f.read(4))[0];rows=[]
  for i in range(count):
   n=struct.unpack('<H',f.read(2))[0];name=f.read(n*2).decode('utf-16le').lstrip('/').replace('\\','/').lower();off,size,flags,index=struct.unpack('<QQII',f.read(24))
   if name in wanted:rows.append((name,off,size))
  for name,off,size in rows:f.seek(sections['Files'][0]+off);result[name]=f.read(size)
 return result
def crop(source,x,columns):
 w,h=struct.unpack_from('<HH',source,12);assert source[1:3]==b'\0\x02'and source[16]==32 and not(source[17]&0xC0);result=bytearray(source[:18]);result[0]=0;struct.pack_into('<H',result,12,columns)
 for row in range(h):start=18+source[0]+(row*w+x)*4;result.extend(source[start:start+columns*4])
 return bytes(result)
def originals():
 pins=read(S/'game/widescreen-ui/source-assets.json');frames={};proof={}
 for race in ['spectator','human','gauri','drauga','haroun','undead','shadow']:
  archive='Data.rwd'if race=='spectator'else'skins/'+race+'.rwd';source=Path('G:/PawsWork/BaseGame/1.3.72/Data.rwd')if race=='spectator'else O/'stock-skins'/(race+'.rwd');wanted={'ui/'+v+'game/controlpanel/background.tga'for v in['','800/','1280/']};values=entries(source,wanted);assert len(values)==3
  for logical,raw in values.items():
   pin=next(h for n,h in pins.items()if n.lower()==(archive+':'+logical).lower());assert hashlib.sha256(raw).hexdigest().upper()==pin
   prefix=('data/'if race=='spectator'else'skins/'+race+'/')+logical;frames[prefix]=raw;w,h=struct.unpack_from('<HH',raw,12)
   for part,x,width in [('left',0,w//2),('right',w//2,w//2),('center',w//2,w//8)]:
    n=prefix.replace('background.tga','pawuniform'+part+'.tga');b=crop(raw,x,width);frames[n]=b
    original=Image.open(io.BytesIO(raw)).convert('RGBA');actual=Image.open(io.BytesIO(b)).convert('RGBA');assert actual.tobytes()==original.crop((x,0,x+width,h)).tobytes();proof[n]=dict(source=archive+':'+logical,sourceSha256=pin,sha256=hashlib.sha256(b).hexdigest().upper(),size=len(b),pixelsMatchOriginalCrop=True)
 write(O/'stock-frames-proof.json',dict(passed=True,frames=proof));return frames
def icon_overrides():
 targets={r['path'][len('paws-hd-ui/'):].lower()for r in read(HD/'fullres-manifest.json')['files']if r['path'].startswith('paws-hd-ui/')and'pawuniform'not in r['path'].lower()}
 with zipfile.ZipFile(AP/'assets/pawpatch-core-0.6.0-beta.5.zip')as z:
  m=json.loads(z.read('module.json'));found=[r['path']for r in m['files']if r['path'].lower().startswith('rivers-data/')and r['path'][12:].lower()in targets]
 retail=entries('G:/PawsWork/BaseGame/1.3.72/Data.rwd',{n[12:].lower()for n in found});assert len(retail)==len(found)==477
 write(O/'stock-icons-proof.json',dict(passed=True,retiredOverrides=found,retailFallback={n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in retail.items()},bridgeFeatureIconsPreserved=True));return found
