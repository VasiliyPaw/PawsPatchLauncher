"""Private path/profile-only adapter. Never include this helper in a release."""
import argparse,hashlib,json,subprocess
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replace(s,a,b):assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--helpers',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--without-presentation',action='store_true');ap.add_argument('--without-recorder',action='store_true');a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 name='k2_paws_lobby_colors_mp_1372_experimental.exe';row=json.loads((a.helpers/'build-report.json').read_text())[name];assert sha(a.helpers/name)==row['sha256'].lower()
 for p,h in row['sources'].items():assert sha(p)==h.lower(),p
 args=[];changes=[]
 for arg in row['args']:
  if arg.startswith('/out:'):arg='/out:'+str(out/name)
  elif arg.lower().endswith('.cs'):
   source=Path(arg);s=source.read_text()
   if source.name.endswith('ReleaseStartup.cs'):
    s=replace(s,'Process[] games = Process.GetProcessesByName("k2");','Process[] games = Process.GetProcessesByName("k2").Where(p => String.Equals(p.MainModule.FileName, expectedPath, StringComparison.OrdinalIgnoreCase)).ToArray();')
   if source.name.endswith(('PawAssistantRuntime.cs','PawAssistantParties.cs','.generated.cs')):
    s=s.replace('Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)','Environment.GetEnvironmentVariable("PAWS_TEST_DOCUMENTS")').replace('Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)','Environment.GetEnvironmentVariable("PAWS_TEST_APPDATA")')
   if source.name.endswith('.generated.cs'):
    if a.without_recorder:s=replace(s,'            GraphicsDiagnostics.Start(game, gameDirectory, delegate(string m) { AppendLog(logPath, m); });','            // OWNED DIAGNOSTIC ONLY: automatic debugger omitted.')
    if a.without_presentation:
     s=replace(s,'            PresentationRuntimePatch.Install(game,imageBase,gameDirectory,delegate(string m) { AppendLog(logPath,m); });','            // OWNED DIAGNOSTIC ONLY: presentation installer omitted.')
     s=replace(s,'            PresentationRuntimePatch.Ready();','            // No presentation readiness event in this diagnostic.')
    s=replace(s,'Process[] running = Process.GetProcessesByName("k2");','Process[] running = Process.GetProcessesByName("k2").Where(p => String.Equals(p.MainModule.FileName, gamePath, StringComparison.OrdinalIgnoreCase)).ToArray();')
    s=replace(s,'ProcessStartInfo start = new ProcessStartInfo(gamePath)','if (!File.Exists(Path.Combine(gameDirectory,"reconnect-test.marker")) || String.IsNullOrEmpty(Environment.GetEnvironmentVariable("PAWS_TEST_DOCUMENTS")) || String.IsNullOrEmpty(Environment.GetEnvironmentVariable("PAWS_TEST_APPDATA"))) throw new IOException("Use the isolated product QA fixture only");\n                ProcessStartInfo start = new ProcessStartInfo(gamePath, "+Exec Mods/rig.txt")')
    s=replace(s,'                    UseShellExecute = true,','                    UseShellExecute = false,')
    s=replace(s,'                game = Process.Start(start);','                game = Process.Start(start);\n                Console.WriteLine("OWNED_GAME " + game.Id); Console.Out.Flush();')
    anchor='            MonitorRuntime(game, process, counters, syncSignal, logPath);';s=replace(s,anchor,'            Console.WriteLine("PACKAGED_HELPER_READY"); Console.Out.Flush();\n'+anchor)
   if s!=source.read_text():
    target=out/source.name;target.write_text(s);arg=str(target);changes.append(source.name)
  args.append(arg)
 r=subprocess.run(args,capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 f=json.loads(subprocess.check_output([str(out/name),'--features'],text=True));assert f==row['features']
 manifest=dict(fixtureOnly=True,diagnosticWithoutPresentation=a.without_presentation,diagnosticWithoutRecorder=a.without_recorder,publicHelper=sha(a.helpers/name),testHelper=sha(out/name),features=f,args=args,changedSources=changes,unchangedRuntimeDllResource=True,sources={p:sha(p) for p in args if p.lower().endswith('.cs')})
 (out/'qa-manifest.json').write_text(json.dumps(manifest,indent=2));print('QA_PATH_PROFILE_ADAPTER_READY',name,changes,flush=True)
if __name__=='__main__':main()
