"""Shape stock Haroun particles into one rectangular bridge-length effect."""
from pathlib import Path
import argparse,hashlib,io,json,math,sys,time

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.out.resolve()
repo=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(repo/'tools'),str(repo.parents[1]/'outputs/bridge-model-ee2-20261109/deps')]
from PrepareSplitLanguages import rwd_files
time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N
files=rwd_files((r/'sandbox/Data.rwd').read_bytes())
folder=r/'sandbox/rivers-data/Paws/Bridges/HarounEffects';folder.mkdir(parents=True,exist_ok=True)
report={}
for kind,source in [('growth','Construction/Haroun/HarounConstructionStructure.nif'),('finish','Construction/Haroun/HarounDeconstructionStructure.nif')]:
 raw=next(v for k,v in files.items() if k.lower()==('Effects/'+source).lower())
 # Relative particle textures remain local to the copied composite model.
 for key,value in files.items():
  if key.lower().startswith('effects/construction/haroun/') and key.lower().endswith('.dds'):
   (folder/Path(key).name).write_bytes(value)
 for count in range(5,33):
  length=(count-1)*2;pieces=1
  for axis in ('x','y'):
   root=N.NiNode();root.name=b'BridgeGrowthRoot';root.flags=16
   positions=[]
   for i in range(pieces):
    position=0
    data=N.Data();data.read(io.BytesIO(raw));offset=N.NiNode();offset.name=f'Growth{i:02}'.encode();offset.flags=16
    if axis=='x':offset.translation.x=position
    else:offset.translation.y=position
    for child in data.roots:
     # Keep the two stock particle layers, replacing circular meshes and
     # cylindrical emitters with one continuous rectangle over the deck.
     for branch in list(child.children):
      if not any(isinstance(b,N.NiParticleSystem) for b in branch.tree()):child.remove_child(branch)
     # These stationary, attached effects can be born before their owning
     # bridge's transform is propagated. World-space particles kept that first
     # unrotated strip for their whole lifetime, making a cross at completion.
     # Local particles follow the final bridge transform from the first draw.
     for block in child.tree():
      if isinstance(block,N.NiParticleSystem):
       block.world_space=False
       for j,old in enumerate(block.modifiers):
        if not isinstance(old,N.NiPSysCylinderEmitter):continue
        box=N.NiPSysBoxEmitter()
        for attr in ['name','order','target','active','speed','speed_variation','declination','declination_variation','planar_angle','planar_angle_variation','initial_radius','radius_variation','life_span','life_span_variation','emitter_object']:setattr(box,attr,getattr(old,attr))
        for color in ['r','g','b','a']:setattr(box.initial_color,color,getattr(old.initial_color,color))
        box.width=length if axis=='x' else 6;box.height=6 if axis=='x' else length;box.depth=.15
        if old.initial_radius>1:box.initial_radius=1.2;box.speed=4;box.life_span=2.2
        else:box.initial_radius=.12;box.speed=6;box.speed_variation=2;box.life_span=2.6
        block.modifiers[j]=box
       controller=block.controller
       while controller:
        if isinstance(controller,N.NiPSysEmitterCtlr) and controller.data:
         for key in controller.data.float_keys.keys:key.value=min(180,max(28,length*3.5))
        controller=controller.next_controller
     offset.add_child(child)
    root.add_child(offset);positions.append(position)
   model=N.Data(version=0x0A010000,user_version=0);model.roots=[root]
   path=folder/f'{kind}_{axis}_{count:02}.nif'
   with path.open('wb') as f:model.write(f)
   read=N.Data();read.read(io.BytesIO(path.read_bytes()));assert len(read.roots[0].children)==pieces
   # Preserve stock particle textures/controllers instead of substituting art.
   report[path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source':source,
                      'sourceSha256':hashlib.sha256(raw).hexdigest(),'length':length,'axis':axis,'pieces':pieces,'positions':positions,'particleSpace':'local','shape':'rectangle','width':6}
(r/'haroun-growth-art.json').write_text(json.dumps({'passed':True,'variants':report},indent=2))
print('HAROUN_GROWTH_ART_PASS',len(report),'continuous rectangular effects, local particle transforms')
