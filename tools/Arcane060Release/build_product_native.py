"""Build the accepted nine R24 modules with a production activation stamp.

Only marker names and module filenames change. No QA driver is compiled or
shipped; the exact bridge simulation payload remains byte-identical to R24.
"""
from pathlib import Path
import json,hashlib,subprocess,os,shutil,re
P=Path(__file__).resolve().parent;R=Path((P/'target.txt').read_text());OLD=P.parent/'r24-racial-build-beta-20261114';OUT=P.parents[1]/'outputs/arcane-060-beta-release-20261115';D=OUT/'native';D.mkdir(exist_ok=True)
CC=P.parent/'crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
env=os.environ.copy();env.update(TEMP=str(P/'Temp'),TMP=str(P/'Temp'))
specs=[('Bridges',OLD/'source/game/engineer-bridges','runtime.c','PawsBridges.dll'),('Militia',P.parent/'rivers-r14-20261111/source/osnova-20261111','militia.c','PawsMilitia.dll'),('Siege',P.parent/'rivers-r14-20261111/source/osnova-20261111/siege','siege.c','PawsSiege.dll'),('Biomes',R/'source/biome-wide','wide_biomes.c','PawsWideBiomes.dll'),('Water',R/'source/water-wide','water_wide.c','PawsWaterBiomes.dll'),('Camera',R/'source/camera-range','gameplay_range.c','PawsCameraRange.dll'),('Minimap',R/'source/minimap-biomes','minimap_biomes.c','PawsMinimapBiomes.dll'),('Startup',R/'source/startup','startup_optimizations.c','PawsStartupOptimizations.dll'),('Font',R/'source/startup','font_runtime.c','PawsFontMetrics.dll')]
manifest={}
for label,src,name,target in specs:
 folder=D/label;folder.mkdir(exist_ok=True)
 for f in src.iterdir():
  if f.is_file()and f.suffix in ['.c','.h']:shutil.copy2(f,folder/f.name)
 if label=='Bridges':shutil.copy2(OLD/'native/plugin_data.h',folder/'plugin_data.h')
 f=folder/name;s=f.read_text();before=s
 for marker in ['terrain-prototype.marker','installed-runtime.marker','militia-test.marker','biome-wide.marker','water-wide.marker']:s=s.replace(marker,'paws_runtime.marker')
 f.write_text(s)
 # The frozen runtime wrapper contains no QA command polling unless explicitly
 # compiled with PAWS_BRIDGE_QA; it is deliberately omitted here.
 args=[str(CC),'-shared','-Wall','-Werror','-I'+str(folder),str(f),'-o',str(D/target),'-lkernel32','-luser32','-lgdi32']
 cp=subprocess.run(args,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert cp.returncode==0,cp.stdout
 manifest[target]={'sha256':sha(D/target),'source':str(f),'sourceSha256':sha(f),'args':args,'markerOnlySourceChange':s!=before,'noQADefine':True,'files':{str(p):sha(p)for p in folder.iterdir()if p.is_file()}}
 print('PRODUCT_NATIVE_READY',target,flush=True)
assert (D/'Bridges/plugin_data.h').read_bytes()==(OLD/'native/plugin_data.h').read_bytes()
(D/'build-report.json').write_text(json.dumps(manifest,indent=2));print('NINE_PRODUCT_MODULES_READY')
