"""Restore only the Powers/Shards layer over the current core; never overwrite core inputs.

Byte-oriented, reviewed inverse edits preserve localization, limits, combat and roaming changes.
Run without --output to audit. Output must be a fresh directory; ambiguity is a hard error.
"""
import argparse
import base64
import difflib
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / 'release_workspace_20260905/original_extract/Arcane Wars 0.82beta/data'
CORE = ROOT / 'release_workspace_20260905/sources/pawpatch-core/data'
SHARD_LINE = re.compile(rb'^\s*(?:fixed\s+)?shards(?:\s*=\s*[^\r\n]*)?\s*$', re.I)
UI = {'UI/Game/floaters.tgi', 'UI/Game/economy_bar.tgi', 'UI/Game/template_game.tgi', 'UI/Editor/kingdom_editing.tgi'}
REVIEWED_CORE = {
    'UI/Game/floaters.tgi': '5BFC06DB462D70FFE4CA39BF6ED9A436A77B832BB949771D09507DB46E2CEA83',
    'UI/Game/economy_bar.tgi': 'AE972BE36E2C21E4906C8B33D0453B9FA41221428313FE2B768D612753D1B1F9',
    'UI/Game/template_game.tgi': '76CD3B02B971C4D6FD0AD1767F92284906F6062590B1EEC3221AF96D5A36BE51',
    'UI/Editor/kingdom_editing.tgi': '5DB48E1142E5FB2EEFD66239B8C7E438F515EF54EFF8FD02EC5519706858C20C',
    'Game/resources.tgi': 'CC523BBD01382DC11DF237CC964C359379C81E8E24A5A74887F70A11E67C774D',
    'Scoring/scoring.tgi': '6F6A30800CD37A4168D1AE1478ECD134853BB21AA761C3E5A3E6E8B65603A2B9',
}

def restore(relative, original, current):
    if relative in REVIEWED_CORE and hashlib.sha256(current).hexdigest().upper() != REVIEWED_CORE[relative]:
        raise ValueError('Reviewed source changed; re-audit instead of overwriting later fixes: ' + relative)
    if relative in UI:
        # Reviewed diffs: only the powers toggle and shard column/editor widget were changed.
        return original
    if relative == 'Game/resources.tgi':
        block = re.search(rb'\[Resource template=PurchaseResource\][^\[]*?IDS\s*=\s*shards[^\[]*?\}', original, re.I).group()
        block = block.replace(b'"Khaldunite Shards"', b'"#awloc_khaldunite_shards_f2e5aef5"').replace(b'"Khaldunite Shards Production"', b'"#awloc_khaldunite_shards_production_d839b2fd"')
        anchor = b'[Resource template=UpkeepResource]'
        assert current.count(anchor) >= 1
        return current.replace(anchor, block + b'\r\n\r\n' + anchor, 1)
    if relative == 'Scoring/scoring.tgi':
        # Only shard statistics were removed; preserve the existing localized kingdom-point labels.
        result = original
        for name, key in [(b'Kingdom points production', b'awloc_kingdom_points_production_9f1b44e0'),
                          (b'Kingdom points consumption', b'awloc_kingdom_points_consumption_df960816'),
                          (b'Khaldunite Shards', b'awloc_khaldunite_shards_f2e5aef5')]:
            result = result.replace(b'"' + name + b'"', b'"#' + key + b'"')
        return result
    if b'NoPowers patch:' in current:
        if relative.startswith('Factions/') or relative == 'Templates/template_sai_k2.tgi':
            result, count = re.subn(rb'/\* NoPowers patch:[^\r\n]*\r?\n(.*?)\*/', rb'\1', current, flags=re.S)
            assert count == 1, relative
            return result
        raise ValueError('Unreviewed NoPowers marker: ' + relative)
    a, b = original.splitlines(keepends=True), current.splitlines(keepends=True)
    edits = []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal' or not any(SHARD_LINE.fullmatch(line) for line in a[i:j]):
            continue
        if tag not in ('delete', 'replace') or any(line.strip() and not SHARD_LINE.fullmatch(line) for line in a[i:j]) or any(line.strip() for line in b[k:l]):
            raise ValueError(f'Ambiguous shard edit in {relative}: {tag} original={a[i:j]!r} core={b[k:l]!r}')
        edits.append((k, l, a[i:j]))
    result = list(b)
    for k, l, lines in reversed(edits): result[k:l] = lines
    return b''.join(result)

def collect():
    results, errors = {}, []
    for path in CORE.rglob('*.tgi'):
        relative = path.relative_to(CORE).as_posix()
        if relative.startswith('Localization/'): continue
        source = ORIGINAL / relative
        if not source.is_file(): continue
        original, current = source.read_bytes(), path.read_bytes()
        if relative not in UI and not re.search(rb'\bshards\b', original, re.I) and b'NoPowers patch:' not in current: continue
        try:
            result = restore(relative, original, current)
            if result != current:
                expected = [line.strip() for line in original.splitlines() if SHARD_LINE.fullmatch(line)]
                actual = [line.strip() for line in result.splitlines() if SHARD_LINE.fullmatch(line)]
                if actual != expected or b'NoPowers patch:' in result:
                    raise ValueError('Incomplete Powers/Shards restoration: ' + relative)
                results[relative] = result
        except (ValueError, AssertionError) as error: errors.append(str(error))
    if errors: raise ValueError('\n'.join(errors))
    return results

def verify_packages(results):
    """Check true archive inputs and refuse conflicts with other selectable profiles."""
    paths = {'data/' + p.lower() for p in results}
    checked = set()
    for channel in ('stable', 'beta'):
        payload = json.loads(base64.b64decode(json.loads((ROOT / f'feed/{channel}.json').read_text())['payload']))
        for package in payload['packages']:
            identity = (package['id'], package['sha256'])
            if identity in checked: continue
            checked.add(identity)
            name = package['urls'][0].rsplit('/', 1)[-1]
            candidates = [ROOT/'packages'/name, ROOT/'release_workspace_20260905/packages'/name]
            archive = next((p for p in candidates if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest().lower() == package['sha256'].lower()), None)
            if archive is None: raise ValueError('Missing verified local archive: ' + name)
            with zipfile.ZipFile(archive) as z:
                module = json.loads(z.read('module.json'))
                indexed = {f['path'].replace('\\', '/').lower(): f for f in module['files']}
                overlap = (set(indexed) | {p.replace('\\', '/').lower() for p in module.get('remove', [])}) & paths
                if package['id'] not in ('arcane-wars', 'pawpatch-core') and overlap:
                    raise ValueError('Overlay conflicts with ' + package['id'] + ': ' + ', '.join(sorted(overlap)))
                if package['id'] in ('arcane-wars', 'pawpatch-core'):
                    base = ORIGINAL if package['id'] == 'arcane-wars' else CORE
                    for relative in results:
                        file = indexed['data/' + relative.lower()]
                        if hashlib.sha256((base/relative).read_bytes()).hexdigest().lower() != file['sha256'].lower():
                            raise ValueError('Source differs from published package: ' + package['id'] + '/' + relative)
    print('PACKAGE INPUTS / NO PROFILE CONFLICTS PASS', len(checked))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    results = collect()
    verify_packages(results)
    print('RESTORED FILES', len(results))
    for relative in sorted(results): print(relative)
    if args.output:
        target = args.output.resolve()
        if target.exists(): raise ValueError('Output must be a fresh directory: ' + str(target))
        if not target.is_relative_to(ROOT): raise ValueError('Output must stay in this release workspace')
        for relative, contents in results.items():
            destination = target / 'data' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(contents)
        evidence = [{'path': p, 'coreSha256': hashlib.sha256((CORE/p).read_bytes()).hexdigest(),
                     'restoredSha256': hashlib.sha256(data).hexdigest()} for p, data in sorted(results.items())]
        (target.parent / (target.name + '-audit.json')).write_text(json.dumps(evidence, indent=2), encoding='utf-8')

if __name__ == '__main__': main()
