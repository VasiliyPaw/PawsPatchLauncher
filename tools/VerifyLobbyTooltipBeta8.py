"""Verify beta.8 scope and the tested payloads inside every packaged helper."""
import argparse
from pathlib import Path
from PrepareRelease070 import read,write,verify,validate_package
from PrepareRelease081 import key
from PrepareSeptember20Release import contents,feature

p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[1];stage=a.stage;out=stage/'publication'
feed=verify(read(out/'test-feeds/beta.json'),key());previous=verify(read(out/'previous/beta.json'),key())
assert feed['patchGuide']['version']=='0.4.0-beta.8'
assert feed['launcher']==previous['launcher']
expected={'common-ui','pawpatch-core','player-colors','desync-continue'}
assert {asset['id'] for asset in read(out/'preparation.json')['assets']}==expected
variants=read(repo/'game/beta7/variants.json');checks=0;helpers=set()
def check(ok,why):
    global checks
    checks+=1;assert ok,why
for package in feed['packages']:
    old=next(p for p in previous['packages'] if p['id']==package['id'])
    if package['id'] not in expected:
        check(package['sha256']==old['sha256'],'Unrelated package changed: '+package['id'])
        continue
    validate_package(Path(package['urls'][0]),package)
    for name,raw in contents(Path(package['urls'][0]),package).items():
        if name in variants:
            check(raw==(stage/'beta-helpers'/name).read_bytes(),'Packaged helper mismatch: '+name)
            for resource in ['PawCommonUiPayload.bin','PawCommonUiFixups.bin']:
                check((repo/'game/beta7'/resource).read_bytes() in raw,'Stale tooltip resource: '+name)
            check((stage/'beta-helpers/bot-lobby-native/controls.bin').read_bytes().hex().encode('utf-16le') in raw,'Stale lobby code: '+name)
            check('goldSoundTitleOnlyHover='.encode('utf-16le') in raw,'Stale hover installer: '+name)
            check('--local-data-check'.encode('utf-16le') not in raw,'Local test entry point in release: '+name)
            f=feature(stage/'beta-helpers'/name)
            check(f['patchVersion']=='0.4.0-beta.8' and f['bulkBotLobbyRevision']==3 and f['aiPolicyRevision']==38,'Feature identity: '+name)
            helpers.add(name)
        elif name=='paws_patch_versions.ini':
            check('PawPatch=0.4.0-beta.8' in raw.decode('utf-8-sig'),'Stale version metadata')
        elif name=='data/ui/game/game_interface.tgi':
            s=raw.decode('utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig')
            check(s.count('[PawGoldSoundButton ')==1,'Duplicate button')
            s=s[s.index('[PawGoldSoundButton'):]
            for value in ['tooltip_name = "Paw\'s Patch"','tooltip = ""','L = 44r','T = 251.333333b','R = 4r','B = 198b']:
                check(value in s,'Button text/geometry: '+value)
        elif name=='data/ui/game/pawgoldsound.png':check(raw==(repo/'game/gold-sound-button/PawGoldSound.png').read_bytes(),'Artwork changed')
        elif name=='data/audio/paws_gold_button.tgi':check(raw==(repo/'game/gold-sound-button/audio.tgi').read_bytes(),'Audio changed')
check(helpers==set(variants),'Not all eight helpers packaged')
for entries in [feed['changelog'],read(out/'final/changelog.history.json')['beta']]:
    for n in range(4,9):
        version='0.4.0-beta.'+str(n)
        entry=next(e for e in entries if e.get('category')=='patch' and e.get('mods')==['arcane-wars'] and e['version']==version)
        check(entry['body']==read(repo/('docs/release-patch-'+version+'.json')),'Unclean recent notes: '+version)
check(read(out/'final/changelog.history.json')['stable']==read(repo/'feed/changelog.history.json')['stable'],'Stable history changed')
write(stage/'lobby-tooltip-package-verification.json',dict(passed=True,checks=checks,helpers=sorted(helpers),packages=sorted(expected),gameLaunched=False))
print('BETA8_PACKAGES_PASS',checks,'checks; eight helpers; four packages')
