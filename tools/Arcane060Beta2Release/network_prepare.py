from context import *
import shutil
NET=Path('G:/PawsWork/QA/Arcane060Beta2Net-20261115');D=P/'net';D.mkdir(exist_ok=True);NET.mkdir(exist_ok=True)
def prepare_sources():
 old=WS/'work/rivers-r17-network-20261111/source'
 s=(old/'control.py').read_text().replace("N=Path(__file__).resolve().parents[1];W=N.parent;ROLES=('host','client','witness');PORT=6097",f"N=Path({str(NET)!r});W=Path({str(WS/'work')!r});ROLES=('host','client','witness');PORT=6115")
 s=s.replace("return W/f'rivers-r17-{role}-20261111'",f"return Path({str(FIX)!r}) if role=='host' else N/role")
 s=s.replace("/'sandbox'","/'game'").replace("'sandbox/","'game/").replace('PawsInstalledRuntime.exe','k2_paws_family_herd_relations_1372.exe').replace('pawsinstalledruntime.exe','k2_paws_family_herd_relations_1372.exe')
 s=s.replace("for f in ('k2.exe','k2_paws_family_herd_relations_1372.exe')","for f in ('k2.exe','k2_paws_family_herd_relations_1372.exe','TestInstalledRuntime.exe')").replace("('k2.exe','k2_paws_family_herd_relations_1372.exe'):","('k2.exe','k2_paws_family_herd_relations_1372.exe','testinstalledruntime.exe'):")
 s=s.replace("helper=r/'game/k2_paws_family_herd_relations_1372.exe'","helper=r/'game/TestInstalledRuntime.exe'")
 (D/'control.py').write_text(s)
 for name in ['memory.py','checksums.py']:(D/name).write_text((old/name).read_text().replace("'sandbox/","'game/"))
 match=(old/'match.py').read_text().replace('!port 6097','!port 6115').replace('RiversPrivate','ArcaneBeta2Private').replace('RiversHost','Beta2Host').replace('RiversClient','Beta2Client').replace('RiversThird','Beta2Third');(D/'match.py').write_text(match)
 src=WS/'work/launcher-104-release/outputs/pure-041-050-20261109/qa-rig-r3/rig_input.c';s=src.read_text();(D/'rig_input.c').write_text('#include <string.h>\n'+s)
 cc=WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe';run([cc,'-shared','-Wall','-Werror',D/'rig_input.c','-o',D/'rig_input.dll','-lkernel32'])
 shutil.copy2(PREV/'PawsNetworkQA.dll',D/'PawsNetworkQA.dll');write(O/'network-tooling.json',dict(inputOnly=True,noSimulationBypass=True,sources={str(D/'rig_input.c'):sha(D/'rig_input.c')},officialSync=True))
 # The public helper intentionally rejects another k2 anywhere on the machine.
 # This QA-only helper scopes that guard to its own isolated game path, as in
 # the previously accepted three-peer harness. All embedded payloads are exact.
 row=read(O/'helpers/build-report.json')['k2_paws_family_herd_relations_1372.exe'];source=O/'helpers/source/k2_paws_family_herd_relations_1372.exe.generated.cs';code=source.read_text();old='Process[] running = Process.GetProcessesByName("k2");';assert code.count(old)==1
 replacement='Process[] running = Process.GetProcessesByName("k2").Where(p => { try { return String.Equals(p.MainModule.FileName, gamePath, StringComparison.OrdinalIgnoreCase); } catch { return false; } }).ToArray();';qa=D/'QA.generated.cs';qa.write_text(code.replace(old,replacement));args=[]
 startup=O/'helpers/source/22-ReleaseStartup.cs';startup_code=startup.read_text();old_wait='Process[] games = Process.GetProcessesByName("k2");';assert startup_code.count(old_wait)==1
 wait_code='Process[] games = Array.FindAll(Process.GetProcessesByName("k2"), p => { try { return String.Equals(p.MainModule.FileName, expectedPath, StringComparison.OrdinalIgnoreCase); } catch { return false; } });';qa_startup=D/'QA.ReleaseStartup.cs';qa_startup.write_text(startup_code.replace(old_wait,wait_code))
 for arg in row['args']:
  if arg.startswith('/out:'):arg='/out:'+str(D/'TestInstalledRuntime.exe')
  elif arg==str(source):arg=str(qa)
  elif arg==str(startup):arg=str(qa_startup)
  args.append(arg)
 run(args);expected=row['features'];actual=json.loads(run([D/'TestInstalledRuntime.exe','--features']));assert actual==expected;write(O/'network-helper.json',dict(qaOnly=True,sourceLinesChanged=2,change='Scope the two launch/child identity single-instance checks to the exact owned game path, matching the accepted R17 harness',productionHelperSha256=row['sha256'],qaHelperSha256=sha(D/'TestInstalledRuntime.exe'),featuresUnchanged=True,embeddedResourcesUnchanged=True))
def peers():
 sys.path.insert(0,str(D));import control
 assert not control.own();GAME=FIX/'game';state=read(GAME/'.pawpatch/state.json');settings=state['appliedSettings'];assert settings['desyncMode']=='official'and not settings['customPlayerColors'];assert state['modules']['pawpatch-core']['version']==VERSION
 paths={r['path'].replace('\\','/').lower():r['path']for v in state['modules'].values()if v['enabled']for r in v['files']}
 for f in GAME.iterdir():
  if f.is_file()and(f.name.lower()in ['k2.exe','data.rwd','music.rwd','steam_appid.txt','paws_presentation.ini','paws_game_text.ini','paws_player_colors.ini','paws_launch_versions.ini','paws_patch_versions.ini']or f.suffix.lower()=='.dll'):paths.setdefault(f.name.lower(),f.name)
 for f in(GAME/'mss').rglob('*'):
  if f.is_file():paths.setdefault(f.relative_to(GAME).as_posix().lower(),f.relative_to(GAME).as_posix())
 for role in ['client','witness']:
  root=NET/role;game=root/'game'
  if game.exists():
   marker=read(root/'fixture-owner.json');assert marker['owner']=='Arcane 0.6.0 beta.2 release QA'and marker['source']==str(GAME);continue
  game.mkdir(parents=True);(root/'Temp').mkdir();(root/'AppData').mkdir();(root/'native').mkdir();shutil.copy2(FIX/'native/prototype.json',root/'native/prototype.json')
  for i,rel in enumerate(paths.values()):
   src=GAME/rel;dst=game/rel;assert src.is_file(),rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
   if i%4000==0:print('PEER_COPY',role,i,'/',len(paths),flush=True)
  (game/'.pawpatch').mkdir(exist_ok=True);shutil.copy2(GAME/'.pawpatch/state.json',game/'.pawpatch/state.json');write(root/'fixture-owner.json',dict(owner='Arcane 0.6.0 beta.2 release QA',source=str(GAME),baseArchives='Independent copies',files=len(paths)))
 for role in control.ROLES:
  root=control.folder(role);game=root/'game';mods=game/'Mods';normal=(mods/'plugins.txt').read_bytes();assert len(normal.decode().splitlines())==9
  (root/'qa-evidence').mkdir(exist_ok=True);(root/'qa-evidence/beta2-normal-plugins.txt').write_bytes(normal)
  user=root/'Documents/Kohan2/data/User';user.mkdir(parents=True,exist_ok=True);u=user/'UVars.tgi'
  if u.exists():shutil.copy2(u,root/'qa-evidence/beta2-user-before.tgi')
  u.write_text('[Vars]\n{\n int ResolutionX = 800\n int ResolutionY = 450\n flag ResolutionWindowed = true\n flag ResolutionCoopFullscreenMode = false\n flag MouseClipCursor = false\n flag RunWhenInactive = true\n flag SinglePlayerAutoPause = false\n flag FirstRun = false\n float AudioMainVolume = 0\n float AudioMusicVolume = 0\n float FrameRateLimit = 20\n string StagingMultiPlayerDefaultRMCIds = paws_mixed_biomes\n int StagingMultiPlayerDefaultRMCWidth = 640\n int StagingMultiPlayerDefaultRMCHeight = 640\n}\n')
  for name in ['network-test.marker','reconnect-test.marker']:(game/name).write_text('Owned three-peer Arcane beta2 QA\n')
  shutil.copy2(R/'sandbox/shfolder.dll',game/'shfolder.dll')
  for name in ['PawsNetworkQA.dll','rig_input.dll']:shutil.copy2(D/name,mods/name)
  shutil.copy2(D/'TestInstalledRuntime.exe',game/'TestInstalledRuntime.exe')
  (mods/'plugins.txt').write_bytes(normal+b'rig_input.dll\nPawsNetworkQA.dll\n')
  for p in [root/'Documents/Kohan2/data/Save',root/'qa-evidence/sessions']:p.mkdir(parents=True,exist_ok=True)
  for row in read(LOSS/'packed.json'):assert sha(game/Path(row['path']).name)==row['sha256'].upper()
 write(O/'network-peers.json',dict(passed=True,roles={r:str(control.folder(r))for r in control.ROLES},officialSync=True,normalModuleCount=9,testModuleCount=2,archiveHashes={Path(r['path']).name:r['sha256']for r in read(LOSS/'packed.json')}));print('THREE_OFFICIAL_BETA2_PEERS_READY',flush=True)
if __name__=='__main__':prepare_sources()if sys.argv[1]=='sources'else peers()
