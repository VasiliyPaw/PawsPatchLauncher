"""Hash-bound rebuild of shipped native/UI and all helper variants; no game access."""
import argparse,re,shutil,zipfile
from context import *
TCC=REPO.parents[1]/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
BASE=Path('F:/PawsLobbyColorsPublish-20261109')
NATIVES={'arcane':Path('C:/PawsArcane051ReleaseQA-20261109/native-r7'),'pure':REPO/'outputs/pure-050-optimizations-20261109/native-r1'}
DLLS={'arcane':'PawsPresentation1372.dll','pure':'PawsPurePresentation1372.dll'}

def once(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)

def correct(s):
 s=once(s,'typedef void(FC*Inverse)(U,U,float*,int,int);','typedef U(FC*Inverse)(U,U,float*,int,int);')
 s=once(s,'static void FC inverse(U self,U unused,float*out,int x,int y){U world,terrain;(void)unused;\n ((Inverse)(base+0x2a42aa))(self,0,out,x,y);','static U FC inverse(U self,U unused,float*out,int x,int y){U world,terrain,result;(void)unused;\n result=((Inverse)(base+0x2a42aa))(self,0,out,x,y);')
 return once(s,' out[1]=((out[1]/F(terrain,0x10)-.5f)/zoom+cy)*F(terrain,0x10);\n }\n}',' out[1]=((out[1]/F(terrain,0x10)-.5f)/zoom+cy)*F(terrain,0x10);\n }\n return result;\n}')

def native():
 sys.path[:0]=[str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
 import pefile
 for kind,base in NATIVES.items():
  meta=read(base/('runtime.json'if kind=='arcane'else'build.json'));assert sha(base/DLLS[kind])==meta['sha256']
  for name,digest in meta['sources'].items():assert sha(base/name)==digest
  out=OUT/(kind+'-native');out.mkdir(exist_ok=False)
  for name in meta['sources']:shutil.copy2(base/name,out/name)
  original=(out/'ui.c').read_text();fixed=correct(original);(out/'ui.c').write_text(fixed)
  if kind=='arcane':
   def body(s):return s[s.index('typedef U(FC*Inverse)'):s.index('typedef void(FC*Draw)')]+s[s.index('static U FC inverse'):s.index('static void FC map_draw')]
   assert body(fixed)==body((REPO/'game/ui-scout-test/runtime.c').read_text())
  args=[TCC,'-shared','-Wall','-Werror',out/'runtime.c',out/'ui.c',out/'find.c','-o',out/DLLS[kind],'-lkernel32','-luser32']
  run(args,out/'build.log');pe=pefile.PE(str(out/DLLS[kind]));exports={x.name.decode().lstrip('_').split('@')[0]:x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols}
  assert set(exports)=={'PawPresentationFrame','PawPresentationQueued'}
  write(out/'build.json',dict(sha256=sha(out/DLLS[kind]),sources={name:sha(out/name)for name in meta['sources']},compiler=list(map(str,args)),exports=exports,baseline=str(base),baselineSha256=meta['sha256'],change='Preserve native inverse-coordinate EAX return pointer'))
  qa=out/'qa';qa.mkdir()
  shutil.copy2(out/'day_clock.h',qa/'day_clock.h')
  if kind=='arcane':
   for name in ['qa.h','dispatch.h']:shutil.copy2(base/name,qa/name)
   text=fixed.replace('#define X\n','#define X __declspec(dllexport)\n')
   (qa/'ui.c').write_text(text);args=[TCC,'-shared','-DPAW_QA','-Wall','-Werror',qa/'ui.c','-o',qa/'PawUiScoutQA.dll','-lkernel32','-luser32']
  else:
   text=fixed+'''\n__declspec(dllexport) U __cdecl Test_Entry(U image,const Host*h,U index){base=image;host=h;
 switch(index){case 4:return(U)inverse;case 5:return(U)project;case 6:return(U)map_draw;case 7:return(U)mini_update;case 9:return(U)wheel_zoom;case 10:return(U)quad_update;case 11:return(U)&zoom;case 13:return(U)day_minutes;case 16:return(U)day_existing;case 17:return(U)day_clock_tick;default:return 0;}}
__declspec(dllexport) void __cdecl Test_View(U widget,float scale,float x,float y){mapWidget=widget;zoom=scale;cx=x;cy=y;}
'''
   (qa/'ui.c').write_text(text);args=[TCC,'-shared','-Wall','-Werror',out/'runtime.c',qa/'ui.c',out/'find.c','-o',qa/'PawUiScoutQA.dll','-lkernel32','-luser32']
  run(args,qa/'build.log')
  run([PYTHON,REPO/'game/ui-scout-test/test_inverse_return.py','--build',qa,'--expect-bug','0','--report',out/'return-contract.json'],qa/'inverse.log')
  if kind=='arcane':test=REPO/'game/ui-scout-test/test_native.py'
  else:
   source=(REPO/'tools/Pure050Release/test_ui.py').read_text();start=source.index(" source=(REPO/'game/ui-scout-test/test_native.py').read_text()");end=source.index(' # Expand the established',start)
   harness='import sys,json,subprocess\nfrom pathlib import Path\nREPO=Path('+repr(str(REPO))+')\nout=Path('+repr(str(qa))+')\n'+''.join(line[1:]+'\n'for line in source[start:end].splitlines())
   test=qa/'run-native.py';test.write_text(harness)
  run([PYTHON,test,'--build',qa],qa/'native.log')
  print('MINIMAP_NATIVE_PASS',kind,read(qa/'native-test.json')['checks'],flush=True)

def helpers():
 for kind in VERSIONS:
  base=BASE/(kind+'-helpers');rows=read(base/'build-report.json');out=OUT/(kind+'-helpers');out.mkdir(exist_ok=False);inputs=out/'inputs';inputs.mkdir()
  meta=read(OUT/(kind+'-native')/'build.json');old_native=meta['baselineSha256'];new_native=meta['sha256']
  previous_patch=next(iter(rows.values()))['features']['patchVersion'];old_runtime=next(iter(rows.values()))['features'].get('version')
  for name,row in rows.items():
   assert sha(base/name)==row['sha256']
   for path,digest in row['sources'].items():assert sha(path)==digest,path
  for name in ['paws_player_colors.ini','paws_patch_versions.ini']:
   if (base/name).exists():(out/name).write_bytes((base/name).read_bytes().replace(previous_patch.encode(),VERSIONS[kind].encode()))
  mapped={};audit={}
  for path in sorted({p for r in rows.values()for p in r['sources']}):
   original=Path(path);data=original.read_bytes();old_data=data
   if original.name==DLLS[kind]:
    assert sha(original)==old_native;data=(OUT/(kind+'-native')/DLLS[kind]).read_bytes()
   elif original.suffix.lower()=='.cs':
    text=data.decode('utf-8-sig');text=text.replace(previous_patch,VERSIONS[kind])
    if kind=='pure':text=text.replace(old_runtime,RUNTIME)
    if original.name in ['PresentationRuntimePayload.cs','PurePresentationRuntimePayload.cs']:
     text=once(text,old_native,new_native)
     for export,field in [('PawPresentationQueued','QueuedRva'),('PawPresentationFrame','FrameRva')]:
      text,n=re.subn(field+r'=\d+',field+'='+str(meta['exports'][export]),text);assert n==1
    data=text.encode('utf-8')
   dest=inputs/hashlib.sha256(data).hexdigest().upper()/original.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data);mapped[path]=str(dest)
   if data!=old_data:audit[path]=dict(before=sha(original),after=sha(dest))
  report={}
  for name,row in rows.items():
   args=[]
   for arg in row['args']:
    if arg.startswith('/out:'):arg='/out:'+str(out/name)
    elif arg.startswith('/resource:'):
     path,res=arg[10:].rsplit(',',1);arg='/resource:'+mapped[path]+','+res
    elif arg in mapped:arg=mapped[arg]
    args.append(arg)
   run(args);features=json.loads(run([out/name,'--features']));expected=dict(row['features']);expected['patchVersion']=VERSIONS[kind]
   if kind=='pure':expected['version']=RUNTIME
   assert features==expected,(name,features,expected)
   flags=[]if kind=='pure'else['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']
   tests={flag:run([out/name,flag])for flag in flags}
   paths=[Path(x)for x in args if x.lower().endswith('.cs')]+[Path(x[10:].rsplit(',',1)[0])for x in args if x.startswith('/resource:')]
   report[name]=dict(sha256=sha(out/name),features=features,args=args,sources={str(p):sha(p)for p in paths},selfTests=tests,baselineSha256=row['sha256'])
  write(out/'build-report.json',report);write(out/'changed-inputs.json',audit)
  print('MINIMAP_HELPERS_PASS',kind,len(report),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['native','helpers']);globals()[p.parse_args().action]()
