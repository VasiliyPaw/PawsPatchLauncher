"""Create fresh option sources from verified archives; change localization references only."""
import argparse
import base64
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = re.compile(rb'#awloc_[A-Za-z0-9_]+')
TARGETS = ('roaming-profile-x4-no-new', 'roaming-profile-standard-no-new', 'siege-balance-standard')

def local_package(package):
    name = package['urls'][0].rsplit('/', 1)[-1]
    for folder in ('packages', 'release_workspace_20260905/packages'):
        path = ROOT / folder / name
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest().lower() == package['sha256'].lower():
            return path
    raise ValueError('Verified archive unavailable: ' + package['id'])

def read_package(package):
    with zipfile.ZipFile(local_package(package)) as archive:
        manifest = json.loads(archive.read('module.json'))
        assert manifest['id'] == package['id'] and manifest['version'] == package['version']
        assert not manifest.get('remove'), 'Removal metadata needs explicit handling'
        files = {}
        for entry in manifest['files']:
            path = entry['path'].replace('\\', '/')
            assert not path.startswith('/') and '..' not in path.split('/')
            data = archive.read('payload/' + path)
            assert len(data) == entry['size'] and hashlib.sha256(data).hexdigest().lower() == entry['sha256'].lower()
            files[path] = data
        return files

def repair(current, core, english, russian):
    missing = set(KEY.findall(core)) - set(KEY.findall(current))
    result = current
    replacements = {}
    for key in sorted(missing):
        bare = key[1:]
        value = english[bare]
        assert bare in russian, 'Russian definition missing: ' + repr(key)
        if value in replacements and replacements[value] != key:
            raise ValueError('Ambiguous English string: ' + repr(value))
        replacements[value] = key
        literal = b'"' + value + b'"'
        assert literal in result, 'Missing original literal: ' + repr((key, value))
        result = result.replace(literal, b'"' + key + b'"')
    inverse = result
    for value, key in replacements.items(): inverse = inverse.replace(b'"' + key + b'"', b'"' + value + b'"')
    assert inverse == current, 'Non-localization bytes changed'
    assert set(KEY.findall(core)) <= set(KEY.findall(result)), 'Localization references still missing'
    return result, sorted(key.decode() for key in missing)

def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--repair-generated', type=Path)
    parser.add_argument('--core-source', type=Path)
    parser.add_argument('--ru-source', type=Path)
    args = parser.parse_args()
    target = (args.output or args.repair_generated).resolve()
    assert target.is_relative_to(ROOT), 'Output must stay inside this workspace'
    assert target.is_dir() if args.repair_generated else not target.exists(), 'Invalid generated/fresh source directory'
    feed = json.loads(base64.b64decode(json.loads((ROOT/'feed/stable.json').read_text())['payload']))
    packages = {p['id']: p for p in feed['packages']}
    core = read_package(packages['pawpatch-core']) if args.core_source is None else {
        'data/' + p.relative_to(args.core_source).as_posix(): p.read_bytes() for p in args.core_source.rglob('*.tgi')}
    ru = read_package(packages['localization-ru']) if args.ru_source is None else {
        'Local_ru/Localization/strings_data_K2.tgi': args.ru_source.read_bytes()}
    definitions = re.compile(rb'^\s*(awloc_[A-Za-z0-9_]+)\s*=\s*"([^"\r\n]*)"', re.M)
    english = dict(definitions.findall(core['data/Localization/strings_data_K2.tgi']))
    russian_data = ru['Local_ru/Localization/strings_data_K2.tgi']
    if russian_data.startswith((b'\xff\xfe', b'\xfe\xff')):
        russian_data = russian_data.decode('utf-16').encode('utf-8')
    russian = dict(definitions.findall(russian_data))
    evidence = []
    for identity in TARGETS:
        files = read_package(packages[identity]) if args.repair_generated is None else {
            p.relative_to(target / identity).as_posix(): p.read_bytes() for p in (target / identity).rglob('*.tgi')}
        assert files, 'Missing generated module: ' + identity
        touched = 0
        for relative, original in files.items():
            result, keys = repair(original, core.get(relative, original), english, russian)
            destination = target / identity / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if args.output or result != original: destination.write_bytes(result)
            if result != original:
                touched += 1
                evidence.append({'module': identity, 'path': relative, 'keys': keys,
                    'beforeSha256': hashlib.sha256(original).hexdigest(), 'afterSha256': hashlib.sha256(result).hexdigest(), 'onlyLocalizationChanged': True})
        print(identity, 'files', len(files), 'corrected', touched)
    (target.parent/'localization-repair-audit.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('REPAIR VERIFIED', len(evidence), 'package files,', len({e['path'] for e in evidence}), 'unique paths; no gameplay changes')

if __name__ == '__main__': main()
