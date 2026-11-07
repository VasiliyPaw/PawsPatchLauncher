"""Emit into a new owned output; leave accepted release/prototype outputs intact."""
import argparse,json,shutil
from pathlib import Path

HERE=Path(__file__).resolve().parent
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cycle-seconds',type=int,default=600);a=ap.parse_args()
 assert 4<=a.cycle_seconds<=3600
 out=a.out.resolve();native=out/'native';native.mkdir(parents=True,exist_ok=False)
 repo=HERE.parents[1];ws=repo.parents[1];source=repo/'game/mixed-biomes/build.py'
 shutil.copy2(ws/'outputs/mixed-biomes-r2-20261106/native/spawn-index.h',native/'spawn-index.h')
 code=source.read_text();code=code[:code.index('# Reuse the full beta.11 feature composition')]
 code=code.replace("'-nostdlib',", "'-nostdlib','-DPAWS_DAY_CYCLE_SECONDS="+str(a.cycle_seconds)+"',",1)
 code=code.replace("OUT=WS/'outputs/mixed-biomes-r2-20261106'",'OUT=Path('+repr(str(out))+')')
 code=code.replace('MixedBiomesTestPatch','MixedBiomesPatch').replace('LOCAL_MIXED_BIOMES r2;','WORLD_OPTIONS r1;')
 anchor="hooks=[dict(site=0x25697a"
 insertion='''
tick=wrapper+0xb00;sunstart=wrapper+0xc00
asm(tick,f'call {IMAGE+0x20d4b};pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push esi;push {CAVE+state};call {CAVE+exports["world_tick"]};add esp,8;fxrstor [esp];mov esp,ebp;popad;popfd;ret;')
asm(sunstart,f'push esi;lea esi,[ecx-0x4c];push dword ptr[esp+20];push dword ptr[esp+20];push dword ptr[esp+20];push dword ptr[esp+20];call {IMAGE+0x23daac};pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push esi;push {CAVE+state};call {CAVE+exports["world_tick"]};add esp,8;fxrstor [esp];mov esp,ebp;popad;popfd;pop esi;ret 16;')
'''
 assert code.count(anchor)==1;code=code.replace(anchor,insertion+anchor)
 anchor="for h in hooks:\n"
 code=code.replace(anchor,"hooks += [dict(site=0x246a40,entry=tick,n=5,op=0xe8),dict(site=0x2462bc,entry=sunstart,n=5,op=0xe8)]\n"+anchor,1)
 exec(compile(code,str(source),'exec'),{'__file__':str(source)})
 meta=json.loads((native/'payload.json').read_text());assert len(meta['hooks'])==8
 meta['dynamicDayCycleSeconds']=a.cycle_seconds;(native/'payload.json').write_text(json.dumps(meta,indent=2))
 assert next(h['before'] for h in meta['hooks'] if h['site']==0x246a40)=='e806a3ddff'
 assert next(h['before'] for h in meta['hooks'] if h['site']==0x2462bc)=='e8eb77ffff'
 print('WORLD_OPTIONS_NATIVE_READY',out)
if __name__=='__main__':main()
