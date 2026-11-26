"""Author QA input metadata only. Run after release artifacts are complete.

No SDK, processes, games, archive extraction, downloads or installation.
Absent pending release inputs print PENDING and exit successfully.
"""
from pathlib import Path
import sys
import json
import zipfile

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent))
from context import O, WS, S, read, verify, sha, write

IDS = ['pawpatch-core', 'common-ui', 'player-colors', 'desync-continue']
FIX = WS / 'outputs/arcane-bridge-terrain-fixes-20261125'


def manifest(path):
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read('module.json'))


def norm(path):
    return path.replace('\\', '/').lower()


def main():
    required = [O / 'packages.json', O / 'package-audit.json', O / 'helpers/build-report.json',
                O / 'materials/manifest.json', FIX / 'water/asset-sha256.json',
                FIX / 'shadow/shadow-work-manifest.json',
                WS / 'outputs/ui-revert-release-20261118/hd-removals.json']
    required += [O / stage / f'feed/v3/{channel}.json' for stage in ('before', 'signed') for channel in ('stable', 'beta')]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        print(json.dumps({'status': 'PENDING', 'missing': missing}, indent=2))
        return
    before = {c: verify(read(O / 'before' / f'feed/v3/{c}.json')) for c in ('stable', 'beta')}
    after = {c: verify(read(O / 'signed' / f'feed/v3/{c}.json')) for c in ('stable', 'beta')}
    old = {p['id']: p for p in before['beta']['packages']}
    new = {p['id']: p for p in after['beta']['packages']}
    audit = read(O / 'package-audit.json')
    archives, old_manifests, new_manifests = {}, {}, {}
    for id in IDS:
        old_path = WS / 'outputs/ui-revert-release-20261118/arcane/assets' / Path(old[id]['urls'][0]).name
        new_path = Path(audit[id]['path'])
        if not old_path.is_file() or not new_path.is_file():
            print(json.dumps({'status': 'PENDING', 'archive': id, 'old': str(old_path), 'new': str(new_path)}, indent=2))
            return
        assert old_path.stat().st_size == old[id]['size'] and sha(old_path).upper() == old[id]['sha256'].upper()
        assert new_path.stat().st_size == new[id]['size'] and sha(new_path).upper() == new[id]['sha256'].upper()
        archives[id] = {'old': str(old_path), 'new': str(new_path)}
        old_manifests[id], new_manifests[id] = manifest(old_path), manifest(new_path)
        assert set(map(norm, old_manifests[id].get('remove', []))) == set(map(norm, new_manifests[id].get('remove', [])))
    pins = {}
    # All unchanged production DLLs are pinned to the prior signed package,
    # independently of the candidate module manifest.
    for id in IDS:
        for row in old_manifests[id]['files']:
            if row['path'].lower().endswith('.dll'):
                pins[norm(row['path'])] = row['sha256']
    pins['mods/pawsbridges.dll'] = sha(FIX / 'final-native-v2/sandbox/Mods/PawsBridges.dll')
    pins['mods/pawswaterbiomes.dll'] = sha(FIX / 'water/PawsWaterBiomes.dll')
    dll_count = len(pins)
    helpers = {n: r['sha256'] for n, r in read(O / 'helpers/build-report.json')['helpers'].items()}
    assert len(helpers) == 8
    pins.update({norm(n): h for n, h in helpers.items()})
    water = read(FIX / 'water/asset-sha256.json')
    assert len(water) == 952
    pins.update({'rivers-data/' + norm(n): h for n, h in water.items()})
    shadow = read(FIX / 'shadow/shadow-work-manifest.json')['models']
    assert len(shadow) == 56
    pins.update({norm(r['path']): r['sha256'] for r in shadow})
    material = read(O / 'materials/manifest.json')
    ao = {norm('rivers-data/' + n): r['sha256'] for n, r in material['files'].items() if r['kind'] != 'unchanged-texture'}
    assert len(ao) == 672 and all(n.endswith('.nif') and '/racialbuild/' not in n for n in ao)
    pins.update(ao)
    hd = read(WS / 'outputs/ui-revert-release-20261118/hd-removals.json')
    assert len(set(map(norm, hd))) == 1132
    # Guard the cloning budget before any fixture exists. Metadata-only read.
    old_bytes = sum(sum(r['size'] for r in m['files']) for m in old_manifests.values())
    new_bytes = sum(sum(r['size'] for r in m['files']) for m in new_manifests.values())
    # Cache both real versions + live + rollback and transient prior snapshot.
    # The beta.6 payload alone is 437.28 MiB, so a 1 GiB fixture cap is not
    # viable. The production harness checks a 3 GiB cap after every stage.
    write(P / 'inputs.json', {
        'output': str(O / 'qa'), 'configuration': str(S / 'src/PawsPatchLauncher/launcher.config.json'),
        'feeds': {stage: {c: str(O / folder / f'feed/v3/{c}.json') for c in ('stable', 'beta')}
                  for stage, folder in [('before', 'before'), ('after', 'signed')]},
        'archives': archives, 'helpers': helpers, 'pins': pins, 'hdRemovals': hd,
        'counts': {'dll': dll_count, 'helper': 8, 'water': 952, 'shadow': 56, 'ao': 672, 'hd': 1132},
        'payloadBytes': {'old': old_bytes, 'new': new_bytes},
        'signatureVerified': True,
    })
    print('RELEASE_QA_INPUTS_READY', P / 'inputs.json', old_bytes, new_bytes)


if __name__ == '__main__':
    main()
