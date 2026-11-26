"""Resumable, single-worker material overlay. No game, SDK, installer or shadows.

The original AO24 hemisphere/radius/strength and rounding cache are preserved.
Only nearest-ray intersection is accelerated by a task-owned standalone helper.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,io,json,os,struct,subprocess,sys,time,threading,_thread,traceback,ctypes,uuid,shutil
import numpy as np

HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'bridge-natural-look-20261125'
sys.path.insert(0,str(OLD))
import build_candidate as original
N=original.N
INPUT=HERE/'inputs';OUTPUT=HERE/'overlay/Paws/Bridges';TEMP=HERE/'temp'
HELPER=HERE/'ao_trace.exe'
active_child=None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
 tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,path)
def parent_peak_bytes():
 class Counters(ctypes.Structure):
  _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong),*[(n,ctypes.c_size_t)for n in ['peak','working','quotaPeakPaged','quotaPaged','quotaPeakNonPaged','quotaNonPaged','pagefile','peakPagefile']]]
 counters=Counters();counters.cb=ctypes.sizeof(counters)
 api=ctypes.WinDLL('psapi').GetProcessMemoryInfo;api.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong];api.restype=ctypes.c_int
 assert api(ctypes.c_void_p(-1),ctypes.byref(counters),counters.cb)
 return int(counters.peak)
def arrays_digest(items):
 h=hashlib.sha256()
 for a in items:
  b=np.asarray(a);h.update(str(b.shape).encode());h.update(b.tobytes())
 return h.hexdigest()
def invariant(d):
 av=[];geometries=[];materials=[];textures=[];hidden=[];controllers=[]
 for b in d.blocks:
  if isinstance(b,N.NiAVObject):
   av.append((type(b).__name__,bytes(b.name).hex(),int(b.flags),b.get_transform().as_list(),
              [(type(c).__name__,bytes(c.name).hex()) for c in getattr(b,'children',[])if c]))
  if isinstance(b,N.NiTriBasedGeom):
   x=b.data
   arrays=[np.array([[v.x,v.y,v.z]for v in x.vertices],dtype='<f4'),
           np.array(list(x.get_triangles()),dtype='<u4'),
           np.array([[v.x,v.y,v.z]for v in x.normals],dtype='<f4')]
   arrays.extend(np.array([[v.u,v.v]for v in uv],dtype='<f4')for uv in x.uv_sets)
   g=(type(b).__name__,bytes(b.name).hex(),int(x.num_vertices),bool(x.has_normals),
      int(x.num_uv_sets),float(x.radius),[x.center.x,x.center.y,x.center.z],arrays_digest(arrays))
   geometries.append(g)
   if bytes(b.name)==b'SelectionBox' or bytes(b.name).endswith(b'_Sg') or int(b.flags)&1:
    stream=io.BytesIO();x.write(stream,d)
    hidden.append((bytes(b.name).hex(),hashlib.sha256(stream.getvalue()).hexdigest(),
                   [(int(p.vertex_mode),int(p.lighting_mode))for p in b.properties if isinstance(p,N.NiVertexColorProperty)]))
  if isinstance(b,N.NiMaterialProperty):
   materials.append((bytes(b.name).hex(),*[original.rgb(getattr(b,k)).tolist() for k in ['ambient_color','diffuse_color','specular_color','emissive_color']],float(b.glossiness),float(b.alpha)))
  if isinstance(b,N.NiTexturingProperty):
   slots=[]
   for slot in ['base','dark','detail','gloss','glow','bump_map','normal','unknown_2','decal_0','decal_1','decal_2','decal_3']:
    flag='has_'+slot+'_texture';desc=slot+'_texture'
    if hasattr(b,flag) and getattr(b,flag):
     t=getattr(b,desc);source=t.source
     slots.append((slot,bytes(source.file_name).hex(),int(source.use_external),int(t.clamp_mode),int(t.filter_mode),int(t.uv_set)))
   textures.append((int(b.apply_mode),int(b.texture_count),slots))
  if isinstance(b,N.NiTimeController):
   controllers.append((type(b).__name__,int(b.flags),float(b.frequency),float(b.phase),float(b.start_time),float(b.stop_time)))
 return {'hierarchy':av,'geometry':geometries,'materials':materials,'textures':textures,'hidden':hidden,'controllers':controllers}

def trace(ps,timeout):
 global active_child
 samples=24;radius=2.4
 tris=np.ascontiguousarray(np.concatenate([p['vertices'][p['triangles']]for p in ps]),dtype='<f8')
 phi=np.arange(samples)*2.399963229728653;rad=np.sqrt((np.arange(samples)+.5)/samples)
 hemi=np.column_stack([rad*np.cos(phi),rad*np.sin(phi),np.sqrt(1-rad**2)])
 cache={};direction_cache={};queries=[];maps=[]
 for p in ps:
  mapping=[]
  for pos,n in zip(p['vertices'],p['normals']):
   key=tuple(np.round(np.r_[pos,n],4))
   index=cache.get(key)
   if index is None:
    index=len(queries);cache[key]=index;normal_key=tuple(n)
    dirs=direction_cache.get(normal_key)
    if dirs is None:
     axis=np.array([0.,0.,1.])if abs(n[2])<.9 else np.array([1.,0.,0.])
     tangent=np.cross(axis,n);tangent/=max(np.linalg.norm(tangent),1e-9);bitangent=np.cross(n,tangent)
     dirs=hemi@np.array([tangent,bitangent,n]);direction_cache[normal_key]=dirs
    queries.append(np.r_[pos,n,dirs.reshape(-1)])
   mapping.append(index)
  maps.append(np.array(mapping,dtype=int))
 query_array=np.ascontiguousarray(queries,dtype='<f8');TEMP.mkdir(exist_ok=True)
 incoming=TEMP/'trace-input.bin';outgoing=TEMP/'trace-output.bin'
 with incoming.open('wb')as f:
  f.write(struct.pack('<4sIIId',b'AO24',len(tris),len(queries),samples,radius));tris.tofile(f);query_array.tofile(f)
 outgoing.unlink(missing_ok=True)
 active_child=subprocess.Popen([str(HELPER),str(incoming),str(outgoing)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  stdout,stderr=active_child.communicate(timeout=timeout)
  if active_child.returncode:raise RuntimeError(f'AO helper exit {active_child.returncode}: '+stderr.decode('utf-8','replace')[:1000])
 finally:
  if active_child.poll()is None:active_child.kill();active_child.wait()
  active_child=None
 hits=np.fromfile(outgoing,dtype='<f8');assert hits.size==len(queries)*24
 hits=hits.reshape(-1,24)
 occlusion=np.where(np.isfinite(hits),1.-np.minimum(hits/radius,1.)*.65,0.).mean(axis=1)
 weights=1.-.48*occlusion
 return [weights[m]for m in maps],{'queries':len(queries),'triangles':len(tris)}

def paint(d,ps,weights):
 for p,w in zip(ps,weights):
  mesh=p['mesh'];mat=p['props'].get('NiMaterialProperty');base=original.rgb(mat.diffuse_color)if mat else np.ones(3)
  colors=np.clip(base[None,:]*w[:,None],0,1)
  data=mesh.data;data.has_vertex_colors=True;data.vertex_colors.update_size()
  for c,value in zip(data.vertex_colors,colors):c.r,c.g,c.b=map(float,value);c.a=1.
  prop=N.NiVertexColorProperty();prop.vertex_mode=2;prop.lighting_mode=1
  previous=next((x for x in mesh.properties if isinstance(x,N.NiVertexColorProperty)),None)
  if previous:mesh.remove_property(previous)
  mesh.add_property(prop)

def process(relative,inputs,timeout):
 started=time.monotonic();path=INPUT/relative
 assert sha(path)==inputs['files'][relative]['sha256'],('Input snapshot changed',relative)
 d=original.load(path);before=invariant(d);ps=original.parts(d);weights,stats=trace(ps,timeout)
 reference=inputs['approvedReferences'].get(relative);delta=None
 if reference:
  approved=OLD/reference['after'];assert sha(approved)==reference['candidateSha256']
  reference_parts=original.parts(original.load(approved));assert len(ps)==len(reference_parts)
  delta=0.
  for p,w,r in zip(ps,weights,reference_parts):
   mat=p['props'].get('NiMaterialProperty');base=original.rgb(mat.diffuse_color)if mat else np.ones(3)
   predicted=np.clip(base[None,:]*w[:,None],0,1).astype(np.float32)
   actual=np.array([[c.r,c.g,c.b]for c in r['mesh'].data.vertex_colors],dtype=np.float32)
   assert actual.shape==predicted.shape
   delta=max(delta,float(np.max(np.abs(predicted-actual))))
  assert delta<=2e-6,('AO reference parity failed',relative,delta)
 paint(d,ps,weights);out=OUTPUT/relative;out.parent.mkdir(parents=True,exist_ok=True)
 if reference:
  # Preserve every previously approved byte, including color float encodings.
  shutil.copy2(OLD/reference['after'],out)
 else:
  temp=out.with_suffix('.nif.tmp')
  with temp.open('wb')as f:d.write(f)
  os.replace(temp,out)
 checked=original.load(out);assert invariant(checked)==before,('Non-color mutation',relative)
 assert sha(path)==inputs['files'][relative]['sha256']
 return {'sourceSha256':inputs['files'][relative]['sha256'],'sha256':sha(out),'bytes':out.stat().st_size,
         'invariantsExact':True,'approvedBytesReused':bool(reference),'referenceMaxColorDelta':delta,
         **stats,'seconds':round(time.monotonic()-started,4)}

def main():
 global active_child
 parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=180);parser.add_argument('--max-models',type=int,default=24);args=parser.parse_args()
 assert 1<=args.seconds<=180 and 1<=args.max_models<=672
 inputs=json.loads((HERE/'inputs-manifest.json').read_text(encoding='utf-8'));assert len(inputs['models'])==672
 assert HELPER.is_file();assert str(HERE.resolve()).lower().startswith('g:\\')
 state_path=HERE/'checkpoint.json';checkpoint=json.loads(state_path.read_text())if state_path.exists()else {'models':{}}
 pins={'inputs':sha(HERE/'inputs-manifest.json'),'helper':sha(HELPER),'script':sha(Path(__file__)),'acceleratorSource':sha(HERE/'ao_trace.c'),'originalScript':sha(OLD/'build_candidate.py')}
 if 'pins'in checkpoint:assert checkpoint['pins']==pins,'Frozen runner inputs changed; review a new checkpoint'
 checkpoint['pins']=pins
 order=sorted(inputs['approvedReferences'])+sorted(set(inputs['models'])-set(inputs['approvedReferences']))
 for rel,row in checkpoint['models'].items():assert sha(OUTPUT/rel)==row['sha256'],('Completed output drift',rel)
 started=time.monotonic();processed=0;batch_id=uuid.uuid4().hex;timer=threading.Timer(args.seconds,_thread.interrupt_main);timer.daemon=True;timer.start()
 status='complete';error=None
 try:
  for relative in order:
   if relative in checkpoint['models']:continue
   if processed>=args.max_models or time.monotonic()-started>args.seconds-15:status='checkpoint';break
   # References must all pass before unseen models can be emitted.
   if relative not in inputs['approvedReferences']:assert all(r in checkpoint['models']for r in inputs['approvedReferences'])
   row=process(relative,inputs,min(20,max(1,args.seconds-(time.monotonic()-started)-2)))
   checkpoint['models'][relative]=row;processed+=1;atomic(state_path,checkpoint)
   print(json.dumps({'done':len(checkpoint['models']),'total':672,'model':relative,'seconds':row['seconds'],'referenceDelta':row['referenceMaxColorDelta']}),flush=True)
 except KeyboardInterrupt:status='checkpoint'
 except BaseException as exc:
  status='failed';error=repr(exc);traceback.print_exc()
 finally:
  timer.cancel()
  if active_child is not None:
   if active_child.poll()is None:active_child.kill()
   active_child.wait();active_child=None
  receipt={'status':status,'error':error,'done':len(checkpoint['models']),'processed':processed,'elapsedSeconds':round(time.monotonic()-started,3),'pid':os.getpid(),'allTraceChildrenClosed':True,'parentPeakBytes':parent_peak_bytes(),'batchId':batch_id,'pins':pins}
  if status=='failed':
   failed=HERE/'failures'/batch_id;failed.mkdir(parents=True)
   for p in [TEMP/'trace-input.bin',TEMP/'trace-output.bin',Path(__file__),HERE/'ao_trace.c',HELPER]:
    if p.is_file():shutil.copy2(p,failed/p.name)
  atomic(HERE/'batches'/(batch_id+'.json'),receipt);atomic(HERE/'last-batch.json',receipt);print(json.dumps(receipt),flush=True)
 if status=='failed':raise SystemExit(1)
if __name__=='__main__':main()
