"""Owned three-peer repeat-return scenario in ONE continuously retained match."""
import json,re,shutil,subprocess,time

ROLES=('host','client','witness')

def commits(peer):
    path=peer['game']/'Mods/plugins.log'
    return re.findall(r'COORDINATED_NATIVE_COMMIT netIndex=(\d+) netCrc=(\d+)',path.read_text(errors='replace')) if path.exists() else []

def run_sequence(a,root,peers,result,expected_exits,state,command,wait,prepare,launch,open_lan,errors,report):
    def all_states():return {role:state(role) for role in ROLES}
    def directories():return {role:peers[role]['root'].name for role in ROLES}
    initial=dict(number=1,target='client',requested='client',nickname=peers['client']['nickname'],
        original=result['originalParticipant'],expectedPaused=result['expectedPauseAfterJoin'],
        beforeAdmission={role:result.get(role+'BeforeAdmission',result.get('hostBeforeAdmission',{})) for role in ROLES},
        afterLoad={role:result['afterLoad'+role.title()] for role in ROLES},
        afterPauseHold=result['beforeManualResume'],afterObserve=all_states(),directories=directories(),
        commitCounts={role:len(commits(peers[role])) for role in ROLES},controls=result.get('controlOrders',{}),
        automaticResumeObserved=result.get('automaticResumeObserved',False),manualResume=result.get('testPlayerResumed',False))
    result['repeatedReturns']=[initial];result['repeatPlan']=a.repeat_plan.split(',');result['repeatInterval']=a.interval
    def retain():
        (root/'repeat-progress.json').write_text(json.dumps(result['repeatedReturns'],indent=2))
    retain()
    for number,requested in enumerate(result['repeatPlan'],2):
        target=next(role for role in ROLES if state(role).get('host')) if requested=='host' else requested
        old=peers[target];nickname=old['nickname'];before=all_states()
        original=next(p for p in before[target]['players'] if p['name']==nickname and not p['ai'])
        assert original.get('kingdom') and original.get('kingdomPtr'), 'Repeated returner must own a human kingdom'
        remaining=tuple(role for role in ROLES if role!=target)
        cycle=dict(number=number,requested=requested,target=target,nickname=nickname,original=original,
            beforeDeparture=before,departedWasHost=bool(before[target].get('host')),leaveMode='menu')
        result['repeatedReturns'].append(cycle);retain()
        report(f'Repeat {number}: {target} ({nickname}) leaves the same running match')
        command(target,'RequestLeaveGame',0)
        wait(lambda:state(target).get('mode')==1 and state(target).get('phase')==12,75,f'Repeat {number}: native ordinary exit completed')
        cycle['departedAfterMenu']=state(target)
        wait(lambda:all(any(p.get('ai') and p.get('implicit') and p.get('kingdom')==original['kingdom'] for p in state(role).get('players',[])) for role in remaining),95,f'Repeat {number}: native AI holds the departed kingdom')
        cycle['afterDeparture']={role:state(role) for role in remaining}
        time.sleep(5)
        cycle['afterDepartureHold']={role:state(role) for role in remaining}
        assert all(p.get('paused')==1 and p['worldTicks']==cycle['afterDeparture'][role]['worldTicks'] for role,p in cycle['afterDepartureHold'].items()), 'Repeated departure must preserve the pause'
        expected_exits.add(old['process'].pid);command(target,'ReallyQuit',.2)
        try:old['process'].wait(timeout=10)
        except subprocess.TimeoutExpired:old['process'].terminate();old['process'].wait(timeout=10)
        assert not errors(), 'Repeated ordinary exit must not produce a native exception'
        peers['retired-'+target+'-'+str(number)]=peers.pop(target)
        wait(lambda:any(state(role).get('host') for role in remaining),95,f'Repeat {number}: native host is settled')
        coordinator=next(role for role in remaining if state(role).get('host'))
        pid=peers[coordinator]['process'].pid
        port=subprocess.check_output(['powershell','-NoProfile','-Command',f'(Get-NetUDPEndpoint -OwningProcess {pid} | Select-Object -First 1).LocalPort'],text=True).strip()
        assert port.isdecimal() and 0<int(port)<65536
        # Alternate retained departure pause and deliberate player continuation.
        # The latter must automatically resume after the following admission.
        cycle['expectedPaused']=not bool(number%2)
        if not cycle['expectedPaused']:
            baseline=min(state(role)['seconds'] for role in remaining)
            for role in remaining:command(role,'GamePause 0',1)
            wait(lambda:all(state(role).get('paused')==0 for role in remaining) and min(state(role)['seconds'] for role in remaining)>=baseline+3,25,f'Repeat {number}: players continue without the absent participant')
        cycle['beforeAdmission']={role:state(role) for role in remaining}
        cycle['coordinator']=coordinator;cycle['endpoint']='127.0.0.1:'+port
        prepare(target,'repeat-'+str(number)+'-'+target)
        peers[target]['joinAddress']=cycle['endpoint']
        shutil.copytree(old['docs']/'Kohan2/data/User',peers[target]['docs']/'Kohan2/data/User',dirs_exist_ok=True)
        credential=peers[target]['docs']/'Kohan2/data/User/HotJoinTicket.bin'
        assert credential.stat().st_size==32
        old_counts={role:len(commits(peers[role])) for role in ROLES}
        cycle['directories']=directories();retain()
        launch(target);open_lan(target,nickname)
        command(target,'LobbyJoinDirect',2);command(target,'JoinDirectJoin',1)
        wait(lambda:all(len(commits(peers[role]))>old_counts[role] and state(role).get('phase')==4 and state(role).get('mode')==2 and not state(role).get('frozen') for role in ROLES),480,f'Repeat {number}: all three completed another native checkpoint')
        cycle['afterLoad']=all_states();cycle['commitCounts']={role:len(commits(peers[role])) for role in ROLES}
        for role in ROLES:command(role,'ScreenShot',.3)
        time.sleep(5);cycle['afterPauseHold']=all_states()
        assert all(p.get('paused')==int(cycle['expectedPaused']) for p in cycle['afterPauseHold'].values()), 'Repeated return must restore the pre-admission pause'
        if cycle['expectedPaused']:
            assert all(p['worldTicks']==cycle['afterLoad'][role]['worldTicks'] for role,p in cycle['afterPauseHold'].items())
            for role in ROLES:command(role,'GamePause 0',1)
            wait(lambda:all(state(role).get('paused')==0 for role in ROLES),25,f'Repeat {number}: players manually resume their retained pause')
            cycle['manualResume']=True
        else:
            assert all(p['worldTicks']>cycle['afterLoad'][role]['worldTicks'] for role,p in cycle['afterPauseHold'].items())
            cycle['automaticResumeObserved']=True
        command(target,'CycleSelection 0',1)
        wait(lambda:state(target).get('selectionActor') and (state(target).get('selectionSally') or state(target).get('selectionRecall')),20,f'Repeat {number}: returning owner selects its city')
        if state(target).get('selectionRecall'):
            command(target,'ActorCommand recall',1)
            wait(lambda:state(target).get('selectionSally')==1,20,f'Repeat {number}: owner recalls existing militia')
        closed=state(target);command(target,'ActorCommand sally_forth',1)
        wait(lambda:state(target).get('selectionRecall')==1,20,f'Repeat {number}: native Sally executed')
        opened=state(target);command(target,'ActorCommand recall',1)
        wait(lambda:state(target).get('selectionSally')==1,20,f'Repeat {number}: native Recall executed')
        cycle['controls']={target:dict(before=closed,opened=opened,recalled=state(target))};retain()
        # Include >=60 s between common checksum samples despite phase offsets.
        start=min(p['seconds'] for p in cycle['afterLoad'].values())
        wait(lambda:min(state(role).get('seconds',0) for role in ROLES)>=start+a.interval+3, a.interval+45,f'Repeat {number}: at least one minute of actual simulation after return')
        cycle['afterObserve']=all_states();cycle['nativeErrors']=errors();retain()
        assert not cycle['nativeErrors'], 'Repeated return produced a native error'
    result['repeatSequenceComplete']=True
