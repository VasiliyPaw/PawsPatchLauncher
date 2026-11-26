"""Private bridge material experiment; preserves gameplay geometry and source files."""
from pathlib import Path
import io, json, hashlib, math, sys, time, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'outputs/bridge-model-ee2-20261109/deps'));time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N
SOURCE=Path('G:/PawsWork/QA/ArcaneFix-20261125/game/rivers-data/Paws/Bridges')
BEFORE=HERE/'before/Paws/Bridges';AFTER=HERE/'candidate/Paws/Bridges'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 d=N.Data();d.read(io.BytesIO(path.read_bytes()));return d
def rgb(c):return np.array([c.r,c.g,c.b],dtype=float)
def parts(model):
 result=[]
 def visit(b,parent,props):
  if not isinstance(b,N.NiAVObject):return
  if int(b.flags)&1 or bytes(b.name) in [b'SelectionBox'] or bytes(b.name).endswith(b'_Sg'):return
  matrix=np.array(b.get_transform().as_list())@parent
  p={**props,**{type(x).__name__:x for x in b.properties if x}}
  if isinstance(b,N.NiTriBasedGeom):
   v=np.array([[q.x,q.y,q.z,1.] for q in b.data.vertices])@matrix
   normals=np.array([[q.x,q.y,q.z] for q in b.data.normals])@np.linalg.inv(matrix[:3,:3]).T
   normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-9)
   result.append(dict(mesh=b,vertices=v[:,:3],normals=normals,triangles=np.array(list(b.data.get_triangles())),props=p))
  for ch in getattr(b,'children',[]):
   if ch:visit(ch,matrix,p)
 for root in model.roots:visit(root,np.eye(4),{})
 return result

def geometry(model):
 return [(bytes(b.name),[(v.x,v.y,v.z)for v in b.data.vertices],list(b.data.get_triangles()),
          [[(u.u,u.v)for u in uv] for uv in b.data.uv_sets],[(v.x,v.y,v.z)for v in b.data.normals])
         for b in model.blocks if isinstance(b,N.NiTriBasedGeom)]

def ambient_occlusion(ps,radius=2.4,samples=24):
 tris=np.concatenate([p['vertices'][p['triangles']] for p in ps]);a=tris[:,0];e1=tris[:,1]-a;e2=tris[:,2]-a
 lo=tris.min(axis=1);hi=tris.max(axis=1);output=[]
 # Deterministic cosine-weighted hemisphere, shared across before/after views.
 phi=np.arange(samples)*2.399963229728653;rad=np.sqrt((np.arange(samples)+.5)/samples)
 hemisphere=np.column_stack([rad*np.cos(phi),rad*np.sin(phi),np.sqrt(1-rad**2)])
 cache={}
 for p in ps:
  weights=[]
  for pos,n in zip(p['vertices'],p['normals']):
   key=tuple(np.round(np.r_[pos,n],4))
   if key in cache:weights.append(cache[key]);continue
   distance=np.maximum(np.maximum(lo-pos,pos-hi),0)
   keep=(distance*distance).sum(axis=1)<radius**2
   aa=a[keep];ee1=e1[keep];ee2=e2[keep]
   axis=np.array([0.,0.,1.]) if abs(n[2])<.9 else np.array([1.,0.,0.])
   tangent=np.cross(axis,n);tangent/=max(np.linalg.norm(tangent),1e-9);bitangent=np.cross(n,tangent)
   dirs=hemisphere@np.array([tangent,bitangent,n])
   origin=pos+n*.045
   h=np.cross(dirs[:,None,:],ee2[None,:,:]);det=(ee1[None,:,:]*h).sum(axis=2)
   valid=np.abs(det)>1e-8;inv=np.divide(1.,det,out=np.zeros_like(det),where=valid)
   s=origin-aa;u=inv*(s[None,:,:]*h).sum(axis=2);q=np.cross(s,ee1)
   v=inv*(dirs[:,None,:]*q[None,:,:]).sum(axis=2);t=inv*(ee2*q).sum(axis=1)[None,:]
   hit=valid&(u>=0)&(v>=0)&(u+v<=1)&(t>.035)&(t<radius)
   nearest=np.where(hit,t,np.inf).min(axis=1)
   occlusion=np.where(np.isfinite(nearest),1.-np.minimum(nearest/radius,1.)*.65,0.).mean()
   weight=float(1.-.48*occlusion);cache[key]=weight;weights.append(weight)
  output.append(np.array(weights))
 return output

def fallback(ps,path):
 # Square world footprint: elongated bridges keep their aspect ratio.
 pts=np.concatenate([p['vertices'] for p in ps]);center=(pts.min(axis=0)+pts.max(axis=0))/2
 span=max(np.ptp(pts[:,0]),np.ptp(pts[:,1]))*1.12;size=512
 mask=Image.new('L',(size,size));draw=ImageDraw.Draw(mask)
 for p in ps:
  xy=(p['vertices'][:,:2]-center[:2])/span*(size-1)+size/2
  for f in p['triangles']:draw.polygon([tuple(x) for x in xy[f]],fill=72)
 mask=mask.filter(ImageFilter.GaussianBlur(2.5))
 # Stock UnitShadow.tga is RGB24 with white neutral background and gray ink.
 # Preserve the native multiplicative texture convention (not black RGBA).
 shade=255-np.asarray(mask,dtype=np.uint8)
 image=Image.fromarray(np.repeat(shade[:,:,None],3,axis=2));path.parent.mkdir(parents=True,exist_ok=True);image.save(path)

def main():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=13);args=parser.parse_args();count=args.count
 manifest=HERE/('candidate-manifest.json'if count==13 else f'candidate-manifest-{count}.json')
 assert not manifest.exists(),'Use a new revision, never replace a reviewed candidate'
 report={'privateCandidate':True,'installedGameModified':False,'liveGameVerified':False,'samples':24,'aoRadius':2.4,'models':[]}
 for race in ['Human','Gauri','Drauga','Haroun','Shadow','Undead']:
  for kind in ['wood','stone']:
   name=f'{kind}_y_{count:02}.nif';src=SOURCE/race/name;before=BEFORE/race/name;target=AFTER/race/name
   before.parent.mkdir(parents=True,exist_ok=True);target.parent.mkdir(parents=True,exist_ok=True)
   shutil.copy2(src,before);d=load(before);original=geometry(d);ps=parts(d);weights=ambient_occlusion(ps)
   copied=[]
   for p,w in zip(ps,weights):
    mesh=p['mesh'];mat=p['props'].get('NiMaterialProperty');base=rgb(mat.diffuse_color)if mat else np.ones(3)
    tex=p['props'].get('NiTexturingProperty')
    if tex and tex.has_base_texture:
     source_name=Path(bytes(tex.base_texture.source.file_name).decode().replace('\\','/')).name
     texture=SOURCE/race/source_name
     if not texture.exists():texture=SOURCE/source_name
     assert texture.is_file(),texture
     for dest in [before.parent/source_name,target.parent/source_name]:shutil.copy2(texture,dest)
     copied.append(source_name)
    data=mesh.data;data.has_vertex_colors=True;data.vertex_colors.update_size()
    for c,value in zip(data.vertex_colors,w):c.r,c.g,c.b=map(float,np.clip(base*value,0,1));c.a=1.
    prop=N.NiVertexColorProperty();prop.vertex_mode=2;prop.lighting_mode=1
    old=next((x for x in mesh.properties if isinstance(x,N.NiVertexColorProperty)),None)
    if old:mesh.remove_property(old)
    mesh.add_property(prop)
   with target.open('wb')as f:d.write(f)
   checked=load(target);assert geometry(checked)==original,'Geometry/UV/normal drift'
   assert sha(src)==sha(before),'Source changed during snapshot'
   shadow=AFTER/'Shadows'/f'{race.lower()}_{kind}_y_{count:02}.tga';fallback(ps,shadow)
   row=dict(race=race,kind=kind,before=str(before.relative_to(HERE)),after=str(target.relative_to(HERE)),sourceSha256=sha(before),candidateSha256=sha(target),geometryUvNormalsUnchanged=True,meshes=len(ps),vertexAoMinimum=round(min(w.min()for w in weights),4),vertexAoMean=round(float(np.mean(np.concatenate(weights))),4),fallback=str(shadow.relative_to(HERE)),textures=sorted(set(copied)))
   report['models'].append(row);print(json.dumps({k:row[k]for k in ['race','kind','meshes','vertexAoMinimum','vertexAoMean']}),flush=True)
 manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
