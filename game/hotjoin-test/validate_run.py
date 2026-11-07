"""Acceptance checks against retained native evidence, independent of the driver."""
import argparse,hashlib,json,re
from pathlib import Path

def rows(path):
    if not path.exists():return []
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]

def r2_active(peer):
    log=(peer/'game/Mods/plugins.log').read_text(errors='replace')
    if 'FAST_TRANSFER_R2_READY originalLobbyCoreSha256=' in log:return True
    manifest=peer/'composed-manifest.json'
    return manifest.is_file() and json.loads(manifest.read_text())['features'].get('bypass') is False and 'FAST_TRANSFER_R2_REUSED' in log

def validate(root,minimum_seconds=60):
    result=json.loads((root/'result.json').read_text())
    if result.get('startupOnly'):
        native=(root/'host/game/Logs/paws_hotjoin.log').read_text(errors='replace')
        observer=(root/'host/game/Mods/plugins.log').read_text(errors='replace')
        manifest=json.loads((root/'host/composed-manifest.json').read_text())
        checks=dict(driverCompleted=bool(result.get('experimentComplete')),mainMenu=result.get('startupState',{}).get('phase')==3,
            packagedHotJoinInstalled='HOTJOIN_READY revision=1 protocol=R' in native,
            observerOnly='PRODUCTION_RUNTIME_OBSERVER_READY' in observer,
            nativeChecks=manifest['features'].get('bypass') is False,
            legacyRecoveryDisabled=manifest['features'].get('legacySaveLobbyRecovery') is False,
            noNativeErrors=not result.get('errors'),normalExit=not result.get('activePeersRequiringForcedShutdown'))
        return dict(accepted=all(checks.values()),scope='packaged-arcane-hotjoin-startup-only-no-live-match',checks=checks,failedChecks=[k for k,v in checks.items() if not v])
    if result.get('replayOnly'):
        log='\n'.join(p.read_text(errors='replace') for p in (root/'host/game/Logs').glob('log-*.log'))
        after=result.get('replayAfter',{});before=result.get('replayBefore',{})
        checks=dict(driverCompleted=bool(result.get('experimentComplete')),noNativeErrors=not result.get('errors'),activePeerExitedNormally=not result.get('activePeersRequiringForcedShutdown'),nativeFilmWorldLoaded=before.get('mode')==4 and bool(before.get('world')),nativeEndOfFilmObserved='NetEvent Pop: END_OF_FILM' in log and 'MessageBox::_Display(End of Film)' in log,simulationAdvanced=after.get('seconds',0)-before.get('seconds',0)>=minimum_seconds)
        return dict(accepted=all(checks.values()),scope='owned-stock-1.3.72-recorded-post-return-segment-with-preserved-source-snapshot',checks=checks,failedChecks=[k for k,v in checks.items() if not v])
    if result.get('edgeCase'):
        from validate_edge import validate_edge
        return validate_edge(root,result,rows,minimum_seconds)
    if result.get('fixtureOnly'):
        checks={'driverCompleted':bool(result.get('experimentComplete') and result.get('transferFixturePassed')),
                'noNativeErrors':not result.get('errors'),
                'activePeersExitedNormally':not result.get('activePeersRequiringForcedShutdown')}
        files=[root/peer/'Documents/Kohan2/data/Save/HotJoinBoundary.RSG' for peer in ('host','client')]
        checks['preservedBytesIdentical']=all(p.is_file() and p.stat().st_size==result.get('fixtureBytes') and hashlib.sha256(p.read_bytes()).hexdigest()==result.get('fixtureSha256') for p in files)
        checks['exactBlockBoundaryExercised']=bool(result.get('fixtureBytes')) and result['fixtureBytes']%64==0
        checks['nativeSenderAcknowledged']=any(p.get('name')=='HotJoinOriginal' and p.get('fileState')==1 for p in result.get('hostAfterFixture',{}).get('players',[]))
        checks['worldWasNotLaunched']=all(result.get(peer+'AfterFixture',{}).get('mode')==1 and not result.get(peer+'AfterFixture',{}).get('world') for peer in ('host','client'))
        if result.get('transferMode')=='lobby-R2':checks['originalLobbyR2CoreActive']=all('FAST_TRANSFER_R2_READY originalLobbyCoreSha256=' in (root/peer/'game/Mods/plugins.log').read_text(errors='replace') for peer in ('host','client'))
        return dict(accepted=all(checks.values()),scope='isolated-stock-1.3.72-lobby-transfer-only-not-hotjoin',bytes=result.get('fixtureBytes'),seconds=result.get('fixtureElapsedSeconds'),sha256=result.get('fixtureSha256'),checks=checks,failedChecks=[k for k,v in checks.items() if not v])
    if result.get('repeatedReturns'):
        from validate_repeats import validate_repeats
        return validate_repeats(root,result,rows,minimum_seconds)
    h,c=result.get('hostAfterJoin',{}),result.get('clientAfterJoin',{})
    host_root=root/result.get('coordinatorDirectory','host')
    witness_root=root/result.get('witnessDirectory','witness')
    client_root=root/('host-return' if (root/'host-return').exists() else 'client-return' if (root/'client-return').exists() else 'client')
    reasons=[];checks={};transport_evidence=None
    def check(name,value):
        checks[name]=bool(value)
        if not value:reasons.append(name)
    check('driverCompleted',result.get('experimentComplete'))
    check('noNativeErrors',not result.get('errors'))
    composed=(host_root/'composed-manifest.json').is_file()
    if composed:
        composition_paths=[host_root,client_root]+([witness_root] if result.get('witness') else [])
        manifests=[json.loads((p/'composed-manifest.json').read_text()) for p in composition_paths]
        check('composedNativeChecksEnabled',all(m['features'].get('bypass') is False for m in manifests))
        check('composedFeaturesIdentical',all(m['features']==manifests[0]['features'] for m in manifests))
        check('composedAdaptersInstalled',all('COMPOSED_COLOR' in (p/'game/Mods/plugins.log').read_text(errors='replace') for p in composition_paths))
    if 'activePeersRequiringForcedShutdown' in result:check('activePeersExitedNormally',not result['activePeersRequiringForcedShutdown'])
    if result.get('transferMode')=='lobby-R2':
        paths=[host_root,client_root]+([witness_root] if result.get('witness') else [])
        if result.get('simultaneousAdmission')=='observer':paths.append(root/'observer')
        check('originalLobbyR2CoreActive',all(r2_active(p) for p in paths))
        if result.get('automaticCheckpoint'):
            saves=list((host_root/'Documents/Kohan2/data/Save').glob('PawHotJoin-*.RSG'))
            source=max(saves,key=lambda p:p.stat().st_mtime_ns) if saves else None
            original=source.read_bytes() if source else None
            identical=bool(original) and all((p/'Documents/Kohan2/data/Save'/source.name).exists() and (p/'Documents/Kohan2/data/Save'/source.name).read_bytes()==original for p in paths)
            check('checkpointTransportBytesMatchOnEveryPeer',identical)
            transport_evidence=dict(file=source.name if source else None,bytes=len(original) if original else 0,sha256=hashlib.sha256(original).hexdigest() if original else None,allPeersIdentical=identical)
    check('bothInGame',all(p.get('mode')==2 and p.get('phase')==4 and not p.get('frozen') and p.get('world') for p in (h,c)))
    check('hostSessionRetained',h.get('session')==result.get('hostBeforeJoin',{}).get('session') and bool(h.get('session')))
    check('nativeChecksEnabled',all(p.get('netDepth')==0 for p in (h,c)))
    if result.get('reusedClientPid'):
        identity=json.loads((client_root/'process.json').read_text())
        check('returnedWithoutRestartingGame',identity.get('pid')==result['reusedClientPid'] and client_root.name=='client' and result.get('reusedClientBeforeAdmission',{}).get('phase')==10)
    start_h=result.get('afterLoadHost',{}).get('seconds',result.get('hostBeforeJoin',{}).get('seconds',0))
    start_c=result.get('afterLoadClient',{}).get('seconds',start_h)
    advance=min(h.get('seconds',0)-start_h,c.get('seconds',0)-start_c)
    check('simulationAdvanced',advance>=minimum_seconds)
    hs=rows(host_root/'game/Mods/lab-state.jsonl')
    admission=result.get('hostBeforeAdmission',{}).get('ms',result.get('hostBeforeJoin',{}).get('ms'))
    check('noHostLobbyAfterAdmission',admission is not None and all(p.get('mode')==2 and p.get('phase')!=12 for p in hs if p.get('ms',0)>=admission and p.get('ms',0)<=h.get('ms',0)))
    def sync_rows(peer,world):
        return {(p['tick'],p['worldIndex']):p for p in rows(peer/'game/Mods/lab-sync.jsonl') if p['world']==world}
    sh,sc=sync_rows(host_root,h.get('world')),sync_rows(client_root,c.get('world'))
    common=sorted(sh.keys()&sc.keys());mismatches=[k for k in common if sh[k]['worldCrc']!=sc[k]['worldCrc']]
    common_span=(common[-1][0]-common[0][0])/16 if len(common)>1 else 0
    check('matchingSimulationChecksums',len(common)>=2 and not mismatches)
    check('checksumObservationDuration',common_span>=minimum_seconds)
    def commits(peer):
        text=(peer/'game/Mods/plugins.log').read_text(errors='replace')
        return re.findall(r'COORDINATED_NATIVE_COMMIT netIndex=(\d+) netCrc=(\d+)',text)
    hc,cc=commits(host_root),commits(client_root)
    check('nativeFullWorldCommitMatches',bool(hc and cc) and hc[-1]==cc[-1])
    witness_evidence=None
    if result.get('witness'):
        w=result.get('witnessAfterJoin',{});before_w=result.get('witnessBeforeDrop',{})
        sw=sync_rows(witness_root,w.get('world'));shared=sorted(sh.keys()&sc.keys()&sw.keys())
        bad=[k for k in shared if len({sh[k]['worldCrc'],sc[k]['worldCrc'],sw[k]['worldCrc']})!=1]
        span=(shared[-1][0]-shared[0][0])/16 if len(shared)>1 else 0
        witness_evidence=dict(commonSamples=len(shared),commonSeconds=span,mismatches=bad)
        check('threeWorldChecksumsMatch',len(shared)>=2 and not bad and span>=minimum_seconds)
        check('thirdPeerInGame',w.get('phase')==4 and w.get('mode')==2 and w.get('world') and not w.get('frozen') and w.get('netDepth')==0)
        if not result.get('doubleDeparture'):check('thirdSessionRetained',bool(w.get('session')) and w.get('session')==before_w.get('session'))
        check('thirdSimulationAdvanced',w.get('seconds',0)-result.get('afterLoadWitness',{}).get('seconds',0)>=minimum_seconds)
        before_players=[p for p in result.get('hostBeforeJoin',{}).get('players',[]) if not p.get('ai')]
        check('startedWithThreeHumanKingdoms',len(before_players)==3 and len({p.get('kingdom') for p in before_players if p.get('kingdom') and p.get('kingdomPtr')})==3)
        witness_name='HotJoinOriginal' if witness_root.name=='client' else 'HotJoinWitness'
        original_w=next((p for p in before_w.get('players',[]) if p['name']==witness_name),{})
        # The stock nickname edit limits length (the former test name was
        # truncated to HotJoinWitnessRena). Ownership is identified by the
        # original kingdom, not by assuming the requested UI text survived.
        current_w=next((p for p in w.get('players',[]) if (not p.get('ai') and p.get('kingdom')==original_w.get('kingdom') if result.get('doubleDeparture') else p['name']==witness_name)),{})
        check('thirdKingdomRetained',bool(original_w.get('kingdom')) and current_w.get('kingdom')==original_w.get('kingdom') and current_w.get('kingdomPtr') and not current_w.get('ai') and not current_w.get('kingdomAi'))
        wc=commits(witness_root);check('threeNativeCommitsMatch',bool(hc and cc and wc) and hc[-1]==cc[-1]==wc[-1])
        role_maps=[sorted((p['id'],p['ai'],p['implicit'],p['kingdom']) for p in peer.get('players',[])) for peer in (h,c,w)]
        check('threeSessionRoleMapsMatch',role_maps[0]==role_maps[1]==role_maps[2] and bool(role_maps[0]))
        admission_w=result.get('witnessBeforeAdmission',{}).get('ms',before_w.get('ms'))
        ws=rows(witness_root/'game/Mods/lab-state.jsonl')
        if not result.get('doubleDeparture'):check('noThirdLobbyDuringReturn',admission_w is not None and all(p.get('mode')==2 and p.get('phase')!=12 for p in ws if p.get('ms',0)>=admission_w and p.get('ms',0)<=w.get('ms',0)))
        if result.get('doubleDeparture'):
            check('secondParticipantReclaimedOwnKingdom',result.get('secondReturnCompleted') and current_w.get('kingdom')==result.get('secondOriginalParticipant',{}).get('kingdom') and current_w.get('kingdomAi')==0 and current_w.get('aiControllers')==0)
            if result.get('simultaneousAdmission')=='return':
                check('bothReturnsUsedOneSharedCheckpoint',len(hc)==len(cc)==len(wc)==1)
            else:
                check('twoSeparateNativeCheckpointCycles',len(hc)>=2 and len(cc)>=2 and len(wc)>=1)
                check('firstReturnDidNotResumeWhileSecondAbsent',all(p.get('paused')==1 for p in result.get('firstReturnBeforeSecond',{}).values()) and len(result.get('firstReturnBeforeSecond',{}))==2)
    if result.get('simultaneousAdmission'):
        host_log=(host_root/'game/Mods/plugins.log').read_text(errors='replace')
        times=re.findall(r'\[(\d+):(\d+):(\d+)\.(\d+)\] hotjoin-lab: TICKET_CONNECT capable=1',host_log)
        stamps=[int(h)*3600+int(m)*60+int(s)+int(ms)/1000 for h,m,s,ms in times[-2:]]
        gap=(stamps[-1]-stamps[0])%86400 if len(stamps)==2 else 86400
        check('twoNativeRequestsArrivedTogether',result.get('simultaneousRequestGapMs',1e9)<500 and gap<1)
        check('authenticatedBatchAdmissionUsed',all(marker in host_log for marker in ('BATCH_AUTHENTICATED_JOIN_QUEUED','BATCH_VERIFIED_JOIN_SENT')) and 'NATIVE_REJECT' not in host_log)
    if result.get('simultaneousAdmission')=='observer':
        o=result.get('observerAfterJoin',{});observer_root=root/'observer'
        so=sync_rows(observer_root,o.get('world'));shared=sorted(sh.keys()&sc.keys()&sw.keys()&so.keys())
        bad=[k for k in shared if len({sh[k]['worldCrc'],sc[k]['worldCrc'],sw[k]['worldCrc'],so[k]['worldCrc']})!=1]
        span=(shared[-1][0]-shared[0][0])/16 if len(shared)>1 else 0
        check('fourthPeerJoinedAsObserver',o.get('phase')==4 and o.get('mode')==2 and not o.get('frozen') and o.get('netDepth')==0 and any(p.get('name')=='HotJoinVisitor' and not p.get('ai') and not p.get('kingdom') and not p.get('kingdomPtr') for p in o.get('players',[])))
        check('fourPeerSimulationMatches',not bad and span>=minimum_seconds and o.get('seconds',0)-result.get('afterLoadObserver',{}).get('seconds',0)>=minimum_seconds)
        oc=commits(observer_root);check('fourFullNativeCommitsMatch',bool(hc and cc and wc and oc) and hc[-1]==cc[-1]==wc[-1]==oc[-1])
        observer_roles=sorted((p['id'],p['ai'],p['implicit'],p['kingdom']) for p in o.get('players',[]))
        check('fourSessionRoleMapsMatch',bool(observer_roles) and all(p==observer_roles for p in role_maps))
        witness_evidence['fourPeer']=dict(commonSamples=len(shared),commonSeconds=span,mismatches=bad)
    scenario=result.get('scenario','visitor');name={'return':'HotJoinRenamed','impostor':'HotJoinOriginal','visitor':'HotJoinVisitor'}[scenario]
    if result.get('roleNoticesRequired'):
        first=next((p for p in h.get('players',[]) if p['name']==name),{}).get('id')
        second=next((p for p in h.get('players',[]) if not p.get('ai') and p.get('kingdom')==result.get('secondOriginalParticipant',{}).get('kingdom')),{}).get('id') if result.get('doubleDeparture') else None
        expected={first:0 if scenario=='return' else 1}
        if second:expected[second]=0
        if result.get('simultaneousAdmission')=='observer':
            visitor=next((p for p in h.get('players',[]) if p['name']=='HotJoinVisitor'),{}).get('id')
            expected[visitor]=1
        peer_expected=[(host_root,expected),(client_root,expected)]
        if result.get('witness'):peer_expected.append((witness_root,{second:0} if second and not result.get('simultaneousAdmission') else expected))
        if result.get('simultaneousAdmission')=='observer':peer_expected.append((root/'observer',expected))
        notice_checks=[]
        for peer,required in peer_expected:
            log=(peer/'game/Mods/plugins.log').read_text(errors='replace')
            shown=[(int(pid),int(observer),int(ok)) for pid,observer,ok in re.findall(r'ROLE_NOTICE_SHOWN playerId=(\d+) observer=(\d+) nativeResult=(\d+)',log)]
            notice_checks.append(all(pid and shown.count((pid,observer,1))==1 for pid,observer in required.items()) and len(shown)==len(required) and 'ROLE_NOTICE_LOCALE_MISSING' not in log)
        check('nativeRoleNoticeOnceOnEveryPeer',all(notice_checks))
    if result.get('leaveMode')=='menu' and scenario!='visitor':
        departed=result.get('departedClientAfterMenu',{})
        check('ordinaryExitReachedPostGameScreen',departed.get('mode')==1 and departed.get('phase')==12 and all(not p.get('kingdomPtr') for p in departed.get('players',[])))
        drop=result.get('hostAfterDrop',{})
        if result.get('manualResumePolicy'):
            after=result.get('hostAfterPauseWait',{})
            check('ordinaryExitRemainedPaused',drop.get('paused')==1 and after.get('paused')==1 and drop.get('worldTicks')==after.get('worldTicks'))
        else:
            check('matchContinuedAfterOrdinaryExit',bool(drop.get('world')) and result.get('hostBeforeAdmission',{}).get('seconds',0)>drop.get('seconds',0))
    if result.get('manualResumePolicy'):
        paused=result.get('beforeManualResume',{})
        roles=('host','client','witness') if result.get('witness') else ('host','client')
        if result.get('simultaneousAdmission')=='observer':roles+=('observer',)
        check('returnRetainedPauseUntilPlayersResume',all(paused.get(role,{}).get('paused')==1 and paused.get(role,{}).get('worldTicks')==result.get('afterLoad'+role.title(),{}).get('worldTicks') for role in roles))
        check('testPlayerExplicitlyResumed',result.get('testPlayerResumed'))
    if result.get('pauseStateRestorationPolicy') and not result.get('expectedPauseAfterJoin'):
        active=('host','client','witness') if result.get('witness') else ('host','client')
        if result.get('simultaneousAdmission')=='observer':active+=('observer',)
        after=result.get('beforeManualResume',{})
        check('runningMatchAutomaticallyResumed',result.get('automaticResumeObserved') and not result.get('testPlayerResumed') and all(after.get(role,{}).get('paused')==0 and after[role].get('worldTicks',0)>result.get('afterLoad'+role.title(),{}).get('worldTicks',0) for role in active))
    if result.get('pauseStateRestorationPolicy'):
        paths=[host_root,client_root]+([witness_root] if result.get('witness') else [])
        if result.get('simultaneousAdmission')=='observer':paths.append(root/'observer')
        expected=int(bool(result.get('expectedPauseAfterJoin')))
        states=[re.findall(r'JOIN_PAUSE_COMMITTED paused=(\d+) ownerId=(\d+)',(p/'game/Mods/plugins.log').read_text(errors='replace')) for p in paths]
        check('authoritativePauseStateMatchesOnEveryPeer',all(p and int(p[-1][0])==expected for p in states) and len({p[-1] for p in states if p})==1)
    if result.get('departureRole')=='host':
        check('remainingPeerBecameHost',h.get('host')==1 and host_root.name!='host' and bool(result.get('migratedHostEndpoint')))
    if result.get('uncleared'):
        check('originalSlotWasNotDeletedByDriver',result.get('unclearedOriginalPresent') and all(not re.search(r'COMMAND \d+: CSDKick', (p/'game/Mods/plugins.log').read_text(errors='replace')) for p in (host_root,witness_root)))
        initial=result.get('hostAfterDrop',{});waiting=result.get('hostAfterPauseWait',{})
        check('connectionLossStoppedSimulation',bool(initial.get('paused') or initial.get('backup')) and bool(waiting.get('paused') or waiting.get('backup')) and initial.get('worldTicks')==waiting.get('worldTicks'))
    if result.get('continuedWithoutParticipant'):
        continued=result['continuedWithoutParticipant'];kingdom=result.get('originalParticipant',{}).get('kingdom')
        check('playersCanContinueWithoutAbsentParticipant',continued.get('paused')==0 and continued.get('seconds',0)>=result.get('hostAfterPauseWait',{}).get('seconds',0)+3 and any(p.get('ai') and p.get('kingdom')==kingdom for p in continued.get('players',[])))
    if result.get('controlOrdersRequired'):
        controls=result.get('controlOrders',{});expected=('client','witness') if result.get('doubleDeparture') else ('client',)
        check('returningOwnersExecutedNativeOrders',all(role in controls and controls[role]['before'].get('selectionSally')==1 and controls[role]['opened'].get('selectionRecall')==1 and controls[role]['recalled'].get('selectionSally')==1 and len({controls[role][stage].get('selectionActor') for stage in ('before','opened','recalled')})==1 and bool(controls[role]['before'].get('selectionKingdom')) for role in expected))
        if result.get('doubleDeparture'):
            kingdom=result.get('secondOriginalParticipant',{}).get('kingdom')
            holder=next((p for p in result.get('witnessAfterJoin',{}).get('players',[]) if not p.get('ai') and p.get('kingdom')==kingdom),{})
            check('secondOwnerOrdersBoundToOwnKingdom',bool(holder.get('kingdomPtr')) and controls.get('witness',{}).get('before',{}).get('selectionKingdom')==holder.get('kingdomPtr'))
    if result.get('automaticCheckpoint'):
        host_log=(host_root/'game/Mods/plugins.log').read_text(errors='replace')
        pause_marker='AUTO_PAUSE_RETAINED' if result.get('manualResumePolicy') else 'AUTO_PRIOR_PAUSE_RESTORED paused=0'
        check('connectionTriggeredCheckpoint',all(marker in host_log for marker in ('AUTO_CAPTURE_REQUESTED','AUTO_NATIVE_SAVE_COMPLETE','AUTO_VERIFIED_JOIN_SENT','AUTO_RETURN_COMMITTED',pause_marker)))
        check('automaticLoadingUi',all(re.search(r'AUTO_(USER_READY|UI_ALREADY_READY)',(p/'game/Mods/plugins.log').read_text(errors='replace')) for p in (host_root,client_root)))
        check('sharedVerifiedLoadBarrier',all('SHARED_CHECKPOINT_READY' in (p/'game/Mods/plugins.log').read_text(errors='replace') for p in (host_root,client_root)))
        check('noDriverCheckpoint',not re.search(r'COMMAND \d+: (!snapshot|GameSave)',host_log))
        check('automaticColdTransfer',not result.get('clientCheckpointPreseeded'))
    players=[next((p for p in peer.get('players',[]) if p['name']==name),{}) for peer in (h,c)]
    if scenario=='return':
        kingdom=result.get('originalParticipant',{}).get('kingdom')
        check('returningPlayerOwnsOriginalKingdom',bool(kingdom) and all(p.get('kingdom')==kingdom and p.get('kingdomPtr') and not p.get('ai') for p in players))
        check('replacementAiRemoved',bool(kingdom) and all(not any(p.get('ai') and p.get('kingdom')==kingdom for p in peer.get('players',[])) for peer in (h,c)))
        check('kingdomNoLongerAi',all(p.get('kingdomAi')==0 for p in players))
        check('aiControllerRetired',all(p.get('aiControllers')==0 for p in players))
    else:
        check('newPlayerIsObserver',all(p and p.get('kingdom')=='' and p.get('kingdomPtr')==0 for p in players))
        if scenario=='impostor':
            kingdom=result.get('originalParticipant',{}).get('kingdom')
            check('sameNameDoesNotStealAiKingdom',bool(kingdom) and all(any(p.get('ai') and p.get('kingdom')==kingdom for p in peer.get('players',[])) for peer in (h,c)))
    scope=('isolated-arcane-wars-0.5.0-beta.1-native-checks-' if composed else 'isolated-stock-1.3.72-')+('four' if result.get('simultaneousAdmission')=='observer' else 'three' if result.get('witness') else 'two')+'-peer-LAN'
    return dict(accepted=not reasons,scope=scope,scenario=scenario,leaveMode=result.get('leaveMode','crash'),automaticCheckpoint=bool(result.get('automaticCheckpoint')),minimumSeconds=minimum_seconds,simulationAdvance=advance,commonChecksumSamples=len(common),commonChecksumSeconds=common_span,checksumMismatches=mismatches,witness=witness_evidence,checkpointPreseeded=bool(result.get('clientCheckpointPreseeded')),checkpointTransfer=transport_evidence,checks=checks,failedChecks=reasons)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--minimum-seconds',type=float,default=60);a=ap.parse_args()
    result=validate(a.root,a.minimum_seconds);(a.root/'acceptance.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['accepted'] else 1)
if __name__=='__main__':main()
