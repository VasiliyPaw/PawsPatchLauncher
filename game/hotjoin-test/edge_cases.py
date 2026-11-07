"""Owned lifecycle/failure scenarios. Every result retains native evidence."""
import ctypes,json,re,shutil,subprocess,time
from pathlib import Path

def run_edge(ctx):
    a,root,peers,result=(ctx[k] for k in ('a','root','peers','result'))
    state,command,wait,report,errors,prepare,launch,open_lan=(ctx[k] for k in ('state','command','wait','report','errors','prepare','launch','open_lan'))
    expected=ctx['expected_exits'];checks={};active=['host']+(['witness'] if a.witness else [])
    if a.second_witness:active.append('witness2')
    result.update(edgeCase=a.edge_case,edgeChecks=checks,edgeBefore={r:state(r) for r in active})
    def log(role):
        game=peers[role]['game'];extra=game/'Logs/paws_hotjoin.log'
        return (game/'Mods/plugins.log').read_text(errors='replace')+('\n'+extra.read_text(errors='replace') if extra.exists() else '')
    def check(name,value):
        checks[name]=bool(value)
        if not value:raise AssertionError(name)
    def kill(role):
        proc=peers[role]['process'];expected.add(proc.pid);proc.terminate();proc.wait(timeout=15)
        report('Abruptly closed owned '+role+' during '+a.edge_case)
    def hold(role,stage):
        (peers[role]['game']/'Mods/lab-hold.flag').write_text(stage)
    def release(role):
        (peers[role]['game']/'Mods/lab-hold.flag').unlink(missing_ok=True)
    def ready(roles):
        return all(state(r).get('mode')==2 and state(r).get('phase')==4 and not state(r).get('frozen') and not state(r).get('backup') for r in roles)
    def observe(roles,seconds=65):
        for r in roles:command(r,'ScreenShot',.1)
        result['edgeObserveBefore']={r:state(r) for r in roles}
        start=time.monotonic()
        while time.monotonic()-start<seconds:
            if errors():raise AssertionError('Native error during edge observation')
            time.sleep(.5)
        result['edgeObserveAfter']={r:state(r) for r in roles}
        result['edgeDirectories']={r:peers[r]['root'].name for r in roles}
        check('simulationAdvancedAfterRecovery',all(state(r).get('seconds',0)-result['edgeObserveBefore'][r].get('seconds',0)>=60 for r in roles))
    def resume(roles):
        for r in roles:command(r,'GamePause 0',.4)
        wait(lambda:all(state(r).get('paused')==0 for r in roles),35,'Remaining players explicitly resumed after interrupted admission')
    def retry():
        old=peers['client'];peers['failed-client']=peers.pop('client')
        prepare('client','client-retry')
        shutil.copytree(old['docs']/'Kohan2/data/User',peers['client']['docs']/'Kohan2/data/User',dirs_exist_ok=True)
        if getattr(a,'_retry_address',None):peers['client']['joinAddress']=a._retry_address
        launch('client');open_lan('client','HotJoinRetried');command('client','LobbyJoinDirect',1);command('client','JoinDirectJoin',.1)
        wait(lambda:ready(active+['client']),180,'Retry after interruption completed native loading')
        roles=active+['client'];result['edgeAfterRetry']={r:state(r) for r in roles}
        original=result.get('originalParticipant',{}).get('kingdom')
        if a.scenario=='return':check('retryReclaimedOriginalKingdom',bool(original) and all(any(p.get('name')=='HotJoinRetried' and p.get('kingdom')==original and not p.get('kingdomAi') and p.get('aiControllers')==0 for p in state(r).get('players',[])) for r in roles))
        resume(roles);observe(roles)
    stage={'cancel-capture':'capture','cancel-saved':'saved','cancel-transfer':'crc','cancel-load':'load','timeout-transfer':'crc','timeout-load':'load'}.get(a.edge_case)
    if stage:
        hold('host' if stage in ('capture','saved') else 'client',stage)
        before={r:state(r) for r in active};command('client','JoinDirectJoin',0)
        marker='TEST_HOLD_'+stage.upper()
        wait(lambda:marker in log('host' if stage in ('capture','saved') else 'client'),120,'Reached held native '+stage+' stage')
        result['edgeAtFault']={r:state(r) for r in active+['client']}
        if a.edge_case.startswith('timeout-'):
            wait(lambda:'ADMISSION_DEADLINE_NATIVE_DISCONNECT' in log('host'),140,'Host expired an alive but stalled new participant through native disconnect')
            check('deadlineDidNotKillProcess',peers['client']['process'].poll() is None)
        else:kill('client')
        if stage in ('capture','saved'):
            wait(lambda:'AUTO_CAPTURE_CANCELLED' in log('host'),135,'Host cancelled the unassigned connection before releasing the QA hold')
        release('host');release('client')
        wait(lambda:ready(active),150,'Remaining peers recovered their game interface after interrupted '+stage)
        result['edgeAfterRecovery']={r:state(r) for r in active}
        check('remainingSessionsRetained',all(state(r).get('session')==before[r].get('session') for r in active))
        if stage in ('capture','saved'):
            time.sleep(3)
            check('preAdmissionPauseRestoredBeforeRoleTransfer',all(state(r).get('paused')==int(result['expectedPauseAfterJoin']) for r in active))
        if a.edge_case.startswith('timeout-'):
            command('client','ReallyQuit',1);expected.add(peers['client']['process'].pid)
            peers['client']['process'].wait(timeout=20)
        retry()
    elif a.edge_case=='observer-host':
        check('freshObserverScenario',a.scenario=='visitor' and not a.witness)
        original=next(p for p in state('host')['players'] if p['name']=='HotJoinHost')
        command('client','JoinDirectJoin',0)
        wait(lambda:ready(['host','client']),180,'Fresh observer completed the first native admission')
        old_host=peers['host'];check('originalHostCredentialRetained',(old_host['docs']/'Kohan2/data/User/HotJoinTicket.bin').is_file())
        command('host','RequestLeaveGame',0)
        wait(lambda:state('host').get('mode')==1 and state('host').get('phase')==12,60,'Last kingdom owner exited normally, leaving only an observer and native AIs')
        command('host','ReallyQuit',.2);expected.add(old_host['process'].pid);old_host['process'].wait(timeout=25)
        wait(lambda:state('client').get('host') or state('client').get('backupHost'),100,'Native election considered the sole observer')
        if state('client').get('backup'):command('client','!backup-vote',1)
        wait(lambda:ready(['client']) and state('client').get('host'),100,'Sole observer retained the live match as native host')
        result['edgeSoleObserver']=state('client')
        peers['failed-host']=peers.pop('host');peers['host']=peers.pop('client');active=['host']
        endpoint=subprocess.check_output(['powershell','-NoProfile','-Command',f"(Get-NetUDPEndpoint -OwningProcess {peers['host']['process'].pid} | Select-Object -First 1).LocalPort"],text=True).strip()
        check('observerHostEndpointAvailable',endpoint.isdecimal())
        prepare('client','kingdom-return');shutil.copytree(old_host['docs']/'Kohan2/data/User',peers['client']['docs']/'Kohan2/data/User',dirs_exist_ok=True)
        peers['client']['joinAddress']='127.0.0.1:'+endpoint
        launch('client');open_lan('client','HotJoinRetried');command('client','LobbyJoinDirect',1);command('client','JoinDirectJoin',0)
        wait(lambda:ready(['host','client']),180,'Former host returned to the match hosted by its sole observer')
        check('formerHostReclaimedKingdom',all(any(p.get('name')=='HotJoinRetried' and p.get('kingdom')==original['kingdom'] and not p.get('kingdomAi') and not p.get('aiControllers') for p in state(r).get('players',[])) for r in ('host','client')))
        check('newHostRemainedObserver',all(any(p.get('name')=='HotJoinVisitor' and not p.get('kingdom') for p in state(r).get('players',[])) for r in ('host','client')))
        resume(['host','client']);observe(['host','client'])
    elif a.edge_case in ('save-during-join','finish-during-join'):
        hold('client','crc');command('client','JoinDirectJoin',0)
        if a.simultaneous=='observer':command('observer','JoinDirectJoin',0)
        wait(lambda:'TEST_HOLD_CRC' in log('client'),120,'Incoming peer reached checkpoint barrier before an existing player action')
        if a.simultaneous=='observer':wait(lambda:'BATCH_VERIFIED_JOIN_SENT' in log('host'),60,'Both arrivals admitted to the same checkpoint')
        roles=active+['client']+(['observer'] if a.simultaneous=='observer' else [])
        result['edgeAtFault']={r:state(r) for r in active+['client']}
        if a.edge_case=='save-during-join':command('host','GameSave "Save/DuringHotJoin.RSG"',2)
        else:
            command('host','OpenGameMenuResignDialog',1);command('host','RequestResign',2)
        result['edgeAfterAction']={r:state(r) for r in active+['client']}
        if a.edge_case=='finish-during-join':
            wait(lambda:'RESIGN_DEFERRED_SHARED' in log('client'),30,'Resign intent replicated without a premature world vote')
            check('resignDeferredBeforeLoad',all(1 not in state(r).get('resignVoteIds',[]) for r in active+['client']))
        release('client')
        wait(lambda:ready(roles),180,'All peers finished admission after an existing player action')
        if a.edge_case=='finish-during-join':
            wait(lambda:all(1 in state(r).get('resignVoteIds',[]) for r in roles),35,'Original player reissued its native resign vote after shared load')
            check('nativeResignExecuted',all(1 in state(r).get('resignVoteIds',[]) for r in roles))
        resume(roles);observe(roles)
        if a.edge_case=='finish-during-join':
            check('resignDecisionRetained',all(1 in state(r).get('resignVoteIds',[]) for r in roles))
            result['resignScope']='Native team vote retained, not a claim of full kingdom resignation or victory'
        if a.edge_case=='save-during-join':
            saved=peers['host']['docs']/'Kohan2/data/Save/DuringHotJoin.RSG'
            result['edgeDuringSaveCreated']=saved.is_file()
            check('ordinarySaveDuringAdmissionCompleted',saved.is_file() and saved.stat().st_size>1000)
    elif a.edge_case=='save-roundtrip':
        command('client','JoinDirectJoin',0);roles=active+['client']
        wait(lambda:ready(roles),180,'Return completed before ordinary player save')
        resume(roles);observe(roles)
        saved=peers['host']['docs']/'Kohan2/data/Save/AfterHotJoin.RSG'
        command('host','GameSave "Save/AfterHotJoin.RSG"',0)
        wait(lambda:saved.is_file() and saved.stat().st_size>1000 and ready(roles),60,'Ordinary GameSave completed after a hot return')
        result['edgeSavedFile']=str(saved);check('ordinarySaveCreated',saved.is_file())
        observe(roles)
    elif a.edge_case in ('duplicate','reject-protocol','reject-password'):
        before={r:state(r) for r in active};offset=len(log('host'))
        if a.edge_case=='reject-password':
            command('host','!password HotJoinQAPassword',1)
            wait(lambda:all(state(r).get('passwordConfigured') for r in active),20,'Native host request configured the temporary test password on existing peers')
        command('client','JoinDirectJoin',0)
        marker={'duplicate':'duplicate=1','reject-protocol':'TICKET_PROTOCOL_MISSING','reject-password':'NATIVE_REJECT reason=1;'}[a.edge_case]
        wait(lambda:marker in log('host')[offset:] and 'NATIVE_REJECT' in log('host')[offset:],60,'Native admission rejected the invalid incoming identity/protocol/password')
        time.sleep(3);result['edgeAfterRejection']={r:state(r) for r in active}
        check('rejectionDidNotChangeRoles',all([(p['id'],p['kingdom'],p['ai']) for p in state(r).get('players',[])]==[(p['id'],p['kingdom'],p['ai']) for p in before[r].get('players',[])] for r in active))
        check('rejectionDidNotReloadWorld',all(state(r).get('world')==before[r].get('world') and not state(r).get('frozen') for r in active))
        check('rejectionDidNotStartCheckpoint','AUTO_CAPTURE_REQUESTED' not in log('host')[offset:])
        if a.edge_case=='reject-password':
            command('host','!password ',1)
            wait(lambda:all(not state(r).get('passwordConfigured') for r in active),20,'Native host request cleared the temporary test password')
        command('client','ReallyQuit',1);expected.add(peers['client']['process'].pid);peers['client']['process'].wait(timeout=20)
        if a.edge_case=='duplicate':shutil.copy2(peers['departed-client']['docs']/'Kohan2/data/User/HotJoinTicket.bin',peers['client']['docs']/'Kohan2/data/User/HotJoinTicket.bin')
        retry()
    elif a.edge_case in ('host-transfer','host-partial-transfer','host-load'):
        check('threeHumanScenario',a.witness)
        stage='crc' if a.edge_case=='host-transfer' else 'load'
        if a.edge_case!='host-partial-transfer':hold('client',stage)
        command('client','JoinDirectJoin',0)
        arrivals=['client']+(['observer'] if a.simultaneous=='observer' else [])
        if a.simultaneous=='observer':
            hold('observer',stage);command('observer','JoinDirectJoin',0)
        def partial():
            incoming=state('client');size=incoming.get('incomingReceiveExpected',0);first=incoming.get('incomingReceiveFirst',0)
            return 1000<size<10000000 and 0<first*64<size and any(p.get('name')=='HotJoinRenamed' and p.get('sendBytes',0)>1000 and 0<p.get('sendFirst',0)<0x80000000 and p['sendFirst']*64<p['sendBytes'] for p in state('host').get('players',[]))
        wait(partial if a.edge_case=='host-partial-transfer' else lambda:'TEST_HOLD_'+stage.upper() in log('client'),120,'Incoming peer reached the target stage before abrupt coordinator loss')
        if a.simultaneous=='observer':wait(lambda:'BATCH_VERIFIED_JOIN_SENT' in log('host') and 'TEST_HOLD_'+stage.upper() in log('observer'),90,'Both uncommitted arrivals reached target stage before host loss')
        if a.edge_case=='host-partial-transfer':check('partialNativeTransferObserved',partial())
        result['edgeAtFault']={r:state(r) for r in active+arrivals}
        if a.test_host_exit=='menu':
            check('nativeMenuExitAvailableAtTarget',state('host').get('phase')==4)
            command('host','RequestLeaveGame',0)
            wait(lambda:state('host').get('mode')==1 and state('host').get('phase')==12,60,'Coordinator left normally during admission')
            command('host','ReallyQuit',1);expected.add(peers['host']['process'].pid);peers['host']['process'].wait(timeout=25)
        else:kill('host')
        wait(lambda:state('witness').get('host') or state('witness').get('backupHost'),100,'Native election selected the remaining original participant')
        survivors=['witness']+(['witness2'] if a.second_witness else [])
        for r in survivors:
            if state(r).get('backup'):command(r,'!backup-vote',1)
        wait(lambda:all('ADMISSION_CANCELLED_HOST_CHANGED' in log(r) for r in arrivals),90,'All incoming peers cancelled before consuming successor world orders')
        for r in arrivals:release(r)
        wait(lambda:ready(survivors) and all(state(r).get('mode')==0 and state(r).get('phase')==10 for r in arrivals),180,'Surviving match recovered paused; all interrupted arrivals returned to lobby')
        check('hostLossRetainedPause',all(state(r).get('paused')==1 for r in survivors))
        result['edgeSurvivors']=survivors
        result['edgeAfterCancellation']={r:state(r) for r in survivors+arrivals}
        if a.second_witness:
            check('twoOriginalHumansSurvived',len(survivors)==2 and all(any(p.get('name')=='HotJoinWitness' and p.get('kingdomPtr') for p in state(r).get('players',[])) and any(p.get('name')=='HotJoinWitnessTwo' and p.get('kingdomPtr') for p in state(r).get('players',[])) for r in survivors))
            resume(survivors);observe(survivors)
            result['edgeSurvivorObservation']={k:result[k] for k in ('edgeObserveBefore','edgeObserveAfter','edgeDirectories')}
        check('allUncommittedArrivalsCancelled',not any(p.get('name') in ('HotJoinRenamed','HotJoinVisitor') for p in state('witness').get('players',[])))
        if 'observer' in arrivals:
            command('observer','ReallyQuit',1);expected.add(peers['observer']['process'].pid);peers['observer']['process'].wait(timeout=25)
        peers['failed-host']=peers.pop('host');peers['host']=peers.pop('witness');active=['host']+(['witness2'] if a.second_witness else [])
        result['edgeElectedHost']=state('host')
        check('survivorBecameHost',bool(state('host').get('host')))
        endpoint=subprocess.check_output(['powershell','-NoProfile','-Command',f"(Get-NetUDPEndpoint -OwningProcess {peers['host']['process'].pid} | Select-Object -First 1).LocalPort"],text=True).strip()
        check('migratedHostEndpointAvailable',endpoint.isdecimal())
        peers['client']['joinAddress']='127.0.0.1:'+endpoint
        command('client','ReallyQuit',1);expected.add(peers['client']['process'].pid);peers['client']['process'].wait(timeout=20)
        # retry() prepares a fresh copy; retain its selected elected endpoint.
        ctx['a']._retry_address='127.0.0.1:'+endpoint
        retry()
    elif a.edge_case=='batch-loss':
        check('simultaneousObserverScenario',a.simultaneous=='observer' and a.witness)
        hold('client','crc');command('client','JoinDirectJoin',0);command('observer','JoinDirectJoin',0)
        wait(lambda:'TEST_HOLD_CRC' in log('client') and 'BATCH_VERIFIED_JOIN_SENT' in log('host'),150,'Two incoming participants assigned to one native checkpoint before fault')
        result['edgeAtFault']={r:state(r) for r in active+['client','observer']};kill('client');release('client')
        active.append('observer')
        wait(lambda:ready(active),180,'Healthy observer completed the shared checkpoint after the other arrival disconnected')
        check('healthyArrivalIsObserver',all(any(p.get('name')=='HotJoinVisitor' and not p.get('kingdom') and not p.get('kingdomPtr') for p in state(r).get('players',[])) for r in active))
        retry()
    elif a.edge_case in ('manual-pause','manual-resume'):
        check('threeHumanScenario',a.witness)
        hold('client','crc');command('client','JoinDirectJoin',0)
        wait(lambda:'TEST_HOLD_CRC' in log('client'),120,'Incoming peer reached verified-file barrier before manual pause action')
        result['edgeAtFault']={r:state(r) for r in active+['client']}
        for r in active:command(r,'GamePause 0',.6)
        wait(lambda:all(state(r).get('paused')==0 for r in active),35,'Existing human players resumed through native pause votes during admission')
        if a.edge_case=='manual-pause':
            command('witness','GamePause 1',1)
            wait(lambda:all(state(r).get('paused')==1 for r in active),35,'Another player manually paused during admission')
        desired=int(a.edge_case=='manual-pause');result['edgeExpectedPause']=desired
        result['edgeAfterManualAction']={r:state(r) for r in active}
        release('client');roles=active+['client']
        wait(lambda:ready(roles),180,'All peers completed native loading after manual pause action')
        time.sleep(3);result['edgePauseAfterCommit']={r:state(r) for r in roles}
        check('manualPauseDecisionRetained',all(state(r).get('paused')==desired for r in roles))
        resume(roles);observe(roles)
    else:raise NotImplementedError(a.edge_case)
    result['experimentComplete']=True;report('Edge scenario completed; independent native evidence still decides acceptance')
