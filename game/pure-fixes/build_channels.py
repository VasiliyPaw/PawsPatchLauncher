"""Build scoped Vanilla/Immortals stable and R2 Beta packages, without feeds or publication.

Verified public archives and the stock RWD are read-only inputs. No game is
launched, attached, installed, or configured. Outputs require a fresh directory.
"""
import argparse
import base64
import importlib.util
import json
import mmap
from pathlib import Path
import re
import shutil
import struct
import sys
import zipfile

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
spec = importlib.util.spec_from_file_location('purebuild', SOURCE / 'build.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
ANALYSIS_HASH = 'B865D8206990C4F055C51DE857F0B09B88AB5EE3B6AE74EE5232134001AA591C'
PROFILE = 'Localization/Hotkeys/Actions/hotkeys_visual_dvorak_k2.txt'
CORE = 'Localization/Hotkeys/hotkeys_core.txt'
VERSIONS = {'stable': ('0.1.1', '1.3.72-pure.6'), 'beta': ('0.2.0-beta.1', '1.3.72-pure.7-beta.1')}


def decode(data):
    if data[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return data.decode('utf-16')
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data.decode('cp1251')


def bindings(data):
    return [' '.join(line.strip().split()) for line in decode(data).splitlines() if line.lstrip().startswith('map ')]


def read_archive(directory, package):
    path = directory / package['urls'][0].rsplit('/', 1)[1]
    raw = path.read_bytes()
    assert len(raw) == package['size'] and base.sha(raw) == package['sha256'].upper(), path
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read('module.json'))
        assert manifest['id'] == package['id'] and manifest['version'] == package['version']
        assert not manifest.get('remove'), 'Unexpected source removal operations'
        names = {n.replace('\\', '/').lower(): n for n in z.namelist()}
        assert len(names) == len(z.namelist()), 'Duplicate archive paths'
        files = {}
        for file in manifest['files']:
            relative = file['path'].replace('\\', '/').lower()
            assert relative not in files and ':' not in relative and '..' not in relative.split('/') and not relative.startswith('/')
            data = z.read(names['payload/' + relative])
            assert len(data) == file['size'] and base.sha(data) == file['sha256'].upper(), relative
            files[relative] = data
        assert len(names) == len(files) + 1, 'Unmanifested archive entries'
    return files


def stock_file(data, relative):
    needle = relative.encode('utf-16le')
    index = data.find(needle)
    assert index >= 0 and data.find(needle, index + 1) < 0, relative
    start, length = struct.unpack_from('<QQ', data, index + len(needle))
    start += 30
    assert 30 <= start < index and 0 < length < 100000 and start + length < index
    return data[start:start + length]


def data_payload(args):
    envelope = json.loads((ROOT / 'feed/v2/stable.json').read_text('utf-8-sig'))
    feed = json.loads(base64.b64decode(envelope['payload'], validate=True))
    packages = {p['id']: p for p in feed['packages']}
    ids = ['pawpatch-core', 'pure-fixes-data', 'immortals', 'vanilla-localization-ru', 'immortals-localization-ru']
    verified = {name: read_archive(args.archives, packages[name]) for name in ids}
    old = verified['pure-fixes-data']
    assert packages['pure-fixes-data']['version'] == '0.1.0'
    assert len(old) == 14 and all(n.startswith('data/organizations/banners/') and Path(n).suffix.lower() in ('.nif', '.tga') for n in old)
    assert not any('hotkeys/' in name for name in verified['immortals']), 'Immortals now overrides input; review its profile first'
    profile = verified['pawpatch-core'][('data/' + PROFILE).lower()]
    core = verified['pawpatch-core'][('data/' + CORE).lower()]
    with args.rwd.open('rb') as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
        assert data[:4] == b'TGCK'
        original = stock_file(data, PROFILE)
        stock_core = stock_file(data, CORE)
    original_bindings = bindings(original)
    wanted = bindings(profile)
    movement = ['map ' + sign + key + ' vworld ' + action + direction
                for sign, action in (('+', 'beginscroll'), ('-', 'endscroll'))
                for key, direction in (('a', 'left'), ('d', 'right'), ('w', 'up'), ('s', 'down'))]
    marker = 'map f game "GoToTeamCommands; SelectTeamKingdom; TeamCommand team_explore"'
    reserved_a = 'map a ActionButtonsButton_4|action'
    assert len(wanted) == len(set(wanted))
    assert set(wanted) - set(original_bindings) == set(movement + [marker])
    assert set(original_bindings) - set(wanted) == {reserved_a}
    assert [x for x in wanted if x not in movement + [marker]] == [x for x in original_bindings if x != reserved_a]
    assert bindings(core) == bindings(stock_core), 'AW has new core input changes; review before porting'
    arrows = ['map ' + sign + direction + ' vworld ' + action + direction
              for sign, action in (('+', 'beginscroll'), ('-', 'endscroll'))
              for direction in ('left', 'right', 'up', 'down')]
    assert set(arrows).issubset(bindings(stock_core))
    for name in ('vanilla-localization-ru', 'immortals-localization-ru'):
        language = verified[name]
        assert bindings(language[('Local_base_ru/' + PROFILE).lower()]) == original_bindings, name
        # Legacy Russian core files differ in three developer/debug shortcuts.
        # They already carry the same camera arrows and are left untouched.
        assert set(arrows).issubset(bindings(language[('Local_base_ru/' + CORE).lower()])), name
    files = dict(old)
    files.update({'data/' + PROFILE: profile, 'Local_base_ru/' + PROFILE: profile})
    assert len(files) == 16 and sum(Path(p).suffix.lower() == '.txt' for p in files) == 2
    return files, dict(sourcePackages={name: {'version': packages[name]['version'], 'sha256': packages[name]['sha256']} for name in ids},
                      oldBadgeFilesRetained=14, dvorakProfiles=2, profileSha256=base.sha(profile),
                      stockProfileSha256=base.sha(original), stockCoreSha256=base.sha(stock_core),
                      addedBindings=movement + [marker], removedBindings=[reserved_a], retainedArrowBindings=arrows,
                      englishRussianSameBindings=True, coreInputFileUnchanged=True, otherProfilesUnchanged=True,
                      changesUserInputSelection=False, gameRulesAdded=False)


def main():
    parser = argparse.ArgumentParser()
    for name in ('out', 'dotnet', 'analysis-work', 'archives', 'rwd'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert not out.exists() or not any(out.iterdir()), 'Choose a fresh output directory'
    out.mkdir(parents=True, exist_ok=True)
    # Bind the build to the already reviewed plaintext Steam 1.3.72 analysis
    # image; guard generation does not accept arbitrary binary inputs.
    assert base.sha((args.analysis_work / 'k2_runtime_1372_20260904.bin').read_bytes()) == ANALYSIS_HASH
    assert base.sha((args.rwd.parent / 'k2.exe').read_bytes()) == base.GAME_HASH
    files, input_audit = data_payload(args)
    base.writejson(out / 'input-audit.json', input_audit)
    guards = out / 'transfer-guards'
    print(base.run([sys.executable, ROOT / 'game/fast-transfer/prepare_guards.py', '--work', args.analysis_work, '--out', guards]).strip())
    guard_audit = json.loads((guards / 'guards.json').read_text())
    assert guard_audit['source_sha256'].upper() == ANALYSIS_HASH
    assert len(guard_audit['ranges']) == 15 and sum(r['size'] for r in guard_audit['ranges']) == 1815
    sdk = base.run([args.dotnet, '--list-sdks']).strip().splitlines()[-1].split(' [', 1)
    compiler = [args.dotnet, Path(sdk[1].rstrip(']')) / sdk[0] / 'Roslyn/bincore/csc.dll']
    common = ['/nologo', '/nostdlib+', '/langversion:7.3', '/deterministic+', '/optimize+', '/platform:x86', '/pathmap:' + str(ROOT) + '=/src']
    common += ['/r:' + str(base.FRAMEWORK / (n + '.dll')) for n in ('mscorlib', 'System', 'System.Core')]
    presentation = ROOT / 'game/beta7/GamePresentation1372.cs'
    resources = ['/resource:' + str(ROOT / 'game/beta7' / (n + '.bin')) + ',' + n for n in ('PawCommonUiPayload', 'PawCommonUiFixups')]
    sources = [SOURCE / n for n in ('Program.cs', 'NativeMemory.cs', 'PurePatch.cs', 'PureChannel.cs')] + [presentation]
    reports = {}
    for channel, (patch_version, runtime_version) in VERSIONS.items():
        target = out / channel
        target.mkdir()
        beta = channel == 'beta'
        flags = 'PAW_MENU_PRESENTATION;PAW_PURE_CHANNEL' + (';PAW_PURE_FAST_TRANSFER' if beta else '')
        inputs = sources + ([ROOT / 'game/fast-transfer/FastTransfer.cs'] if beta else [])
        embedded = resources + (['/resource:' + str(guards / 'FastTransferGuards.bin') + ',FastTransferGuards'] if beta else [])
        options = common + ['/define:' + flags] + embedded
        runtime = target / base.EXE
        base.run(compiler + options + ['/target:winexe', '/out:' + str(runtime)] + inputs)
        repro = target / 'reproducibility'
        repro.mkdir()
        base.run(compiler + options + ['/target:winexe', '/out:' + str(repro / base.EXE)] + inputs)
        assert runtime.read_bytes() == (repro / base.EXE).read_bytes()
        features = json.loads(base.run([runtime, '--features']))
        assert features['version'] == runtime_version and features['patchVersion'] == patch_version and features['channel'] == channel
        assert features['fastSaveTransfer'] == beta and features['nativeTransferRevision'] == ('R2' if beta else 'stock')
        assert all(features[k] for k in ('negativeZero', 'terrainInitialization', 'stockSyncChecks', 'menuVersions', 'quiet'))
        assert all(not features[k] for k in ('colors', 'bypass', 'hostility', 'randomMap', 'randomTime', 'cityAssistant', 'changesGameFiles'))
        base.writejson(target / 'features.json', features)
        preflight = base.run([runtime, '--preflight', args.rwd.parent]).strip()
        assert preflight == 'PURE_PREFLIGHT_PASS 1.3.72'
        checks = target / 'checks'
        checks.mkdir()
        pure_tests = target / 'PureFixes.Tests.exe'
        base.run(compiler + options + ['/target:exe', '/main:PawPureFixes.Tests', '/out:' + str(pure_tests)] + inputs + [SOURCE / 'Tests.cs'])
        managed_output = base.run([pure_tests, checks / 'pure'])
        (target / 'pure-managed-output.txt').write_text(managed_output, encoding='utf-8')
        native_output = base.run([sys.executable, SOURCE / 'test_native.py', '--out', checks / 'pure', '--deps', args.analysis_work / 'lobby_colors_1372/pydeps_r3', '--original-ui-payload', ROOT / 'game/beta7/PawCommonUiPayload.bin'])
        (target / 'pure-native-output.txt').write_text(native_output, encoding='utf-8')
        channel_tests = target / 'Channel.Tests.exe'
        test_sources = inputs + [SOURCE / 'ChannelTests.cs'] + ([ROOT / 'game/fast-transfer/FastTransferTests.cs'] if beta else [])
        base.run(compiler + options + ['/target:exe', '/main:PawPureFixes.ChannelTests', '/out:' + str(channel_tests)] + test_sources)
        channel_output = base.run([channel_tests, checks / 'channel'])
        (target / 'channel-managed-output.txt').write_text(channel_output, encoding='utf-8')
        if beta:
            shutil.copy2(guards / 'guards.json', checks / 'channel/guards.json')
            output = base.run([sys.executable, ROOT / 'game/fast-transfer/test_native.py', '--work', args.analysis_work, '--out', checks / 'channel'])
            (target / 'transfer-native-output.txt').write_text(output, encoding='utf-8')
        data_package = base.package(target, 'pure-fixes-data', patch_version, files, True, 900,
            {'ru': "Paw's Patch: значки и управление", 'en': "Paw's Patch: badges and controls"},
            {'ru': 'Исправленные значки рот; WASD и союзная метка F в профиле Dvorak. Стрелки сохраняются.', 'en': 'Corrected company badges; WASD and F allied marker in the Dvorak profile. Arrow controls are retained.'})
        runtime_package = base.package(target, 'pure-fixes-runtime', runtime_version, {base.EXE: runtime.read_bytes()}, False, 910,
            {'ru': "Paw's Patch: исправления движка", 'en': "Paw's Patch: engine fixes"},
            {'ru': 'Исправления отображения чисел и рельефа, версия патча в меню.' + (' Встроена быстрая нативная передача сохранений R2.' if beta else ''),
             'en': 'Number-display and terrain fixes, with the patch version in the menu.' + (' Built-in fast native R2 save transfer.' if beta else '')})
        runtime_package['dependsOn'] = ['menu-runtime']
        runtime_package['experimental'] = beta
        for package in (data_package, runtime_package):
            base.writejson(target / (package['id'] + '-package.json'), package)
        base.writejson(target / 'packages.json', [data_package, runtime_package])
        tests = {name: json.loads((checks / path).read_text('utf-8')) for name, path in (
            ('pureManaged', 'pure/managed-tests.json'), ('pureNative', 'pure/native-tests.json'), ('channelManaged', 'channel/channel-tests.json'))}
        if beta:
            tests['transferManagedChecks'] = int(re.search(r'FAST_TRANSFER_MANAGED_PASS checks=(\d+)', channel_output)[1])
            tests['transferNative'] = json.loads((checks / 'channel/native-tests.json').read_text())
        reports[channel] = dict(packages=[data_package, runtime_package], features=features, tests=tests,
            runtimeSha256=base.sha(runtime.read_bytes()), runtimeBuildReproducible=True, deterministicZip=True,
            readOnlyGamePreflight=preflight, sourceHashes={str(p.relative_to(ROOT)): base.sha(p.read_bytes()) for p in inputs},
            payloadFiles=16, nativeExecutable=base.EXE, steamBootstrapRetained=True,
            gameLaunched=False, liveNetworkTested=False, published=False)
        base.writejson(target / 'build-verification.json', reports[channel])
        print(channel, 'PASS', 'pure managed', tests['pureManaged']['checks'], 'pure native', tests['pureNative']['checks'],
              'channel', tests['channelManaged']['checks'], 'R2 native', tests.get('transferNative', {}).get('checks', 0))
    requirement = {'version': '1.3.72', 'steamBuild': '25068126', 'k2ExeSha256': [base.GAME_HASH]}
    base.writejson(out / 'mod-games.json', {'vanilla': requirement, 'immortals': requirement})
    base.writejson(out / 'packages.json', {name: report['packages'] for name, report in reports.items()})
    base.writejson(out / 'build-verification.json', dict(channels=reports, inputAudit=input_audit,
        guardSourceSha256=ANALYSIS_HASH, guardResourceSha256=base.sha((guards / 'FastTransferGuards.bin').read_bytes()),
        versions=VERSIONS, gameLaunched=False, published=False,
        remainingAcceptance='Parent runs isolated launch combinations and visible input checks; no new WAN throughput is claimed.'))


if __name__ == '__main__':
    main()
