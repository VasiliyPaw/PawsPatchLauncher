"""Rebuild the accepted Arcane helpers, retaining pinned gameplay payloads.
Only the packaged live-join runtime, startup integration and version change.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def run(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stdout+'\n'+p.stderr)
    return p.stdout
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--version',required=True);ap.add_argument('--compiler',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);sources=out/'source';sources.mkdir()
    baseline=json.loads(a.baseline.read_text());dll=out/'paws_hotjoin.dll'
    run([a.compiler,'-shared','-Wall','-Werror',ROOT/'game/hotjoin/release_runtime.c','-o',dll,'-lkernel32','-luser32'])
    lobby=out/'paws_lobby_compatibility.dll'
    # Arcane uses direct admission. Deliberately omit PAW_RECOVERY_INTEGRATED;
    # that legacy save-and-lobby behavior remains a separate Pure-only module.
    run([a.compiler,'-shared','-Wall','-Werror',ROOT/'game/lobby-compatibility/lobby_compatibility.c','-o',lobby,'-lkernel32','-luser32'])
    assert b'PawRecovery' not in lobby.read_bytes()
    for name in ('paws_player_colors.ini','paws_patch_versions.ini'):
        data=(a.baseline.parent/'helpers'/name) if (a.baseline.parent/'helpers'/name).exists() else a.baseline.parent/name
        if not data.exists():data=ROOT/'game/beta7'/name
        value=data.read_bytes()
        if name=='paws_patch_versions.ini':value=value.replace(b'PawPatch='+next(iter(baseline.values()))['features']['patchVersion'].encode(),b'PawPatch='+a.version.encode())
        (out/name).write_bytes(value)
    report={};capture={}
    for name,row in baseline.items():
        for p,digest in row['sources'].items():assert sha(p)==digest.upper(),p
        args=[]
        for value in row['args']:
            if value.startswith('/out:'):value='/out:'+str(out/name)
            elif value.lower().endswith('.cs'):
                original=Path(value);text=original.read_text(encoding='utf-8-sig');new=text
                if original.name.endswith('BuildFeatures.cs'):
                    block='''#if PAW_HOTJOIN
        const string hotjoin = ",\\\"hotJoinRevision\\\":1,\\\"hotJoinProtocol\\\":\\\"R\\\",\\\"legacySaveLobbyRecovery\\\":false";
#else
        const string hotjoin = "";
#endif
'''
                    assert text.count('        Console.WriteLine(')==1 and text.count(' + companyBehavior +')==1
                    new=text.replace('        Console.WriteLine(',block+'        Console.WriteLine(').replace(' + companyBehavior +',' + companyBehavior + hotjoin +')
                if original.name.endswith('LargeMapsIdentity.cs'):
                    assert text.count(row['features']['patchVersion'])==1
                    new=text.replace(row['features']['patchVersion'],a.version)
                if original.name.endswith('.generated.cs'):
                    pairs=[('PawLobbyCompatibility.Prepare(gameDirectory);','PawLobbyCompatibility.Prepare(gameDirectory); PawHotJoin.Prepare(gameDirectory);'),
                        ('PawFastTransfer.Install(game, imageBase, delegate(string m) { AppendLog(logPath, m); });','PawFastTransfer.Install(game, imageBase, delegate(string m) { AppendLog(logPath, m); }); PawHotJoin.Install(game, imageBase, delegate(string m) { AppendLog(logPath, m); });')]
                    for old,replacement in pairs:assert new.count(old)==1;new=new.replace(old,replacement)
                target=sources/original.name
                if target.exists():assert target.read_text(encoding='utf-8')==new
                else:target.write_text(new,encoding='utf-8')
                capture[str(target)]=sha(target);value=str(target)
            elif value.startswith('/resource:') and value.endswith(',PawLobbyCompatibilityNative'):
                value='/resource:'+str(lobby)+',PawLobbyCompatibilityNative'
            args.append(value)
        assert not any('PAW_PURE_RECOVERY' in x or 'PawMultiplayerSavesNative' in x for x in args)
        args+=['/define:PAW_HOTJOIN',str(ROOT/'game/hotjoin/PawHotJoin.cs'),'/resource:'+str(dll)+',PawHotJoinNative']
        run(args);exe=out/name;features=json.loads(run([exe,'--features']))
        expected=dict(row['features'],patchVersion=a.version,hotJoinRevision=1,hotJoinProtocol='R',legacySaveLobbyRecovery=False)
        assert features==expected,(name,[(k,features.get(k),v) for k,v in expected.items() if features.get(k)!=v])
        tests={}
        for mode in ('--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test'):
            tests[mode]=run([exe,mode]).strip()
        paths=[Path(s) for s in args if s.lower().endswith('.cs')]
        # Resource inputs are included too, retaining provenance for every
        # original machine-code payload and the new native DLL.
        paths += [Path(s[len('/resource:'):].rsplit(',',1)[0]) for s in args if s.startswith('/resource:')]
        report[name]=dict(sha256=sha(exe),features=features,args=args,sources={str(p):sha(p) for p in paths},selfTests=tests)
        print('HELPER_PASS',name,flush=True)
    (out/'build-report.json').write_text(json.dumps(report,indent=2))
    (out/'native-inputs.json').write_text(json.dumps({str(p):sha(p) for folder in ('hotjoin','hotjoin-test') for p in (ROOT/'game'/folder).iterdir() if p.suffix in ('.c','.h','.cs')},indent=2))
if __name__=='__main__':main()
