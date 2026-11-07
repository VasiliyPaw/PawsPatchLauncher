"""Independent acceptance for retained repeat-return native evidence."""
import re
from collections import Counter

def validate_repeats(root,result,rows,minimum_seconds):
    checks={};cycles=[]
    def check(name,value):checks[name]=bool(value)
    evidence=result.get('repeatedReturns',[])
    consecutive_hosts=result.get('repeatPlan')==['host','host']
    check('driverCompletedSequence',result.get('experimentComplete') and result.get('repeatSequenceComplete'))
    check('allRequestedReturnsRecorded',len(evidence)==len(result.get('repeatPlan',[]))+1 and len(evidence)>=(3 if consecutive_hosts else 4))
    check('noNativeErrorsIncludingShutdown',not result.get('errors'))
    if 'activePeersRequiringForcedShutdown' in result:check('activePeersExitedNormally',not result['activePeersRequiringForcedShutdown'])
    original_humans=[p for p in result.get('hostBeforeJoin',{}).get('players',[]) if not p.get('ai') and p.get('kingdom')]
    check('startedWithThreeHumanKingdoms',len(original_humans)==3 and len({p['kingdom'] for p in original_humans})==3)
    for cycle in evidence:
        number=cycle['number'];target=cycle['target'];roles=('host','client','witness')
        local={}
        def item(name,value):local[name]=bool(value);check('cycle'+str(number)+':'+name,value)
        paths={role:root/cycle.get('directories',{}).get(role,'INVALID') for role in roles}
        states=cycle.get('afterObserve',{});loaded=cycle.get('afterLoad',{});held=cycle.get('afterPauseHold',{})
        item('threeActivePeers',len(states)==3 and all(p.get('mode')==2 and p.get('phase')==4 and p.get('world') and not p.get('frozen') and p.get('netDepth')==0 for p in states.values()))
        owner=[]
        for role in roles:
            p=next((p for p in states.get(role,{}).get('players',[]) if p['name']==cycle['nickname'] and not p['ai']),{})
            owner.append(p)
        kingdom=cycle.get('original',{}).get('kingdom')
        item('sameKingdomReclaimed',bool(kingdom) and all(p.get('kingdom')==kingdom and p.get('kingdomPtr') and p.get('kingdomAi')==0 and p.get('aiControllers')==0 for p in owner))
        item('replacementAiRetired',all(not any(p.get('ai') and p.get('kingdom')==kingdom for p in states.get(role,{}).get('players',[])) for role in roles))
        role_maps=[sorted((p['id'],p['ai'],p['implicit'],p['kingdom']) for p in states.get(role,{}).get('players',[])) for role in roles]
        item('allRoleMapsMatch',bool(role_maps[0]) and role_maps[0]==role_maps[1]==role_maps[2])
        item('allThreeOriginalKingdomsHuman',all({p.get('kingdom') for p in states.get(role,{}).get('players',[]) if not p.get('ai') and p.get('kingdomPtr')}=={p['kingdom'] for p in original_humans} for role in roles))
        before=cycle.get('beforeAdmission',{})
        retained=[role for role in roles if role!=target]
        item('existingSessionsRetained',all(before.get(role,{}).get('session') and before[role]['session']==states.get(role,{}).get('session') for role in retained))
        if number>1:
            departure=cycle.get('afterDeparture',{});departure_hold=cycle.get('afterDepartureHold',{})
            item('departureRemainedPaused',len(departure_hold)==2 and all(p.get('paused')==1 and p.get('worldTicks')==departure.get(role,{}).get('worldTicks') for role,p in departure_hold.items()))
            item('normalExitToStaging',cycle.get('departedAfterMenu',{}).get('phase')==12 and cycle.get('departedAfterMenu',{}).get('mode')==1)
            if cycle.get('departedWasHost'):item('nativeHostMigrated',states.get(cycle.get('coordinator'),{}).get('host')==1 and cycle.get('coordinator')!=target)
        paused=bool(cycle.get('expectedPaused'))
        item('pauseStateRestored',len(held)==3 and all(p.get('paused')==int(paused) and (p.get('worldTicks')==loaded.get(role,{}).get('worldTicks') if paused else p.get('worldTicks',0)>loaded.get(role,{}).get('worldTicks',0)) for role,p in held.items()))
        item('correctResumeDecision',cycle.get('manualResume') if paused else cycle.get('automaticResumeObserved') and not cycle.get('manualResume'))
        crc_sets=[];full_commits=[];pause_states=[];notices=[]
        for role in roles:
            log_path=paths[role]/'game/Mods/plugins.log'
            log=log_path.read_text(errors='replace') if log_path.exists() else ''
            count=cycle.get('commitCounts',{}).get(role,0)
            commits=re.findall(r'COORDINATED_NATIVE_COMMIT netIndex=(\d+) netCrc=(\d+)',log)
            full_commits.append(commits[count-1] if 0<count<=len(commits) else None)
            pauses=re.findall(r'JOIN_PAUSE_COMMITTED paused=(\d+) ownerId=(\d+)',log)
            pause_states.append(pauses[count-1] if 0<count<=len(pauses) else None)
            pid=next((p.get('id') for p in states.get(role,{}).get('players',[]) if p['name']==cycle['nickname'] and not p['ai']),None)
            shown=re.findall(r'ROLE_NOTICE_SHOWN playerId=(\d+) observer=(\d+) nativeResult=(\d+)',log)
            notices.append(pid is not None and shown.count((str(pid),'0','1'))==1 and 'ROLE_NOTICE_LOCALE_MISSING' not in log)
            start=loaded.get(role,{});end=states.get(role,{})
            crc_sets.append({(p['tick'],p['worldIndex']):p for p in rows(paths[role]/'game/Mods/lab-sync.jsonl') if p.get('world')==end.get('world') and start.get('worldTicks',0)<=p['tick']<=end.get('worldTicks',0)})
            session_rows=rows(paths[role]/'game/Mods/lab-state.jsonl')
            if role!=target:
                item(role+'DidNotEnterLobby',all(p.get('mode')==2 and p.get('phase')!=12 for p in session_rows if before.get(role,{}).get('ms',0)<=p.get('ms',0)<=end.get('ms',0)))
        item('fullNativeCommitsMatch',bool(full_commits[0]) and full_commits[0]==full_commits[1]==full_commits[2])
        item('pauseOwnersMatch',bool(pause_states[0]) and pause_states[0]==pause_states[1]==pause_states[2] and int(pause_states[0][0])==int(paused))
        item('oneNativeReturnNoticePerPeer',all(notices))
        common=sorted(set.intersection(*(set(p) for p in crc_sets)))
        bad=[key for key in common if len({p[key]['worldCrc'] for p in crc_sets})!=1]
        span=(common[-1][0]-common[0][0])/16 if len(common)>1 else 0
        advance=min((states.get(role,{}).get('seconds',0)-loaded.get(role,{}).get('seconds',0) for role in roles),default=0)
        item('oneMinuteMatchingSimulation',not bad and span>=minimum_seconds and advance>=minimum_seconds)
        controls=cycle.get('controls',{}).get(target,{})
        item('ownerExecutedSallyAndRecall',controls.get('before',{}).get('selectionSally')==1 and controls.get('opened',{}).get('selectionRecall')==1 and controls.get('recalled',{}).get('selectionSally')==1 and len({controls.get(stage,{}).get('selectionActor') for stage in ('before','opened','recalled')})==1 and bool(controls.get('before',{}).get('selectionActor')))
        cycles.append(dict(number=number,target=target,kingdom=kingdom,expectedPaused=paused,simulationAdvance=advance,commonChecksumSamples=len(common),commonChecksumSeconds=span,mismatches=bad,accepted=all(local.values())))
    identities=Counter(c.get('original',{}).get('kingdom') for c in evidence)
    if consecutive_hosts:
        check('twoConsecutiveCurrentHostsReturned',len(evidence)==3 and all(c.get('departedWasHost') for c in evidence[1:]))
    else:check('sameParticipantReturnedRepeatedly',any(n>=3 for k,n in identities.items() if k))
    check('differentParticipantsReturned',len([k for k in identities if k])>=3)
    check('includedCurrentHostDeparture',any(c.get('departedWasHost') for c in evidence))
    check('bothPausePoliciesCovered',{bool(c.get('expectedPaused')) for c in evidence}=={False,True})
    return dict(accepted=all(checks.values()),scope='isolated-stock-1.3.72-three-peer-LAN-'+('consecutive-host-returns' if consecutive_hosts else 'repeated-returns'),minimumSeconds=minimum_seconds,cycles=cycles,checks=checks,failedChecks=[k for k,v in checks.items() if not v])
