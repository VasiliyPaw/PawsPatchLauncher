"""Signed beta.7: central-building city tribute and a compact title-only tooltip."""
import argparse, importlib.util, re
from pathlib import Path
import PrepareDesyncBeta4 as release
from PrepareFiberSyncBeta6 import checks

release.VERSION='0.4.0-beta.7'
release.BASELINE_VERSION='0.4.0-beta.6'
release.AI_POLICY_REVISION=38
release.RELEASE_DATE='2026-09-26'
release.TAG='patch-'+release.VERSION
release.URL='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+release.TAG+'/'

spec=importlib.util.spec_from_file_location('gold_button',release.REPO/'game/gold-sound-button/prepare.py')
button=importlib.util.module_from_spec(spec);spec.loader.exec_module(button)

def presentation(package,payload):
    allowed=set()
    for path,raw in list(payload.items()):
        if package['id']=='common-ui' and path=='data/ui/game/game_interface.tgi':
            payload[path]=button.add_button(raw,(release.REPO/'game/gold-sound-button/button.tgi').read_text('utf-8'))
            allowed.add(path)
        elif path.endswith('/localization/strings_data_k2.tgi'):
            encoding='utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig'
            text=raw.decode(encoding)
            updated,count=re.subn(r'(?m)^[ \t]*paws_gold_sound_tooltip\s*=\s*"[^"\r\n]*"[ \t]*\r?\n?', '', text)
            if count:
                assert count==1,(package['id'],path,count)
                payload[path]=updated.encode(encoding);allowed.add(path)
    return allowed

release.extra_payload_transform=presentation

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--signing-dir',type=Path)
    p.add_argument('--action',choices=['prepare','public','promote'],default='prepare');a=p.parse_args()
    checks(a.stage)
    city=release.read(a.stage/'beta-helpers/ai-native/city-sharing.json')
    assert city['passed'] and city['checks']>=603
    assert city['nativeSha256']==release.sha(a.stage/'beta-helpers/ai-native/ai-policy.bin')
    tip=release.read(a.stage/'button/tooltip-native-tests.json')
    assert tip['passed'] and tip['checks']>=124
    layout=release.read(a.stage/'button/tooltip-layout-tests.json')
    assert layout['passed'] and layout['originalNativeLayout']
    if a.action=='promote':
        report=release.read(a.stage/'offline-verification.json')
        assert report['passed'] and not report['gameLaunched'] and report['launcherTestsPassed']
        assert release.read(a.stage/'button-package-verification.json')['passed']
    {'prepare':release.prepare,'public':release.public,'promote':release.promote}[a.action](a)
