"""A deck-height corner outline, independent of terrain-projected decals."""
from pathlib import Path
import argparse,hashlib,json,sys,time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.out.resolve()
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'outputs/bridge-model-ee2-20261109/deps'));time.clock=time.perf_counter
from pyffi.formats.nif import NifFormat as N
folder=r/'sandbox/rivers-data/Paws/Bridges/Selection';folder.mkdir(parents=True,exist_ok=True);report={}
for kind,color in [('selected',(0,1,0)),('focused',(1,1,.4))]:
 for count in range(5,33):
  half=count-1;end=half+.25;width=3.45
  for axis in ('x','y'):
   root=N.NiNode();root.name=b'BridgeOutline';root.flags=16;mesh=N.NiTriShape();mesh.name=b'DeckCorners';mesh.flags=16
   vertices=[];triangles=[]
   def quad(x0,y0,x1,y1):
    at=len(vertices)
    for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:vertices.append((y,x,.24) if axis=='x' else (x,y,.24))
    triangles.extend([(at,at+1,at+2),(at,at+2,at+3)])
   for signx in [-1,1]:
    for signy in [-1,1]:
     x=signx*width;y=signy*end
     quad(min(x,x-signx*1.8),min(y,y-signy*.18),max(x,x-signx*1.8),max(y,y-signy*.18))
     quad(min(x,x-signx*.18),min(y,y-signy*min(2.2,half*.4)),max(x,x-signx*.18),max(y,y-signy*min(2.2,half*.4)))
   data=N.NiTriShapeData();data.num_vertices=len(vertices);data.has_vertices=True;data.vertices.update_size();data.has_normals=True;data.normals.update_size()
   for v,point in zip(data.vertices,vertices):v.x,v.y,v.z=point
   for normal in data.normals:normal.x,normal.y,normal.z=0,0,1
   # Draw both sides so x/y bake reflection never reverses visible winding.
   triangles+= [(c,b,a) for a,b,c in list(triangles)];data.set_triangles(triangles);data.update_center_radius();mesh.data=data
   mat=N.NiMaterialProperty();mat.diffuse_color.r,mat.diffuse_color.g,mat.diffuse_color.b=color
   mat.ambient_color.r,mat.ambient_color.g,mat.ambient_color.b=color
   mat.emissive_color.r,mat.emissive_color.g,mat.emissive_color.b=color;mat.alpha=1;mesh.add_property(mat)
   vertex=N.NiVertexColorProperty();vertex.vertex_mode=0;vertex.lighting_mode=1;mesh.add_property(vertex)
   z=N.NiZBufferProperty();z.flags=3;z.function=3;mesh.add_property(z)
   root.add_child(mesh);model=N.Data(version=0x0A010000,user_version=0);model.roots=[root];path=folder/f'{kind}_{axis}_{count:02}.nif'
   with path.open('wb') as f:model.write(f)
   report[path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'deckZ':.24,'halfWidth':width,'halfLength':end,'depthTest':True,'depthWrite':True,'triangles':len(triangles)}
(r/'bridge-outline-art.json').write_text(json.dumps({'passed':True,'variants':report},indent=2))
print('BRIDGE_OUTLINES_READY',len(report),'thin depth-tested deck contours')
