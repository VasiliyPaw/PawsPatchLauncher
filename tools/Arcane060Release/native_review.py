from review import *
import struct,math,threading

def visual(ident):
 m=Memory('preview');u=m.u
 try:
  reg=u(m.base+0x5ef72c);a=u(reg+0x20004+(ident&65535)*4);assert a and u(a+20)==ident
  view=u(a+12);body=u(a+0x60);model=u(view+0x78);root=u(model+12) if model else 0;effects=[];node=u(u(view+0x9c)) if u(view+0x9c) else 0
  while node and len(effects)<40:
   fx=u(node);name=m.name(u(fx+16));row={'fx':fx,'name':name,'type':u(fx)-m.base,'owner':u(fx+0x90)}
   if row['type']==0x50aa5c and u(fx+0xac):
    model_fx=u(fx+0xac);root_fx=u(model_fx+12);row.update(model=model_fx,root=root_fx,parent=u(root_fx+0x24),rotation=list(struct.unpack('<9f',m.read(root_fx+0x6c,36))),position=list(struct.unpack('<3f',m.read(root_fx+0x90,12))),scale=m.f(root_fx+0x9c))
   if name=='paws_bridge_shadow_fade':row['alpha']=m.f(fx+0xb4)
   effects.append(row);node=u(node+4)
  return {'id':ident,'name':m.name(u(a+4)),'construction':bool(u(a+0x100)&0x200000),'hp':m.f(body+0x10),'maxhp':m.f(body+0x14),'modelAlpha':m.f(model+0x48) if model else None,'modelPosition':list(struct.unpack('<3f',m.read(root+0x90,12))) if root else None,'effects':effects}
 finally:m.close()

def bind_visual():
 bind();m=Memory('preview')
 try:(M/'network-visual-api.txt').write_text(f"{m.road} {m.export('bridge_actor_fixture')} {m.export('bridge_health_fixture')} {m.export('bridge_request')}")
 finally:m.close()

def run(race,wood,preview=False):
 label=race+'-'+('wood' if wood else 'stone');load('R6-art-'+race);wait(lambda:any(k['id']==429 and k['nation'].lower()==race for k in snap()['kingdoms']),10,'race');bind_visual()
 cmd('GamePause 0');cmd('GameSpeed 0');cmd('!sp-river');time.sleep(.4);cmd('!sp-gold 429 100000')
 worker={'human':'engineer','gauri':'forge','drauga':'crafter','haroun':'caretaker','undead':'boneweaver','shadow':'nightbringer'}[race];organization='workers_shadow' if race=='shadow' else 'company_'+worker
 cmd(f'!sp-org {organization} 429 101 81');wait(lambda:any(a['name']==organization and a['id']!=432 for a in snap()['actors']),12,'racial worker')
 worker_id=next(a['id'] for a in snap()['actors'] if a['name']==organization and a['id']!=432)
 cmd(f'!sp-review-site {worker_id} {wood} 1');wait(lambda:any(a['name'].startswith('paws_bridge_') and a['construction'] for a in snap()['actors']),15,'native paid site')
 actor_id=next(a['id'] for a in snap()['actors'] if a['name'].startswith('paws_bridge_'));v=visual(actor_id);stages=[]
 cmd('MoveCamera 0 0 116 81 1')
 cmd(f"!sp-review-health {actor_id} {v['maxhp']*.1}");time.sleep(.7);stages.append(visual(actor_id));shot(label+'-10')
 if race=='shadow':assert abs(stages[-1]['modelAlpha']-.55)<1e-6
 cmd(f'!sp-review-resume {worker_id} {actor_id}')
 wait(lambda:any('root' in f and ('paws_bridge_build_' in f['name'] or 'haroun_growth' in f['name']) for f in visual(actor_id)['effects']),15,'native construction effect')
 cmd(f"!sp-review-health {actor_id} {v['maxhp']*.5}");time.sleep(3);stages.append(visual(actor_id));shot(label+'-50')
 cmd(f"!sp-review-health {actor_id} {v['maxhp']*.85}");time.sleep(1);stages.append(visual(actor_id));shot(label+'-85')
 if race=='shadow':assert all(abs(s['modelAlpha']-.55)<1e-6 for s in stages)
 if race in ['human','gauri','drauga']:
  for stage in stages:
   scaffold=next(f for f in stage['effects'] if f'paws_bridge_build_{race}_scaffold_' in f['name'])
   assert scaffold['parent'] and max(abs(x-y) for x,y in zip(scaffold['position'],stage['modelPosition']))<.01,('scaffold must stay at the stable bridge root',race,scaffold)
 if preview:
  (E/(label+'-preview.json')).write_text(json.dumps({'stages':stages},indent=2));print('PREVIEW_READY',json.dumps(stages[-1]),flush=True);return
 v=visual(actor_id);tracked=[f for f in v['effects'] if 'root' in f and ('paws_bridge_build_' in f['name'] or 'haroun_growth' in f['name'])];assert tracked
 samples=[]
 def collect():
  m=Memory('preview');start=time.monotonic();vt={f['root']:m.u(f['root']) for f in tracked}
  try:
   while time.monotonic()-start<7:
    row={'seconds':time.monotonic()-start,'nodes':[]}
    for f in tracked:
     root=f['root']
     try:
      if m.u(root)!=vt[root]:continue
      rotation=list(struct.unpack('<9f',m.read(root+0x6c,36)))
      if all(math.isfinite(x) for x in rotation):row['nodes'].append({'root':root,'parent':m.u(root+0x24),'rotation':rotation})
     except AssertionError:pass
    samples.append(row);time.sleep(.01)
  finally:m.close()
 t=threading.Thread(target=collect);t.start();time.sleep(.1);cmd(f"!sp-review-health {actor_id} {v['maxhp']-1}")
 wait(lambda:not visual(actor_id)['construction'],15,'native finish');stages.append(visual(actor_id));shot(label+'-completed');t.join();time.sleep(.3);stages.append(visual(actor_id));shot(label+'-after-fade')
 assert not stages[-1]['construction'] and stages[-1]['hp']==stages[-1]['maxhp']
 if race=='shadow':assert stages[-1]['modelAlpha']==1
 errors=[]
 for f in tracked:
  det=[n for s in samples for n in s['nodes'] if n['root']==f['root'] and n['parent']!=f['parent']];assert len(det)>=2,('detach missing',label,f['name'])
  expected=math.atan2(f['rotation'][3],f['rotation'][0]);err=[abs(math.atan2(math.sin(math.atan2(n['rotation'][3],n['rotation'][0])-expected),math.cos(math.atan2(n['rotation'][3],n['rotation'][0])-expected))) for n in det];assert max(err)<.12,(label,f['name'],max(err))
  errors.append({'name':f['name'],'detachedSamples':len(det),'maxYawErrorRadians':max(err)})
 (E/(label+'-lifecycle.json')).write_text(json.dumps({'passed':True,'race':race,'wood':bool(wood),'actor':actor_id,'stages':stages,'detachment':errors,'samples':samples,'paidNativeSite':True,'nativeWorker':organization,'qaHealthAdvanced':True},indent=2))
 print('RACIAL_BRIDGE_PASS',label,[(e['detachedSamples'],round(e['maxYawErrorRadians'],6)) for e in errors],flush=True)

if __name__=='__main__':
 for spec in sys.argv[1:]:
  race,mat=spec.split('-');run(race,1 if mat=='wood' else 0)
