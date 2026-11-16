from context import *
import ctypes as C

def main():
 # Enumerate all six exact fixture paths before any reversible QA cleanup.
 roots=[FIX/m for m in ['vanilla','immortals']]+[FIX/('network-'+m)/r for m in ['vanilla','immortals']for r in ['client','witness']]
 paths={str((r/'game/k2.exe').resolve()).lower()for r in roots}|{str((r/'game/TestInstalledRuntime.exe').resolve()).lower()for r in roots}
 q=subprocess.run(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "k2.exe" -or $_.Name -eq "TestInstalledRuntime.exe" } | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress'],capture_output=True,text=True)
 processes=json.loads(q.stdout or'[]');processes=processes if isinstance(processes,list)else[processes];assert not any(str(p.get('ExecutablePath','')).lower()in paths for p in processes)
 for r in roots:
  assert r.resolve().is_relative_to(FIX.resolve());g=r/'game'
  for name,raw in read(r/'qa-before.json').items():
   f=g/name
   if raw is None:f.unlink(missing_ok=True)
   else:f.write_bytes(bytes.fromhex(raw))
  for n in ['Mods/PawsCaptureQA.dll','Mods/RigInput.dll','TestInstalledRuntime.exe','reconnect-test.marker']:(g/n).unlink(missing_ok=True)
 write(O/'cleanup.json',dict(passed=True,ownedProcessesStopped=True,qaLoadersAndModulesRemoved=True,roots=[str(r)for r in roots],installedUserGameUntouched=True));print('PURE_QA_CLEANUP_PASS')
if __name__=='__main__':main()
