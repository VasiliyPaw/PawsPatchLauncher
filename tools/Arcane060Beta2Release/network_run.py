from context import *
import time,shutil
sys.path.insert(0,str(P/'net'));from control import *
from checksums import compare
import match
def main():
 try:
  match.lobby();match.launch();start=state('host')['seconds'];wall=time.monotonic();last=-1
  while state('host')['seconds']-start<65:
   assert time.monotonic()-wall<150,'Network simulation stopped progressing'
   status=compare();assert not status['mismatchCount']and not status['errors'],status
   elapsed=state('host')['seconds']-start
   if int(elapsed)//15!=last:last=int(elapsed)//15;print('NETWORK_CRC_PROGRESS',round(elapsed,1),status['commonSamples'],flush=True)
   time.sleep(1)
  command('host','GamePause 1');wait(lambda:all(state(r).get('paused')for r in ROLES),20,'common network pause');result=compare();assert result['commonSamples']>=60 and result['alignedSeconds']>=59 and not result['mismatchCount']and not result['errors'],result
  checksums={}
  for r in ROLES:
   logs='\n'.join(p.read_text(errors='replace')for p in(folder(r)/'game/Logs').glob('*.log'));lines=[line for line in logs.splitlines()if'checksums ='in line];assert lines,(r,'No native archive checksum record');checksums[r]=lines[-1].split('checksums =',1)[1].strip();assert all(Path(p['path']).name in checksums[r]for p in read(LOSS/'packed.json')),(r,checksums[r]);assert 'GUARD_REJECT'not in(folder(r)/'game/Mods/plugins.log').read_text()
  assert len(set(checksums.values()))==1,checksums
  write(O/'network-result.json',dict(passed=True,peers=3,officialSync=True,checksums=result,archiveChecksumLines=checksums,features=read(O/'helpers/build-report.json')['k2_paws_family_herd_relations_1372.exe']['features'],scope='New compact archive compatibility and short native LAN CRC smoke; inherited bridge simulation and construction checks are unchanged.'))
  print('THREE_NATIVE_PEERS_CRC_PASS',json.dumps(result),flush=True)
 finally:
  for r in ['witness','client','host']:
   if not any(Path(p['path'])==folder(r)/'game/k2.exe'for p in own()):continue
   try:command(r,'ReallyQuit');wait(lambda:not any(Path(p['path'])==folder(r)/'game/k2.exe'for p in own()),20,r+' normal exit')
   except Exception:stop(r)
  if own():stop()
  for r in ROLES:
   root=folder(r);game=root/'game';mods=game/'Mods';normal=(root/'qa-evidence/beta2-normal-plugins.txt').read_bytes();(mods/'plugins.txt').write_bytes(normal)
   backup=root/'qa-evidence/beta2-user-before.tgi'
   if backup.exists():shutil.copy2(backup,root/'Documents/Kohan2/data/User/UVars.tgi')
   archive=O/'network-test-control'/str(time.time_ns())/r;archive.mkdir(parents=True,exist_ok=True)
   for f in [mods/'PawsNetworkQA.dll',mods/'rig_input.dll',game/'TestInstalledRuntime.exe',game/'shfolder.dll',game/'network-test.marker',game/'reconnect-test.marker',*list(mods.glob('network-command.*'))]:
    if f.exists():assert not(archive/f.name).exists();f.rename(archive/f.name)
   assert len((mods/'plugins.txt').read_text().splitlines())==9
  write(O/'network-cleanup.json',dict(passed=True,normalNineLists=True,ownedProcessesStopped=not bool(own())))
if __name__=='__main__':main()
