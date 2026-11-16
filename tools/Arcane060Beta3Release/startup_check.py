from context import *
Q=O/'startup-contract';Q.mkdir(exist_ok=True)
src=Q/'Probe.cs';src.write_text('''using System;using System.Reflection;class Probe{static int Main(string[] args){try{Assembly.LoadFrom(args[0]).GetType("PawRuntimeStartup",true).GetMethod("Validate",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{args[1]});Console.WriteLine("STARTUP_VALID");return 0;}catch(TargetInvocationException e){Console.WriteLine(e.InnerException.Message);return 2;}}}''')
run(['C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe','/nologo','/target:exe','/platform:x86','/out:'+str(Q/'Probe.exe'),src],Q/'compile.log')
def probe(helper,expected):
 q=subprocess.run([str(Q/'Probe.exe'),str(helper),str(FIX/'game')],env=env(),capture_output=True,text=True);assert q.returncode==expected,q.stdout+q.stderr;return q.stdout.strip()
results={n:probe(O/'helpers'/n,0)for n in read(O/'helpers/build-report.json')}
dll=FIX/'game/Mods/PawsCaptureKnowledge.dll';plugins=FIX/'game/Mods/plugins.txt';raw=dll.read_bytes();cfg=plugins.read_bytes();helper=O/'helpers/k2_paws_family_herd_relations_1372.exe'
try:
 dll.unlink();results['missing']=probe(helper,2);dll.write_bytes(raw)
 dll.write_bytes(raw+b'bad');results['tampered']=probe(helper,2);dll.write_bytes(raw)
 plugins.write_bytes(cfg.replace(b'PawsCaptureKnowledge.dll',b'#PawsCaptureKnowledge.dll'));results['disabled']=probe(helper,2)
finally:dll.write_bytes(raw);plugins.write_bytes(cfg)
assert all('PawsCaptureKnowledge.dll'in results[n]for n in ['missing','tampered','disabled']);assert sha(dll)==read(CAND/'verification.json')['productionSha256'];probe(helper,0)
write(O/'startup-contract.json',dict(passed=True,normalHelpers=8,rejected=3,results=results,fixtureRestored=True));print('STARTUP_CONTRACT_PASS')
