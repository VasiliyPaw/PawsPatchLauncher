"""Read-only partial progress, never substitutes for final acceptance."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('peers',nargs='+');a=ap.parse_args()
streams={};states={}
for peer in a.peers:
    folder=a.root/peer/'game/Mods'
    with (folder/'lab-state.jsonl').open() as f:
        for line in f:
            if line.strip():states[peer]=json.loads(line)
    stream={}
    with (folder/'lab-sync.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            if r['world']==states[peer]['world']:stream[r['tick'],r['worldIndex']]=r['worldCrc']
    streams[peer]=stream
common=sorted(set.intersection(*(set(v) for v in streams.values())))
bad=[key for key in common if len({v[key] for v in streams.values()})!=1]
print(json.dumps(dict(scope='partial-live-evidence-not-final-acceptance',alignedSeconds=(common[-1][0]-common[0][0])/16 if len(common)>1 else 0,samples=len(common),mismatches=bad,peers={k:{field:v.get(field) for field in ('seconds','paused','frozen','phase','mode','mapWidth','mapHeight')} for k,v in states.items()}),indent=2))
