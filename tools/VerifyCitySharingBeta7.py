"""Inspect every signed beta package and language overlay before publication."""
import argparse,hashlib,re
from pathlib import Path
from PrepareRelease070 import read,write,verify,validate_package
from PrepareRelease081 import key
from PrepareSeptember20Release import contents

p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[1];stage=a.stage;out=stage/'publication'
feed=verify(read(out/'test-feeds/beta.json'),key());assert feed['patchGuide']['version']=='0.4.0-beta.7'
previous=verify(read(out/'previous/beta.json'),key())
expected={'common-ui','pawpatch-core','player-colors','desync-continue'}|{'localization-bot-ui-'+lang for lang in ['ru','de','fr','cs','uk']}
assert {asset['id'] for asset in read(out/'preparation.json')['assets']}==expected
for package in feed['packages']:
    if package['id'] not in expected:
        old=next(p for p in previous['packages'] if p['id']==package['id'])
        assert package['sha256']==old['sha256'], 'Unrelated package changed: '+package['id']
checks=0;tables=[];layouts=[];languages=set();guard_hashes={}
def check(ok,why):
    global checks
    checks+=1;assert ok,why
def decode(raw):
    return raw.decode('utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig')
for package in feed['packages']:
    if package.get('mods')!=['arcane-wars']:continue
    archive=Path(package['urls'][0]);validate_package(archive,package)
    files=contents(archive,package)
    for name,raw in files.items():
        if name.endswith('/localization/strings_data_k2.tgi'):
            check('paws_gold_sound_tooltip' not in decode(raw),'Retired body in '+package['id']+'/'+name)
            tables.append(package['id']+'/'+name)
            if package['id']=='common-ui':languages.add('en')
            if package['id'].startswith('localization-bot-ui-'):languages.add(package['id'].removeprefix('localization-bot-ui-'))
            if package['id']=='common-ui' and name=='data/localization/strings_data_k2.tgi':
                guard_hashes['English']=hashlib.sha256(raw).hexdigest().upper()
            if package['id']=='localization-bot-ui-ru' and name=='local_ru/localization/strings_data_k2.tgi':
                guard_hashes['Russian']=hashlib.sha256(raw).hexdigest().upper()
        if name=='data/ui/game/game_interface.tgi' and '[PawGoldSoundButton' in decode(raw):
            text=decode(raw);check(text.count('[PawGoldSoundButton ')==1,'Duplicate sound button')
            section=text[text.index('[PawGoldSoundButton'):]
            check('tooltip_name = "Paw\'s Patch"' in section,'Missing title')
            check(bool(re.search(r'(?m)^\s*tooltip\s*=\s*""\s*$',section)),'Nonempty tooltip body')
            for value in ['L = 44r','T = 251.333333b','R = 4r','B = 198b']:
                check(value in section,'Changed button geometry: '+value)
            check('paws_gold_sound_tooltip' not in text,'Obsolete localized reference')
            layouts.append(package['id'])
        if name=='data/ui/game/pawgoldsound.png':
            check(raw==(repo/'game/gold-sound-button/PawGoldSound.png').read_bytes(),'Artwork changed')
        if name=='data/audio/paws_gold_button.tgi':
            check(raw==(repo/'game/gold-sound-button/audio.tgi').read_bytes(),'Audio changed')
check(languages=={'en','ru','de','fr','cs','uk'},'Missing language overlays')
check(layouts==['common-ui'],'Unexpected button layout owners')
check(set(guard_hashes)=={'English','Russian'},'Missing guarded localization tables')
for exe in read(repo/'game/beta7/variants.json'):
    raw=(stage/'beta-helpers'/exe).read_bytes()
    for language,digest in guard_hashes.items():
        check(digest.encode('utf-16le') in raw,'Helper rejects current '+language+' table: '+exe)
    for name in ['PawCommonUiPayload.bin','PawCommonUiFixups.bin']:
        check((repo/'game/beta7'/name).read_bytes() in raw,'Helper embeds stale tooltip code: '+exe)
write(stage/'button-package-verification.json',dict(passed=True,checks=checks,languages=sorted(languages),tables=tables,layouts=layouts,localizationGuards=guard_hashes,buttonSize='100x100 at 2560x1440',gameLaunched=False))
print('BETA7_PRESENTATION_PACKAGES_PASS',checks,'checks;',len(tables),'tables; six languages')
