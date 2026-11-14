import shutil,sys
from common import *
LAUNCHER=WS/'work/launcher-1014-release/src/PawsPatchLauncher/bin/Release/net8.0-windows'
def project(folder,source):
    folder.mkdir(exist_ok=False);snapshot=folder/'launcher';snapshot.mkdir()
    for p in LAUNCHER.glob('*.dll'):
        digest=sha(p);shutil.copy2(p,snapshot/p.name);assert sha(snapshot/p.name)==digest==sha(p)
    refs=''.join('<Reference Include="'+p.stem+'"><HintPath>'+str(p)+'</HintPath></Reference>' for p in snapshot.glob('*.dll'))
    (folder/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
    (folder/'Program.cs').write_text(source,encoding='utf-8')
def catalog():
    source=(REPO/'outputs/arcane-051-release-20261109/stable/catalog-qa/Program.cs').read_text()
    source=source.replace('=="0.5.0"','=="0.5.1"').replace('ARCANE_STABLE_ALL_SWITCHES_PASS','ARCANE_051_STABLE_ALL_SWITCHES_PASS')
    folder=OUT/'catalog-qa-final';project(folder,source)
    text=run([SDK,'run','--project',folder/'QA.csproj','-c','Release','--',OUT,REPO,OUT/'helpers',OUT],OUT/'catalog-checks.log');print(text[-1500:],flush=True)
    assert '55296 selections' in text and 'ARCANE_051_STABLE_ALL_SWITCHES_PASS' in text
    write(OUT/'catalog-result.json',dict(passed=True,selections=55296,launcher='1.0.18',localLauncherDllSha256=sha(folder/'launcher/PawsPatchLauncher.dll'),gamesLaunched=False))
def installers():
    source=(WS/'outputs/cache-stability-release-20261114/installer-qa-r6/Program.cs').read_text()
    start=source.index('    private static IEnumerable<Case> Cases()');end=source.index('    private static IEnumerable<Case> PureBetaCases()',start)
    source=source[:start]+source[start:end].replace('Channel="beta"','Channel="stable"').replace('"beta-helper-"','"stable-helper-"').replace('"beta-locale-"','"stable-locale-"')+source[end:]
    old='if(Path.GetExtension(source).Equals(".rwd",StringComparison.OrdinalIgnoreCase))'
    source=source.replace(old,'if(new[]{"Data.rwd","Music.rwd"}.Contains(Path.GetFileName(source)))')
    assert 'No-launch verification only' in source
    folder=OUT/'installer-qa';project(folder,source)
    for p in (WS/'outputs/cache-stability-release-20261114/installer-qa-r6').glob('*.cs'):
        if p.name!='Program.cs':shutil.copy2(p,folder/p.name)
    fixture=OUT/'installer-fixture';cached=fixture/'cache/downloads';cached.mkdir(parents=True,exist_ok=True)
    oldCache=Path('G:/PawCacheReleaseQA-20261114/arcane-r6/cache/downloads')
    for p in oldCache.rglob('*.zip'):
        dest=cached/p.relative_to(oldCache);dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():os.link('\\\\?\\'+str(p.resolve()),'\\\\?\\'+str(dest.resolve()))
    stock=Path('G:/PawsWork/BaseGame/1.3.72');before={n:sha(stock/n) for n in ['Data.rwd','Music.rwd']}
    args=[SDK,'run','--project',folder/'QA.csproj','-c','Release','--','--root='+str(fixture),'--stock='+str(stock),'--stable='+str(OUT/'local-feeds/v3-stable.json'),'--beta='+str(OUT/'before/feed/v3/beta.json'),'--key='+str(OUT/'public.pem'),'--mode=verify','--channel=stable','--mod=arcane-wars']
    text=run(args,OUT/'installer-checks.log');print(text[-2200:],flush=True);assert text.count('INSTALL_PASS ')==12
    assert before=={n:sha(stock/n) for n in before}
    write(OUT/'installer-result.json',dict(passed=True,cases=12,launcher='1.0.18',localLauncherDllSha256=sha(folder/'launcher/PawsPatchLauncher.dll'),baseArchivesUnchanged=before,gamesLaunched=False))
if __name__=='__main__':globals()[sys.argv[1]]()
