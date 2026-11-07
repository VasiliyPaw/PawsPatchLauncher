"""Private startup adaptation of archived Arcane release inputs; no gameplay edits."""
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--helper',default='k2_paws_lobby_colors_mp_1372_experimental.exe');p.add_argument('--data-root',type=Path,required=True);a=p.parse_args()
    row=json.loads(a.report.read_text())[a.helper];out=a.out.resolve();out.mkdir(exist_ok=False,parents=True)
    for name,digest in row['sources'].items():assert sha(Path(name)).lower()==digest.lower(),name
    for name in ('paws_player_colors.ini','paws_patch_versions.ini'):shutil.copy2(a.data_root/name,out/name)
    args=[];adapted=[]
    for arg in row['args']:
        if arg.startswith('/out:'):arg='/out:'+str(out/a.helper)
        elif arg.startswith('/target:'):arg='/target:exe'
        elif arg.lower().endswith('.cs'):
            source=Path(arg);text=source.read_text(encoding='utf-8-sig');original=text
            if source.name.endswith('ReleaseStartup.cs'):
                old='Process[] games = Process.GetProcessesByName("k2");';assert text.count(old)==1
                text=text.replace(old,'Process[] games = Process.GetProcessesByName("k2").Where(p => String.Equals(p.MainModule.FileName, expectedPath, StringComparison.OrdinalIgnoreCase)).ToArray();')
            if source.name.endswith(('PawAssistantParties.cs','PawAssistantRuntime.cs','.generated.cs')):
                text=text.replace('Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)','Environment.GetEnvironmentVariable("PAWS_TEST_DOCUMENTS")').replace('Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)','Environment.GetEnvironmentVariable("PAWS_TEST_APPDATA")')
            if source.name.endswith('.generated.cs'):
                pairs=[('Process[] running = Process.GetProcessesByName("k2");','Process[] running = Process.GetProcessesByName("k2").Where(p => String.Equals(p.MainModule.FileName, gamePath, StringComparison.OrdinalIgnoreCase)).ToArray();'),
                       ('ProcessStartInfo start = new ProcessStartInfo(gamePath)','if (!File.Exists(Path.Combine(gameDirectory, "hotjoin-lab.marker"))) throw new IOException("Private hot-join marker required");\n                ProcessStartInfo start = new ProcessStartInfo(gamePath, "+Exec Mods/rig.txt")'),
                       ('game = Process.Start(start);','game = Process.Start(start);\n                Console.WriteLine("OWNED_GAME " + game.Id); Console.Out.Flush();'),
                       ('                    UseShellExecute = true,','                    UseShellExecute = false,'),
                       ('            MonitorRuntime(game, process, counters, syncSignal, logPath);','            File.WriteAllText(Path.Combine(gameDirectory, "Mods/hotjoin-helper-ready.marker"), "READY");\n            Console.WriteLine("PACKAGED_HELPER_READY"); Console.Out.Flush();\n            MonitorRuntime(game, process, counters, syncSignal, logPath);')]
                for old,new in pairs:assert text.count(old)==1,old;text=text.replace(old,new)
            if text!=original:
                target=out/source.name;target.write_text(text,encoding='utf-8');arg=str(target);adapted.append(source.name)
        args.append(arg)
    subprocess.run(args,check=True)
    helper=out/a.helper;actual=json.loads(subprocess.check_output([str(helper),'--features']))
    assert actual==row['features']
    for mode in ('--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test'):
        subprocess.run([str(helper),mode],check=True,capture_output=True)
    (out/'qa-manifest.json').write_text(json.dumps(dict(publicHelper=row['sha256'],testHelper=sha(helper),features=actual,adaptedSources=adapted,scope='Fresh-process/private-profile/owned-job startup only; archived release gameplay/native payloads unchanged',args=args,verifiedSources=row['sources']),indent=2))
    print('COMPOSED_QA_BUILD_PASS',helper)
if __name__=='__main__':main()
