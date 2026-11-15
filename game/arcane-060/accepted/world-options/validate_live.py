"""Independent acceptance of native Dynamic/Random evidence; no game writes."""
import argparse,hashlib,json,re
from pathlib import Path

ANCHORS=[(.8,.8,1,.7,.7,.9,.1,.1,.15),(1,1,1,1,1,1,0,0,0),(1,.8,.55,.8,.6,.4,.2,.1,.05),(.4,.4,.7,.4,.4,.7,.1,.1,.25)]
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
def expected(seconds,offset,cycle=600):
 ticks=cycle*16;segment=ticks//4
 phase=(int(seconds*16)%ticks+offset)%ticks;k=phase//segment;t=(phase%segment)/segment;t=t*t*(3-2*t)
 return [a+(b-a)*t for a,b in zip(ANCHORS[k],ANCHORS[(k+1)%4])]
def validate(root,minimum,cycle=600):
 result=json.loads((root/'result.json').read_text());checks={};details={'cycleSeconds':cycle}
 def check(k,v):checks[k]=bool(v)
 check('completed',result.get('experimentComplete'));check('noNativeErrors',not result.get('errors'))
 check('normalOwnedShutdown',not result.get('activePeersRequiringForcedShutdown'))
 check('confirmedNewOptions',result.get('worldOptionsInitial',{}).get('rules',{}).get('sun')==5 and result.get('worldOptionsInitial',{}).get('rules',{}).get('biomes')==1)
 paths=[root/'host',root/'client-return'];samples=[rows(p/'game/Mods/lab-world-options.jsonl') for p in paths]
 offsets={s['rules']['phase'] for peer in samples for s in peer};check('savedPhaseIdenticalBeforeAndAfterReturn',len(offsets)==1)
 check('sameSettingsOnAllPeers',all(s['rules']['sun']==5 and s['rules']['biomes']==1 for peer in samples for s in peer))
 # Tick zero is the loading screen before native StartMission applies Sun.
 # Keep those observations, but assess rendered simulation colors after start.
 details['preStartLoadingSamples']=sum(s['tick']==0 for peer in samples for s in peer)
 errors=[max(abs(a-b) for a,b in zip(s['colors'],expected(s['seconds'],s['rules']['phase'],cycle))) for peer in samples for s in peer if s['tick']>0]
 details['maximumNativeColorError']=max(errors);check('nativeColorsFollowGameClock',max(errors)<.0008)
 seconds=[s['seconds'] for s in samples[1]];span=max(seconds)-min(seconds);details['observedGameSeconds']=span
 check('requiredGameTimeElapsed',span>=minimum)
 paused={};repeats=0;stable=True
 for s in samples[0]:
  if s['tick']==0:continue
  key=(s['tick'],s['seconds']);old=paused.get(key)
  if old is not None:repeats+=1;stable=stable and old==s['colors']
  paused[key]=s['colors']
 check('pauseStopsCycle',repeats>=5 and stable);details['pausedRepeatedSamples']=repeats
 sync=[]
 for peer,key in zip(paths,['hostAfterJoin','clientAfterJoin']):
  sync.append({(s['tick'],s['worldIndex']):s['worldCrc'] for s in rows(peer/'game/Mods/lab-sync.jsonl') if s['world']==result[key]['world']})
 common=sorted(sync[0].keys()&sync[1].keys());mismatches=[k for k in common if sync[0][k]!=sync[1][k]]
 crcspan=(common[-1][0]-common[0][0])/16 if len(common)>1 else 0
 check('nativeWorldChecksumsAgree',len(common)>=2 and not mismatches and crcspan>=minimum)
 details.update(commonChecksumSamples=len(common),commonChecksumSeconds=crcspan,checksumMismatches=mismatches)
 commits=[]
 for peer in paths:
  native=(peer/'game/Logs/paws_hotjoin.log').read_text(errors='replace');observer=(peer/'game/Mods/plugins.log').read_text(errors='replace')
  commits.append(re.findall(r'COORDINATED_NATIVE_COMMIT netIndex=(\d+) netCrc=(\d+)',native))
  check(peer.name+'ProductionRuntime','HOTJOIN_READY revision=1 protocol=R' in native and 'PRODUCTION_RUNTIME_OBSERVER_READY' in observer)
 check('nativeCheckpointCommitAgrees',all(commits) and commits[0][-1]==commits[1][-1])
 kingdom=result['originalParticipant']['kingdom']
 check('returnedToOwnKingdom',all(any(p['kingdom']==kingdom and not p['ai'] and not p['kingdomAi'] for p in result[k]['players']) for k in ('hostAfterJoin','clientAfterJoin')))
 census=root/'host/world-options-census.json'
 if census.exists():
  c=json.loads(census.read_text());details['terrainCensus']=c['cellCounts'];check('randomSubsetExistsInActualTerrain',1<=c['biomeCount']<=4)
 files=[next((p/'Documents/Kohan2/data/Save').glob('PawHotJoin*.RSG'),None) for p in paths]
 check('nativeCheckpointFilesPresent',all(files))
 if all(files):
  hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in files];check('transferredCheckpointBytesIdentical',len(set(hashes))==1);details['checkpointSha256']=hashes[0]
 return dict(accepted=all(checks.values()),scope='two owned local peers; normal exit, cold native checkpoint return; Dynamic Sun and Random mixed biomes',checks=checks,details=details,failedChecks=[k for k,v in checks.items() if not v])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--minimum-seconds',type=float,default=600);ap.add_argument('--cycle-seconds',type=int,default=600);a=ap.parse_args()
 result=validate(a.root,a.minimum_seconds,a.cycle_seconds);(a.root/'world-options-acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));raise SystemExit(0 if result['accepted'] else 1)
if __name__=='__main__':main()
