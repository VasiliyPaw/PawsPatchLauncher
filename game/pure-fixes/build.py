"""Deterministic local builds/packages; no game launch, attach, install or publication."""
from pathlib import Path
import argparse,hashlib,io,json,os,subprocess,sys,zipfile

SOURCE=Path(__file__).resolve().parent
REPO=SOURCE.parents[1]
FRAMEWORK=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Microsoft.NET/Framework/v4.0.30319'
EXE='k2_paws_pure_fixes_1372.exe'
GAME_HASH='1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45'

def sha(b):return hashlib.sha256(b).hexdigest().upper()
def encoded(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def writejson(p,x):p.write_bytes(encoded(x))
def run(cmd):
    proc=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if proc.returncode:raise RuntimeError('Command failed: '+str(cmd[0])+'\n'+proc.stdout+'\n'+proc.stderr)
    return proc.stdout
def zipbytes(manifest,files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for name,data in [('module.json',encoded(manifest))]+[('payload/'+p,b) for p,b in sorted(files.items())]:
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    return out.getvalue()
def package(out,id,version,files,independent,priority,name,description):
    manifest={'id':id,'version':version,'files':[{'path':p,'size':len(b),'sha256':sha(b)} for p,b in sorted(files.items())],'remove':[]}
    raw=zipbytes(manifest,files);assert raw==zipbytes(manifest,files)
    folder=out/'packages';folder.mkdir(exist_ok=True);path=folder/(id+'-'+version+'.zip')
    if path.exists():assert path.read_bytes()==raw,'Immutable archive collision'
    else:path.write_bytes(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert len(z.namelist())==len(files)+1
        for f in manifest['files']:
            b=z.read('payload/'+f['path']);assert sha(b)==f['sha256'] and len(b)==f['size']
    release={'id':id,'version':version,'mods':['vanilla','immortals'],'priority':priority,'required':False,'experimental':False,
             'executableIndependent':independent,'size':len(raw),'sha256':sha(raw),'urls':[str(path)],'dependsOn':[],
             'name':name,'description':description}
    writejson(out/(id+'-module.json'),manifest);writejson(out/(id+'-package.json'),release)
    return release

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--dotnet',type=Path,required=True)
    p.add_argument('--native-deps',type=Path,required=True)
    p.add_argument('--original-ui-payload',type=Path)
    p.add_argument('--game-directory',type=Path,help='Optional read-only executable preflight; never launches game')
    args=p.parse_args();out=args.out.resolve()
    if out.exists() and any(out.iterdir()):raise RuntimeError('Choose a new empty output directory.')
    out.mkdir(parents=True,exist_ok=True)
    sdks=run([args.dotnet,'--list-sdks']).strip().splitlines();assert sdks,'No SDK compiler'
    sdk=sdks[-1].split(' [',1);sdk_root=Path(sdk[1].rstrip(']'))/sdk[0]
    compiler=[args.dotnet,sdk_root/'Roslyn/bincore/csc.dll']
    shared=['/nologo','/nostdlib+','/langversion:7.3','/deterministic+','/optimize+','/platform:x86',
            '/pathmap:'+str(SOURCE)+'=/src/pure-fixes']+['/r:'+str(FRAMEWORK/(n+'.dll')) for n in ('mscorlib','System','System.Core')]
    sources=[SOURCE/n for n in ('PurePatch.cs','NativeMemory.cs','Program.cs')]
    runtime=out/EXE
    run(compiler+shared+['/target:winexe','/out:'+str(runtime)]+sources)
    repro=out/'reproducibility';repro.mkdir()
    run(compiler+shared+['/target:winexe','/out:'+str(repro/EXE)]+sources)
    assert runtime.read_bytes()==(repro/EXE).read_bytes(),'Runtime build not reproducible'
    tests=out/'PureFixes.Tests.exe'
    run(compiler+shared+['/target:exe','/main:PawPureFixes.Tests','/out:'+str(tests)]+sources+[SOURCE/'Tests.cs'])
    evidence=out/'checks';evidence.mkdir()
    managed=run([tests,evidence]);(out/'managed-test-output.txt').write_text(managed,encoding='utf-8')
    native=[sys.executable,SOURCE/'test_native.py','--out',evidence,'--deps',args.native_deps]
    if args.original_ui_payload:native+=['--original-ui-payload',args.original_ui_payload]
    native_output=run(native);(out/'native-test-output.txt').write_text(native_output,encoding='utf-8')
    features=json.loads(run([runtime,'--features']));writejson(out/'features.json',features)
    assert features['negativeZero'] and features['terrainInitialization'] and features['stockSyncChecks']
    assert all(not features[k] for k in ('colors','bypass','hostility','randomMap','randomTime','menuVersions','cityAssistant','fastSaveTransfer','changesGameFiles'))
    preflight=None
    if args.game_directory:
        preflight=run([runtime,'--preflight',args.game_directory]).strip()
        assert 'PURE_PREFLIGHT_PASS 1.3.72' in preflight
    source_text='\n'.join(p.read_text('utf-8') for p in sources)
    # The optional PAW_MENU_PRESENTATION block is excluded by this baseline build.
    # No presentation source/resource is supplied to the compiler here.
    forbidden=['RandomMapPatch','paws_patch_versions.ini','CreateRemoteThread','SY'+'NC_CONTINUE','MigratePersisted','RACE_'+'RELATIONS']
    assert all(s not in source_text for s in forbidden),'Unrelated feature source dependency'
    assert all(n not in source_text for n in ('System.Windows.Forms','System.Drawing','MessageBox','ShowDialog')),'Unexpected native UI dependency'
    data={}
    for org in ('Ceyah','Council','Default','Fallen','Monster','Nationalist','Royalist'):
        for name in (org+'Banner.NIF',org+'PlayerColor.tga'):
            rel='data/Organizations/Banners/'+org+'/'+name
            data[rel]=(REPO/'game/release-assets'/rel).read_bytes()
    assert len(data)==14 and all(Path(n).suffix.lower() in ('.nif','.tga') for n in data)
    releases=[
        package(out,'pure-fixes-data','1.0.0-pure.1',data,True,900,
                {'ru':"Paw's Patch: цвета значков рот",'en':"Paw's Patch: company badge colors"},
                {'ru':'Исправляет отображение цветов на значках рот, сохраняя мягкое затенение.','en':'Corrects company-badge colors while retaining soft shading.'}),
        package(out,'pure-fixes-runtime','1.3.72-pure.2',{EXE:runtime.read_bytes()},False,910,
                {'ru':"Paw's Patch: исправления движка",'en':"Paw's Patch: engine fixes"},
                {'ru':'Исправляет отображение отрицательного нуля и инициализацию параметра рельефа. Для поддерживаемой Kohan II 1.3.72.','en':'Corrects negative-zero display and terrain-parameter initialization. Requires the supported Kohan II 1.3.72 build.'})]
    writejson(out/'packages.json',releases)
    requirement={'version':'1.3.72','steamBuild':'25068126','k2ExeSha256':[GAME_HASH]}
    writejson(out/'mod-games.json',{'vanilla':requirement,'immortals':requirement})
    checks={'managed':json.loads((evidence/'managed-tests.json').read_text('utf-8')),
            'native':json.loads((evidence/'native-tests.json').read_text('utf-8'))}
    report={'packages':releases,'runtimeSha256':sha(runtime.read_bytes()),'runtimeBuildReproducible':True,
            'deterministicZip':True,'fileOnlyPayloadCount':len(data),'nativePayloadCount':1,
            'nativeExecutable':EXE,'knownGameHash':GAME_HASH,'readOnlyRealGamePreflight':preflight,
            'sourceHashes':{p.name:sha(p.read_bytes()) for p in sources+[SOURCE/'Tests.cs',SOURCE/'test_native.py',SOURCE/'build.py']},
            'checks':checks,'features':features,'unrelatedSourceDependencies':[],
            'gameLaunched':False,'nativeWindowsOpened':False,'published':False,
            'remainingAcceptance':'Parent will run visual and real-game/multiplayer checks; these are isolated offline tests.'}
    writejson(out/'build-verification.json',report)
    print(json.dumps({'runtime':str(runtime),'managedChecks':checks['managed']['checks'],'nativeChecks':checks['native']['checks'],
                      'reproducible':True,'packages':[p['id'] for p in releases],'published':False},indent=2))

if __name__=='__main__':main()
