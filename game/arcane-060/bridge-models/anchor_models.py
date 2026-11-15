"""Give rigid-scaffold bridges the native Scene Root attachment name.

The two names have the same byte length. Nothing else in the NIF changes:
geometry, collision boxes, materials, controllers and transforms are exact.
"""
from pathlib import Path
import sys,json,hashlib,shutil,os
P=Path(__file__).resolve().parent;R=Path((P/'target.txt').read_text())
sys.path.insert(0,str(R/'source'));from control import own
assert not own()
def sha(b):return hashlib.sha256(b).hexdigest()
changes=[]; hashes={}
for style in ['', 'Human','Gauri','Drauga']:
 folder=R/'sandbox/rivers-data/Paws/Bridges'/style
 files=sorted(folder.glob('*.nif'));assert len(files)==112
 for f in files:
  raw=f.read_bytes();assert raw.count(b'BridgeRoot')==1
  i=raw.index(b'BridgeRoot');assert raw[i-4:i]==b'\x0a\x00\x00\x00'
  new=raw[:i]+b'Scene Root'+raw[i+10:];assert len(new)==len(raw) and new[:i]==raw[:i] and new[i+10:]==raw[i+10:]
  rel=f.relative_to(R);before=P/'before'/rel;before.parent.mkdir(parents=True,exist_ok=True)
  assert not before.exists();shutil.copy2(f,before)
  for root in [P,R]:
   dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);tmp=dst.with_name(dst.name+'.anchor-next');tmp.write_bytes(new);os.replace(tmp,dst)
  changes.append({'path':str(rel),'before':sha(raw),'after':sha(new),'changedByteOffset':i,'oldName':'BridgeRoot','newName':'Scene Root','geometryByteExact':True});hashes[sha(raw)]=sha(new)
def update(obj):
 if isinstance(obj,dict):
  if obj.get('sha256') in hashes:obj['sha256']=hashes[obj['sha256']]
  for value in obj.values():update(value)
 elif isinstance(obj,list):
  for value in obj:update(value)
for root in [P,R]:
 f=root/'bridge-art.json';data=json.loads(f.read_text());update(data);tmp=f.with_suffix('.next');tmp.write_text(json.dumps(data,indent=2));os.replace(tmp,f)
f=P/'source/game/engineer-bridges/models.py';s=f.read_text();assert "root.name=b'BridgeRoot'"in s;f.write_text(s.replace("root.name=b'BridgeRoot'","root.name=b'Scene Root'"))
(P/'root-anchor-models.json').write_text(json.dumps({'passed':True,'modelCount':len(changes),'nativeAttachmentLocation':'position / Scene Root','geometryAndControllersByteExact':True,'changes':changes},indent=2))
print('NATIVE_SCENE_ROOT_ANCHORS',len(changes),'models; only the ten-byte root name changed')
