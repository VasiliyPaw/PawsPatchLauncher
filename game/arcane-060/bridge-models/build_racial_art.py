from pathlib import Path
import sys,io,time,math,json,hashlib,importlib.util,shutil
P=Path(__file__).resolve().parent;repo=P.parents[1];R=Path((P/'target.txt').read_text())
sys.path[:0]=[str(repo/'outputs/bridge-model-ee2-20261109/deps'),str(repo/'work/r24-construction-span-20261113')];time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N
from PrepareSplitLanguages import rwd_files
files=rwd_files((R/'sandbox/Data.rwd').read_bytes());keys={k.lower():k for k in files}
stock=repo/'work/racial-construction-audit-20261113/stock/Effects/Construction'
out=P/'sandbox/rivers-data';folder=out/'Paws/Bridges/RacialBuild';folder.mkdir(parents=True,exist_ok=True);manifest={};textures={}
def load(raw):
 d=N.Data();d.read(io.BytesIO(raw));return d
def container(axis):
 root=N.NiNode();root.name=b'BridgeRacialBuildRoot';root.flags=16
 if axis=='x':root.rotation.m_11=0;root.rotation.m_12=1;root.rotation.m_21=-1;root.rotation.m_22=0
 return root
def texture_copy(data,race):
 for b in data.blocks:
  if not isinstance(b,N.NiSourceTexture):continue
  name=bytes(b.file_name).decode('ascii');filename=Path(name.replace('\\','/')).name
  candidates=[f'Effects/Construction/{race.title()}/{filename}',f'Shared/SharedTextures/{filename}']
  key=next((keys[c.lower()] for c in candidates if c.lower() in keys),None)
  if key is None:
   found=[k for k in files if k.lower().endswith('/'+filename.lower())];assert len(found)==1,(race,filename,found);key=found[0]
  dst=folder/race/filename;dst.parent.mkdir(exist_ok=True);dst.write_bytes(files[key]);b.file_name=filename.encode('ascii')
  textures[str(dst.relative_to(out))]={'source':key,'sha256':hashlib.sha256(files[key]).hexdigest()}
def write(root,path,info):
 model=N.Data(version=0x0A010000,user_version=0);model.roots=[root];path.parent.mkdir(exist_ok=True,parents=True)
 with path.open('wb') as f:model.write(f)
 checked=load(path.read_bytes());assert checked.roots
 info.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),nodes=sum(isinstance(b,N.NiNode) for b in checked.blocks),particles=sum(isinstance(b,N.NiParticleSystem) for b in checked.blocks))
 manifest[str(path.relative_to(out))]=info
for race,base_span,module_span in [('human',5.,5.),('gauri',7.5,7.3),('drauga',6.3,6.3)]:
 scale=7.4/base_span
 for kind,stem in [('scaffold','Construction'),('finish','Deconstruction')]:
  source=stock/race.title()/(race.title()+stem+'Structure.nif');raw=source.read_bytes()
  for count in range(5,33):
   length=(count-1)*2;span=module_span*scale;pieces=max(1,math.ceil(length/span));positions=[0] if pieces==1 else [-(length-span)/2+i*(length-span)/(pieces-1) for i in range(pieces)]
   for axis in ['x','y']:
    root=container(axis);shared=[]
    for i,position in enumerate(positions):
     data=load(raw);texture_copy(data,race);meshes=[b for b in data.blocks if isinstance(b,N.NiTriBasedGeom)]
     if i==0:shared=[b.data for b in meshes]
     else:
      assert len(meshes)==len(shared)
      for mesh,geometry in zip(meshes,shared):mesh.data=geometry
     offset=N.NiNode();offset.name=f'ScaffoldModule{i:02}'.encode();offset.flags=16;offset.scale=scale;offset.translation.y=position
     for child in data.roots:offset.add_child(child)
     root.add_child(offset)
    write(root,folder/race/f'{kind}_{axis}_{count:02}.nif',{'race':race,'kind':kind,'axis':axis,'length':length,'width':7.4,'modules':pieces,'modulePositions':positions,'uniformScale':scale,'source':str(source),'sourceSha256':hashlib.sha256(raw).hexdigest(),'originalControllers':True,'sharedImmutableMeshData':True})
  print('RACIAL_SCAFFOLDS_READY',race,kind,flush=True)
for race,kinds in [('undead',['growth','work','finish']),('shadow',['work'])]:
 for kind in kinds:
  source=stock/race.title()/(('UndeadConstructionSmokeEffect.nif' if kind=='work' else 'UndeadConstruction.nif') if race=='undead' else 'ShadowConstructionStructure.nif');raw=source.read_bytes()
  for count in range(5,33):
   length=(count-1)*2;copies=max(1,math.ceil(length/20)) if race=='undead' else 1
   for axis in ['x','y']:
    root=container('y');emitter_count=0
    for copy in range(copies):
     data=load(raw);texture_copy(data,race)
     # Preserve native particle layers, without a round central mesh/card.
     for node in [b for b in data.blocks if isinstance(b,N.NiNode)]:
      for child in list(node.children):
       if child and isinstance(child,N.NiTriBasedGeom):node.remove_child(child)
     for block in data.blocks:
      if not isinstance(block,N.NiParticleSystem):continue
      block.world_space=False;rate=1.
      for j,old in enumerate(block.modifiers):
       if not isinstance(old,(N.NiPSysCylinderEmitter,N.NiPSysBoxEmitter,N.NiPSysSphereEmitter)):continue
       box=N.NiPSysBoxEmitter()
       for attr in ['name','order','target','active','speed','speed_variation','declination','declination_variation','planar_angle','planar_angle_variation','initial_radius','radius_variation','life_span','life_span_variation','emitter_object']:setattr(box,attr,getattr(old,attr))
       for c in ['r','g','b','a']:setattr(box.initial_color,c,getattr(old.initial_color,c))
       box.width=length if axis=='x' else 6;box.height=6 if axis=='x' else length;box.depth=.2;box.initial_radius=min(box.initial_radius,2.4)
       rate=max(.5,min(block.data.num_vertices*.75/max(.5,box.life_span),length*.8));block.modifiers[j]=box;emitter_count+=1
      c=block.controller
      while c:
       if isinstance(c,N.NiPSysEmitterCtlr) and c.data:
        if race=='undead' and kind=='finish':c.flags=(int(c.flags)&~6)|4
        for key in c.data.float_keys.keys:key.value=rate
        if kind!='finish':
         for key in c.data.visibility_keys:key.value=True
       c=c.next_controller
     for child in data.roots:root.add_child(child)
    path=folder/race/f'{kind}_{axis}_{count:02}.nif';write(root,path,{'race':race,'kind':kind,'axis':axis,'length':length,'width':6,'particleSpace':'local','layerCopies':copies,'emitters':emitter_count,'source':str(source),'sourceSha256':hashlib.sha256(raw).hexdigest()})
    checked=load(path.read_bytes());emitters=[b for b in checked.blocks if isinstance(b,N.NiPSysBoxEmitter)];assert len(emitters)==emitter_count and all((e.width,e.height)==((length,6) if axis=='x' else (6,length)) for e in emitters)
  print('RACIAL_PARTICLES_READY',race,kind,flush=True)
sys.path.insert(0,str(P/'source/game/engineer-bridges'))
from models import definitions,construction_effect
spec=importlib.util.spec_from_file_location('previous_models',repo/'work/r24-construction-span-20261113/source/game/engineer-bridges/models.py');previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
styles=json.loads((P/'bridge-art.json').read_text())['styles']
for rel,old,new in [('Special/Things/thing_visibilityactors.tgi',previous.definitions('ru',styles),definitions('ru',styles)),('Effects/construction.tgi',previous.construction_effect(),construction_effect())]:
 src=P/'before/sandbox/rivers-data'/rel;s=src.read_text(encoding='utf-16');assert s.endswith(old),rel
 dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(s[:-len(old)]+new,encoding='utf-16')
assert len(manifest)==560
(P/'racial-art.json').write_text(json.dumps({'models':manifest,'textures':textures,'totalModels':len(manifest),'nativeStockArt':True,'newRasterGeneration':False},indent=2))
print('RACIAL_BRIDGE_ART_READY',len(manifest),'models;',len(textures),'textures',flush=True)
