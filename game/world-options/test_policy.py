"""Execute the real geometry/hash/interpolation in a host DLL, without a game."""
import argparse,collections,ctypes as C,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];WS=REPO.parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 source=out/'policy.c';native=WS/'outputs/world-options-20261107/native-r1/native'
 source.write_text('#include "'+str((REPO/'game/mixed-biomes/biomes.c').resolve()).replace('\\','/')+'"\n'+'''
__attribute__((dllexport)) U select_test(U seed,U *mapping){return biome_selection(seed,mapping);}
__attribute__((dllexport)) U offset_test(U seed){return cycle_offset(seed);}
__attribute__((dllexport)) void colors_test(U phase,float *a,float *b,float *out){cycle_colors(phase,a,b,out);}
''')
 compiler=WS/'work/crash-20260914-continue/tools/tinycc/tcc/x86_64-win32-tcc.exe';dll=out/'policy.dll'
 subprocess.run([str(compiler),'-shared','-w','-I'+str(native),str(source),'-o',str(dll)],check=True)
 d=C.CDLL(str(dll));d.select_test.argtypes=[C.c_uint,C.POINTER(C.c_uint)];d.offset_test.argtypes=[C.c_uint]
 d.colors_test.argtypes=[C.c_uint,*([C.POINTER(C.c_float)]*3)]
 mapping=(C.c_uint*4)();counts=collections.Counter();masks=collections.Counter();offsets=set()
 for seed in range(10000):
  n=d.select_test(seed,mapping);assert n in (1,2,3,4) and len(set(mapping))==n
  assert all(0<=v<4 for v in mapping)
  counts[n]+=1;masks[sum(1<<v for v in set(mapping))]+=1;offset=d.offset_test(seed);assert 0<=offset<9600;offsets.add(offset)
 assert set(masks)==set(range(1,16)) and all(abs(counts[n]/10000-.25)<.025 for n in range(1,5))
 assert len(offsets)>5000
 d.prepare_regions.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint];state=C.create_string_buffer(6295552);geometry=[]
 for seed in range(128):
  d.prepare_regions(state,96,96,seed);original=state.raw[164:164+96*96];assert set(original)=={0,1,2,3}
  n=d.select_test(seed,mapping);selected=bytes(mapping[v] for v in original);area=collections.Counter(selected)
  assert len(area)==n and min(area.values())>len(selected)*.08
  geometry.append(dict(seed=seed,count=n,mapping=list(mapping),areas=dict(area),sha256=hashlib.sha256(selected).hexdigest()))
 anchors=[(.8,.8,1,.7,.7,.9,.1,.1,.15),(1,1,1,1,1,1,0,0,0),(1,.8,.55,.8,.6,.4,.2,.1,.05),(.4,.4,.7,.4,.4,.7,.1,.1,.25)]
 maximum_step=0.;previous=None
 for phase in range(9601):
  k=(phase%9600)//2400;left=(C.c_float*9)(*anchors[k]);right=(C.c_float*9)(*anchors[(k+1)%4]);colors=(C.c_float*9)();d.colors_test(phase,left,right,colors)
  t=(phase%2400)/2400;t=t*t*(3-2*t);expected=[x+(y-x)*t for x,y in zip(left,right)]
  assert max(abs(x-y) for x,y in zip(colors,expected))<2e-7
  if phase%2400==0:assert list(colors)==list(left)
  if previous:maximum_step=max(maximum_step,max(abs(x-y) for x,y in zip(previous,colors)))
  previous=list(colors)
 assert maximum_step<.0005
 receipt=dict(accepted=True,seeds=10000,counts=dict(counts),all15Subsets=True,startPhases=len(offsets),geometryMaps=len(geometry),maximumColorStepPerGameTick=maximum_step,cycleSeconds=600,geometry=geometry)
 (out/'acceptance.json').write_text(json.dumps(receipt,indent=2));print('WORLD_POLICY_PASS 10000 seeds; all 15 subsets; 128 broad-region maps; 9601 smooth cycle samples')
if __name__=='__main__':main()
