"""Owned Pure beta gameplay acceptance; packaged helpers remain unchanged."""
from context import *
from rwd import entries,decode
import re
STOCK_AVARS=decode(entries(OUT/'stable-fixtures/vanilla/game/Data.rwd')['data/avars_k2.tgi'])
source=REPO/'game/reconnect-test/installed_saves_pair.py';code=source.read_text()
code=code.replace(" p.add_argument('--different-keys'", " p.add_argument('--manual',action='store_true')\n p.add_argument('--large',action='store_true')\n p.add_argument('--pair',action='store_true')\n p.add_argument('--reload',action='store_true')\n p.add_argument('--hold',action='store_true')\n p.add_argument('--different-keys'",1)
code=code.replace('Wait 45\\nRequestMultiplayer','Wait 10\\nRequestMultiplayer')
code=code.replace('LobbySetLANNickname PawSavesClient\\nWait 2\\nLobbyJoinDirect','LobbySetLANNickname PawSavesClient\\nWait 2\\nMessageBoxButtonAction 1\\nWait 1\\nLobbyJoinDirect')
code=code.replace("  i['seq']+=1;mods=i['dir']/'game/Mods';n=i['seq']", "  mods=i['dir']/'game/Mods';i['seq']=max(i['seq'],int(text(mods/'rig-command.txt').strip()or'0'))+1;n=i['seq']")
anchor='  stay(8)\n  return i';assert code.count(anchor)==1
code=code.replace(anchor,"  wait(lambda:any('connect end MainMenuInterface'in text(f)for f in(d/'game/Logs').glob('log-*.log')),120,'Actual native menu interface connected '+d.name);stay(2)\n  return i")
# Manual navigation must not leave an old startup +Exec Wait queued behind it.
anchor="  (mods/'rig.txt').write_text(opening)";assert code.count(anchor)==1
code=code.replace(anchor,"  if a.manual:opening='Echo Pure isolated manual QA\\n'\n"+anchor)
anchor=" def host_lobby(i,load=False):\n  wait(";assert code.count(anchor)==1
code=code.replace(anchor," def host_lobby(i,load=False):\n  if a.manual:\n   for body in ['RequestMultiplayer','RequestLobbyLAN','LobbySetLANNickname PawSavesHost','MessageBoxButtonAction 1','InternetGameCreate PawSaves 2 2','SelectLaunchType '+('LOAD_SAVED_GAME'if load else'RANDOM_MAP')]:\n    command(i,body);stay(2)\n   if load:command(i,'Commit');stay(2)\n  wait(")
code=code.replace('status.availPage<5*1024**3','status.availPage<'+str(1 if '--pair'in sys.argv else 2)+'*1024**3')
trace=" with open(QA_MEMORY_PATH,'a')as f:f.write(json.dumps(dict(utc=time.time(),availablePhysical=status.availPhys,availableCommit=status.availPage,totalCommit=status.totalPage))+'\\n')\n"
code=code.replace(' if status.availPhys<3*1024**3',trace+' if status.availPhys<3*1024**3')
QA_MEMORY_PATH=Path(sys.argv[sys.argv.index('--out')+1]).resolve()/'memory.jsonl'if'--out'in sys.argv else Path('unused-memory.jsonl')

code=code.replace('int ResolutionX = 800','int ResolutionX = 1280').replace('int ResolutionY = 600','int ResolutionY = 720')
code=code.replace(' flag SinglePlayerAutoPause = false\\n',' flag SinglePlayerAutoPause = false\\n flag MPRunWhenInactive = true\\n int ResourceCacheTextureRAMWeight = 5\\n int ResourceCacheTextureVRAMWeight = 5\\n flag ViewShadows = false\\n')
anchor="  if save:shutil.copy2(save,data/'Save'/save.name)"
preparation="""  # QA configuration chooses native lobby defaults; packaged gameplay files and helper resources stay exact.
  avars=STOCK_AVARS
  avars=re.sub(r'(string StagingMultiPlayerDefaultRMCIds\\s*=\\s*)\\w+',r'\\g<1>paws_mixed_biomes',avars)
  for axis in ['Width','Height']:avars=re.sub(r'(float StagingMultiPlayerDefaultRMC'+axis+r'\\s*=\\s*)[\\d.]+',lambda m:m[1]+str(2048 if a.large else 384),avars)
  (game/'data/avars_k2.tgi').write_text(avars,encoding='utf-16')
  (game/'paws_launch_versions.ini').write_text('[Versions]\\nMod='+('immortals'if 'immortals'in str(a.game)else'vanilla')+'\\n'+('ModVersion=2.1\\n'if'immortals'in str(a.game)else'')+'PawPatch=0.5.0-beta.1\\nPatchChannel=beta\\n')
"""
code=code.replace(anchor,preparation+anchor)
# Hardlink only immutable native archives in our short-path QA copies.
code=code.replace("shutil.copytree(source,d/'game',ignore=omit)","shutil.copytree(source,d/'game',ignore=omit,copy_function=lambda x,y: os.link(x,y) if Path(x).suffix.lower()=='.rwd' else shutil.copy2(x,y))")
code=code.replace('result=dict(state=u(session+0xf0),','result=dict(phase=u(b+0x5f92f4),state=u(session+0xf0),')
anchor="   if world:result['seconds']=struct.unpack('<f',read(world+0xe8,4))[0]";code=code.replace(anchor,anchor+'''
   if world:
    result['colors']=list(struct.unpack('<9f',read(world+0x84,36)));result['tick']=u(world+0xe4);rules={};table=u(world+0x18);count=u(world+0x1c)
    if table and count<=256:
     for j in range(count):
      record=table+j*12;definition=u(record);pointer=u(definition+8);name=read(pointer,100).decode('utf-16le').split(chr(0))[0];rules[name]=u(record+8)
    result['rules']=rules
''')
anchor=' def errors():'
extra=''' def details(i):
  handle=K.OpenProcess(0x1410,False,i['pid']);assert handle
  try:
   identity(handle,i)
   def read(at,n):
    data=C.create_string_buffer(n);got=C.c_size_t();assert K.ReadProcessMemory(handle,at,data,n,C.byref(got))and got.value==n,hex(at);return data.raw
   def u(at):return struct.unpack('<I',read(at,4))[0]
   def string(at):return read(at,100).decode('utf-16le').split(chr(0))[0]if at else''
   b=i['base'];world=u(b+0x5f3fb8);mp=u(world+0x30);w=u(mp+0x1c);height=u(mp+0x20);assert 32<=w<=1024 and 32<=height<=1024
   raw=read(u(mp+0x28),w*height*48);counts={};variants={}
   for k in range(w*height):
    ptr=struct.unpack_from('<I',raw,k*48)[0];variants[ptr]=variants.get(ptr,0)+1
   for ptr,n in variants.items():
    name=string(u(ptr+8)).split('_')[0];counts[name]=counts.get(name,0)+n
   mgr=u(b+0x5f3fc0);buckets=u(mgr+0x7c);n=u(mgr+0x80);assert n<=65536;seen=set();roots=[]
   for k in range(n):
    node=u(buckets+k*4);steps=0
    while node and steps<1024:
     steps+=1;widget=u(node)
     if widget not in seen:
      seen.add(widget)
      if u(widget)==b+0x48e090:roots.append(widget)
     node=u(node+4)
   clocks=[]
   for root_ui in roots:
    node=u(root_ui+0x28);steps=0
    while node and steps<4096:
     steps+=1;widget=u(node)
     if u(widget)==b+0x504d88 and string(u(widget+0x1c))=='PawsDayClock':
      ve=u(widget+0x6c);clocks.append(dict(widget=widget,text=string(u(ve+0xc8))if ve else'',box=list(struct.unpack('<4f',read(ve+0x20,16)))if ve else[]))
     node=u(node+8)
   return dict(side=[w*2,height*2],climates=counts,clocks=clocks)
  finally:K.CloseHandle(handle)
 def setup(i):
  if a.manual:
   i['setupNumber']=i.get('setupNumber',0)+1;command(i,'MessageBoxButtonAction 1');stay(2);command(i,'ScreenShot');stay(1);flag=root/('ui-setup-'+str(i['setupNumber'])+'.flag');report('MANUAL_UI_READY '+str(flag));wait(lambda:flag.exists(),600,'Native UI configuration completed');return
  command(i,'MessageBoxButtonAction 1');stay(2);command(i,'Commit');stay(2);command(i,'OpenRandomMapDialog');stay(2);command(i,'Select paws_mixed_biomes');stay(2);command(i,'SelectMapSize '+('16'if a.large else'0'));stay(2)
  command(i,'!world-option Sun paws_dynamic_sun');stay(1)
  command(i,'!world-option PawsBiomes '+('paws_all'if a.large else'paws_random'));stay(1)
  command(i,'ScreenShot');stay(1);command(i,'Commit');stay(3)
  plugin=text(i['dir']/'game/Mods/plugins.log');checked('native-ui-rule-selection', 'rule=Sun value=paws_dynamic_sun index=5 panels='in plugin and 'index=5 panels=0'not in plugin and 'rule=PawsBiomes'in plugin)
 def observe(i):
  path=i['dir']/'game/Mods/pure-world.jsonl';result=[]
  for line in text(path).splitlines():
   try:r=json.loads(line)
   except ValueError:continue
   if r['tick']==r['tickAfter']and r['tick']>0:result.append(r)
  return result
'''
code=code.replace(anchor,extra+anchor,1)
start=code.index("  hd=prepare('host');cd=prepare('client');h=launch(hd);host_lobby(h);c=launch(cd,True);join(c);begin(h,c)\n  if a.client_game:");end=code.index(' except Exception as error:',start)
code=code[:start]+'''  hd=prepare('host');h=launch(hd);host_lobby(h);setup(h)
  if a.pair:
   cd=prepare('client');c=launch(cd,True)
   if a.manual:
    for body in ['RequestMultiplayer','RequestLobbyLAN','LobbySetLANNickname PawSavesClient','MessageBoxButtonAction 1','LobbyJoinDirect','JoinDirectJoin']:
     command(c,body);stay(2)
   if a.manual:report('CLIENT_UI_READY '+str(root/'client-ready.flag'));wait(lambda:(root/'client-ready.flag').exists(),600,'Client UI inspected')
   join(c)
   if a.manual:
    report('PAIR_LAUNCH_UI_READY '+str(root/'pair-launch.flag'));wait(lambda:(root/'pair-launch.flag').exists(),600,'Native pair launch completed');wait(lambda:all(snapshot(i).get('state')==2 and snapshot(i).get('world')for i in (h,c)),180,'Both peers entered match')
   else:begin(h,c)
  else:
   command(h,'StagingLaunch');wait(lambda:snapshot(h).get('state')==2 and snapshot(h).get('world'),180,'Pure mixed match started')
  wait(lambda:snapshot(h).get('taskStatus')==3 and snapshot(h).get('phase')==4,300,'Native world and interface finished loading');command(h,'GamePause 0');wait(lambda:snapshot(h).get('seconds',0)>1,45,'Simulation actually started');stay(2);initial=snapshot(h);view=details(h);write=(root/'initial.json').write_text(json.dumps(dict(world=initial,view=view),indent=2))
  checked('dynamic-sun-selected',initial['rules'].get('Sun')==5)
  checked('native-map-size',view['side']==([2048,2048]if a.large else[384,384]))
  checked('native-biomes',set(view['climates'])<={'temperate','arctic','desert'}and(len(view['climates'])==3 if a.large else 1<=len(view['climates'])<=3))
  checked('one-visible-clock',len(view['clocks'])==1 and len(view['clocks'][0]['text'])==5)
  checked('ui-runtime-active','PURE_PRESENTATION_READY'in text(hd/'game/harness-status.log'))
  command(h,'ScreenShot');stay(1);command(h,'GamePause 1');stay(2);paused=snapshot(h);before=details(h);stay(3);after=details(h);checked('pause-stops-clock',snapshot(h)['seconds']==paused['seconds']and before['clocks']==after['clocks']);checked('pause-stops-light',snapshot(h)['colors']==paused['colors']);phase=(int(paused['seconds']*16)%9600+paused['rules']['PawsDayPhase'])%9600;minutes=(phase*1440//9600+360)%1440;checked('clock-matches-lighting-phase',before['clocks'][0]['text']==('%02d:%02d'%(minutes//60,minutes%60)))
  command(h,'GamePause 0');stay(3);before=snapshot(h);stay(5);after=snapshot(h);checked('simulation-advances',after['seconds']>before['seconds']+2)
  command(h,'SpeedUp\\nSpeedUp\\nSpeedUp\\nSpeedUp');stay(2);before=snapshot(h);stay(5);after=snapshot(h);checked('game-speed-advances-native-time',after['seconds']>before['seconds']+4)
  command(h,'GameSave "Save/QA Pure050.RSG"');wait(lambda:(saves(h)/'QA Pure050.RSG').is_file()and(saves(h)/'QA Pure050.RSG').stat().st_size>1000,60,'Native beta save written');stay(3)
  if a.pair:
   stay(25);peers=[observe(i)for i in [h,c]];maps=[{(r['tick'],r['worldIndex']):r['worldCrc']for r in peer}for peer in peers];common=set(maps[0])&set(maps[1]);mismatches=[k for k in common if maps[0][k]!=maps[1][k]];(root/'checksums.json').write_text(json.dumps(dict(common=len(common),mismatches=mismatches,samples=[len(p)for p in peers]),indent=2));checked('native-peer-checksums',len(common)>=10 and not mismatches)
   checked('phase-same-on-peers',snapshot(c)['rules']['PawsDayPhase']==initial['rules']['PawsDayPhase'])
   if a.hold:report('PAIR_UI_HOLD '+str(root/'pair-continue.flag'));wait(lambda:(root/'pair-continue.flag').exists(),600,'Pair UI checks complete')
   command(c,'ReallyQuit');c['required']=False;c['process'].wait(timeout=30)
  if a.reload:
   command(h,'RequestLeaveGame');wait(lambda:snapshot(h).get('state')==1,60,'Returned normally to lobby');stay(3)
   command(h,'SelectLaunchType LOAD_SAVED_GAME');stay(3);command(h,'Commit');stay(3);command(h,'StagingLaunch');wait(lambda:snapshot(h).get('state')==2 and snapshot(h).get('world'),120,'Saved beta match loaded');wait(lambda:snapshot(h).get('taskStatus')==3 and snapshot(h).get('phase')==4,120,'Loaded native interface ready');stay(2);command(h,'GamePause 1');stay(2);loaded=snapshot(h);loadedview=details(h)
   checked('save-phase-preserved',loaded['rules']['PawsDayPhase']==initial['rules']['PawsDayPhase']and loaded['rules']['Sun']==5);checked('one-clock-after-reload',len(loadedview['clocks'])==1);checked('saved-map-size',loadedview['side']==view['side']);(root/'reloaded.json').write_text(json.dumps(dict(world=loaded,view=loadedview),indent=2))
   command(h,'RequestLeaveGame');wait(lambda:snapshot(h).get('state')==1,60,'Returned to lobby again');stay(3);command(h,'SelectLaunchType RANDOM_MAP');stay(3);setup(h);command(h,'StagingLaunch');wait(lambda:snapshot(h).get('state')==2 and snapshot(h).get('world'),120,'Second new match created');wait(lambda:snapshot(h).get('taskStatus')==3 and snapshot(h).get('phase')==4,120,'Second native interface ready');stay(2);second=details(h);checked('one-clock-in-second-new-match',len(second['clocks'])==1);(root/'second-match.json').write_text(json.dumps(dict(world=snapshot(h),view=second),indent=2));command(h,'ScreenShot');stay(1)
  if a.hold and not a.pair:
   report('QA_HOLD; create continue.flag after visual checks')
   wait(lambda:(root/'continue.flag').exists(),600,'Visual hold complete')
  command(h,'ReallyQuit');h['required']=False;h['process'].wait(timeout=30);checked('normal-exit',h['process'].returncode==0);checked('no-assert-desync',not errors())
  (root/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,runtimeHashes=expected,large=a.large,twoPeers=a.pair,automaticRecovery=False),indent=2));report('PURE_050_LIVE_PASS')
'''+code[end:]
exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source),'STOCK_AVARS':STOCK_AVARS,'re':re,'QA_MEMORY_PATH':QA_MEMORY_PATH})
