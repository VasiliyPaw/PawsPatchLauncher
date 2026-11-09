"""Rebuild an accepted helper set, changing only its lobby-color inputs.

No installer, game, feed or publication operations. All inputs are hash checked
and copied to the unused output directory to preserve a reviewable snapshot.
"""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def run(args):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout.strip()

def main():
    p=argparse.ArgumentParser()
    for key in ['helpers','native','out']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--loader',type=Path,help='Optional updated LobbyColorsNative.cs, including its diagnostic revision')
    p.add_argument('--patch-version',help='New package/lobby compatibility identity')
    p.add_argument('--runtime-version',help='New Pure runtime identity')
    p.add_argument('--assembly-version',help='New Pure four-part numeric assembly identity')
    p.add_argument('--palette',type=Path,help='Palette for offline verification')
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    for filename in ['paws_player_colors.ini','paws_patch_versions.ini']:
        if (a.helpers/filename).is_file():shutil.copy2(a.helpers/filename,out/filename)
    baseline=json.loads((a.helpers/'build-report.json').read_text())
    old_patch=next(iter(baseline.values()))['features']['patchVersion']
    assert all(r['features']['patchVersion']==old_patch for r in baseline.values())
    if a.patch_version:assert re.fullmatch(r'0\.\d+\.\d+-beta\.\d+',a.patch_version)
    old_runtime=next(iter(baseline.values()))['features'].get('version')
    if a.runtime_version:assert old_runtime and re.fullmatch(r'1\.3\.72-pure\.\d+-beta\.\d+',a.runtime_version)
    if a.assembly_version:assert re.fullmatch(r'1\.3\.72\.\d+',a.assembly_version)
    if a.palette:shutil.copy2(a.palette,out/'paws_player_colors.ini')
    versions=out/'paws_patch_versions.ini'
    if a.patch_version and versions.exists():versions.write_text(versions.read_text().replace(old_patch,a.patch_version))
    for name,row in baseline.items():
        assert sha(a.helpers/name)==row['sha256'].upper(),name
        for path,digest in row['sources'].items():assert sha(path)==digest.upper(),path
    inputs=out/'inputs';inputs.mkdir();mapped={}
    for source in sorted({p for row in baseline.values() for p in row['sources']}):
        original=Path(source)
        if a.loader and original.name.endswith('LobbyColorsNative.cs'):original=a.loader.resolve()
        data=original.read_bytes()
        if original.suffix.lower()=='.cs':
            text=data.decode('utf-8-sig')
            if a.patch_version:text=text.replace(old_patch,a.patch_version)
            if a.runtime_version:text=text.replace(old_runtime,a.runtime_version)
            if a.assembly_version:text=text.replace('1.3.72.'+old_runtime.split('pure.')[1].split('-')[0],a.assembly_version)
            data=text.encode('utf-8')
        target=inputs/hashlib.sha256(data).hexdigest().upper()/original.name
        target.parent.mkdir(exist_ok=True);target.write_bytes(data);mapped[source]=str(target)
    resources={'PawLobbyColorsPayload':a.native/'payload.bin','PawLobbyColorsFixups':a.native/'fixups.bin'}
    for name,path in resources.items():shutil.copy2(path,out/(name+'.bin'))
    report={}
    for name,row in baseline.items():
        args=[]
        for arg in row['args']:
            if arg.startswith('/out:'):arg='/out:'+str(out/name)
            elif arg.startswith('/resource:'):
                path,resource=arg[10:].rsplit(',',1)
                arg='/resource:'+str(out/(resource+'.bin'))+','+resource if resource in resources else '/resource:'+mapped[path]+','+resource
            elif arg in mapped:arg=mapped[arg]
            args.append(arg)
        run(args);features=json.loads(run([out/name,'--features']))
        expected=dict(row['features'])
        if a.patch_version:expected['patchVersion']=a.patch_version
        if a.runtime_version:expected['version']=a.runtime_version
        assert features==expected,(name,features,expected)
        flags=[] if name.startswith('k2_paws_pure_') else ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']
        tests={flag:run([out/name,flag]) for flag in flags}
        paths=[Path(x) for x in args if x.lower().endswith('.cs')]+[Path(x[10:].rsplit(',',1)[0]) for x in args if x.startswith('/resource:')]
        report[name]=dict(sha256=sha(out/name),features=features,args=args,sources={str(p):sha(p) for p in paths},selfTests=tests,baselineSha256=row['sha256'])
        print('LIFETIME_HELPER_PASS',name,flush=True)
    (out/'build-report.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
