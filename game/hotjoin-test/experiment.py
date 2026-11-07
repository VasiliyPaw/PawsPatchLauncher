"""Owned, isolated 1.3.72 admission experiment. Never writes an installation.

This is a research driver, not the shipping reconnect implementation. Retains
failed runs and process identity; native assertions and desync handling stay on.
"""
import argparse, ctypes as C, hashlib, json, os, re, shutil, struct, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]
STOCK_HASH = '1eb79bbb678668be5a05f8c98103cd9988048490ce7c53c74c9a1d0813e9cd45'
COMPILER = WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
LOADER = WS/'outputs/reconnect-build-20261013/probe/avifil32.dll'
SHFOLDER = WS/'outputs/full-patch-network-20261025/artifacts/native/shfolder.dll'
JOIN_INPUT = WS/'outputs/full-patch-network-20261025/artifacts/rig_input.dll'
STOCK = Path('D:/PawsMultiplayerRig/game')
K = C.WinDLL('kernel32', use_last_error=True)
N = C.WinDLL('ntdll')
K.CreateJobObjectW.restype = C.c_void_p
K.SetInformationJobObject.argtypes = [C.c_void_p,C.c_int,C.c_void_p,C.c_ulong]
K.AssignProcessToJobObject.argtypes = [C.c_void_p,C.c_void_p]
K.TerminateJobObject.argtypes = [C.c_void_p,C.c_uint]
K.CloseHandle.argtypes = [C.c_void_p]
K.OpenProcess.argtypes=[C.c_ulong,C.c_int,C.c_ulong];K.OpenProcess.restype=C.c_void_p
K.GetExitCodeProcess.argtypes=[C.c_void_p,C.c_void_p];K.TerminateProcess.argtypes=[C.c_void_p,C.c_uint]
K.IsProcessInJob.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p]
K.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p]
N.NtResumeProcess.argtypes = [C.c_void_p]
N.NtSuspendProcess.argtypes = [C.c_void_p]
class Basic(C.Structure):
    _fields_=[('processTime',C.c_longlong),('jobTime',C.c_longlong),('flags',C.c_ulong),('min',C.c_size_t),('max',C.c_size_t),('active',C.c_ulong),('affinity',C.c_size_t),('priority',C.c_ulong),('scheduling',C.c_ulong)]
class Io(C.Structure):
    _fields_=[(n,C.c_ulonglong) for n in ('read','write','other','readBytes','writeBytes','otherBytes')]
class Limits(C.Structure):
    _fields_=[('basic',Basic),('io',Io),('processMemory',C.c_size_t),('jobMemory',C.c_size_t),('peakProcess',C.c_size_t),('peakJob',C.c_size_t)]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
class OwnedChild:
    def __init__(self,pid):
        self.pid=pid;self._handle=K.OpenProcess(0x1fffff,False,pid);self.returncode=None
        if not self._handle:raise C.WinError(C.get_last_error())
    def poll(self):
        code=C.c_ulong()
        if not K.GetExitCodeProcess(self._handle,C.byref(code)):raise C.WinError(C.get_last_error())
        self.returncode=None if code.value==259 else code.value
        return self.returncode
    def wait(self,timeout=15):
        until=time.monotonic()+timeout
        while self.poll() is None:
            if time.monotonic()>until:raise subprocess.TimeoutExpired(str(self.pid),timeout)
            time.sleep(.1)
        return self.returncode
    def terminate(self):
        if not K.TerminateProcess(self._handle,125):raise C.WinError(C.get_last_error())
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--mode',choices=['baseline','admission-only','snapshot','coordinated'],default='baseline')
    ap.add_argument('--observe',type=int,default=40)
    ap.add_argument('--world-options',action='store_true',help='Observe dynamic Sun and random mixed biomes in an owned composed beta fixture')
    ap.add_argument('--manual-world-setup',action='store_true',help='Hold the owned lobby for agent UI setup, then continue after continue-setup.flag')
    ap.add_argument('--port',type=int,default=5860,help='Private local host port; permits independent owned test sessions')
    ap.add_argument('--cached-snapshot',action='store_true',help='Development only: stage identical checkpoint in isolated client cache; cold transfer must also pass separately')
    ap.add_argument('--scenario',choices=['visitor','return','impostor'],default='visitor')
    ap.add_argument('--leave-mode',choices=['crash','menu'],default='crash')
    ap.add_argument('--automatic',action='store_true',help='Connection requests fresh checkpoint and restores the pre-admission pause state')
    ap.add_argument('--prepaused',action='store_true',help='Test player pauses before the late connection; that pause must survive joining')
    ap.add_argument('--join-unpaused',action='store_true',help='With continue-without, leave the resumed match running when the former owner returns')
    ap.add_argument('--repeat-plan',default='',help='Additional returns in the same match, e.g. client,client,witness,host,client; host means the current native host')
    ap.add_argument('--interval',type=int,default=60,help='Seconds of actual simulation between repeated returns (minimum 60)')
    ap.add_argument('--simultaneous',choices=['return','observer'],help='Connect the two departed owners together, or a returning owner together with a new observer')
    ap.add_argument('--reuse-client',action='store_true',help='Return after normal menu exit in the SAME game process; no restart/profile copy')
    ap.add_argument('--stock-transfer',action='store_true',help='A/B measurement only: leave native transfer pacing; retain the exact-block boundary fix')
    ap.add_argument('--fixture-transfer',type=Path,help='Only transfer this preserved lab RSG through the native lobby; no world launch or hot-join claim')
    ap.add_argument('--game-source',type=Path,help='Read-only source for a complete private game copy')
    ap.add_argument('--composed-helper',type=Path,help='Hash-pinned private startup adaptation of archived Arcane helper')
    ap.add_argument('--initial-save',type=Path,help='Copy a preserved lab/user-save fixture into the host only and launch it natively')
    ap.add_argument('--replay-film',type=Path,help='Read-only preserved owned film fixture; playback in one fresh private game')
    ap.add_argument('--replay-saves',type=Path,help='Owned snapshot directory needed by the preserved film')
    ap.add_argument('--startup-only',action='store_true',help='Composition preflight only: launch one owned game to menu, then close it without a LAN socket')
    ap.add_argument('--test-capture-timeout',type=int,default=0,help='Owned failure-injection deadline, 5000..120000 ms; normal default remains 120 s')
    ap.add_argument('--test-host-exit',choices=['crash','menu'],default='crash',help='Owned interrupted-admission host loss injection')
    ap.add_argument('--edge-case',choices=['cancel-capture','cancel-saved','cancel-transfer','cancel-load','timeout-transfer','timeout-load','batch-loss','host-transfer','host-partial-transfer','host-load','manual-pause','manual-resume','duplicate','reject-protocol','reject-password','save-roundtrip','save-during-join','observer-host','finish-during-join'],help='Private failure/lifecycle scenario, with separate acceptance')
    ap.add_argument('--witness',action='store_true',help='Three human participants; a third owned copy stays connected during departure and return (experimental protocol 3)')
    ap.add_argument('--second-witness',action='store_true',help='Fourth original human; two original peers survive coordinator loss during admission')
    ap.add_argument('--release-observer',action='store_true',help='Observe packaged runtime; no experimental hot-join implementation installed by fixture')
    ap.add_argument('--depart',choices=['client','host'],default='client',help='Host departure requires three participants; native election must select a remaining peer')
    ap.add_argument('--uncleared',action='store_true',help='Keep the original disconnected participant in native connection status; driver never votes Delete')
    ap.add_argument('--continue-without',action='store_true',help='After asserting the departure pause, explicitly resume without the departed peer, then pause before rejoining')
    ap.add_argument('--double-drop',action='store_true',help='Two of three participants leave; one remains, then both return sequentially')
    ap.add_argument('--control-orders',action='store_true',help='Require returning owners to execute normal Sally/Recall commands; observe native command availability changing')
    locales=json.loads((HERE/'localization.json').read_text(encoding='utf-8'))
    assert set(locales)=={'en','ru','de','fr','cs','uk'}
    for language,entries in locales.items():
        assert set(entries)==set(locales['en']), 'Missing role-notice translation: '+language
        for key,value in entries.items():
            assert ''.join(re.findall(r'%([sd])',value))==key.split('|')[1] and '%' not in re.sub(r'%[sd]','',value), 'Unsafe native format placeholders: '+language+' '+key
    ap.add_argument('--language',choices=sorted(locales),default='en')
    a=ap.parse_args(); root=a.out.resolve()
    if root.exists(): raise ValueError('Fresh output required')
    assert sha(STOCK/'k2.exe')==STOCK_HASH
    assert sha(HERE/'FastTransferR2Source.cs')==sha(HERE.parent/'fast-transfer/FastTransfer.cs'),'Regenerate R2 export from current lobby source'
    assert sha(HERE/'FastTransferR2Source.cs') in (HERE/'r2_payload.h').read_text(),'R2 payload/source mismatch'
    root.mkdir(parents=True); native=root/'native'; native.mkdir()
    shutil.copytree(HERE,root/'source',ignore=shutil.ignore_patterns('__pycache__'))
    subprocess.run([str(COMPILER),'-shared','-Wall','-Werror',*(['-DPAWS_HOTJOIN_MONITOR'] if a.release_observer else []),str(HERE/'lab.c'),'-o',str(native/'hotjoin_lab.dll'),'-lkernel32'],check=True)
    binary=(native/'hotjoin_lab.dll').read_bytes()
    assert struct.unpack_from('<H',binary,struct.unpack_from('<I',binary,60)[0]+4)[0]==0x14c, 'x86 game requires x86 plugin'
    inputs={str(p):sha(p) for p in [*sorted(p for p in HERE.iterdir() if p.is_file()),LOADER,SHFOLDER,JOIN_INPUT,STOCK/'k2.exe']}
    (root/'inputs.json').write_text(json.dumps(inputs,indent=2))
    assert 5000<=a.port<=65000
    peers={}; events=[]; processes=[];helper_processes=[];expected_exits=set();log_read_retries=[];join_address='127.0.0.1:'+str(a.port)
    if a.second_witness:assert a.witness and a.edge_case in ('host-transfer','host-partial-transfer','host-load') and a.depart=='client' and not a.double_drop and not a.repeat_plan
    if a.release_observer:assert a.composed_helper and (a.startup_only or a.edge_case=='host-partial-transfer' or a.world_options)
    if a.depart=='host':assert a.witness and a.scenario=='return', 'Host migration needs a three-human return scenario'
    if a.uncleared:assert a.leave_mode=='crash' and a.automatic and a.witness, 'Uncleared experiment requires three peers, automatic return and crash'
    if a.continue_without:assert not a.uncleared and a.scenario!='visitor', 'Continue-without requires a resolved departure'
    if a.join_unpaused:assert a.continue_without and not a.double_drop and not a.prepaused, 'Unpaused return requires one resolved departure and explicit continue-without'
    if a.double_drop:assert a.witness and a.automatic and a.scenario=='return', 'Double departure requires three-human automatic return'
    if a.repeat_plan:assert a.witness and a.automatic and a.scenario=='return' and not a.double_drop and a.interval>=60 and all(p in ('host','client','witness') for p in a.repeat_plan.split(',')), 'Repeated returns need three peers, valid roles and at least a minute of simulation'
    if a.simultaneous:assert a.witness and a.automatic and a.scenario=='return' and not a.repeat_plan and (a.double_drop if a.simultaneous=='return' else not a.double_drop), 'Simultaneous return needs double-drop; simultaneous observer needs one departure'
    if a.reuse_client:assert a.leave_mode=='menu' and a.scenario=='return' and a.depart=='client' and not a.double_drop and not a.repeat_plan, 'Same-process return needs a single ordinary client departure'
    if a.fixture_transfer:assert a.mode=='coordinated' and a.scenario=='return' and not a.witness and a.fixture_transfer.is_file(), 'Transfer-only fixture needs two owned lobby peers and a lab RSG'
    def report(s):
        events.append(dict(at=time.time(),text=s)); print(s,flush=True)
        (root/'events.json').write_text(json.dumps(events,indent=2))
    def prepare(role,dirname=None):
        source=a.game_source.resolve() if a.game_source else STOCK
        assert sha(source/'k2.exe')==STOCK_HASH
        def omit(folder,names):
            if Path(folder).name=='.pawpatch':return [n for n in names if n not in ('state.json','native')]
            if Path(folder).name.lower()=='mods':
                return [n for n in names if n.startswith(('lab-','rig-request-','rig-command.','hotjoin-helper-ready.'))]
            return shutil.ignore_patterns('Logs','PawsRig','.rig-running.lock','.pawpatch-tests','Paw Backups','Paw Hotkey Backups','Бекап','Файлы','*.log','*status*.txt','hotjoin-helper-ready.marker')(folder,names)
        def copy_input(src,dst):
            f=Path(src)
            if f.parent==source and f.name.lower() in ('data.rwd','music.rwd'):
                digest=sha(f);cache=Path('G:/PawHotJoinSharedArchives-20261107');cache.mkdir(exist_ok=True)
                archive=cache/(digest+'-'+f.name)
                if not archive.exists():shutil.copy2(f,archive)
                assert sha(archive)==digest,'Owned shared archive cache changed'
                if Path(dst).anchor.lower()==archive.anchor.lower():os.link(archive,dst)
                else:shutil.copy2(archive,dst)
                return str(dst)
            return shutil.copy2(src,dst)
        d=root/(dirname or role); g=d/'game'; shutil.copytree(source,g,ignore=omit,copy_function=copy_input)
        # Fixture itself has no user mods; explicit custom startup uses stock data.
        mods=g/'Mods'; mods.mkdir(exist_ok=True)
        (g/'hotjoin-lab.marker').write_text('Paw hot-join lab; not for installed game\n')
        (g/'reconnect-test.marker').write_text('Private hot-join research\n')
        for src,dst in [(LOADER,g/'avifil32.dll'),(SHFOLDER,g/'shfolder.dll'),(JOIN_INPUT,mods/'rig_input.dll'),(native/'hotjoin_lab.dll',mods/'hotjoin_lab.dll')]: shutil.copy2(src,dst)
        (mods/'plugins.txt').write_text('rig_input.dll\nhotjoin_lab.dll\n')
        (mods/'rig.txt').write_text('Echo hotjoin lab boot\n')
        if not a.game_source:(g/'startup/autoexec.txt').write_text('adddepot Data.rwd\nadddepot data/\nadddepot Music.rwd\nadddepot %USERDATA%/data/ 1\n')
        locale=g/'data/Localization/paws_hotjoin.tgi';locale.parent.mkdir(parents=True,exist_ok=True)
        locale.write_text('[Text language=default]\n{\n ids = Localization/paws_hotjoin.tgi\n name = "@Localization/paws_hotjoin.tgi"\n'+''.join(' '+key+' = '+json.dumps(value,ensure_ascii=False)+'\n' for key,value in locales[a.language].items())+'}\n',encoding='utf-16')
        docs=d/'Documents'; user=docs/'Kohan2/data/User'; user.mkdir(parents=True)
        (docs/'Kohan2/data/Save').mkdir()
        if role=='host' and a.replay_film:
            films=docs/'Kohan2/data/Films';films.mkdir();shutil.copy2(a.replay_film,films/'HotJoinReplay.RFM')
            if a.replay_saves:shutil.copytree(a.replay_saves,docs/'Kohan2/data/Save',dirs_exist_ok=True)
        if role=='host' and a.initial_save:shutil.copy2(a.initial_save,docs/'Kohan2/data/Save/HotJoinBoundary.RSG')
        (user/'UVars.tgi').write_text('[Vars]\n{\n int ResolutionX = 800\n int ResolutionY = 600\n flag ResolutionWindowed = true\n flag ResolutionCoopFullscreenMode = false\n flag MouseClipCursor = false\n flag RunWhenInactive = true\n flag SinglePlayerAutoPause = false\n flag FirstRun = false\n float AudioMainVolume = 0\n float FrameRateLimit = 30\n}\n')
        if a.world_options:
            p=user/'UVars.tgi';p.write_text(p.read_text().replace('}\n',' string StagingMultiPlayerDefaultRMCIds = paws_mixed_biomes\n int StagingMultiPlayerDefaultRMCWidth = 1280\n int StagingMultiPlayerDefaultRMCHeight = 1280\n}\n'))
        peers[role]=dict(root=d,game=g,docs=docs,serial=0)
        return peers[role]
    limits=Limits(); limits.basic.flags=0x2000
    job=K.CreateJobObjectW(None,None)
    if not job or not K.SetInformationJobObject(job,9,C.byref(limits),C.sizeof(limits)):raise C.WinError(C.get_last_error())
    def launch(role):
        p=peers[role]; env=os.environ.copy()
        env.update(SteamAppId='97130',SteamGameId='97130',PAWS_TEST_DOCUMENTS=str(p['docs']),PAWS_RIG_EXTERNAL_SCRIPT='1',PAWS_HOTJOIN_LAB=a.mode)
        env['PAWS_HOTJOIN_AUTO']='1' if a.automatic else '0'
        env['PAWS_HOTJOIN_MULTI']='1' if a.witness else '0'
        env['PAWS_HOTJOIN_RECOVER']='1' if a.uncleared or a.double_drop else '0'
        env['PAWS_HOTJOIN_CONTROL']='1' if a.control_orders else '0'
        env['PAWS_HOTJOIN_FAST']='0' if a.stock_transfer else '1'
        env['PAWS_TEST_APPDATA']=str(p['root']/'AppData')
        env['PAWS_HOTJOIN_COMPOSED']='1' if a.composed_helper else '0'
        env['PAWS_HOTJOIN_TEST_LEGACY']='1' if p.get('testLegacyProtocol') else '0'
        if a.test_capture_timeout:env['PAWS_HOTJOIN_TEST_CAPTURE_TIMEOUT_MS']=str(a.test_capture_timeout)
        else:env.pop('PAWS_HOTJOIN_TEST_CAPTURE_TIMEOUT_MS',None)
        if role!='host' or p.get('joinAddress'): env['PAWS_TEST_JOIN']=p.get('joinAddress',join_address)
        else: env.pop('PAWS_TEST_JOIN',None)
        exe=p['game']/'k2.exe'
        assert (p['game']/'hotjoin-lab.marker').read_text()=='Paw hot-join lab; not for installed game\n' and sha(exe)==STOCK_HASH
        if a.composed_helper:
            manifest=json.loads((a.composed_helper.parent/'qa-manifest.json').read_text());assert sha(a.composed_helper)==manifest['testHelper']
            assert sha(p['game']/a.composed_helper.name).lower()==manifest['publicHelper'].lower()
            shutil.copy2(a.composed_helper,p['game']/a.composed_helper.name)
            output=p['root']/'composed-helper.log';handle=output.open('w')
            helper=subprocess.Popen([str(p['game']/a.composed_helper.name),'--game-dir',str(p['game'])],cwd=p['game'],env=env,creationflags=4|0x08000000,stdout=handle,stderr=subprocess.STDOUT)
            helper_processes.append((helper,handle));assert K.AssignProcessToJobObject(job,int(helper._handle))
            assert N.NtResumeProcess(int(helper._handle))==0
            until=time.monotonic()+100;pid=None
            while time.monotonic()<until:
                text=output.read_text(errors='replace');m=re.search(r'OWNED_GAME (\d+)',text)
                if m:pid=int(m.group(1))
                if pid and 'PACKAGED_HELPER_READY' in text:break
                failures=[f.read_text(errors='replace')[-4000:] for f in p['game'].glob('*status*.txt')]
                if any(' ERROR ' in f for f in failures):raise RuntimeError('Owned helper rejected this fixture: '+'\n'.join(f for f in failures if ' ERROR ' in f))
                if helper.poll() is not None:raise RuntimeError('Composed helper stopped: '+text[-3000:])
                time.sleep(.2)
            if not pid or 'PACKAGED_HELPER_READY' not in text:raise TimeoutError('Composed helper startup')
            proc=OwnedChild(pid)
            actual=C.create_unicode_buffer(32768);length=C.c_uint(len(actual))
            assert K.QueryFullProcessImageNameW(proc._handle,0,actual,C.byref(length)) and Path(actual.value).resolve()==exe.resolve(),'Composed child path mismatch'
            (p['root']/'composed-manifest.json').write_text(json.dumps(manifest,indent=2))
        else:proc=subprocess.Popen([str(exe),'+Exec Mods/rig.txt'],cwd=p['game'],env=env,creationflags=4)
        processes.append(proc);p['process']=proc
        already=C.c_int();assert K.IsProcessInJob(int(proc._handle),job,C.byref(already))
        if not already.value and not K.AssignProcessToJobObject(job,int(proc._handle)):raise C.WinError(C.get_last_error())
        if not a.composed_helper and N.NtResumeProcess(int(proc._handle)):raise RuntimeError('Could not resume owned process')
        (p['root']/'process.json').write_text(json.dumps(dict(pid=proc.pid,exe=str(exe),exeSha256=STOCK_HASH),indent=2))
        report('Started owned '+role+' pid='+str(proc.pid))
    def state(role):
        try:return json.loads((peers[role]['game']/'Mods/lab-state.jsonl').read_text().splitlines()[-1])
        except (OSError,ValueError,IndexError):return {}
    def wait(check,seconds,label):
        until=time.monotonic()+seconds
        while not check():
            if errors():raise RuntimeError('Native error while waiting: '+label)
            if any(p.poll() is not None and p.pid not in expected_exits for p in processes): raise RuntimeError('Owned game exited: '+label)
            if label.startswith('Visitor loaded') and 'HOT_ADMISSION_REFUSED' in (peers['host']['game']/'Mods/plugins.log').read_text(errors='replace'):raise RuntimeError('Native hot admission refused; inspect private plugin log')
            if label.startswith('Visitor loaded') and 'NATIVE_REJECT' in (peers['host']['game']/'Mods/plugins.log').read_text(errors='replace'):raise RuntimeError('Native join rejected; inspect private plugin log')
            if time.monotonic()>until:raise TimeoutError(label)
            time.sleep(.25)
        report(label)
    def command(role,text,delay=2):
        p=peers[role];p['serial']+=1
        tmp=p['game']/'Mods/lab-command.tmp';tmp.write_text(str(p['serial'])+' '+text,encoding='utf-8')
        until=time.monotonic()+5
        while True:
            try:
                os.replace(tmp,p['game']/'Mods/lab-command.txt');break
            except PermissionError:
                if time.monotonic()>=until:raise
                time.sleep(.02)
        time.sleep(delay)
    def open_lan(role,nickname):
        peers[role]['nickname']=nickname
        wait(lambda:bool(state(role)),60,role+' native probe ready')
        wait(lambda:state(role).get('phase')==3,60,role+' main menu ready')
        time.sleep(2)
        for cmd in ('RequestMultiplayer','RequestLobbyLAN','LobbySetLANNickname '+nickname):command(role,cmd,3)
        command(role,'MessageBoxButtonAction 1',1)
    error_offsets={};native_errors=[];native_error_keys=set()
    def errors():
        def record(role,filename,line):
            key=(role,filename,line)
            if key not in native_error_keys:
                native_error_keys.add(key);native_errors.append(dict(role=role,file=filename,line=line))
        for role,p in peers.items():
            logs=p['game']/'Logs'
            for f in logs.glob('*.log'):
                for attempt in range(10):
                    try:
                        info=f.stat();key=(role,info.st_ino);offset=error_offsets.get(key,0)
                        if offset>info.st_size:offset=0
                        with f.open('rb') as stream:
                            stream.seek(offset)
                            while True:
                                begin=stream.tell();raw=stream.readline()
                                if not raw:break
                                line=raw.decode('utf-8',errors='replace').rstrip()
                                if any(s in line.lower() for s in ('out of sync','out-of-sync','syncfailure(','assert:','unhandled exception','timeout waiting for mutex')):record(role,f.name,line)
                                if not raw.endswith(b'\n'):
                                    stream.seek(begin);break
                            error_offsets[key]=stream.tell()
                        break
                    except OSError as error:
                        # Native flush/rename can transiently reject reads on
                        # Windows. Retain the file and retry; never skip it.
                        log_read_retries.append(dict(role=role,file=f.name,errno=error.errno))
                        if isinstance(error,FileNotFoundError):
                            completed=f.with_name(f.stem+'-ok.log')
                            if completed.exists():f=completed
                        if attempt==9:
                            record(role,f.name,'Unreadable native log after 10 attempts: '+str(error))
                        else:time.sleep(.1)
        return list(native_errors)
    result=dict(mode=a.mode,scenario=a.scenario,leaveMode=a.leave_mode,departureRole=a.depart,uncleared=a.uncleared,doubleDeparture=a.double_drop,controlOrdersRequired=a.control_orders,noticeLanguage=a.language,roleNoticesRequired=True,automaticCheckpoint=a.automatic,witness=a.witness,manualResumePolicy=True,hotJoinPassed=False,transferMode='stock' if a.stock_transfer else 'lobby-R2',fixtureOnly=bool(a.fixture_transfer),gameSource=str(a.game_source or STOCK),composedHelper=str(a.composed_helper) if a.composed_helper else None)
    try:
        prepare('host');prepare('client')
        if a.witness:prepare('witness')
        if a.second_witness:prepare('witness2')
        launch('host')
        if a.startup_only:
            wait(lambda:state('host').get('phase')==3,90,'Composed game reached main menu with hot-join hooks active')
            result.update(experimentComplete=True,startupOnly=True,startupState=state('host'));return
        if a.replay_film:
            wait(lambda:state('host').get('phase')==3,90,'Fresh owned replay copy reached main menu')
            result.update(replayOnly=True,replaySource=str(a.replay_film),replaySha256=sha(a.replay_film))
            command('host','RequestFilm',2)
            command('host','FilmOK "Films/HotJoinReplay.RFM"',1)
            wait(lambda:state('host').get('world') and state('host').get('mode')==4,90,'Native film loaded its recorded world')
            command('host','UserReady',1);result['replayBefore']=state('host')
            until=time.monotonic()+a.observe
            while time.monotonic()<until:
                if errors():raise AssertionError('Native replay failure')
                time.sleep(.5)
            result.update(replayAfter=state('host'),experimentComplete=True)
            command('host','ScreenShot',1);report('Replay observed; EOF/trace evidence requires independent review');return
        if a.scenario!='visitor':launch('client')
        if a.witness:launch('witness')
        if a.second_witness:launch('witness2')
        open_lan('host','HotJoinHost')
        if a.port!=5860:command('host','!port '+str(a.port),1)
        # 13f84f uses the saved port (+48), then reads max players and room.
        # The bundled help still claims a port argument; passing it here makes
        # later tokens a password. Keep native password checking intact.
        command('host','InternetGameCreate HotJoinLab '+('4' if a.second_witness else '3' if a.witness else '2')+' 2',4)
        if a.initial_save:
            command('host','!transfer-fixture',2)
            wait(lambda:state('host').get('mapType')==2,45,'Preserved save selected natively in private lobby')
            result['initialSave']=dict(source=str(a.initial_save),sha256=sha(a.initial_save),bytes=a.initial_save.stat().st_size)
        else:
            if a.manual_world_setup:
                assert a.world_options and a.release_observer
                report('Owned lobby ready for manual world-options UI setup')
                wait(lambda:(root/'continue-setup.flag').exists(),600,'Owned UI setup confirmed; network scenario resumes')
                result['worldOptions']=True
            else:
                command('host','SelectLaunchType RANDOM_MAP',4)
            if a.world_options and not a.manual_world_setup:
                assert a.release_observer and a.composed_helper and a.game_source
                command('host','Commit',2)
                command('host','OpenRandomMapDialog',3)
                command('host','Select paws_mixed_biomes',2)
                command('host','!world-option Sun paws_dynamic_sun',2)
                command('host','!world-option PawsBiomes paws_random',2)
                result['worldOptions']=True
            if not a.manual_world_setup:command('host','Commit',2)
        if a.witness:
            assert a.automatic and a.scenario!='visitor', 'Witness scenario requires automatic original-participant setup'
            command('host','TeamFormatDropdown '+('4' if a.second_witness else '3'),3)
        if a.scenario!='visitor':
            open_lan('client','HotJoinOriginal')
            command('client','LobbyJoinDirect',3);command('client','JoinDirectJoin',3)
            wait(lambda:state('client').get('mode')==1 and len(state('host').get('players',[]))==2,40,'Original participant joined lobby')
            if a.initial_save:
                def loaded_file(role):
                    try:return sha(peers[role]['docs']/'Kohan2/data/Save/HotJoinBoundary.RSG')==sha(a.initial_save)
                    except OSError:return False
                wait(lambda:loaded_file('client'),180,'First participant received the preserved save through native transfer')
            if a.fixture_transfer:
                source=a.fixture_transfer.resolve();data=source.read_bytes();assert len(data)>1000 and source.suffix.upper()=='.RSG'
                target=peers['host']['docs']/'Kohan2/data/Save/HotJoinBoundary.RSG';target.write_bytes(data)
                received=peers['client']['docs']/'Kohan2/data/Save/HotJoinBoundary.RSG'
                started=time.monotonic();command('host','!transfer-fixture',0)
                def fixture_ready():
                    if not any(p.get('name')=='HotJoinOriginal' and p.get('fileState')==1 for p in state('host').get('players',[])):return False
                    # The native receiver owns an exclusive writer handle until
                    # its final block closes. Wait for completion, then inspect;
                    # persistent locks/missing/different bytes still time out.
                    try:return received.read_bytes()==data
                    except OSError:return False
                wait(fixture_ready,180,'Native lobby transferred the complete preserved boundary fixture and acknowledged it')
                result.update(experimentComplete=True,transferFixturePassed=True,fixtureSource=str(source),fixtureBytes=len(data),fixtureSha256=sha(source),fixtureElapsedSeconds=time.monotonic()-started,hostAfterFixture=state('host'),clientAfterFixture=state('client'))
                return
            command('client','StagingReady 0',3)
        if a.witness:
            open_lan('witness','HotJoinWitness')
            command('witness','LobbyJoinDirect',3);command('witness','JoinDirectJoin',3)
            wait(lambda:state('witness').get('mode')==1 and len(state('host').get('players',[]))==3,40,'Third human participant joined lobby')
            if a.initial_save:wait(lambda:loaded_file('witness'),180,'Third participant received the preserved save through native transfer')
            command('witness','StagingReady 0',3)
            command('client','StagingReady 0',2)
        if a.second_witness:
            open_lan('witness2','HotJoinWitnessTwo')
            command('witness2','LobbyJoinDirect',3);command('witness2','JoinDirectJoin',3)
            wait(lambda:state('witness2').get('mode')==1 and len(state('host').get('players',[]))==4,40,'Fourth original human joined lobby')
            if a.initial_save:wait(lambda:loaded_file('witness2'),180,'Fourth participant received preserved save')
            for role in ('client','witness','witness2'):command(role,'StagingReady 0',2)
        command('host','StagingLaunch',1)
        if a.witness:
            # Stock 384 map recommends two participants and asks "proceed
            # anyway" for three. Accept that normal UI recommendation dialog;
            # native launch, file, player and synchronization checks stay on.
            command('host','MessageBoxButtonAction 0',1)
        wait(lambda:state('host').get('mode')==2 and state('host').get('world',0)!=0,75,'Host entered live match')
        command('host','UserReady',2)
        if a.scenario!='visitor':
            wait(lambda:state('client').get('world',0)!=0 and state('client').get('mode')==2,75,'Original participant entered match')
            command('client','UserReady',2)
        if a.witness:
            wait(lambda:state('witness').get('mode')==2 and state('witness').get('world'),75,'Third participant entered match')
            command('witness','UserReady',2)
        if a.second_witness:
            wait(lambda:state('witness2').get('mode')==2 and state('witness2').get('world'),75,'Fourth original human entered match')
            command('witness2','UserReady',2)
        time.sleep(5); before=state('host');result['hostBeforeJoin']=before
        if a.world_options:
            sample=json.loads((peers['host']['game']/'Mods/lab-world-options.jsonl').read_text().splitlines()[-1])
            result['worldOptionsInitial']=sample
            assert sample['rules'].get('sun')==5 and sample['rules'].get('biomes')==1 and sample['rules'].get('phase') is not None,'Native world must actually use Dynamic Sun and Random biomes'
        if a.witness:
            result['witnessBeforeDrop']=state('witness')
            humans=[p for p in before['players'] if not p['ai']]
            expected_humans=4 if a.second_witness else 3
            assert len(humans)==expected_humans and len({p['kingdom'] for p in humans if p['kingdom']})==expected_humans and all(p['kingdomPtr'] for p in humans), 'Original humans must control distinct kingdoms'
            result['secondWitness']=a.second_witness
        if a.scenario!='visitor':
            original_name='HotJoinHost' if a.depart=='host' else 'HotJoinOriginal'
            if a.depart=='host':
                # Keep logical host = surviving coordinator, client = departing
                # peer. Paths remain unchanged and are recorded for validation.
                peers['host'],peers['client']=peers['client'],peers['host']
                result['hostBeforeJoin']=state('host')
            original=next(p for p in before['players'] if p['name']==original_name)
            assert original['kingdom'] and original['kingdomPtr'] and not original['ai']
            ticket=peers['client']['docs']/'Kohan2/data/User/HotJoinTicket.bin'
            assert ticket.exists() and ticket.stat().st_size==32, 'Private reconnect credential was not received'
            result['originalParticipant']=original
            if a.double_drop:
                result['secondOriginalParticipant']=next(p for p in before['players'] if p['name']=='HotJoinWitness')
                assert (peers['witness']['docs']/'Kohan2/data/User/HotJoinTicket.bin').stat().st_size==32, 'Second participant needs its own private credential'
            proc=peers['client']['process']
            departing=('client','witness') if a.double_drop else ('client',)
            remaining=('host','witness') if a.witness and not a.double_drop else ('host',)
            if a.second_witness:remaining=remaining+('witness2',)
            if a.leave_mode=='menu':
                for role in departing:command(role,'RequestLeaveGame',0)
                # Native RequestLeaveGame returns to staging while retaining
                # an inert world allocation. Check the session/UI and released
                # player binding, rather than assuming the allocation is gone.
                wait(lambda:all(state(role).get('phase')==12 and state(role).get('mode')==1 and all(not p.get('kingdomPtr') for p in state(role).get('players',[])) for role in departing),75,'Departing participants left through normal game exit command')
                result['departedClientAfterMenu']=state('client')
                if a.double_drop:result['secondDepartedAfterMenu']=state('witness')
                for role in departing:
                    if a.reuse_client and role=='client':continue
                    proc=peers[role]['process'];expected_exits.add(proc.pid);command(role,'ReallyQuit',.2)
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
            else:
                if a.uncleared:
                    # A locally closed UDP socket sends ICMP reset and the
                    # native engine removes it immediately. Suspend this owned
                    # fixture instead: keep its socket, stop all packets, and
                    # genuinely exercise the unresolved connection-status path.
                    for role in departing:
                        if N.NtSuspendProcess(int(peers[role]['process']._handle)):raise RuntimeError('Could not suspend owned fault-injection process')
                    result['disconnectSimulation']='suspended-owned-process-with-open-socket'
                    report('Stopped packets from owned participant while retaining its socket; no Delete vote')
                    wait(lambda:all(state(role).get('backup') for role in remaining),95,'Native connection status stopped the remaining peers; original participant is not deleted')
                else:
                    for role in departing:
                        proc=peers[role]['process'];expected_exits.add(proc.pid);proc.terminate();proc.wait(timeout=15)
                    result['disconnectSimulation']='terminated-owned-process'
                    report('Simulated abrupt disconnect of owned original participant')
                    time.sleep(15)
                    for role in remaining:
                        command(role,'CSDKickPlayer '+str(original['id'])+' 1',2)
                        if a.double_drop:command(role,'CSDKickPlayer '+str(result['secondOriginalParticipant']['id'])+' 1',2)
            if a.double_drop and a.continue_without:
                # Two simultaneous departures can leave the last participant
                # waiting for native recovery consensus. Here that test player
                # explicitly chooses Continue without them through the CSD's
                # actual backup-channel vote; no quorum check is bypassed.
                wait(lambda:state('host').get('host') or state('host').get('backupHost'),60,'Remaining participant is native server or backup server')
                if state('host').get('backup'):
                    command('host','!backup-vote',1)
                    result['testPlayerResolvedDisconnectsToContinue']=True
            if a.depart=='host':
                def elected(role):return role in remaining and state(role).get('mode')==2 and (state(role).get('host') or ((a.uncleared or (a.double_drop and not a.continue_without)) and state(role).get('backupHost')))
                wait(lambda:elected('host') or elected('witness'),95,'Native host election selected a remaining participant')
                if not elected('host'):peers['host'],peers['witness']=peers['witness'],peers['host']
                result['hostBeforeJoin']=result.get('witnessBeforeDrop') if peers['host']['root'].name=='witness' else result['hostBeforeJoin']
                result['witnessBeforeDrop']=next(json.loads(line) for line in reversed((peers['witness']['game']/'Mods/lab-state.jsonl').read_text().splitlines()) if json.loads(line).get('mode')==2 and any(p.get('name')==original_name for p in json.loads(line).get('players',[])))
                pid=peers['host']['process'].pid
                endpoint=subprocess.check_output(['powershell','-NoProfile','-Command',f'(Get-NetUDPEndpoint -OwningProcess {pid} | Select-Object -First 1).LocalPort'],text=True).strip()
                assert endpoint.isdecimal() and 0<int(endpoint)<65536
                join_address='127.0.0.1:'+endpoint
                result['migratedHostEndpoint']=join_address
                report('Reconnecting to native elected host at '+join_address)
            unresolved=a.uncleared or (a.double_drop and not a.continue_without and bool(state('host').get('backup')))
            result['uncleared']=unresolved
            if not unresolved:
                wait(lambda:any(p.get('ai') and p.get('implicit') and p.get('kingdom')==original['kingdom'] for p in state('host').get('players',[])),95,'Native AI took over original kingdom')
            else:
                assert all(any(p.get('id')==original['id'] and not p.get('ai') for p in state(role).get('players',[])) for role in remaining), 'Original native slot must remain unresolved before returning'
                result['unclearedOriginalPresent']=True
            result['hostAfterDrop']=state('host')
            if a.witness and not a.double_drop:result['witnessAfterDrop']=state('witness')
            time.sleep(5)
            result['hostAfterPauseWait']=state('host')
            assert (state('host').get('paused')==1 or (unresolved and state('host').get('backup'))) and state('host')['worldTicks']==result['hostAfterDrop']['worldTicks'], 'Departure must stop simulation before native AI can act'
            if a.witness and not a.double_drop:
                result['witnessAfterPauseWait']=state('witness')
                assert (state('witness').get('paused')==1 or (unresolved and state('witness').get('backup'))) and state('witness')['worldTicks']==result['witnessAfterDrop']['worldTicks'], 'Third peer must remain stopped after loss'
                if not unresolved:assert state('witness')['worldTicks']==state('host')['worldTicks'], 'Shared departure pause must stop both remaining peers at the same simulation tick'
            if a.continue_without:
                for role in remaining:command(role,'GamePause 0',1)
                wait(lambda:all(state(role).get('paused')==0 for role in remaining) and state('host').get('seconds',0)>=result['hostAfterPauseWait']['seconds']+3,25,'Test players explicitly continued without the absent participant')
                result['continuedWithoutParticipant']=state('host')
                if not a.join_unpaused:
                    command('host','GamePause 1',1)
                    wait(lambda:all(state(role).get('paused')==1 for role in remaining),20,'Test players paused again before return')
            if not a.reuse_client:
                peers['departed-client']=peers.pop('client')
                old_user=peers['departed-client']['docs']/'Kohan2/data/User'
                prepare('client','host-return' if a.depart=='host' else 'client-return')
                shutil.copytree(old_user,peers['client']['docs']/'Kohan2/data/User',dirs_exist_ok=True,ignore=shutil.ignore_patterns('HotJoinTicket.bin') if a.scenario=='impostor' else None)
                old_process=peers['departed-client']['process']
                if old_process.poll() is None:
                    command('departed-client','ReallyQuit',.2)
                    old_process.wait(timeout=25);expected_exits.add(old_process.pid)
                    assert old_process.returncode==0,'Departed private game did not quit normally'
        if a.mode in ('snapshot','coordinated') and not a.automatic:
            command('host','GamePause 1',2)
            command('host','GameSave "Save/HotJoinSnapshot.RSG"',2)
            snapshot=peers['host']['docs']/'Kohan2/data/Save/HotJoinSnapshot.RSG'
            wait(lambda:snapshot.exists() and snapshot.stat().st_size>1000,35,'Host snapshot written')
            time.sleep(3)
            crc=0
            for value in snapshot.read_bytes():crc=(crc*7+value)&0xffffffff
            command('host','!snapshot '+str(crc),3)
            log=peers['host']['game']/'Mods/plugins.log'
            wait(lambda:'SNAPSHOT_READY ' in log.read_text(),20,'Native resource metadata ready')
            if a.cached_snapshot:
                shutil.copy2(snapshot,peers['client']['docs']/'Kohan2/data/Save/HotJoinSnapshot.RSG')
                result['clientCheckpointPreseeded']=True
                report('Development run: identical checkpoint preseeded in private client cache')
        if a.edge_case=='duplicate':
            assert a.witness
            shutil.copy2(peers['witness']['docs']/'Kohan2/data/User/HotJoinTicket.bin',peers['client']['docs']/'Kohan2/data/User/HotJoinTicket.bin')
        if a.edge_case=='reject-protocol':peers['client']['testLegacyProtocol']=True
        late_name={'return':'HotJoinRenamed','impostor':'HotJoinOriginal','visitor':'HotJoinVisitor'}[a.scenario]
        result['coordinatorDirectory']=peers['host']['root'].name
        if a.witness:result['witnessDirectory']=peers['witness']['root'].name
        if a.prepaused:
            command('host','GamePause 1',1)
            wait(lambda:state('host').get('paused')==1,20,'Test player paused before admission')
        result['pauseStateRestorationPolicy']=True
        # Native backup/CSD already stops the match while Sim.paused may still
        # be zero. Recovery completes the queued loss-pause before AI takeover;
        # that departure pause must survive, not be mistaken for a running join.
        result['expectedPauseAfterJoin']=bool(state('host').get('paused') or state('host').get('backup'))
        result['manualResumePolicy']=result['expectedPauseAfterJoin']
        if a.reuse_client:
            result['reusedClientPid']=peers['client']['process'].pid
            command('client','ScoringExit',3)
            wait(lambda:state('client').get('phase') in (3,10),45,'Original game process closed its scoring screen')
            if state('client').get('phase')==3:
                command('client','RequestMultiplayer',3);command('client','RequestLobbyLAN',3)
            wait(lambda:state('client').get('phase')==10,45,'Original game process returned to LAN lobby without restarting')
            command('client','LobbySetLANNickname '+late_name,2);command('client','MessageBoxButtonAction 1',1)
            peers['client']['nickname']=late_name
            result['reusedClientBeforeAdmission']=state('client')
        else:
            launch('client');open_lan('client',late_name)
        command('client','LobbyJoinDirect',3)
        batch_role=None
        if a.simultaneous:
            batch_role='witness' if a.simultaneous=='return' else 'observer'
            if batch_role=='witness':
                peers['departed-witness']=peers.pop('witness');old_second=peers['departed-witness']['docs']/'Kohan2/data/User'
                prepare('witness','witness-return');shutil.copytree(old_second,peers['witness']['docs']/'Kohan2/data/User',dirs_exist_ok=True)
                result['witnessDirectory']=peers['witness']['root'].name
            else:prepare('observer')
            launch(batch_role);open_lan(batch_role,'HotJoinWitness2' if batch_role=='witness' else 'HotJoinVisitor')
            command(batch_role,'LobbyJoinDirect',2)
            result['simultaneousAdmission']=a.simultaneous
        result['hostBeforeAdmission']=state('host')
        if a.witness:result['witnessBeforeAdmission']=state('witness')
        if a.edge_case:
            sys.path.insert(0,str(root/'source'))
            from edge_cases import run_edge
            run_edge(locals())
            return
        first_requested=time.monotonic();command('client','JoinDirectJoin',0 if batch_role else 3)
        if batch_role:
            command(batch_role,'JoinDirectJoin',0)
            result['simultaneousRequestGapMs']=(time.monotonic()-first_requested)*1000
        report('Late native join requested against running host')
        if a.mode in ('snapshot','coordinated'):
            wait(lambda:state('client').get('mode')==2 and state('client').get('world',0)!=0,480 if a.witness else 240,'Visitor loaded world without host returning to lobby')
            if not a.automatic:
                command('client','UserReady',2)
                if a.mode=='coordinated':command('host','UserReady',2)
            if a.mode=='coordinated':
                wait(lambda:all(state(role).get('phase')==4 and not state(role).get('frozen') for role in ('host','client')),60,'Both peers returned to active game interface')
            if a.double_drop and not a.simultaneous:
                # Keep the first return paused while the second owner returns.
                # Existing peers must complete another native checkpoint cycle;
                # old world pointers alone cannot establish that this happened.
                result['firstReturnBeforeSecond']={role:state(role) for role in ('host','client')}
                assert all(p.get('paused')==1 for p in result['firstReturnBeforeSecond'].values())
                first_rosters=[sorted((p['id'],p['ai'],p['implicit'],p['kingdom']) for p in state(role)['players']) for role in ('host','client')]
                assert first_rosters[0]==first_rosters[1], 'Existing and returned peers must keep the same human/AI session identities'
                second=result['secondOriginalParticipant']
                assert any(p.get('ai') and p.get('kingdom')==second['kingdom'] for p in state('host').get('players',[])), 'Second absent kingdom must still be held by its native replacement AI'
                if a.continue_without:
                    first_time=state('host')['seconds']
                    for role in ('host','client'):command(role,'GamePause 0',1)
                    wait(lambda:all(state(role).get('paused')==0 for role in ('host','client')) and state('host')['seconds']>=first_time+5,25,'First returned owner and remaining player continued while the second owner was absent')
                    result['firstReturnedPlayedBeforeSecond']=state('host')
                    command('host','GamePause 1',1)
                    wait(lambda:all(state(role).get('paused')==1 for role in ('host','client')),20,'Players paused again for the second return')
                peers['departed-witness']=peers.pop('witness')
                old_second_user=peers['departed-witness']['docs']/'Kohan2/data/User'
                prepare('witness','witness-return')
                shutil.copytree(old_second_user,peers['witness']['docs']/'Kohan2/data/User',dirs_exist_ok=True)
                def commit_count(role):return (peers[role]['game']/'Mods/plugins.log').read_text(errors='replace').count('COORDINATED_NATIVE_COMMIT')
                first_counts={role:commit_count(role) for role in ('host','client')}
                launch('witness');open_lan('witness','HotJoinWitness2')
                command('witness','LobbyJoinDirect',2);command('witness','JoinDirectJoin',1)
                wait(lambda:all(commit_count(role)>first_counts[role] and state(role).get('phase')==4 and not state(role).get('frozen') for role in ('host','client')) and commit_count('witness')>=1 and state('witness').get('phase')==4 and not state('witness').get('frozen'),480,'Both departed participants returned; three peers completed the second native checkpoint')
                result['witnessDirectory']=peers['witness']['root'].name
                result['secondReturnCompleted']=True
            result['afterLoadHost']=state('host');result['afterLoadClient']=state('client')
            if a.witness:
                wait(lambda:state('witness').get('mode')==2 and state('witness').get('phase')==4 and not state('witness').get('frozen'),60,'Third participant returned to the same match')
                result['afterLoadWitness']=state('witness')
            if batch_role:
                wait(lambda:state(batch_role).get('mode')==2 and state(batch_role).get('phase')==4 and not state(batch_role).get('frozen'),480,'Second simultaneous arrival completed the shared checkpoint')
                if batch_role=='witness':result['secondReturnCompleted']=True
                else:result['afterLoadObserver']=state('observer')
            # Check the actual pre-admission state, then use ordinary native
            # player Resume votes only when the match was already paused.
            time.sleep(5)
            active_roles=('host','client','witness') if a.witness else ('host','client')
            if batch_role=='observer':active_roles+=('observer',)
            result['beforeManualResume']={role:state(role) for role in active_roles}
            for role in active_roles:
                assert state(role).get('paused')==int(result['expectedPauseAfterJoin']), 'Join must restore pre-admission pause on '+role
                if result['expectedPauseAfterJoin']:
                    assert state(role)['worldTicks']==result['afterLoad'+role.title()]['worldTicks'], 'Existing pause must not advance '+role
                else:
                    assert state(role)['worldTicks']>result['afterLoad'+role.title()]['worldTicks'], 'Unpaused join must automatically continue '+role
            for role in active_roles:command(role,'ScreenShot',.4)
            # Native multiplayer pause uses a majority vote. Cast ordinary
            # Resume votes from the test players, retaining that game rule.
            if result['expectedPauseAfterJoin']:
                for role in active_roles:command(role,'GamePause 0',1)
                wait(lambda:all(state(role).get('paused')==0 for role in active_roles),20,'Test player explicitly resumed the match')
                result['testPlayerResumed']=True
            else:
                result['automaticResumeObserved']=True
                report('Join finished; previously running match automatically continued without player Resume commands')
            if a.scenario=='return':
                # The ordinary Tab selection action and Stop actor command
                # exercise the returning identity through native game orders.
                # Issuing them is recorded separately from proving acceptance.
                command('client','CycleSelection 0',1)
                command('client','ActorCommand stop',1)
                result['controlProbeIssued']=True
                if a.control_orders:
                    result['controlOrders']={}
                    for role in ('client','witness') if a.double_drop else ('client',):
                        command(role,'CycleSelection 0',1)
                        wait(lambda:state(role).get('selectionActor') and (state(role).get('selectionSally') or state(role).get('selectionRecall')),15,role+' selected its restored city with native militia controls')
                        if state(role).get('selectionRecall'):
                            command(role,'ActorCommand recall',1)
                            wait(lambda:state(role).get('selectionSally')==1,20,role+' recalled existing militia')
                        closed=state(role)
                        command(role,'ActorCommand sally_forth',1)
                        wait(lambda:state(role).get('selectionRecall')==1,20,role+' native Sally order executed')
                        opened=state(role)
                        command(role,'ActorCommand recall',1)
                        wait(lambda:state(role).get('selectionSally')==1,20,role+' native Recall order executed')
                        result['controlOrders'][role]=dict(before=closed,opened=opened,recalled=state(role))
            for role in active_roles:
                command(role,'ScreenShot',.4)
        until=time.monotonic()+a.observe
        while time.monotonic()<until:
            if errors():report('Native error detected; candidate failed');break
            time.sleep(1)
        result.update(hostAfterJoin=state('host'),clientAfterJoin=state('client'),errors=errors())
        if a.witness:result['witnessAfterJoin']=state('witness')
        if batch_role=='observer':result['observerAfterJoin']=state('observer')
        if a.repeat_plan:
            # Import the source captured BEFORE this run, even if development
            # continues while the owned games are exercising the first cycle.
            sys.path.insert(0,str(root/'source'))
            from repeat_cycles import run_sequence
            run_sequence(a,root,peers,result,expected_exits,state,command,wait,prepare,launch,open_lan,errors,report)
        result['experimentComplete']=True
        report('Observed late join; this experiment never asserts hot-join success')
    except Exception as e:
        result.update(experimentComplete=False,error=str(e),hostAfterJoin=state('host') if 'host' in peers else {},clientAfterJoin=state('client') if 'client' in peers else {})
        report('EXPERIMENT FAILED: '+str(e));raise
    finally:
        for role,p in peers.items():
            if 'process' in p and p['process'].poll() is None:
                try:command(role,'ReallyQuit',.1)
                except OSError:pass
                # Let this peer process its normal quit before the next one
                # disappears. A simultaneous teardown can open native CSD on
                # a busy saved world before its queued quit has executed.
                until=time.monotonic()+20
                while p['process'].poll() is None and time.monotonic()<until:time.sleep(.1)
        until=time.monotonic()+15
        while any(p.poll() is None for p in processes) and time.monotonic()<until:time.sleep(.1)
        result['activePeersRequiringForcedShutdown']=[role for role in ('host','client','witness','observer') if role in peers and peers[role].get('process') and peers[role]['process'].poll() is None]
        K.TerminateJobObject(job,125)
        for proc in processes:proc.wait(timeout=15)
        result['ownedProcessExitCodes']={str(proc.pid):proc.returncode for proc in processes}
        K.CloseHandle(job)
        for helper,handle in helper_processes:
            helper.wait(timeout=15);handle.close()
        for proc in processes:
            if isinstance(proc,OwnedChild):K.CloseHandle(proc._handle)
        result.update(events=events,errors=errors(),logReadRetries=log_read_retries)
        (root/'result.json').write_text(json.dumps(result,indent=2))
        report('Stopped only owned lab processes')

if __name__=='__main__':main()
