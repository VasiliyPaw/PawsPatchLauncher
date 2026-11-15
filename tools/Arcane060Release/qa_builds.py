"""Real worker growth, payment, interruption and native RSG round trips.

Only scene preparation creates an unpaid site. This runner never invokes a
health setter, edits HP, or fabricates a completed bridge. Speed 3 is the
game's 4x simulation setting; elapsed construction time uses native game time.
"""
from native_review import *
import hashlib
run_id='R060-'+str(int(time.time()))
WORKERS={'human':'company_engineer','gauri':'company_forge','drauga':'company_crafter','haroun':'company_caretaker','undead':'company_boneweaver','shadow':'workers_shadow'}
COST={'human':(100,200),'gauri':(125,250),'drauga':(80,160),'haroun':(80,160),'undead':(80,160),'shadow':(100,200)}

def bind_all():
 bind();m=Memory('preview')
 try:(M/'network-visual-api.txt').write_text(' '.join(str(x)for x in [m.road,m.export('bridge_actor_fixture'),m.export('bridge_health_fixture'),m.export('bridge_request'),m.export('bridge_move_request')]))
 finally:m.close()

def details(ident):
 m=Memory('preview');u=m.u
 try:
  reg=u(m.base+0x5ef72c);a=u(reg+0x20004+(ident&65535)*4);assert a and u(a+20)==ident
  k=u(a+0xe8);n=u(k+0x1d0);assert n<32;body=u(a+0x60);mind=u(a+0x70);order=u(mind+0x20)if mind else 0;world=u(m.base+0x5f3fb8)
  instance=m.text(u(a+0x18));construction=u(a+0x9c);paid_count=u(construction+0x14)if construction else 0;assert paid_count<=32
  paid_vector=list(struct.unpack('<%df'%paid_count,m.read(u(construction+0x10),paid_count*4)))if paid_count else []
  return {'id':ident,'definition':m.name(u(a+4)),'instance':instance,'paid':instance[18]!='U'if instance.startswith('paws_bridge_meta')else False,'nativePaidVector':paid_vector,'construction':bool(u(a+0x100)&0x200000),'hp':m.f(body+0x10)if body else None,'maxhp':m.f(body+0x14)if body else None,'seconds':m.f(world+0xe8),'tick':u(world+0xe4),'stock':list(struct.unpack('<%df'%n,m.read(u(k+0x1cc),n*4))),'income':list(struct.unpack('<%df'%n,m.read(u(k+0x1a8),n*4))),'upkeep':list(struct.unpack('<%df'%n,m.read(u(k+0x1c0),n*4))),'order':m.name(u(order+8))if order else None,'target':u(order+0x10)if order else 0}
 finally:m.close()

def pause():cmd('GamePause 1');time.sleep(.12)
def advance(ident,sim_seconds):
 start=details(ident)['seconds'];cmd('GamePause 0');wait(lambda:details(ident)['seconds']>=start+sim_seconds,sim_seconds+12,'native simulated time');pause();return details(ident)

def visible(ident,race):
 time.sleep(.25);v=visual(ident)
 if v['construction']:
  if race=='shadow':assert abs(v['modelAlpha']-.55)<1e-6
  elif race in ['human','gauri','drauga']:
   f=next(f for f in v['effects']if f'paws_bridge_build_{race}_scaffold_'in f['name']);assert f['parent']
   assert max(abs(x-y)for x,y in zip(f['position'],v['modelPosition']))<.01
 return v

def checkpoint(label,stage,ident,worker,race,restart=False):
 pause();before=details(ident);v=visible(ident,race);name=run_id+'-'+label+'-'+stage
 path=R/'Documents/Kohan2/data/Save'/(name+'.RSG');assert not path.exists(),path
 cmd('GameSave Save/'+name+'.RSG');wait(lambda:path.exists()and path.stat().st_size>1000,20,'native saved file');time.sleep(.3)
 digest=hashlib.sha256(path.read_bytes()).hexdigest();shot(label+'-'+stage+'-before-save')
 if restart:
  cmd('ReallyQuit');wait(lambda:not own(),30,'native process exit');(M/'plugins.txt').write_text((E/'final-plugins.txt').read_text());launch()
 if state('preview').get('world'):cmd('GameLoad Save/'+name+'.RSG')
 else:
  for c in ['RequestSinglePlayer','RequestCustom','SelectLaunchType LOAD_SAVED_GAME','Select Save/'+name+'.RSG','Commit','StagingLaunch']:cmd(c);time.sleep(.2)
 wait(lambda:state('preview').get('world')and state('preview').get('mode')==2,90,'saved world loaded');time.sleep(.2)
 restored=details(ident)
 assert abs(restored['hp']-before['hp'])<.01,(label,stage,'saved HP differs',before,restored)
 assert restored['instance']==before['instance']and restored['paid']and restored['construction']
 assert restored['stock']==before['stock'],(label,stage,'stockpile changed on load',before['stock'],restored['stock'])
 cmd('UserReady');wait(lambda:state('preview').get('phase')==4 and not state('preview').get('frozen'),60,'saved interface');pause();cmd('GameSpeed 3');bind_all()
 after_visual=visible(ident,race);shot(label+'-'+stage+'-loaded')
 worker_state=details(worker);assert worker_state['target']==ident,(label,stage,'builder order not restored',worker_state)
 return {'stage':stage,'fullProcessRestart':restart,'path':str(path),'sha256':digest,'before':before,'restoredBeforeUserReady':restored,'visualBefore':v,'visualAfter':after_visual,'workerAfter':worker_state}

def case(race,wood):
 label=race+'-'+('wood'if wood else'stone');report=E/(label+'-savebuild.json');assert not report.exists(),report
 load('R6-art-'+race);bind_all();cmd('GamePause 0');cmd('GameSpeed 3');cmd('!sp-river');cmd('!sp-gold 429 100000');cmd(f'!sp-org {WORKERS[race]} 429 101 121');time.sleep(.3)
 wid=next(a['id']for a in snap()['actors']if a['name']==WORKERS[race]and a['id']!=432)
 cmd(f'!sp-review-site {wid} {wood} 0');wait(lambda:any(a['name'].startswith('paws_bridge_')for a in snap()['actors']),10,'unpaid site');aid=next(a['id']for a in snap()['actors']if a['name'].startswith('paws_bridge_'));pause()
 initial=details(aid);assert initial['hp']==1 and not initial['paid'];cmd(f'!sp-review-resume {wid} {aid}');cmd('GamePause 0');wait(lambda:details(aid)['paid'],20,'first native worker payment');pause();charged=details(aid)
 base_cost=COST[race][not wood];cost=charged['nativePaidVector'][0];debit=initial['stock'][0]-charged['stock'][0]
 expected_debit=cost+(initial['upkeep'][0]-initial['income'][0])*(charged['seconds']-initial['seconds'])/60
 assert 0<cost<=base_cost*2 and abs(debit-expected_debit)<1,(label,'payment',debit,expected_debit,initial,charged)
 assert charged['hp']>initial['hp']and charged['hp']<charged['maxhp']*.3
 print('NATURAL_PAYMENT_PASS',label,'debit',round(debit,3),'expected',cost,flush=True)
 cmd('GamePause 0');wait(lambda:details(aid)['hp']>=initial['maxhp']*.10,180,'early natural growth');pause()
 cmd(f'!sp-review-away {wid}');a=advance(aid,5);b=advance(aid,5)
 if race!='haroun':assert abs(b['hp']-a['hp'])<.01,(label,'HP grows after worker interruption',a,b)
 else:
  # Paid Haroun bridges retain the deliberately requested autonomous growth.
  assert abs((b['hp']-a['hp'])/(b['seconds']-a['seconds'])-15)<.2,(label,'Haroun native growth changed',a,b)
 stopped={'afterSettling':a,'afterFiveMoreSeconds':b,'worker':details(wid)}
 cmd(f'!sp-review-resume {wid} {aid}');cmd('GamePause 0');wait(lambda:details(aid)['hp']>b['hp']+1,30,'builder returns to the site');pause();c=details(aid);assert c['paid'];assert c['hp']<c['maxhp']*.4
 resume_debit=b['stock'][0]-c['stock'][0];resume_upkeep=(b['upkeep'][0]-b['income'][0])*(c['seconds']-b['seconds'])/60
 assert abs(resume_debit-resume_upkeep)<2,(label,'resuming charged construction again',b,c)
 early=checkpoint(label,'early',aid,wid,race)
 now=details(aid);progress=advance(aid,3);assert progress['hp']>now['hp'],'saved worker did not resume automatically'
 cmd('GamePause 0');wait(lambda:details(aid)['hp']>=initial['maxhp']*.83,240,'late natural growth');pause();assert details(aid)['construction']
 late=checkpoint(label,'late',aid,wid,race,restart=True)
 now=details(aid);progress=advance(aid,3);assert progress['hp']>now['hp'],'builder did not resume after full restart'
 cmd('GamePause 0');wait(lambda:not details(aid)['construction'],120,'natural finish');pause();complete=details(aid);assert complete['hp']==complete['maxhp']and complete['paid']
 after=advance(aid,12)
 def remains():return [f for f in visual(aid)['effects']if'paws_bridge_build_'in f['name']or'paws_bridge_haroun_growth_'in f['name']or'paws_bridge_haroun_finish_'in f['name']]
 if remains():
  assert all('finish_'in f['name']for f in remains()),('working construction effect remained after finish',label,remains())
  cmd('GamePause 0');wait(lambda:not remains(),12,'native completion effect timed cleanup');pause()
 vv=visual(aid);assert not remains(),('unfinished construction effects',label,vv)
 if race=='shadow':assert vv['modelAlpha']==1
 shot(label+'-natural-completed')
 result={'passed':True,'race':race,'wood':bool(wood),'worker':wid,'actor':aid,'healthNeverEdited':True,'nativeUnpaidSitePrepared':True,'nativeSpeedSetting':3,'nativeSpeedFactor':4,'initial':initial,'charged':charged,'baseGoldCost':base_cost,'nativeModifiedGoldCost':cost,'observedDebitIncludingNormalUpkeep':debit,'stopped':stopped,'earlySave':early,'lateSave':late,'completed':complete,'afterEffects':vv,'elapsedNativeConstructionSecondsIncludingInterruption':complete['seconds']-initial['seconds']}
 report.write_text(json.dumps(result,indent=2));print('SAVE_AND_NATURAL_BUILD_PASS',label,round(result['elapsedNativeConstructionSecondsIncludingInterruption'],3),'sim seconds',flush=True)

if __name__=='__main__':
 for label in sys.argv[1:]:
  race,mat=label.split('-');case(race,1 if mat=='wood'else 0)
