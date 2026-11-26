"""One explicitly coordinated SDK build and real release QA; no game launch."""
from context import *
import time,winreg
SDK=Path('G:/CodexData/projects/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe')
def paths():
 values={}
 for hive,name in[(winreg.HKEY_CURRENT_USER,'Environment'),(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment')]:
  with winreg.OpenKey(hive,name)as k:values[name]=winreg.QueryValueEx(k,'Path')
 return values
def main():
 preflight=run(['powershell','-NoProfile','-Command',"$p=@(Get-CimInstance Win32_Process|Where-Object { $_.Name -match '^(k2\\.exe|KohanReborn.*|dotnet\\.exe|csc\\.exe)$' }); if($p.Count){$p|Select-Object Name,ProcessId,ExecutablePath|ConvertTo-Json;exit 21}"])
 assert not preflight;before=paths();e=env();e['MSBUILDDISABLENODEREUSE']='1';started=time.monotonic();stages=[]
 runtime_only='--runtime-only' in sys.argv
 generic_only='--generic-only' in sys.argv
 budget=600 if runtime_only else 180
 def stage(name,args):
  remaining=budget-(time.monotonic()-started);assert remaining>1,'Shared window exhausted';log=O/(name+('-runtime3'if generic_only else'-runtime2'if runtime_only else'')+'.log')
  assert not log.exists(),'Do not overwrite an earlier physical run'
  with log.open('w',encoding='utf-8')as f:
   p=subprocess.Popen(list(map(str,args)),cwd=P,env=e,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:code=p.wait(timeout=remaining)
   except subprocess.TimeoutExpired:
    p.kill();p.wait();raise
  assert code==0,(name,code,log.read_text('utf-8')[-3500:]);stages.append(dict(name=name,pid=p.pid,exitCode=code));print('QA_STAGE_CLOSED',name,code,flush=True)
 try:
  if not runtime_only:stage('qa-build',[SDK,'build',P/'qa/QA.csproj','-c','Release','--disable-build-servers','-m:1','-nr:false','-p:UseSharedCompilation=false'])
  stage('qa-run',[SDK,P/'qa/bin/Release/net8.0-windows/QA.dll',P/'qa/inputs.json']+([]if generic_only else['--upgrade-private']))
  assert read(O/'qa/result.json')['passed']
 finally:
  assert paths()==before,'Persistent PATH changed';write(O/('qa-runtime3-closure.json'if generic_only else'qa-runtime2-closure.json'if runtime_only else'qa-closure.json'),dict(stages=stages,persistentPathUnchanged=True,seconds=round(time.monotonic()-started,3),budgetSeconds=budget,dotnetAddGlobalToolsToPath=e['DOTNET_ADD_GLOBAL_TOOLS_TO_PATH'],sdkInvoked=not runtime_only,noGameLaunched=True,optionalRetiredPrivateUpgrade=not generic_only))
 print('SDK_RELEASE_QA_COMPLETE',flush=True)
if __name__=='__main__':main()
