"""Run the actual Pure compiled minimap/clock and emitted HUD payload."""
import subprocess
from context import *

def main():
 out=OUT/'ui-tests-r4';out.mkdir(exist_ok=False);native=OUT/'ui-native-r3'
 # QA exports only expose existing static callbacks; shipping DLL has two exports.
 text=(native/'ui.c').read_text()+'''
__declspec(dllexport) U __cdecl Test_Entry(U image,const Host*h,U index){base=image;host=h;
 switch(index){case 4:return(U)inverse;case 5:return(U)project;case 6:return(U)map_draw;case 7:return(U)mini_update;case 9:return(U)wheel_zoom;case 10:return(U)quad_update;case 11:return(U)&zoom;case 13:return(U)day_minutes;case 16:return(U)day_existing;case 17:return(U)day_clock_tick;default:return 0;}}
__declspec(dllexport) void __cdecl Test_View(U widget,float scale,float x,float y){mapWidget=widget;zoom=scale;cx=x;cy=y;}
'''
 (out/'ui.c').write_text(text);(out/'day_clock.h').write_bytes((native/'day_clock.h').read_bytes())
 args=[TCC,'-shared','-Wall','-Werror',native/'runtime.c',out/'ui.c','-o',out/'PawUiScoutQA.dll','-lkernel32','-luser32'];subprocess.run(list(map(str,args)),check=True)
 source=(REPO/'game/ui-scout-test/test_native.py').read_text()
 start=source.index('for image,dll in [');prefix=source[:start]
 start=source.index(' # Actual compiled minimap callbacks.');end=source.index(' f=Fixture(image,dll);owned=',start);mini=source[start:end]
 start=source.index(' f=Fixture(image,dll);table=');end=source.index('reference=None',start);clock=source[start:end]
 start=source.index('# Native Game HUD survives');end=source.index("print('UI_SCOUT_NATIVE_PASS'",start);lifecycle=source[start:end]
 clock=clock.replace("'sun_default'","'sun_afternoon'").replace('cmp word ptr [edx+10],101','cmp word ptr [edx+8],97')
 test=prefix+'for image,dll in [(0x460000,0x10000000),(0xb30000,0x14000000),(0x12000000,0x20000000)]:\n f=Fixture(image,dll)\n'+mini+clock+lifecycle+"\nprint('PURE_PRESENTATION_NATIVE_PASS',checks)\n(a.build/'native-test.json').write_text(json.dumps(dict(passed=True,checks=checks,bases=3,scope=['minimap','clock']),indent=2))\n"
 (out/'test_native.py').write_text(test);subprocess.run([sys.executable,out/'test_native.py','--build',out],check=True)
 # Expand the established emitted machine-code test with actual new names,
 # unnamed template identity, null/empty name fallback and native resign vtable.
 import base64,re
 build=OUT/'beta-helpers-r4';emitted=out/'hud';emitted.mkdir()
 managed=(build/'source/13-GamePresentation1372.cs').read_text();managed=managed[managed.index('internal static byte[] HudLayoutCode'):]
 code=base64.b64decode(re.search(r'FromBase64String\("([A-Za-z0-9+/=]+)"\)',managed).group(1));assert code==(build/'hud/hud.bin').read_bytes();(emitted/'hud-layout.bin').write_bytes(code)
 (emitted/'uniform-phase.bin').write_bytes(bytes.fromhex('a10000000083f80f77158b04850000000085c0740a8138000000000f94c0c330c0c3'))
 hud=(REPO/'game/widescreen-ui/test_hud_layout.py').read_text()
 hud=hud.replace("[('ObjectDisplay',295,456,None)","[('NativeResign',358,308,0),('GameMenuDialog',340,340,0),('StagingFileSavedDialog',340,340,0),('StagingFileLoadSavedDialog',340,340,0),('TemplateFallback',340,340,0),('EmptyFallback',340,340,0),('ObjectDisplay',295,456,None)")
 hud=hud.replace('word(ve+0xc,owner);',"word(owner,image+0x491788 if key=='NativeResign' else 0);word(owner+0x1c,name+200);u.mem_write(name+200,('GameMenuDialog'+chr(0)).encode('utf-16le'));word(ve+0xc,owner);")
 anchor="u.mem_write(name,(key+'\\0').encode('utf-16le'))";assert anchor in hud
 hud=hud.replace(anchor,anchor+";word(owner+4,0 if key=='TemplateFallback' else name);u.mem_write(name,bytes(2)) if key=='EmptyFallback' else None")
 (out/'test_hud.py').write_text(hud);subprocess.run([sys.executable,out/'test_hud.py','--legacy',LEG,'--emitted',emitted,'--fixups',build/'hud/hud-fixups.json'],check=True)
 write(out/'result.json',dict(passed=True,productionDllSha256=sha(native/'PawsPurePresentation1372.dll'),hudBuild='beta-helpers-r4'))
if __name__=='__main__':main()
