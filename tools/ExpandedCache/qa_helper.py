"""Private-profile/main-thread rig wrapper for the existing graphics QA game."""
from build import OUT,read,write,sha,run,once
from pathlib import Path
folder=OUT/'qa-helper';folder.mkdir(exist_ok=True);name='k2_paws_lobby_colors_mp_1372_experimental.exe';row=read(OUT/'arcane-helpers/build-report.json')[name];args=[]
for arg in row['args']:
 if arg.startswith('/out:'):arg='/out:'+str(folder/name)
 elif arg.lower().endswith('.cs'):
  p=Path(arg);s=p.read_text('utf-8-sig')
  if p.name.endswith('ReleaseStartup.cs'):s=once(s,'Process[] games = Process.GetProcessesByName("k2");','Process[] games = Process.GetProcessesByName("k2").Where(p => String.Equals(p.MainModule.FileName, expectedPath, StringComparison.OrdinalIgnoreCase)).ToArray();')
  if p.name.endswith(('PawAssistantRuntime.cs','PawAssistantParties.cs','.generated.cs')):s=s.replace('Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)','Environment.GetEnvironmentVariable("PAWS_TEST_DOCUMENTS")').replace('Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)','Environment.GetEnvironmentVariable("PAWS_TEST_APPDATA")')
  if p.name.endswith('.generated.cs'):
   s=once(s,'Process[] running = Process.GetProcessesByName("k2");','Process[] running = Process.GetProcessesByName("k2").Where(p => String.Equals(p.MainModule.FileName, gamePath, StringComparison.OrdinalIgnoreCase)).ToArray();')
   s=once(s,'ProcessStartInfo start = new ProcessStartInfo(gamePath)','if (Path.GetFullPath(gameDirectory).TrimEnd(\'\\\\\') != @"G:\\PawGraphicsQA-20261113\\game" && Path.GetFullPath(gameDirectory).TrimEnd(\'\\\\\') != @"G:\\PawBufferPublishQA-20261113\\arcane-r6\\game" || String.IsNullOrEmpty(Environment.GetEnvironmentVariable("PAWS_TEST_DOCUMENTS")) || String.IsNullOrEmpty(Environment.GetEnvironmentVariable("PAWS_TEST_APPDATA"))) throw new IOException("Owned expanded-cache QA only");\n                ProcessStartInfo start = new ProcessStartInfo(gamePath, "+Exec Mods/rig.txt")')
   s=once(s,'                    UseShellExecute = true,','                    UseShellExecute = false,')
   s=once(s,'                game = Process.Start(start);','                game = Process.Start(start);Console.WriteLine("OWNED_GAME " + game.Id);Console.Out.Flush();')
   s=once(s,'            MonitorRuntime(game, process, counters, syncSignal, logPath);','            Console.WriteLine("PACKAGED_HELPER_READY");Console.Out.Flush();\n            MonitorRuntime(game, process, counters, syncSignal, logPath);')
   s=once(s,'            GraphicsDiagnostics.Start(game, gameDirectory, delegate(string m) { AppendLog(logPath, m); });','            // QA: avoid the automatic full-memory recorder.')
  dest=folder/p.name;dest.write_text(s);arg=str(dest)
 args.append(arg)
run(args);assert __import__('json').loads(run([folder/name,'--features']))==row['features']
write(folder/'manifest.json',dict(candidateOnly=True,privateQaHelper=True,normalHelperSha256=row['sha256'],qaHelperSha256=sha(folder/name),args=args,scope='private profiles, owned path, native script dispatcher; gameplay/presentation/cache bytes unchanged'))
print('EXPANDED_PRIVATE_PROFILE_HELPER_READY')
