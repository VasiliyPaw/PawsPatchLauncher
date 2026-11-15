from context import *
import collections
sys.path.insert(0,str(P/'net'));import control,checksums
assert not control.own() and read(O/'network-cleanup.json')['ownedProcessesStopped']
worlds={};evidence={};lines={}
for role in control.ROLES:
 f=control.folder(role)/'game/Mods/network-sync.jsonl';rows=[json.loads(line)for line in f.read_text().splitlines()];active=[r for r in rows if r['worldIndex']!=0x80000000 and r['world']]
 counts=collections.Counter(r['world']for r in active);assert len(counts)==1,(role,counts);worlds[role]=next(iter(counts));evidence[role]=dict(path=str(f),sha256=sha(f),rows=len(rows),world=worlds[role])
 logs='\n'.join(p.read_text(errors='replace')for p in(control.folder(role)/'game/Logs').glob('*.log'));matches=[line.split('checksums =',1)[1].strip()for line in logs.splitlines()if'checksums ='in line];assert matches;lines[role]=matches[-1]
 assert all(Path(r['path']).name in lines[role]for r in read(LOSS/'packed.json'))
 assert 'GUARD_REJECT'not in(control.folder(role)/'game/Mods/plugins.log').read_text()
checksums.state=lambda role:dict(world=worlds[role]);result=checksums.compare()
assert result['commonSamples']>=60 and result['alignedSeconds']>=59 and not result['mismatchCount']and not result['errors'],result
assert len(set(lines.values()))==1,lines
write(O/'network-result.json',dict(passed=True,peers=3,officialSync=True,checksums=result,archiveChecksumLines=lines,rawEvidence=evidence,features=read(O/'helpers/build-report.json')['k2_paws_family_herd_relations_1372.exe']['features'],scope='Three native peers ran 65 seconds in the same generated map. Offline audit of retained raw CRC streams after normal shutdown; compare only the archive checksum suffix, excluding the expected per-player connect identities.'))
print('THREE_NATIVE_PEERS_CRC_PASS',json.dumps(result),flush=True)
