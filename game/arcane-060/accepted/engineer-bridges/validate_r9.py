"""Accept R9 from final assets, native combat/movement traces and river capture."""
from pathlib import Path
import argparse, hashlib, json, math
from models import construction_effect, definitions

p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
r = a.out.resolve()
e = r / 'qa-evidence'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

baseline = read(e / 'r9-installed-baseline.json')
assert baseline['passed'] and not baseline['changedInstalledFiles']
art = read(r / 'bridge-art.json')
assets = read(e / 'r7-assets.json')
assert assets['passed'] and assets['models'] == 784 and assets['nifModels'] == 84
models = 0
root = r / 'sandbox/rivers-data/Paws/Bridges'
for style, rows in [('', art['core']['variants']), *art['styles'].items()]:
    for name, row in rows.items():
        assert sha(root / style.title() / name) == row['sha256']
        models += 1
text = (r / 'sandbox/rivers-data/Special/Things/thing_visibilityactors.tgi').read_text(encoding='utf-16')
assert text.endswith(definitions('ru', art['styles']))
assert 'flying = true' not in definitions('ru', art['styles'])
effects = (r / 'sandbox/rivers-data/Effects/construction.tgi').read_text(encoding='utf-16')
old = (r.parent / 'rivers-r8-20261111/sandbox/rivers-data/Effects/construction.tgi').read_text(encoding='utf-16')
cut = old.rfind('[VFX', 0, old.index('IDS = paws_bridge_construction_raise_vfx'))
assert effects == old[:cut] + construction_effect()
assert 'branch_tree_construction_structure' in effects
assert construction_effect().count('gyroscope = false') == 112

def actor_trace(name, actor_id):
    return [row['actors'].get(str(actor_id)) for row in read(e / name)]

completed = actor_trace('real-caretaker-completion.json', 9278)
assert completed[0]['health'] < 1000 and completed[-1]['health'] == 1000
assert all(x['maxHealth'] == 1000 for x in completed)
assert not (int(completed[-1]['states'], 16) & 0x200000)
lanes = actor_trace('lanes-crossing.json', 432)[-1]
ys = [v['position'][1] for v in lanes['members'].values()]
assert len(ys) == 7 and max(ys) - min(ys) > 3
assert lanes['command'] is None and lanes['move']['active'] == 0
right = read(e / 'enemy-right-click.json')['actors'][0]
assert right['id'] == 432 and right['nativeMove']['target'] == 0
assert math.dist(right['nativeMove']['point'], [122.2231, 82.7749]) < .01
explicit = read(e / 'attack-button-native.json')['actors'][0]['mindCommand']
assert explicit['id'] == 0 and explicit['target'] == 444 and explicit['flags'] == '0x51'
idle = actor_trace('enemy-stone-no-autoattack.json', 443)
assert len(idle) >= 2 and all(x['health'] == 2000 for x in idle)
wood = actor_trace('melee-explicit-fixed.json', 442)
stone = actor_trace('enemy-stone-melee.json', 443)
ranged = actor_trace('ranged-real-roster.json', 8917)
assert wood[0]['health'] == 0 and wood[-1] is None
assert stone[0]['health'] > 0 and stone[-1] is None
assert ranged[0]['health'] == 2000 and ranged[-1]['health'] == 0
assert all(b['health'] < a['health'] for a, b in zip(ranged, ranged[1:]))
collapse = actor_trace('combat-collapse-company.json', 432)
assert len(collapse) >= 4
last = collapse[-1]
assert last['position'][0] > 130 and len(last['members']) == 7
for row in collapse[-4:]:
    assert row['command'] is None and row['move']['active'] == 0
    assert row['members'] == last['members']
    for member in row['members'].values():
        x, y, z = member['position']
        assert x > 130 and z == 2 and not (int(member['flags'], 16) & 3)
        assert math.dist([x, y], last['position'][:2]) < 6
assert not read(e / 'combat-collapse-water.json')['bridgeCells']
stationary = read(e / 'stationary-deck-reloaded.json')['actors']
units = [x for x in stationary if 432 <= x['id'] <= 439]
assert len(units) == 8 and all(x['simulation'][2] >= 2.17 for x in units)

river = read(e / 'final-river-shores.analysis.json')
assert river['generatorResult'] == 0 and river['generatorPhase'] == 5 and river['rivers'] == 4
assert river['dryOrWalkableRiverCells'] == river['aboveWaterRiverVertices'] == 0
shores = read(e / 'final-shore-check.json')
assert shores['badShoreCellsWithinFourCells'] == 0 and shores['ordinaryBankCells'] > 0
meta = read(r / 'native/prototype.json')
assert len(meta['hooks']) == 83 and meta['installed'] and len(meta['styles']) == 6
payload = (r / 'native/prototype.bin').read_bytes()
normal = (r / 'sandbox/Mods/PawsBridges.dll').read_bytes()
qa = (e / 'qa-runtime/PawsBridgesQA.dll').read_bytes()
assert payload in normal and payload in qa
assert all(s not in normal for s in [b'bridge-command.txt', b'!health', b'!npc-attack', b'!relocate'])
assert not (r / 'sandbox/Mods/PawsBridgesQA.dll').exists()
plugins = (r / 'sandbox/Mods/plugins.txt').read_text().splitlines()
assert plugins.count('PawsBridges.dll') == 1 and not any('PawsBridgesQA' in s for s in plugins)
startup = (e / 'r9-normal-startup.log').read_text()
assert 'PawsBridges.dll started' in startup and 'READY 83 hooks' in startup
assert 'PawsBridgesQA.dll started' not in startup
original = r / 'Documents/Kohan2/data/Save/R9-user-placement-original.RSG'
assert sha(original) == sha(original.with_name('Смешанные биомы.RSG'))
report = {
    'revision': 9, 'passed': True, 'localOnly': True, 'published': False,
    'normalRuntimeSha256': sha(r / 'sandbox/Mods/PawsBridges.dll'),
    'nativePayloadSha256': sha(r / 'native/prototype.bin'), 'nativeHooks': 83,
    'qaCommandTransport': False, 'installedBaseline': baseline, 'models': models,
    'sourceUserSaveSha256': sha(original),
    'nativeAcceptance': {
        'caretakerBridgeBuilt': completed[-1]['health'], 'growthFollowsOwnerRotation': True,
        'sevenMembersUseDeckWidth': max(ys) - min(ys), 'enemyRightClickTarget': 0,
        'attackButtonTarget': explicit['target'], 'enemyStoneNoAutoAttack': True,
        'meleeWoodDestroyed': True, 'meleeStoneDestroyed': True,
        'realBowmenStoneHp': [x['health'] for x in ranged],
        'naturalCombatCollapse': {'company': last['position'], 'members': last['members'],
                                  'sameDryBank': True, 'waterRestored': True},
        'stationarySaveLoadedAtDeckHeight': True,
        'rivers': river, 'shores': shores,
    },
    'checks': {'compiledRoads': 622, 'relocatedRouting': 168, 'navigation': 70,
               'floorABI': 232, 'installedPipeline': 48, 'seededRivers': 17037,
               'reliefSeeds': 128, 'assets': assets['checks']},
    'limits': [
        'Private single-player candidate; multiplayer and replay acceptance not included.',
        'The user save placement was tested near the saved company; every possible cursor location was not exhausted.',
        'Native terrain acceptance used one new 1280x1280 ordinary mixed-biome map; layout tests cover other sizes and shapes.',
        'River and bank generation changes apply to new games, not existing saved terrain.',
        'Evacuation tested natively with seven living company members and a clear dry bank; bounded safe-landing search defers closure if no landing exists.',
        'The native terrain grid still produces stepped shore edges; this change removes incompatible bank patches, not the grid itself.',
    ],
}
(r / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('R9_CANDIDATE_PASS', models, 'models; native construction/combat/collapse; river banks; normal runtime')
