"""Build isolated experimental payload/12 helpers from the last local candidate."""
import argparse,ast,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2];WS=REPO.parents[1]
OUT=Path(os.environ.get('PAW_EXPANDED_OUT',str(WS/'outputs/expanded-cache-20261114')));BASE=WS/'outputs/cache-capacity-20261114'
RAM_PERCENT=int(os.environ.get('PAW_EXPANDED_RAM_PERCENT','80'))
AIRCRAFT_REPAIR=os.environ.get('PAW_AIRCRAFT_FALL_REPAIR')=='1'
VERSIONS={'arcane':os.environ.get('PAW_PATCH_ARCANE_VERSION','0.5.1-beta.4'),'pure':os.environ.get('PAW_PATCH_PURE_VERSION','0.5.0-beta.5')}
PURE_RUNTIME=os.environ.get('PAW_PATCH_PURE_RUNTIME','1.3.72-pure.19-beta.5')
assert 80<=RAM_PERCENT<=90
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
sys.path[:0]=[str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def once(s,a,b):assert s.count(a)==1,(a[:60],s.count(a));return s.replace(a,b)
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,indent=2),encoding='utf-8')
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout

def native():
 out=OUT/'native';out.mkdir(exist_ok=True);src=out/'source';src.mkdir(exist_ok=True)
 if(out/'payload').exists():
  revision=1
  while(out/('payload-r'+str(revision))).exists():revision+=1
  assert out.resolve().drive=='G:' and out.resolve().is_relative_to(OUT.resolve())
  (out/'payload').rename(out/('payload-r'+str(revision)))
 s=(REPO/'game/resource-cache/policy.c').read_text()
 s=once(s,'{ram=100;vram=100;}','{ram=120;vram=120;}')
 s=once(s,'0)=80;','0)='+str(RAM_PERCENT)+';')
 s=once(s,'return sum?(U)((U64)total*weight/sum):0;','U64 q=sum?(U64)total*weight/sum:0;return q>0x70000000?0x70000000:(U)q;')
 (src/'base-policy.c').write_text(s);shutil.copy2(REPO/'game/resource-cache/expanded.c',src/'cache.c')
 s=(REPO/'game/resource-cache/build_native.py').read_text()
 s=once(s,'HERE=Path(__file__).resolve().parent','HERE=Path('+repr(str(src))+')')
 s=once(s,'WS=HERE.parents[3]','WS=Path('+repr(str(WS))+')')
 s=once(s,"asm(weights,'push ebp;mov ebp,esp;'", "asm(wrapper+0x300,'push ebp;mov ebp,esp;'+save+f'push dword ptr[ebp+16];push dword ptr[ebp+12];push dword ptr[ebp+8];push ecx;push {CAVE+state};call {CAVE+exports[\"rc_budget\"]};add esp,20;'+restore+'pop ebp;ret 12;')\n asm(weights,'push ebp;mov ebp,esp;'")
 s=once(s,"exports[\"rc_weights\"]", "exports[\"rc_weights_base\"]")
 s=once(s," assert hooks[0]['original']", " hooks.append(dict(site=0x1b57a8,entry=wrapper+0x300,original=raw[0x1b57a8:0x1b57b0].hex(),imageFixup=-1))\n assert hooks[2]['original']=='83ec18538a5c2428'\n assert hooks[0]['original']")
 if AIRCRAFT_REPAIR:
  s=once(s," asm(trampoline,",''' asm(wrapper+0x400,f'pushfd;push eax;mov eax,[esi+0x20];add eax,eax;jnz native; jmp finish;native:mulss xmm0,[esi+0x20];finish:pop eax;popfd;jmp {IMAGE+0x213dd5}')
 asm(trampoline,''')
  s=once(s," assert hooks[2]['original']", " hooks.append(dict(site=0x213dd0,entry=wrapper+0x400,original=raw[0x213dd0:0x213dd5].hex(),imageFixup=-1))\n assert hooks[3]['original']=='f30f594620'\n assert hooks[2]['original']")
 start=s.index(" cs+='internal static byte[] Original(");end=s.index(" cs+='internal static byte[] Build(",start)
 s=s[:start]+''' cs+='internal static byte[] Original(int i,uint image){string[] originals={'+','.join('"'+x['original']+'"' for x in hooks)+'};byte[] b=TerrainPatch.Hex(originals[i]);if(i==0)Add(b,1,unchecked(image-0x460000));return b;}\\n'
'''+s[end:]
 script=out/'build_native.py';script.write_text(s);print(run([sys.executable,script,'--out',out/'payload']).strip(),flush=True)
 # All older changes are retained by starting with the current local helpers.
 overlay=OUT/'overlay/data/UVars_k2.tgi';overlay.parent.mkdir(parents=True,exist_ok=True)
 text=(BASE/'overlay/data/UVars_k2.tgi').read_bytes()
 text=text.replace(b'ResourceCacheNiAVObjRAMWeight = 60',b'ResourceCacheNiAVObjRAMWeight = 40').replace(b'ResourceCacheNiAVObjVRAMWeight = 60',b'ResourceCacheNiAVObjVRAMWeight = 40')
 text=text.replace(b'}\r\n',b'\t\tint ResourceCachePercentOfTotalVRAM = 60\r\n}\r\n');overlay.write_bytes(text)
 write(OUT/'policy.json',dict(candidateOnly=True,ramCeilingMiB=3072,vramCeilingMiB=3072,perClassCeilingMiB=1792,reserveVirtualMiB=768,reservePhysicalMiB=384,pressurePollMs=1000,modelWeights=[40,40],sequenceWeights=[120,120],ramPercent=RAM_PERCENT,vramPercent=60,preparation=False,find=False,aircraftFallRepair=AIRCRAFT_REPAIR,overlaySha256=sha(overlay)))

def helpers():
 for kind in ['arcane','pure']:
  folder=OUT/(kind+'-helpers');folder.mkdir(exist_ok=True);(folder/'inputs').mkdir(exist_ok=True)
  old=BASE/(kind+'-helpers');rows=read(old/'build-report.json');mapping={};audit={}
  for name in ['paws_player_colors.ini','paws_patch_versions.ini']:
   if(old/name).is_file():(folder/name).write_bytes((old/name).read_bytes().replace(('0.5.1-beta.4'if kind=='arcane'else'0.5.0-beta.5').encode(),VERSIONS[kind].encode()))
  for path in sorted({p for row in rows.values()for p in row['sources']}):
   p=Path(path);original=p.read_bytes();assert all(sha(p)==r['sources'][path]for r in rows.values()if path in r['sources'])
   data=original
   if p.name.endswith('ResourceCachePayload.cs'):data=(OUT/'native/payload/ResourceCachePayload.cs').read_bytes()
   elif p.suffix.lower()=='.cs':
    s=original.decode('utf-8-sig');s=s.replace('0.5.1-beta.4'if kind=='arcane'else'0.5.0-beta.5',VERSIONS[kind])
    if kind=='pure':s=s.replace('1.3.72-pure.19-beta.5',PURE_RUNTIME)
    if p.name.endswith('ReleaseStartup.cs'):s=once(s,sha(BASE/'overlay/data/UVars_k2.tgi'),sha(OUT/'overlay/data/UVars_k2.tgi'))
    if p.name.endswith('ResourceCachePatch.cs'):s=once(s,'RESOURCE_CACHE r1; native per-class budgets repaired;', 'RESOURCE_CACHE experimental expanded r1; ceiling=3072MiB; reserveVA=768MiB; native per-class budgets repaired;')
    s=s.replace('animationCache=80/100/100','animationCache='+str(RAM_PERCENT)+'/120/120')
    s=s.replace(r'\"modelEffectCacheRamWeight\":60',r'\"modelEffectCacheRamWeight\":40').replace(r'\"modelEffectCacheVramWeight\":60',r'\"modelEffectCacheVramWeight\":40,\"expandedCacheBudgetRevision\":1,\"resourceCacheMaximumMiB\":3072,\"animationCacheWeight\":120')
    s=s.replace(r'\"animationCacheWeight\":120',r'\"animationCacheWeight\":120,\"resourceCacheRamPercent\":'+str(RAM_PERCENT)+r',\"aircraftFallRecoveryRevision\":'+str(int(AIRCRAFT_REPAIR)))
    if s!=original.decode('utf-8-sig'):data=(b'\xef\xbb\xbf'if original.startswith(b'\xef\xbb\xbf')else b'')+s.encode('utf-8')
   dest=folder/'inputs'/hashlib.sha256(data).hexdigest().upper()/p.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data);mapping[path]=str(dest)
   if original!=data:audit[path]=dict(before=sha(p),after=sha(dest))
  report={}
  for name,row in rows.items():
   args=[]
   for arg in row['args']:
    if arg.startswith('/out:'):arg='/out:'+str(folder/name)
    elif arg.startswith('/resource:'):
     path,res=arg[10:].rsplit(',',1);arg='/resource:'+mapping[path]+','+res
    elif arg in mapping:arg=mapping[arg]
    args.append(arg)
   run(args);f=json.loads(run([folder/name,'--features']))
   expected=dict(row['features'],patchVersion=VERSIONS[kind],modelEffectCacheRamWeight=40,modelEffectCacheVramWeight=40,expandedCacheBudgetRevision=1,resourceCacheMaximumMiB=3072,animationCacheWeight=120,resourceCacheRamPercent=RAM_PERCENT,aircraftFallRecoveryRevision=int(AIRCRAFT_REPAIR))
   if kind=='pure':expected['version']=PURE_RUNTIME
   assert f==expected
   paths=[Path(p)for p in args if p.lower().endswith('.cs')]+[Path(p[10:].rsplit(',',1)[0])for p in args if p.startswith('/resource:')]
   report[name]=dict(sha256=sha(folder/name),features=f,args=args,sources={str(p):sha(p)for p in paths},candidateOnly=True,baselineSha256=read(WS/'outputs/buffer-ownership-release-20261113'/(kind+'-helpers/build-report.json'))[name]['sha256'])
   print('EXPANDED_HELPER_READY',kind,name,flush=True)
  write(folder/'build-report.json',report);write(folder/'changed-inputs.json',audit)

if __name__=='__main__':
 OUT.mkdir(exist_ok=True);(OUT/'temp').mkdir(exist_ok=True);os.environ.update(TEMP=str(OUT/'temp'),TMP=str(OUT/'temp'),PYTHONDONTWRITEBYTECODE='1')
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['native','helpers']);globals()[parser.parse_args().action]()
