"""Owned product-runtime smoke/paired save QA; only native commands and reads."""
import argparse,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
p_emit=argparse.ArgumentParser(add_help=False);p_emit.add_argument('--emit-script',type=Path);emit,remaining=p_emit.parse_known_args();sys.argv=[sys.argv[0],*remaining]
p=argparse.ArgumentParser(add_help=False);p.add_argument('--single',action='store_true');p.add_argument('--save-file',type=Path);p.add_argument('--soak',type=int,default=70);p.add_argument('--map-side',type=int,default=384);p.add_argument('--default-map',action='store_true');p.add_argument('--diagnostic-without-presentation',action='store_true');p.add_argument('--graphics-override',type=Path);p.add_argument('--low-graphics-cache',action='store_true');p.add_argument('--commit-reserve-mib',type=int,default=5120);own,rest=p.parse_known_args();sys.argv=[sys.argv[0],*rest]
QA=dict(single=own.single,save=str(own.save_file.resolve()) if own.save_file else None,soak=own.soak,mapSide=own.map_side,diagnosticWithoutPresentation=own.diagnostic_without_presentation)
QA['out']=str(Path(rest[rest.index('--out')+1]).resolve())
QA['graphicsOverride']=str(own.graphics_override.resolve()) if own.graphics_override else None
QA['lowGraphicsCache']=own.low_graphics_cache
QA['commitReserveMiB']=own.commit_reserve_mib
voice_arg=next((i for i,x in enumerate(rest) if x=='--voice-qa'),None)
QA['voiceQa']=str(Path(rest[voice_arg+1]).resolve()) if voice_arg is not None else None
if voice_arg is not None:
 del rest[voice_arg:voice_arg+2];sys.argv=[sys.argv[0],*rest]
assert 1024<=own.commit_reserve_mib<=5120
assert not own.graphics_override or own.diagnostic_without_presentation
assert 20<=QA['soak']<=180 and 384<=QA['mapSide']<=2048
source=REPO/'game/reconnect-test/installed_saves_pair.py';code=source.read_text()
anchor="opening='Wait 45\\nRequestMultiplayer";assert code.count(anchor)==1
code=code.replace(anchor,"opening='Wait 45\\nCommit\\nWait 1\\nRequestMultiplayer")
anchor=' flag RunWhenInactive = true\\n';assert code.count(anchor)==1
code=code.replace(anchor,anchor+' flag MPRunWhenInactive = true\\n')
anchor="  (mods/'rig.txt').write_text(opening)";assert code.count(anchor)==1
code=code.replace(anchor,"  (mods/'rig.txt').write_text('Echo owned release QA ready\\n')")
anchor='  stay(8)\n  return i';assert code.count(anchor)==1
code=code.replace(anchor,'''  last_probe=[0.0]
  def menu_registered():
   if any(p.stat().st_mtime>=i['boot'] and 'connect end MainMenuInterface' in text(p) for p in (d/'game/Logs').glob('log-*.log')):return True
   if time.monotonic()-last_probe[0]>=3:
    last_probe[0]=time.monotonic();command(i,'\\n'.join('Echo owned menu readiness probe '+str(n)+' '+'x'*96 for n in range(40)))
   return False
  wait(menu_registered,90,'Native main menu interface fully registered '+d.name)
  stay(8)
  if film:
   command(i,'RequestFilm');stay(2);command(i,'Select Films/'+film);stay(2);command(i,'FilmOK Films/'+film)
  else:
   command(i,'RequestMultiplayer');stay(2);command(i,'RequestLobbyLAN');stay(2)
   command(i,'LobbySetLANNickname '+('PawSavesClient' if client else 'PawSavesHost'));stay(1);command(i,'MessageBoxButtonAction 1');stay(1)
   if client:
    command(i,'LobbyJoinDirect');stay(2);command(i,'JoinDirectJoin')
   else:
    command(i,'InternetGameCreate PawSaves 2 2');stay(2);command(i,'SelectLaunchType '+('LOAD_SAVED_GAME' if load else 'RANDOM_MAP'))
    if load:stay(2);command(i,'Commit')
  return i''')
for nickname in ['PawSavesHost','PawSavesClient']:
 anchor='LobbySetLANNickname '+nickname+'\\nWait 2\\n';assert code.count(anchor)==1
 code=code.replace(anchor,anchor+'MessageBoxButtonAction 1\\nWait 1\\n')
anchor="'--game-dir',str(d/'game')";assert code.count(anchor)==1
code=code.replace(anchor,"'--game-dir',str(d/'game')+chr(92)")
anchor="  proc=subprocess.Popen(invocation,cwd=d/'game',env=env,stdout=handle,stderr=subprocess.STDOUT)";assert code.count(anchor)==1
code=code.replace(anchor,'  boot=time.time()\n'+anchor)
anchor='  owned.append(i)';assert code.count(anchor)==1
code=code.replace(anchor,"  i['boot']=boot\n"+anchor)
anchor="  i['seq']+=1;mods=i['dir']/'game/Mods';n=i['seq']";assert code.count(anchor)==1
code=code.replace(anchor,"  mods=i['dir']/'game/Mods';i['seq']=max(i['seq'],int((mods/'rig-command.txt').read_text().strip() or '0'))+1;n=i['seq']")
anchor="  report(i['dir'].name+' request '+str(n)+': '+body.replace('\\n','; '))";assert code.count(anchor)==1
code=code.replace(anchor,"  report(i['dir'].name+' request '+str(n)+': '+('Echo menu readiness probe (40 lines)' if body.startswith('Echo owned menu readiness probe ') else body.replace('\\n','; ')))")
anchor="   wait(lambda:sum(text(f).count('NetEvent Push: END_OF_FILM') for f in (d/'game/Logs').glob('log-*.log'))>prior,180,'Fresh film completed')";assert code.count(anchor)==1
code=code.replace(anchor,'''   film_probe=[0.0]
   def film_finished():
    if sum(text(f).count('NetEvent Push: END_OF_FILM') for f in (d/'game/Logs').glob('log-*.log'))>prior:return True
    if time.monotonic()-film_probe[0]>=3:
     film_probe[0]=time.monotonic();command(i,'\\n'.join('Echo owned menu readiness probe film '+str(n)+' '+'x'*96 for n in range(40)))
    return False
   wait(film_finished,180,'Fresh film completed')''')
if QA['voiceQa']:
 anchor="  proc=subprocess.Popen(invocation,cwd=d/'game',env=env,stdout=handle,stderr=subprocess.STDOUT)";assert code.count(anchor)==1
 code=code.replace(anchor,"  if QA['voiceQa']:invocation=['C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe',QA['voiceQa'],'launch',str(d/'game'),a.arcane_qa.name,'B' if client else 'A','--test-profile='+str(d/'appdata/launcher-voice')]\n"+anchor)
 anchor="  if a.arcane_qa:\n   status='\\n'.join(text(f) for f in (d/'game').glob('*status.txt'))";assert code.count(anchor)==1
 code=code.replace(anchor,'''  if QA['voiceQa']:
   wait(lambda:'OWNED_PRODUCT_FACTION_READY' in text(i['output']),55,'Production speech runtime ready '+d.name)
   checked('faction-runtime-ready-'+d.name,True)
'''+anchor)
anchor="  shutil.copy2(loader,game/'avifil32.dll');shutil.copy2(a.artifacts/'native/shfolder.dll',game/'shfolder.dll')";assert code.count(anchor)==1
code=code.replace(anchor,anchor+"\n  if QA['graphicsOverride']:shutil.copy2(QA['graphicsOverride'],game/'d3d9.dll')")
# MEMORYSTATUSEX.ullAvailPageFile is process-limited, not system free commit.
# https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/ns-sysinfoapi-memorystatusex
start=code.index('def resource_guard():');end=code.index('sha=lambda',start)
code=code[:start]+'''class SystemPerformance(C.Structure):
 _fields_=[('cb',C.c_ulong)]+[(n,C.c_size_t) for n in ('commit','limit','peak','physTotal','physFree','sysCache','kernelTotal','kernelPaged','kernelNonPaged','pageSize')]+[(n,C.c_ulong) for n in ('handles','processes','threads')]
PS=C.WinDLL('psapi',use_last_error=True);PS.GetPerformanceInfo.argtypes=[C.POINTER(SystemPerformance),C.c_ulong]
import memory_snapshot
def resource_guard():
 status=MemoryStatus();status.length=C.sizeof(status)
 if not K.GlobalMemoryStatusEx(C.byref(status)):raise C.WinError(C.get_last_error())
 system=SystemPerformance();system.cb=C.sizeof(system)
 if not PS.GetPerformanceInfo(C.byref(system),C.sizeof(system)):raise C.WinError(C.get_last_error())
 free=(system.limit-system.commit)*system.pageSize
 row=dict(utc=time.time(),physicalMiB=status.availPhys//2**20,processCommitAvailableMiB=status.availPage//2**20,globalCommitAvailableMiB=free//2**20,globalLimitMiB=system.limit*system.pageSize//2**20)
 row.update(memory_snapshot.snapshot(QA['out']))
 with (Path(QA['out'])/'memory-guard.jsonl').open('a') as f:f.write(json.dumps(row)+'\\n')
 if status.availPhys<3*1024**3 or free<QA['commitReserveMiB']*1024**2 or status.availPage<512*1024**2:
  raise RuntimeError('Owned QA memory reserve reached: '+json.dumps(row))
''' +code[end:]
anchor=' flag SinglePlayerAutoPause = false\\n';assert code.count(anchor)==1
if not own.default_map:code=code.replace(anchor,anchor+' string StagingMultiPlayerDefaultRMCIds = paws_mixed_biomes\\n int StagingMultiPlayerDefaultRMCWidth = '+str(own.map_side)+'\\n int StagingMultiPlayerDefaultRMCHeight = '+str(own.map_side)+'\\n')
if own.low_graphics_cache:
 code=code.replace(anchor,anchor+' int ResourceCacheTextureRAMWeight = 5\\n int ResourceCacheTextureVRAMWeight = 5\\n flag ViewShadows = false\\n')
anchor="   if controller:result['paused']=any(read(controller+0x28,2))";assert code.count(anchor)==1
voice_reader='''   if QA['voiceQa']:
    meta=json.loads((Path('VOICE_META_PATH')).read_text());site=b+meta['site'];call=read(site,5)
    if call[0]==0xe8:
     entry=(site+5+struct.unpack('<i',call[1:])[0])&0xffffffff;speech=entry-meta['entry']+meta['state']
     values=struct.unpack('<13I',read(speech,52))
     if values[0]==0x56574346:result['speech']=dict(languages=list(values[2:8]),calls=values[8],switched=values[9],lastFaction=values[10],lastLanguage=values[11])
'''.replace('VOICE_META_PATH',(REPO/'src/PawsPatchLauncher/Assets/FactionVoices.json').as_posix())
code=code.replace(anchor,'''   if world:
    tick=u(world+0xe4);ws=u(b+0x5f3ff4);net=u(b+0x5f3ff0)
    if ws and net:
     fields=(u(ws+0x14),u(ws+8),u(net+0x14),u(net+8))
     if fields==(u(ws+0x14),u(ws+8),u(net+0x14),u(net+8)) and tick==u(world+0xe4):
      result.update(worldTick=tick,worldIndex=fields[0],worldCrc=fields[1],netIndex=fields[2],netCrc=fields[3])
'''+voice_reader+anchor)
start=code.index('  if a.arcane_qa:\n   hd=prepare(\'host\');cd=prepare(\'client\');h=launch(hd);host_lobby(h);c=launch(cd,True);join(c)')
end=code.index("  hd=prepare('host');cd=prepare('client');h=launch(hd);host_lobby(h);c=launch(cd,True);join(c);begin(h,c)\n  if a.client_game:",start)
scenario='''  if a.arcane_qa:
   original=Path(QA['save']) if QA['save'] else None
   hd=prepare('host',save=original);h=launch(hd,load=bool(original));host_lobby(h,load=bool(original));peers=[h]
   if not QA['single']:
    cd=prepare('client');c=launch(cd,True);join(c);peers.append(c);begin(h,c)
   else:
    command(h,'StagingLaunch');wait(lambda:snapshot(h).get('state')==2 and snapshot(h).get('world'),90,'Product match entered simulation')
   command(h,'GamePause 0');stay(3);before=[snapshot(i) for i in peers];samples=[];until=time.monotonic()+QA['soak']
   while time.monotonic()<until:
    check_alive();samples.append([snapshot(i) for i in peers]);time.sleep(.1)
   after=[snapshot(i) for i in peers]
   if QA['voiceQa']:
    expected_speech=[[3,0,2,1,0,1]]+([[2,1,3,0,3,0]] if len(peers)==2 else [])
    checked('native-personal-speech-state',all(s.get('speech',{}).get('languages')==languages for s,languages in zip(after,expected_speech)))
   checked('simulation-advances',all(y.get('seconds',0)>x.get('seconds',0)+QA['soak']*.5 for x,y in zip(before,after)))
   if len(peers)==2:
    observed=[];unstable=[]
    for n in range(2):
     values={};bad=set()
     for row in samples:
      s=row[n]
      if not all(k in s for k in ('worldIndex','worldCrc','netIndex','netCrc')):continue
      key=(s['worldIndex'],s['netIndex']);value=(s['worldCrc'],s['netCrc'])
      if key in values and values[key]!=value:bad.add(key)
      values[key]=value
     observed.append({k:v for k,v in values.items() if k not in bad});unstable.append(list(bad))
    common=set(observed[0])&set(observed[1]);different=[k for k in common if observed[0][k]!=observed[1][k]]
    (root/'native-crc.json').write_text(json.dumps(dict(common=len(common),different=different,unstableSnapshots=unstable,checks=[dict(worldIndex=k[0],netIndex=k[1],host=observed[0][k],client=observed[1][k]) for k in sorted(common)],scope='stable read-only snapshots keyed by shared native world/net indices; no checksum hooks'),indent=2))
    checked('native-shared-crc',len(common)>=10 and not different)
   (root/'simulation.json').write_text(json.dumps(dict(before=before,after=after,samples=samples),indent=2))
   command(h,'GamePause 1');stay(3);command(h,'GameSave "Save/QA Arcane051.RSG"')
   wait(lambda:(saves(h)/'QA Arcane051.RSG').is_file() and (saves(h)/'QA Arcane051.RSG').stat().st_size>1000,45,'Product host save written')
   stay(4);checked('save-written',(saves(h)/'QA Arcane051.RSG').stat().st_size>1000)
   command(h,'ScreenShot');stay(2)
   for i in reversed(peers):
    command(i,'ReallyQuit');i['required']=False;i['process'].wait(timeout=30);checked('normal-exit-'+i['dir'].name,i['process'].returncode==0)
   checked('no-assert-desync',not errors())
   for i in peers:
    status='\\n'.join(text(f) for f in (i['dir']/'game').glob('*status*.txt'))
    if not QA['diagnosticWithoutPresentation']:checked('product-runtime-ready-'+i['dir'].name,'PRESENTATION_READY revision=1' in status)
   (root/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,publicRuntimeHashes=expected,seconds=QA['soak'],loadedSave=QA['save'],environment='owned native processes; private path/profile startup adapter, exact product runtime DLL/resources'),indent=2));report('PASS combined product runtime and native save');return
'''
code=code[:start]+scenario+code[end:]
if emit.emit_script:
 compile(code,str(emit.emit_script),'exec');emit.emit_script.write_text(code,encoding='utf-8');print('OWNED_QA_SCRIPT_COMPILED; no game started');sys.exit(0)
generated=Path(QA['out']).with_suffix('.runner.py');generated.write_text(code,encoding='utf-8')
exec(compile(code,str(generated),'exec'),{'__name__':'__main__','__file__':str(source),'QA':QA})
