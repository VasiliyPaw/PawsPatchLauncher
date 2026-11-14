"""Local candidates: native Find, no preparation, larger native data-defined caches.

Does not access feeds, upload assets, install files, or control a game process.
"""
import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WS = REPO.parents[1]
BASE = WS / 'outputs/buffer-ownership-release-20261113'
OUT = WS / 'outputs/cache-capacity-20261114'
TCC = WS / 'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
GRAPHICS = '3B596B4A9435A8BDCD183906CAABE9CB60706FCE56783D42E8C66C52DA43944E'
CACHE_FEATURES = dict(terrainTexturePoolEntries=2048, modelEffectCacheRamWeight=60, modelEffectCacheVramWeight=60)
OLD_POOL_HASH = 'BB73F2CDF722024F89B7C57865A9D33FFE855D80637D7F3FCADEAD8089D25FCA'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p): return json.loads(Path(p).read_text('utf-8-sig'))
def write(p, v): Path(p).write_text(json.dumps(v, indent=2), encoding='utf-8')
def once(s, a, b):
    assert s.count(a) == 1, (a[:100], s.count(a))
    return s.replace(a, b)
def run(args):
    p = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=120)
    if p.returncode: raise RuntimeError(str(args[:2])+'\n'+p.stdout+p.stderr)
    return p.stdout

def native():
    shutil.copytree(REPO/'game/terrain-texture-pool/data',OUT/'overlay',dirs_exist_ok=True)
    spec = importlib.util.spec_from_file_location('arcane_policy_builder', REPO/'tools/Arcane051Release/build_native.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    arcane = OUT/'arcane-native'; arcane.mkdir(exist_ok=True)
    module.build_runtime(arcane)
    if not (arcane/'cache-build').exists(): module.build_cache(arcane)
    else: assert sha(arcane/'cache/cache.c')==sha(REPO/'game/resource-cache/policy.c')
    pure = OUT/'pure-native'; pure.mkdir(exist_ok=True)
    frozen = Path('G:/PawsWork/Retained/PawsMinimapCrashPublish-20261109/pure-native')
    proof = read(frozen/'build.json')
    for name in ['ui.c', 'day_clock.h']:
        assert sha(frozen/name) == proof['sources'][name], name
        shutil.copy2(frozen/name, pure/name)
    shutil.copy2(REPO/'game/presentation-runtime/runtime.c', pure/'runtime.c')
    assert 'PawFindStart' not in (pure/'runtime.c').read_text()
    args = [TCC, '-shared', '-Wall', '-Werror', pure/'runtime.c', pure/'ui.c', '-o', pure/'PawsPurePresentation1372.dll', '-lkernel32', '-luser32']
    run(args)
    pe = module.pefile.PE(str(pure/'PawsPurePresentation1372.dll'))
    exports = {x.name.decode().lstrip('_').split('@')[0]: x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols}
    assert set(exports) == {'PawPresentationFrame', 'PawPresentationQueued'}
    write(pure/'runtime.json', dict(sha256=sha(pure/'PawsPurePresentation1372.dll'), exports=exports, perFindCacheRevision=0, compiler=list(map(str,args)), sources={n:sha(pure/n) for n in ['ui.c','day_clock.h','runtime.c']}))
    qa = pure/'qa'; qa.mkdir(exist_ok=True)
    text=(frozen/'qa/ui.c').read_text()
    assert text.startswith((frozen/'ui.c').read_text())
    (qa/'ui.c').write_text(text);shutil.copy2(pure/'day_clock.h',qa/'day_clock.h')
    run([TCC,'-shared','-Wall','-Werror',pure/'runtime.c',qa/'ui.c','-o',qa/'PawUiScoutQA.dll','-lkernel32','-luser32'])
    print('NATIVE_CANDIDATES_READY; frozen UI unchanged; Find not compiled; no preparation code', flush=True)

def helpers():
    for kind in ['arcane', 'pure']:
        base = BASE/(kind+'-helpers'); rows = read(base/'build-report.json')
        dest = OUT/(kind+'-helpers'); dest.mkdir(exist_ok=True); (dest/'inputs').mkdir(exist_ok=True)
        for name in ['paws_player_colors.ini','paws_patch_versions.ini']:
            if (base/name).is_file(): shutil.copy2(base/name,dest/name)
        native_dir = OUT/(kind+'-native'); meta = read(native_dir/'runtime.json')
        native_name = 'PawsPresentation1372.dll' if kind=='arcane' else 'PawsPurePresentation1372.dll'
        mapped = {}; audit = {}
        for p in sorted({p for row in rows.values() for p in row['sources']}):
            src = Path(p); original = src.read_bytes()
            assert all(row['sources'][p]==sha(src) for row in rows.values() if p in row['sources']), p
            data = original
            if src.name == native_name:
                data = (native_dir/native_name).read_bytes()
            elif src.name.endswith('ResourceCachePayload.cs'):
                data = (OUT/'arcane-native/cache-build/ResourceCachePayload.cs').read_bytes()
            elif src.suffix.lower() == '.cs':
                s = original.decode('utf-8-sig')
                if src.name.endswith('ResourceCachePatch.cs'):
                    s = once(s, 'BitConverter.GetBytes(3u)', 'BitConverter.GetBytes(1u)')
                    s = once(s, 'bounded VIEW-thread model/effect preparation', 'model/effect preparation removed')
                elif src.name.endswith('PresentationRuntimePatch.cs'):
                    s = once(s, 'localFind=true', 'localFind=false/native')
                    s = once(s, 'resourcePreparation=bounded', 'resourcePreparation=disabled')
                    s = once(s, ',0x18e3c8', '')
                elif src.name.endswith('PresentationRuntimePayload.cs'):
                    s, n = re.subn(r'Sha256="[A-F0-9]{64}"', 'Sha256="'+meta['sha256']+'"', s, count=1); assert n==1
                    s, n = re.subn(r'QueuedRva=\d+,FrameRva=\d+', 'QueuedRva='+str(meta['exports']['PawPresentationQueued'])+',FrameRva='+str(meta['exports']['PawPresentationFrame']), s); assert n==1
                    assert GRAPHICS in s
                elif src.name.endswith('ReleaseStartup.cs'):
                    s = once(s, OLD_POOL_HASH, sha(OUT/'overlay/data/UVars_k2.tgi'))
                s = s.replace(r'\"resourcePrewarmRevision\":1', r'\"resourcePrewarmRevision\":0')
                s = s.replace(r'\"perFindCacheRevision\":1', r'\"perFindCacheRevision\":0')
                s = s.replace(r'\"terrainTexturePoolEntries\":1024',r'\"terrainTexturePoolEntries\":2048,\"modelEffectCacheRamWeight\":60,\"modelEffectCacheVramWeight\":60')
                # Preserve BOM/newlines and every unrelated input byte exactly.
                if s != original.decode('utf-8-sig'):
                    data = (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+s.encode('utf-8')
            target = dest/'inputs'/hashlib.sha256(data).hexdigest().upper()/src.name
            target.parent.mkdir(exist_ok=True); target.write_bytes(data); mapped[p] = str(target)
            if data!=original: audit[p] = dict(before=sha(src), after=sha(target))
        report = {}
        for name, row in rows.items():
            args = []
            for arg in row['args']:
                if arg.startswith('/out:'): arg='/out:'+str(dest/name)
                elif arg.startswith('/resource:'):
                    p,res = arg[10:].rsplit(',',1); arg='/resource:'+mapped[p]+','+res
                elif arg in mapped: arg=mapped[arg]
                args.append(arg)
            run(args)
            features = json.loads(run([dest/name, '--features']))
            assert features==dict(row['features'], resourcePrewarmRevision=0, perFindCacheRevision=0, **CACHE_FEATURES), name
            flags = [] if kind=='pure' else ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']
            tests = {flag:run([dest/name,flag]).strip() for flag in flags}
            paths = [Path(p) for p in args if p.lower().endswith('.cs')]+[Path(p[10:].rsplit(',',1)[0]) for p in args if p.startswith('/resource:')]
            report[name] = dict(sha256=sha(dest/name), features=features, args=args, sources={str(p):sha(p) for p in paths}, selfTests=tests, baselineSha256=row['sha256'], candidateOnly=True)
            print('CANDIDATE_HELPER_READY', kind, name, flush=True)
        write(dest/'build-report.json', report); write(dest/'changed-inputs.json',audit)

def checks():
    folder = OUT/'checks'; folder.mkdir(exist_ok=True)
    compiler = Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
    exe = folder/'CompiledChecks.exe'
    run([compiler, '/nologo', '/target:exe', '/platform:x86', '/out:'+str(exe), REPO/'tools/NativeRenderPolicy/CompiledChecks.cs'])
    result = run([exe,OUT,BASE,GRAPHICS]); (folder/'compiled.log').write_text(result); print(result.strip(),flush=True)
    guards=folder/'TerrainGuardChecks.exe'
    run([compiler,'/nologo','/target:exe','/platform:x86','/out:'+str(guards),REPO/'game/terrain-texture-pool/StartupGuardTests.cs'])
    helpers=sorted((OUT/'arcane-helpers').glob('k2_paws_*.exe'))+sorted((OUT/'pure-helpers').glob('k2_paws_*.exe'))
    result=run([guards,OUT/'overlay/data/UVars_k2.tgi',*helpers]);(folder/'terrain-guards.log').write_text(result);print(result.strip(),flush=True)
    result=run([sys.executable,REPO/'game/terrain-texture-pool/validate.py']);(folder/'overlay.log').write_text(result);print(result.strip(),flush=True)
    fixture = folder/'PathFixture.exe'
    # Each UI flavour checks a different first guard. Map both fake regions.
    source=(REPO/'game/presentation-runtime/path_fixture.c').read_text()
    source=once(source,'if(!pages||!code||!manager)return 93;', 'if(!pages||!code||!manager)return 93; if(!VirtualAlloc((void*)(uintptr_t)(image+0x500000),0x10000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE))return 96;')
    (folder/'path_fixture.c').write_text(source)
    run([TCC, '-Wall','-Werror','-Wl,--image-base=0x20000000',folder/'path_fixture.c','-o',fixture,'-lkernel32','-luser32'])
    install_fixture=folder/'PolicyFixture.exe'
    run([TCC, '-Wall','-Werror','-Wl,--image-base=0x20000000',REPO/'tools/NativeRenderPolicy/install_fixture.c','-o',install_fixture,'-lkernel32','-luser32'])
    path_results = {}
    for kind,name in [('arcane','PawsPresentation1372.dll'),('pure','PawsPurePresentation1372.dll')]:
        path_results[kind] = run([fixture,OUT/(kind+'-native')/name,'1']).strip()
        path_results[kind+'Install'] = run([install_fixture,OUT/(kind+'-native')/name,kind]).strip()
    write(folder/'paths.json',path_results); print(path_results,flush=True)
    result = run([sys.executable, REPO/'tools/NativeRenderPolicy/test_policy.py','--native',OUT/'arcane-native/cache-build'])
    (folder/'cache.log').write_text(result); print(result.strip(),flush=True)
    result = run([sys.executable, REPO/'game/ui-scout-test/test_native.py','--build',OUT/'arcane-native'])
    (folder/'ui.log').write_text(result); print(result.strip(),flush=True)
    for kind in ['arcane','pure']:
        build=OUT/(kind+'-native');qa=build if kind=='arcane' else build/'qa'
        result=run([sys.executable,REPO/'game/ui-scout-test/test_inverse_return.py','--build',qa,'--expect-bug','0','--report',build/'return-contract.json'])
        (folder/(kind+'-return.log')).write_text(result);print(result.strip(),flush=True)
    write(folder/'result.json',dict(passed=True,helpers=12,gamesLaunched=False,liveGameModified=False,published=False,removed=['resource preparation','accelerated Find'],animationPolicyUnchanged=True,cacheSettings=CACHE_FEATURES,overlaySha256=sha(OUT/'overlay/data/UVars_k2.tgi')))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['native','helpers','checks']);parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args();OUT=args.out.resolve();OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'temp').mkdir(exist_ok=True)
    os.environ.update(TEMP=str(OUT/'temp'),TMP=str(OUT/'temp'),PYTHONDONTWRITEBYTECODE='1')
    globals()[args.action]()
