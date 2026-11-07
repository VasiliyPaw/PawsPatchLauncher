"""Independent acceptance for retained lifecycle/failure evidence."""
import re
def validate_edge(root,result,rows,minimum):
    checks=dict(result.get('edgeChecks',{}));checks['driverCompleted']=bool(result.get('experimentComplete'))
    checks['noNativeErrors']=not result.get('errors');checks['activePeersExitedNormally']=not result.get('activePeersRequiringForcedShutdown')
    after=result.get('edgeObserveAfter',{});before=result.get('edgeObserveBefore',{});dirs=result.get('edgeDirectories',{})
    paths={r:root/d for r,d in dirs.items()}
    checks['allObservedPeersInGame']=bool(after) and all(s.get('phase')==4 and s.get('mode')==2 and not s.get('backup') and not s.get('frozen') and s.get('netDepth')==0 for s in after.values())
    checks['observedSimulationAdvanced']=bool(after) and all(s.get('seconds',0)-before.get(r,{}).get('seconds',0)>=minimum for r,s in after.items())
    streams={r:{(s['tick'],s['worldIndex']):s['worldCrc'] for s in rows(paths[r]/'game/Mods/lab-sync.jsonl') if s['world']==after[r].get('world')} for r in paths}
    common=set.intersection(*(set(s) for s in streams.values())) if streams else set();common=sorted(common)
    span=(common[-1][0]-common[0][0])/16 if len(common)>1 else 0
    bad=[k for k in common if len({s[k] for s in streams.values()})!=1]
    checks['allPeerMinuteChecksumsMatch']=span>=minimum and not bad
    def native_log(p):
        extra=p/'game/Logs/paws_hotjoin.log'
        return (p/'game/Mods/plugins.log').read_text(errors='replace')+('\n'+extra.read_text(errors='replace') if extra.exists() else '')
    logs={r:native_log(p) for r,p in paths.items()}
    commits=[re.findall(r'COORDINATED_NATIVE_COMMIT netIndex=(\d+) netCrc=(\d+)',t) for t in logs.values()]
    checks['lastNativeCommitsMatch']=bool(commits) and all(c for c in commits) and len({c[-1] for c in commits if c})==1
    if result.get('edgeCase')=='finish-during-join':
        checks['actualNativeResignTested']=bool(result.get('edgeChecks',{}).get('nativeResignExecuted') and result.get('edgeChecks',{}).get('resignDecisionRetained'))
    fault=result.get('edgeAtFault',{});victim=next((p.get('id') for p in fault.get('host',{}).get('players',[]) if p.get('name') in ('HotJoinRenamed','HotJoinVisitor')),None)
    if victim and result.get('edgeCase','').startswith(('cancel-','timeout-','batch-loss')):
        checks['noFalseNoticeForFailedAdmission']=all(not re.search(r'ROLE_NOTICE_SHOWN playerId='+str(victim)+r'\b',t) for r,t in logs.items() if r!='client')
    if result.get('edgeCase') in ('host-transfer','host-partial-transfer','host-load'):
        cancelled=result.get('edgeAfterCancellation',{})
        survivors=result.get('edgeSurvivors',['witness'])
        checks['cancelledArrivalsReturnedToLobby']=bool(cancelled) and all(s.get('mode')==0 and s.get('phase')==10 for r,s in cancelled.items() if r not in survivors)
        ids=[p.get('id') for p in fault.get('witness',{}).get('players',[]) if p.get('name') in ('HotJoinRenamed','HotJoinVisitor')]
        checks['expectedAdmissionGroupExercised']=len(ids)==(2 if result.get('simultaneousAdmission')=='observer' else 1)
        checks['noFalseNoticeForCancelledArrivals']=bool(ids) and all(not re.search(r'ROLE_NOTICE_SHOWN playerId='+str(pid)+r'\b',t) for pid in ids for r,t in logs.items() if r!='client')
        if result.get('edgeChecks',{}).get('nativeMenuExitAvailableAtTarget'):
            checks['leavingHostClearedPendingWork']='LOCAL_ADMISSION_CANCELLED_SESSION_LEFT' in (root/'host/game/Mods/plugins.log').read_text(errors='replace')
        if result.get('edgeCase')=='host-partial-transfer':
            old=fault.get('witness',{});current=cancelled.get('witness',{})
            checks['preBarrierWorldRetainedAfterHostLoss']=bool(old.get('world')) and current.get('world')==old.get('world') and current.get('worldTicks')==old.get('worldTicks')
        if result.get('secondWitness'):
            checks['twoOriginalSurvivorsRetained']=len(survivors)==2 and all(cancelled[r].get('paused')==1 and cancelled[r].get('session')==fault[r].get('session') for r in survivors)
            proof=result.get('edgeSurvivorObservation',{});streams=[]
            for r,d in proof.get('edgeDirectories',{}).items():
                begin=proof['edgeObserveBefore'][r];end=proof['edgeObserveAfter'][r]
                streams.append({(s['tick'],s['worldIndex']):s['worldCrc'] for s in rows(root/d/'game/Mods/lab-sync.jsonl') if s['world']==end['world'] and begin['worldTicks']<=s['tick']<=end['worldTicks']})
            if not proof:
                # First four-original fixture predates the explicit window
                # field. Its driver ran 65 s before retrying. Native ticks
                # through +64 s isolate that retained-world window, before
                # the retry can capture/reload the next checkpoint.
                for r in survivors:
                    start=cancelled[r]
                    streams.append({(s['tick'],s['worldIndex']):s['worldCrc'] for s in rows(root/r/'game/Mods/lab-sync.jsonl') if s['world']==start['world'] and start['worldTicks']<=s['tick']<=start['worldTicks']+64*16})
            overlap=sorted(set.intersection(*(set(s) for s in streams))) if streams else []
            checks['twoSurvivorsMinuteChecksumsMatch']=len(streams)==2 and len(overlap)>1 and (overlap[-1][0]-overlap[0][0])/16>=minimum and all(len({s[k] for s in streams})==1 for k in overlap)
    composed=(root/'host/composed-manifest.json').exists()
    patch_version='0.5.0-beta.1'
    if composed:
        import json
        composition_paths=list(paths.values()) if paths else [p.parent for p in root.glob('*/composed-manifest.json')]
        manifests=[json.loads((p/'composed-manifest.json').read_text()) for p in composition_paths if (p/'composed-manifest.json').is_file()]
        checks['composedNativeChecksEnabled']=bool(composition_paths) and len(manifests)==len(composition_paths) and all(m['features'].get('bypass') is False for m in manifests)
        checks['composedFeaturesIdentical']=bool(manifests) and all(m['features']==manifests[0]['features'] for m in manifests)
        if manifests:patch_version=manifests[0]['features'].get('patchVersion',patch_version)
        if manifests and manifests[0]['features'].get('hotJoinRevision'):
            checks['packagedRuntimeOnEveryActivePeer']=all('HOTJOIN_READY revision=1 protocol=R' in t for t in logs.values())
            checks['legacySaveLobbyRecoveryDisabled']=all(m['features'].get('legacySaveLobbyRecovery') is False for m in manifests)
            checks['nativeLocalizedReturnNoticeOnEveryPeer']=all('ROLE_NOTICE_SHOWN' in t and 'nativeResult=1' in t and 'ROLE_NOTICE_LOCALE_MISSING' not in t for t in logs.values())
    return dict(accepted=bool(checks) and all(checks.values()),scope='owned-'+('arcane-wars-'+patch_version+'-native-checks' if composed else 'stock-1.3.72')+'-local-edge-scenario',edgeCase=result.get('edgeCase'),commonChecksumSeconds=span,commonChecksumSamples=len(common),checksumMismatches=bad,checks=checks,failedChecks=[k for k,v in checks.items() if not v])
