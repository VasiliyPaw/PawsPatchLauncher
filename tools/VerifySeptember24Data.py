"""Validate beta.3 presentation/data payloads without launching the game."""
import argparse, json, re
from pathlib import Path
from PrepareRelease070 import read, write, validate_package
from PrepareSeptember20Release import contents, module
from GameplayPresentationData import decode

p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[1];out=a.stage/'publication'
prep=read(out/'preparation.json')
assets={row['id']:contents(Path(row['path']),dict(row,version=prep['version'])) for row in prep['assets']}
tooltips=module('release_tooltips',repo/'game/bot-lobby/prepare_tooltips.py')
lobby=module('release_lobby',repo/'game/bot-lobby/prepare_ui.py')
checks=0
def check(ok,why):
    global checks
    checks+=1
    assert ok,why

for language in tooltips.TEXT:
    layer='common-ui' if language=='en' else 'localization-bot-ui-'+language
    files=assets[layer]
    if language!='en':
        check('data/localization/strings_data_k2.tgi' not in files,'Localized package replaces guarded English table')
    for name in ('pcolors','staging'):
        text=decode(files['data/ui/menus/'+name+'.tgi'])[0]
        start,end=lobby.span(text,'Slots')
        check(bool(re.search(r'B\s*=\s*\+405\b',text[start:end])),'Client list height: '+language)
        for kind in ('Race','Faction','Difficulty'):
            start,end=lobby.span(text,'PawBots'+kind)
            check('tooltip' not in text[start:end].lower(),'Unexpected panel tooltip')
    catalogs=[(n,b) for n,b in files.items() if n.endswith('/localization/strings_data_k2.tgi')]
    check(bool(catalogs),'Missing localized table: '+language)
    for name,blob in catalogs:
        check(tooltips.transform(blob,language)==blob,'Wrong cost/button text: '+name)
        check(tooltips.TEXT[language][3] in decode(blob)[0],'Missing button text: '+language)

ui=assets['common-ui'];layout=decode(ui['data/ui/game/game_interface.tgi'])[0]
check(layout.count('[PawGoldSoundButton ')==1,'Duplicate button')
start,end=lobby.span(layout,'PawGoldSoundButton');button=layout[start:end]
for value in ['L = 44r','T = 251.333333b','R = 4r','B = 198b',
              'set_sound = paws_gold_button_select','tooltip_name = "Paw\'s Patch"']:
    check(value in button,'Button geometry/identity: '+value)
audio=decode(ui['data/audio/paws_gold_button.tgi'])[0]
for value in ['control_flags = NULL','simultaneous_limit = 64','ignore_rate = true',
              'files = sounds/Feedback/ResourceGoldSelect.wav','who_flags = LOCAL']:
    check(value in audio,'Audio behavior: '+value)
check(ui['data/ui/game/pawgoldsound.png']==(repo/'game/gold-sound-button/PawGoldSound.png').read_bytes(),'Button image changed')
unit='data/units/gauri/aw_maelstrom_destroyer.tgi';layers=[]
for layer,files in assets.items():
    if unit in files:
        text=decode(files[unit])[0]
        if re.search(r'Kingdom_points_consumed\s*=\s*0\.75\s',text,re.I):
            check(bool(re.search(r'required_properties\s*=\s*gauri_kingdom\s',text)),'Missing kingdom requirement')
            layers.append(layer)
check('aw-siege-balance' in layers,'Missing balanced unit layer')
write(out/'data-verification.json',dict(passed=True,checks=checks,languages=list(tooltips.TEXT),kingdomRequirementLayers=layers))
print('BETA3_DATA_PASS',checks)
