from control import *
from context import O
def compare():
 streams={};uninitialized={}
 for r in ROLES:
  world=state(r).get('world');path=folder(r)/'game/Mods/network-sync.jsonl';rows=[]
  if path.exists():
   for line in path.read_text().splitlines():
    try:row=json.loads(line)
    except ValueError:continue
    if row['world']==world:rows.append(row)
  # The native world checker has not emitted a CRC while its index is the
  # constructor sentinel. Readiness/menu orders can already change netIndex.
  # Keep raw samples, but compare only initialized simulation checkpoints.
  uninitialized[r]=sum(s['worldIndex']==0x80000000 for s in rows)
  streams[r]={(s['tick'],s['worldIndex']):s for s in rows if s['worldIndex']!=0x80000000}
 common=sorted(set.intersection(*(set(s)for s in streams.values())))
 bad=[{'key':k,'values':{r:[streams[r][k][f]for f in ['worldCrc','netIndex','netCrc']]for r in ROLES}}for k in common if len({tuple(streams[r][k][f]for f in ['worldCrc','netIndex','netCrc'])for r in ROLES})!=1]
 errors=[]
 for r in ROLES:
  for p in (folder(r)/'game/Logs').glob('*.log'):
   for line in p.read_text(errors='replace').splitlines():
    if any(s in line.lower()for s in ['out of sync','out-of-sync','syncfailure(','assert:','unhandled exception','timeout waiting for mutex']):errors.append({'role':r,'file':p.name,'line':line})
 return {'commonSamples':len(common),'alignedSeconds':(common[-1][0]-common[0][0])/16 if len(common)>1 else 0,'uninitializedSamples':uninitialized,'first':common[0]if common else None,'last':common[-1]if common else None,'mismatches':bad[:12],'mismatchCount':len(bad),'errors':errors}
if __name__=='__main__':
 result=compare();(O/(sys.argv[1]if len(sys.argv)>1 else 'checksums.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
