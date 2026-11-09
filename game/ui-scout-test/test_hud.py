import argparse,sys,re,base64,subprocess,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];out=a.build/'hud-emitted';out.mkdir(exist_ok=True)
s=next((a.build/'source').glob('*GamePresentation1372.cs')).read_text();block=s[s.index('internal static byte[] HudLayoutCode'):];b=base64.b64decode(re.search(r'FromBase64String\("([A-Za-z0-9+/=]+)"\)',block).group(1));assert b==(a.build/'hud/hud.bin').read_bytes();(out/'hud-layout.bin').write_bytes(b)
phase=bytes.fromhex('a10000000083f80f77158b04850000000085c0740a8138000000000f94c0c330c0c3');(out/'uniform-phase.bin').write_bytes(phase)
test=(root/'game/widescreen-ui/test_hud_layout.py').read_text();old="[('ObjectDisplay',295,456,None)";assert old in test;test=test.replace(old,"[('NativeResign',358,308,0),('ObjectDisplay',295,456,None)");test=test.replace('word(ve+0xc,owner);','word(owner,image+0x491788 if key==\'NativeResign\' else 0);word(ve+0xc,owner);')
path=out/'test_emitted.py';path.write_text(test);subprocess.run([sys.executable,str(path),'--legacy','G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work','--emitted',str(out),'--fixups',str(a.build/'hud/hud-fixups.json')],check=True)
print('UI_SCOUT_HUD_PASS actual compiled helper payload; exit and game dialogs; three bases/nine resolutions')
