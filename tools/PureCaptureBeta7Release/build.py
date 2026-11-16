from context import *
import shutil,re

def native():
 d=O/'native';d.mkdir(exist_ok=True);m=read(BASE/'pure-native/runtime.json')
 for n,h in m['sources'].items():
  src=Path(m['compiler'][m['compiler'].index(str(BASE/'pure-native'/n))])if str(BASE/'pure-native'/n)in m['compiler']else BASE/'pure-native'/n
  if not src.exists():src=WS/'outputs/cache-capacity-20261114/pure-native'/n
  assert sha(src)==h,n;shutil.copy2(src,d/n)
 c=(S/'game/capture-knowledge/capture_knowledge.c').read_text();start=c.index('__declspec(dllexport)int __cdecl K2Plugin_Start');end=c.index('#ifdef CAPTURE_KNOWLEDGE_TEST',start)
 c=c[:start]+'#ifndef CAPTURE_KNOWLEDGE_EMBEDDED\n'+c[start:end]+'#else\nint __cdecl PawCaptureStart(const Host*h){if(!h||h->api!=1)return 1;host=h;image=h->exeBase;return install()?0:1;}\n#endif\n'+c[end:]
 (d/'capture_knowledge.c').write_text(c)
 f=d/'runtime.c';s=f.read_text();anchor='extern int __cdecl PawUiStart(const Host*);';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\nextern int __cdecl PawCaptureStart(const Host*);')
 anchor=' if(PawUiStart(&host)||PawUiInstall())return 6;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n if(PawCaptureStart(&host)){PawUiUndo();return 9;}');f.write_text(s)
 args=[CC,'-shared','-Wall','-Werror','-DCAPTURE_KNOWLEDGE_EMBEDDED',d/'runtime.c',d/'ui.c',d/'capture_knowledge.c','-o',d/'PawsPurePresentation1372.dll','-lkernel32','-luser32'];run(args,d/'build.log')
 import pefile
 pe=pefile.PE(str(d/'PawsPurePresentation1372.dll'));exports={x.name.decode().lstrip('_').split('@')[0]:x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols};assert set(exports)=={'PawPresentationFrame','PawPresentationQueued'}
 # The standalone Arcane compilation remains byte-identical after this opt-in integration.
 (d/'standalone').mkdir(exist_ok=True)
 run([CC,'-shared','-Wall','-Werror',d/'capture_knowledge.c','-o',d/'standalone/PawsCaptureKnowledge.dll','-lkernel32'],d/'standalone-build.log');assert sha(d/'standalone/PawsCaptureKnowledge.dll')==read(CAND/'verification.json')['productionSha256']
 run([CC,'-shared','-Wall','-Werror','-DCAPTURE_KNOWLEDGE_EMBEDDED','-DCAPTURE_KNOWLEDGE_TEST',d/'capture_knowledge.c','-o',d/'PawsCaptureTest.dll','-lkernel32'],d/'test-build.log')
 write(d/'build-report.json',dict(sha256=sha(d/'PawsPurePresentation1372.dll'),exports=exports,compiler=list(map(str,args)),sources={n:sha(d/n)for n in ['runtime.c','ui.c','day_clock.h','capture_knowledge.c']},standaloneCompatibility=True,baselineSha256=m['sha256']));print('PURE_CAPTURE_NATIVE_BUILT',flush=True)

def helpers():
 rows=read(BASE/'pure-helpers/build-report.json');d=O/'helpers';d.mkdir(exist_ok=True);inputs=d/'inputs';inputs.mkdir(exist_ok=True);meta=read(O/'native/build-report.json');mapped={};audit={}
 for path,h in {p:h for r in rows.values()for p,h in r['sources'].items()}.items():
  src=Path(path);assert sha(src)==h,path;data=src.read_bytes()
  if src.name=='PawsPurePresentation1372.dll':assert h==meta['baselineSha256'];data=(O/'native/PawsPurePresentation1372.dll').read_bytes()
  elif src.suffix=='.cs':
   s=data.decode('utf-8-sig')
   if src.name=='4-PureChannel.cs':
    s=s.replace('0.5.0-beta.6',VERSION).replace('1.3.72-pure.20-beta.6',RUNTIME)
    assert s.count('                return result;')==1
    s=s.replace('                return result;', '''                result = result.TrimEnd('}') + ",\\"captureKnowledgeRevision\\":1}";
                return result;''')
   if src.name=='PurePresentationRuntimePayload.cs':
    s=s.replace(meta['baselineSha256'],meta['sha256'])
    for export,field in [('PawPresentationQueued','QueuedRva'),('PawPresentationFrame','FrameRva')]:s,n=re.subn(field+r'=\d+',field+'='+str(meta['exports'][export]),s);assert n==1
   if src.name=='PurePresentationRuntimePatch.cs':
    assert s.count('0x2b1ae6};')==1;s=s.replace('0x2b1ae6};','0x2b1ae6,0x228b6c};').replace('noActorHooks=true','captureKnowledge=1')
   data=s.encode()
  dest=inputs/hashlib.sha256(data).hexdigest().upper()/src.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data);mapped[path]=str(dest)
  if sha(dest)!=h:audit[path]=dict(before=h,after=sha(dest))
 for n in ['paws_player_colors.ini','paws_patch_versions.ini']:
  if(BASE/'pure-helpers'/n).exists():(d/n).write_bytes((BASE/'pure-helpers'/n).read_bytes().replace(b'0.5.0-beta.6',VERSION.encode()))
 report={}
 for name,row in rows.items():
  args=[]
  for a in row['args']:
   if a.startswith('/out:'):a='/out:'+str(d/name)
   elif a.startswith('/resource:'):
    p,label=a[10:].rsplit(',',1);a='/resource:'+mapped[p]+','+label
   elif a in mapped:a=mapped[a]
   args.append(a)
  run(args,d/(name+'.build.log'));features=json.loads(run([d/name,'--features']));expected=dict(row['features'],patchVersion=VERSION,version=RUNTIME,captureKnowledgeRevision=1);assert features==expected,(name,features,expected)
  sources={mapped[p]:sha(mapped[p])for p in row['sources']};report[name]=dict(sha256=sha(d/name),features=features,args=args,sources=sources,baselineSha256=row['sha256']);print('PURE_HELPER_PASS',name,flush=True)
 write(d/'build-report.json',report);write(d/'changed-inputs.json',audit)
if __name__=='__main__':native();helpers()
