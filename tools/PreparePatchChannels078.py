"""Prepare immutable patch archives and signed LOCAL/PRODUCTION CANDIDATES only.

Never builds helpers, edits canonical feeds, changes a game, uploads or commits.
All source signatures and archives are verified. City helpers require an explicit
hash-bound release-ready.json from their completed offline validation.
"""
import argparse
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

REPO = Path(__file__).resolve().parents[1]
CHANNELS = ('stable', 'beta')
SCHEMAS = ('legacy', 'v2')
PURE_VERSIONS = {'stable': ('0.1.1', '1.3.72-pure.6'), 'beta': ('0.2.0-beta.1', '1.3.72-pure.7-beta.1')}
AW_VERSION = '0.3.0-beta.3'
AW_BUILD_ID = 'beta.0.3.0-beta.3-1372-city-policy14-transfer-r2-quiet'
AW_VERSIONS = {'pawpatch-core': AW_VERSION, 'common-ui': '1.3.72-ui.4-beta.3', 'player-colors': AW_VERSION}
DOWNLOADS = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'
GAME_HASH = '1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45'
CITY_DATA = ('data/UI/Game/paw_city_en.tgi', 'data/UI/Game/paw_city_ru.tgi',
             'data/Localization/paw_city_policy.tgi', 'Local_ru/Localization/paw_city_policy.tgi')
PROFILE = 'Localization/Hotkeys/Actions/hotkeys_visual_dvorak_k2.txt'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode(value))


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest().upper()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def normalize(path):
    path = path.replace('\\', '/')
    assert path and not path.startswith('/') and ':' not in path and not any(p in ('', '.', '..') for p in path.split('/')), 'Unsafe package path'
    return path.lower()


def command(args):
    result = subprocess.run([str(a) for a in args], cwd=REPO, capture_output=True,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Command failed: ' + str(args[0]) + '\n' + (result.stdout + result.stderr).decode('utf-8', errors='replace'))
    return result.stdout.decode('utf-8', errors='replace')


class Preparation:
    def __init__(self, args):
        self.args = args
        self.out = args.out.resolve()
        self.publisher = REPO / 'tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll'
        self.private = args.signing_dir / 'pawpatch-signing-private.pem'
        self.public = args.signing_dir / 'pawpatch-signing-public.pem'
        self.cache = [REPO.parent / 'launcher-release-070/public', REPO.parent / 'launcher-release-070/packages', REPO / 'packages']
        self.cache.extend(args.cache)
        self.paths = {}
        self.audited = {}
        self.baselines = {}
        self.before_hashes = {}
        self.assets = {}
        configured = read(REPO / 'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem']
        assert re.sub(r'\s+', '', configured) == re.sub(r'\s+', '', self.public.read_text('utf-8-sig')), 'Signing public key differs from the launcher trust root'

    def verify_signed(self, path):
        command([self.args.dotnet, self.publisher, 'verify', path, self.public])
        envelope = read(path)
        assert envelope['keyId'] == 'pawpatch-prod-2026'
        return json.loads(base64.b64decode(envelope['payload'], validate=True))

    def source_path(self, schema, channel):
        return REPO / 'feed' / (('v2/' if schema == 'v2' else '') + channel + '.json')

    def local(self, package):
        digest = package['sha256'].upper()
        if digest in self.paths:
            return self.paths[digest]
        name = package['urls'][0].replace('\\', '/').rsplit('/', 1)[-1]
        direct = [Path(url) for url in package['urls'] if not re.match(r'^https?://', url, re.I)]
        for candidate in direct + [folder / name for folder in self.cache]:
            if candidate.is_file() and candidate.stat().st_size == package['size'] and sha(candidate) == digest:
                self.paths[digest] = candidate.resolve()
                return candidate.resolve()
        raise FileNotFoundError('Missing verified archive: ' + name)

    def audit_archive(self, package):
        digest = package['sha256'].upper()
        if digest in self.audited:
            old = self.audited[digest]
            assert (old['id'], old['version']) == (package['id'], package['version'])
            return old
        path = self.local(package)
        with zipfile.ZipFile(path) as archive:
            names = {normalize(n): n for n in archive.namelist()}
            assert len(names) == len(archive.namelist()), 'Duplicate archive names'
            manifest = json.loads(archive.read(names['module.json']))
            assert manifest['id'] == package['id'] and manifest['version'] == package['version']
            listed = set()
            for file in manifest['files']:
                normalized = normalize(file['path'])
                assert normalized not in listed
                listed.add(normalized)
                name = names['payload/' + normalized]
                assert archive.getinfo(name).file_size == file['size']
                with archive.open(name) as stream:
                    assert hashlib.file_digest(stream, 'sha256').hexdigest().upper() == file['sha256'].upper(), name
            assert set(names) == {'module.json'} | {'payload/' + n for n in listed}, 'Unmanifested archive content'
            for removed in manifest.get('remove', []):
                normalize(removed)
            if package.get('executableIndependent'):
                assert all(Path(n).suffix.lower() not in ('.exe', '.dll', '.asi', '.com', '.cmd', '.bat', '.ps1') for n in listed | {normalize(p) for p in manifest.get('remove', [])})
        result = dict(id=package['id'], version=package['version'], path=str(path), sha256=digest, size=path.stat().st_size,
                      fileCount=len(manifest['files']), manifest=manifest)
        self.audited[digest] = result
        return result

    def payload(self, package):
        verified = self.audit_archive(package)
        with zipfile.ZipFile(Path(verified['path'])) as archive:
            names = {normalize(n): n for n in archive.namelist()}
            return {file['path'].replace('\\', '/'): archive.read(names['payload/' + normalize(file['path'])])
                    for file in verified['manifest']['files']}

    def load_sources(self):
        for schema in SCHEMAS:
            for channel in CHANNELS:
                path = self.source_path(schema, channel)
                feed = self.verify_signed(path)
                assert feed['channel'] == channel and feed['launcher']['version'] == '0.7.7', 'Unexpected source generation'
                if schema == 'v2':
                    for mod in ('vanilla', 'immortals'):
                        assert feed['modGames'][mod]['k2ExeSha256'] == [GAME_HASH], 'Unexpected pure runtime requirement'
                assert len({p['id'] for p in feed['packages']}) == len(feed['packages'])
                key = schema + '/' + channel
                self.baselines[key] = feed
                self.before_hashes[key] = sha(path)
                for package in feed['packages']:
                    self.audit_archive(package)
        for id in AW_VERSIONS:
            legacy = next(p for p in self.baselines['legacy/beta']['packages'] if p['id'] == id)
            v2 = next(p for p in self.baselines['v2/beta']['packages'] if p['id'] == id)
            assert (legacy['version'], legacy['sha256']) == (v2['version'], v2['sha256'])
        print('SOURCE PASS:', len(self.baselines), 'verified signatures;', len(self.audited), 'verified archives', flush=True)

    def register_asset(self, package, tag, path):
        assert path.stat().st_size == package['size'] and sha(path) == package['sha256'].upper(), 'Staged asset identity mismatch'
        self.paths[package['sha256'].upper()] = path.resolve()
        entry = dict(path=str(path.resolve()), name=path.name, size=path.stat().st_size, sha256=sha(path), packageId=package['id'], version=package['version'])
        self.assets.setdefault(tag, []).append(entry)

    def copy_pure(self):
        incoming = read(self.args.pure / 'packages.json')
        result = {}
        data_payloads = {}
        checks = {}
        for channel, (version, runtime_version) in PURE_VERSIONS.items():
            packages = copy.deepcopy(incoming[channel])
            assert {p['id'] for p in packages} == {'pure-fixes-data', 'pure-fixes-runtime'}
            expected = {'pure-fixes-data': version, 'pure-fixes-runtime': runtime_version}
            tag = 'patch-' + version
            for package in packages:
                assert package['version'] == expected[package['id']]
                assert package['mods'] == ['vanilla', 'immortals'] and package['required'] is False
                independent = package['id'] == 'pure-fixes-data'
                assert package['priority'] == (900 if independent else 910) and package['executableIndependent'] == independent
                assert package['dependsOn'] == ([] if independent else ['menu-runtime'])
                assert bool(package['experimental']) == (channel == 'beta' and not independent)
                contents = self.payload(package)
                assert not self.audited[package['sha256'].upper()]['manifest'].get('remove')
                if independent:
                    assert len(contents) == 16
                    normalized = {normalize(p): data for p, data in contents.items()}
                    assert sum(p.startswith('data/organizations/banners/') for p in normalized) == 14
                    assert normalized[normalize('data/' + PROFILE)] == normalized[normalize('Local_base_ru/' + PROFILE)]
                    data_payloads[channel] = normalized
                else:
                    assert list(contents) == ['k2_paws_pure_fixes_1372.exe']
                    helper = self.out / 'verification/pure' / channel / 'k2_paws_pure_fixes_1372.exe'
                    helper.parent.mkdir(parents=True, exist_ok=True)
                    helper.write_bytes(next(iter(contents.values())))
                    features = json.loads(command([helper, '--features']))
                    assert features['version'] == runtime_version and features['patchVersion'] == version and features['channel'] == channel
                    assert features['fastSaveTransfer'] == (channel == 'beta')
                    assert all(not features[k] for k in ('cityAssistant', 'colors', 'bypass', 'hostility', 'randomMap', 'randomTime', 'changesGameFiles'))
                    checks[channel] = features
                destination = self.out / 'releases' / tag / 'assets' / self.local(package).name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.local(package), destination)
                self.register_asset(package, tag, destination)
                package['urls'] = [DOWNLOADS + tag + '/' + destination.name]
            result[channel] = packages
        assert data_payloads['stable'] == data_payloads['beta'], 'Pure Beta must inherit the same input and badge data'
        old_data = next(p for p in self.baselines['v2/stable']['packages'] if p['id'] == 'pure-fixes-data')
        assert all(data_payloads['stable'][normalize(p)] == data for p, data in self.payload(old_data).items()), 'Existing badges changed'
        core = next(p for p in self.baselines['v2/stable']['packages'] if p['id'] == 'pawpatch-core')
        aw_profile = next(data for path, data in self.payload(core).items() if normalize(path) == normalize('data/' + PROFILE))
        assert data_payloads['stable'][normalize('data/' + PROFILE)] == aw_profile, 'Pure controls differ from the reviewed AW Dvorak profile'
        write(self.out / 'pure-features.json', checks)
        return result

    def prepare_city(self):
        helpers = self.args.city_helpers.resolve()
        ready_path = helpers / 'release-ready.json'
        ready = read(ready_path)
        assert ready.get('ready') is True and ready.get('revision') == 'r14', 'City validation gate is incomplete'
        variants = read(REPO / 'game/beta7/variants.json')
        required = set(variants) | set(CITY_DATA)
        bound = {normalize(p): digest.upper() for p, digest in ready['files'].items()}
        assert len(bound) == len(ready['files']), 'Duplicate validation paths'
        validated = {p: (helpers / p).read_bytes() for p in required}
        assert all(normalize(p) in bound and sha_bytes(data) == bound[normalize(p)] for p, data in validated.items()), 'City artifacts differ from the validated gate'
        features = {}
        for name, defines in variants.items():
            feature = json.loads(command([helpers / name, '--features']))
            assert sha(helpers / name) == bound[normalize(name)], 'Helper changed during feature verification'
            assert all(feature[k] for k in ('cityAssistant', 'advancedCityPolicy', 'fastSaveTransfer', 'commonFixes', 'quiet'))
            assert feature['cityPolicyRevision'] == 14 and all(feature[k] for k in ('nativeCityQueue', 'automaticMines', 'newCityMilitia'))
            assert AW_BUILD_ID.encode('utf-16le') in validated[name], 'Diagnostic build identity differs from the release'
            assert 'beta.0.3.0-beta.2-1372-city-policy13-transfer-r2-quiet'.encode('utf-16le') not in validated[name], 'Stale diagnostic identity remains'
            for key, flag in (('colors', 'PAW_COLORS'), ('bypass', 'SYNC_CONTINUE'), ('hostility', 'HERD_RELATIONS_ONLY')):
                assert feature[key] == (flag in defines), name + ': ' + key
            features[name] = dict(sha256=sha(helpers / name), features=feature, diagnosticBuild=AW_BUILD_ID)
        packages = {p['id']: p for p in self.baselines['v2/beta']['packages']}
        result = {}
        scope = {}
        replaced = []
        for id, version in AW_VERSIONS.items():
            original = self.payload(packages[id])
            contents = dict(original)
            names = {normalize(p): p for p in contents}
            allowed = set()
            for name in variants:
                if normalize(name) in names:
                    target = names[normalize(name)]
                    contents[target] = validated[name]
                    allowed.add(target)
                    replaced.append(name)
            if id == 'common-ui':
                for relative in CITY_DATA:
                    target = names[normalize(relative)]
                    contents[target] = validated[relative]
                    allowed.add(target)
                target = names['paws_patch_versions.ini']
                before = contents[target]
                assert before.count(b'PawPatch=0.3.0-beta.2') == 1
                contents[target] = before.replace(b'PawPatch=0.3.0-beta.2', ('PawPatch=' + AW_VERSION).encode('ascii'))
                allowed.add(target)
            assert set(contents) == set(original)
            changed = {p for p in contents if contents[p] != original[p]}
            assert changed <= allowed and all(contents[p] == original[p] for p in set(contents) - allowed)
            manifest = copy.deepcopy(self.audited[packages[id]['sha256'].upper()]['manifest'])
            assert not manifest.get('remove'), 'Unexpected AW removal operations'
            manifest['version'] = version
            manifest['files'] = [dict(path=p, size=len(data), sha256=sha_bytes(data)) for p, data in sorted(contents.items(), key=lambda item: item[0].lower())]
            archive = zip_bytes(manifest, contents)
            assert archive == zip_bytes(manifest, contents), 'Archive output is nondeterministic'
            destination = self.out / 'releases' / ('patch-' + AW_VERSION) / 'assets' / (id + '-' + version + '.zip')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive)
            package = copy.deepcopy(packages[id])
            package.update(version=version, size=len(archive), sha256=sha_bytes(archive), experimental=True,
                           urls=[DOWNLOADS + 'patch-' + AW_VERSION + '/' + destination.name])
            self.register_asset(package, 'patch-' + AW_VERSION, destination)
            self.audit_archive(package)
            assert self.payload(package) == contents
            result[id] = package
            scope[id] = dict(previousVersion=packages[id]['version'], previousArchiveSha256=packages[id]['sha256'],
                             files=len(contents), unchangedPayloadFiles=len(contents) - len(changed),
                             changed={p: dict(before=sha_bytes(original[p]), after=sha_bytes(contents[p])) for p in sorted(changed)},
                             added=[], removed=[])
        assert set(replaced) == set(variants) and len(replaced) == 9, 'Expected 8 variants including the duplicate core family helper'
        write(self.out / 'city-scope.json', dict(revision='r14', diagnosticBuild=AW_BUILD_ID, readyManifestSha256=sha(ready_path), uniqueHelpers=8, helperPayloadCopies=9,
                                               features=features, packages=scope, validation=ready.get('checks', {})))
        return result

    def sign(self, feed, schema, channel, flavor):
        folder = self.out / 'feeds' / schema
        payload = folder / (channel + '.' + flavor + '.payload.json')
        signed = folder / (channel + '.' + flavor + '.signed.json')
        write(payload, feed)
        command([self.args.dotnet, self.publisher, 'sign', payload, self.private, 'pawpatch-prod-2026', signed])
        assert self.verify_signed(signed) == feed
        return dict(payload=str(payload), signed=str(signed), payloadSha256=sha(payload), signedSha256=sha(signed))

    def compose(self, pure, city):
        date = self.args.published_at[:10]
        pure_entries = {channel: [release_entry('release-patch-' + PURE_VERSIONS[channel][0] + '.md',
                            PURE_VERSIONS[channel][0], date, mod, channel) for mod in ('vanilla', 'immortals')] for channel in CHANNELS}
        aw_entry = release_entry('release-patch-' + AW_VERSION + '.md', AW_VERSION, date, 'arcane-wars', 'beta')
        feeds = {}
        proof = {}
        for schema in SCHEMAS:
            for channel in CHANNELS:
                key = schema + '/' + channel
                before = self.baselines[key]
                feed = copy.deepcopy(before)
                replacements = {}
                entries = []
                if channel == 'beta':
                    replacements.update(city)
                    entries.append(aw_entry)
                if schema == 'v2':
                    replacements.update({p['id']: p for p in pure[channel]})
                    entries = pure_entries[channel] + entries
                # Preserve channel/schema metadata (legacy has no mod scopes).
                for package in feed['packages']:
                    replacement = replacements.get(package['id'])
                    if replacement:
                        for field in ('version', 'size', 'sha256', 'urls', 'experimental'):
                            package[field] = copy.deepcopy(replacement[field])
                        if package['id'].startswith('pure-fixes-'):
                            for field in ('name', 'description'):
                                package[field] = copy.deepcopy(replacement[field])
                assert set(replacements) <= {p['id'] for p in feed['packages']}
                feed['patchGuide'] = aw_guide(before['patchGuide'])
                if schema == 'v2':
                    for mod in feed['modGuides']:
                        if mod['id'] in ('vanilla', 'immortals'):
                            mod['patchGuide'] = pure_guide(mod['patchGuide'], channel)
                            assert mod['patchGuide']['version'] == PURE_VERSIONS[channel][0]
                identities = {(e['category'], e['version'], tuple(e.get('mods', []))) for e in feed['changelog']}
                assert all((e['category'], e['version'], tuple(e['mods'])) not in identities for e in entries), 'Release already exists in source history'
                feed['changelog'] = copy.deepcopy(entries) + feed['changelog']
                # Launcher news stays about the unchanged launcher; scoped patch
                # histories/guide versions advertise these independent releases.
                feed['publishedAt'] = self.args.published_at
                assert feed['launcher'] == before['launcher'] and feed['game'] == before['game']
                assert feed.get('modGames') == before.get('modGames')
                assert len(feed['packages']) == len(before['packages'])
                assert [p for p in feed['packages'] if p['id'] not in replacements] == [p for p in before['packages'] if p['id'] not in replacements]
                if channel == 'stable':
                    assert [p for p in feed['packages'] if p['id'] in AW_VERSIONS] == [p for p in before['packages'] if p['id'] in AW_VERSIONS]
                for package in feed['packages']:
                    self.audit_archive(package)
                production = self.sign(feed, schema, channel, 'production')
                local = copy.deepcopy(feed)
                for package in local['packages']:
                    package['urls'] = [str(self.local(package))]
                local_proof = self.sign(local, schema, channel, 'local')
                previous = self.out / 'previous' / schema / (channel + '.signed.json')
                previous.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.source_path(schema, channel), previous)
                feeds[key] = feed
                proof[key] = dict(production=production, local=local_proof, newHistoryEntries=len(entries), changedPackageIds=sorted(replacements),
                                  unchangedPackageCount=len(feed['packages']) - len(replacements), launcherUnchanged=True, gameRequirementsUnchanged=True)
        write(self.out / 'changelog.history.json', {channel: feeds['v2/' + channel]['changelog'] for channel in CHANNELS})
        write(self.out / 'legacy.changelog.history.json', {channel: feeds['legacy/' + channel]['changelog'] for channel in CHANNELS})
        write(self.out / 'patch-guide.json', feeds['v2/beta']['patchGuide'])
        write(self.out / 'mod-guides.json', {channel: feeds['v2/' + channel]['modGuides'] for channel in CHANNELS})
        # v2 already has revised mod/component wording outside the city entry.
        # Preserve those source differences rather than copying a legacy guide.
        city_entry = next(e for e in feeds['v2/beta']['patchGuide']['entries'] if e['id'] == 'city-assistant')
        for key, feed in feeds.items():
            assert feed['patchGuide']['version'] == AW_VERSION
            assert next(e for e in feed['patchGuide']['entries'] if e['id'] == 'city-assistant') == city_entry
            assert [e for e in feed['patchGuide']['entries'] if e['id'] != 'city-assistant'] == [e for e in self.baselines[key]['patchGuide']['entries'] if e['id'] != 'city-assistant']
        return proof

    def finish(self, proof):
        assert all(sha(self.source_path(*key.split('/'))) == digest for key, digest in self.before_hashes.items()), 'Canonical feed changed during preparation'
        plan = []
        for tag, assets in self.assets.items():
            version = tag.removeprefix('patch-')
            plan.append(dict(tag=tag, version=version, prerelease='beta' in version, makeLatest=False, assets=assets,
                             notes=str(REPO / 'docs' / ('release-' + tag + '.md')),
                             notesSha256=sha(REPO / 'docs' / ('release-' + tag + '.md'))))
        write(self.out / 'release-plan.json', dict(published=False, releases=plan, launcherIncluded=False))
        report = dict(published=False, canonicalFeedsChanged=False, helperBuildStarted=False, gameLaunched=False,
                      launcherVersion='0.7.7', intendedLauncherVersionLater='0.7.8', beforeFeedSha256=self.before_hashes,
                      signedCandidates=8, verifiedSourceArchives=len(self.audited) - 7, newArchives=7,
                      publishedAt=self.args.published_at,
                      feeds=proof, releases=plan, sourceScriptSha256=sha(Path(__file__)),
                      preservation=['AW stable packages', 'menu-runtime', 'all localization and voice packages', 'game requirements', 'launcher metadata'],
                      candidateSignaturesVerified=True)
        write(self.out / 'preparation.json', report)
        print('PREPARED: 3 patch releases, 7 immutable archives, 8 verified signed candidates; no publication.', flush=True)


def zip_bytes(manifest, files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, data in [('module.json', encode(manifest))] + [('payload/' + p, data) for p, data in sorted(files.items(), key=lambda item: item[0].lower())]:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return stream.getvalue()


def localized_notes(filename):
    text = (REPO / 'docs' / filename).read_text('utf-8')
    ru, en = text.split('## Русский\n', 1)[1].split('## English\n', 1)
    return {'ru': ru.strip(), 'en': en.strip()}


def release_entry(filename, version, date, mod, channel):
    name = {'vanilla': 'Vanilla', 'immortals': 'Immortals', 'arcane-wars': 'Arcane Wars'}[mod]
    return dict(category='patch', version=version, publishedAt=date, mods=[mod],
                title={'ru': name + ' — Paw\'s Patch ' + version, 'en': name + ' — Paw\'s Patch ' + version},
                body=localized_notes(filename))


def pure_guide(original, channel):
    guide = copy.deepcopy(original)
    guide['version'] = PURE_VERSIONS[channel][0]
    guide['entries'] = [e for e in guide['entries'] if e['id'] not in ('dvorak', 'fast-save-transfer')]
    guide['entries'].append(dict(id='dvorak', category='always', titleRu='Камера и союзная метка в Dvorak', titleEn='Camera and allied marker in Dvorak',
        bodyRu='В профиле Dvorak клавиши WASD двигают камеру; управление стрелками сохраняется. F выбирает союзную метку. Остальные позиционные клавиши профиля сохранены, прежняя команда на A освобождена для камеры.\n\nПрофиль выбирается в настройках самой игры: патч не переключает его автоматически. Исправление работает с английским и русским текстом, в том числе в режиме «Только игровые файлы». Другие профили управления не меняются.',
        bodyEn='In the Dvorak profile, WASD moves the camera and arrow controls remain available. F selects the allied marker. Other positional bindings are retained; the old A action is freed for camera movement.\n\nSelect Dvorak in the game settings; the patch does not switch profiles automatically. Works with English or Russian text, including file-only mode. Other input profiles remain unchanged.'))
    if channel == 'beta':
        guide['entries'].append(dict(id='fast-save-transfer', category='beta', titleRu='Встроенная передача сохранений R2', titleEn='Built-in R2 save transfer',
            bodyRu='В бете Paw\'s Patch ускорена передача сохранений участникам сетевого лобби средствами самой игры. Функция включается вместе с Paw\'s Patch; отдельная настройка и ручное принятие файла в лаунчере не нужны.\n\nДля сетевой игры всем участникам нужны совместимая бета и одинаковые игровые настройки.\n\nУскорение работает с поддерживаемым EXE Kohan II 1.3.72. С неподдерживаемым EXE, в режиме «Только игровые файлы» или при выключенном Paw\'s Patch передача остаётся обычной.',
            bodyEn='Paw\'s Patch Beta speeds up lobby save transfers through the game. The feature is included when Paw\'s Patch is enabled; no separate setting or manual file acceptance in the launcher is needed.\n\nAll multiplayer participants need a compatible Beta and matching gameplay settings.\n\nFaster transfer requires the supported Kohan II 1.3.72 executable. Transfer stays at its regular speed with an unsupported executable, in file-only mode, or with Paw\'s Patch disabled.'))
    assert {e['id'] for e in guide['entries']} == {'base', 'badge-colors', 'negative-zero', 'terrain', 'dvorak'} | ({'fast-save-transfer'} if channel == 'beta' else set())
    return guide


def aw_guide(original):
    guide = copy.deepcopy(original)
    guide['version'] = AW_VERSION
    city = next(e for e in guide['entries'] if e['id'] == 'city-assistant')
    city.update(titleRu='Автоулучшение городов и полная очередь', titleEn='City automation and the full queue',
        bodyRu='Встроено в Paw\'s Patch для беты Arcane Wars при любых сочетаниях остальных компонентов. Нужен поддерживаемый EXE 1.3.72; в режиме «Только игровые файлы» недоступно. F1 содержит включение автоматики, пороги дохода камня, дерева, железа и кристаллов, резерв золота и сохранённую настройку открытого ополчения для новых городов. Enter применяет число; Esc или щелчок вне поля отменяет ввод.\n\nУчитываются все принятые ручные и автоматические заказы, включая ожидающие: будущий положительный доход уменьшает оставшийся дефицит, отрицательный учитывается для защиты дохода. Положительный эффект незавершённого здания не считается уже полученным доходом. Оплата использует текущие ресурсы. Пока отправленные игроком строительные приказы не обработаны игрой, автоматика ждёт; затем пересчитывает золото и резерв. Города работают параллельно; осада блокирует свой город.\n\nРынки всех шести рас разрешены, если до заказа все четыре дохода строго выше порогов с учётом ожидаемых отрицательных эффектов. После заказа рынок может опустить доход ниже порога; тогда приоритет возвращается к восполнению ресурсов. Остальные здания сохраняют защиту порогов. После экономических приоритетов автоматика постоянно выбирает случайный доступный вариант при достаточном доходе; отдельная настройка «Другие здания» не нужна. Независимые рудники всех рас участвуют в улучшениях, разные рудники получают отдельные приказы.\n\nОткрытое ополчение для новых собственных городов включено по умолчанию и сохраняется на компьютере. Применяется к новым построенным и захваченным городам; уже существующие на момент начала партии или загрузки города не изменяются. Общие правила сохраняются локально, исключения городов сбрасываются при новой партии или загрузке; формат сейвов не меняется.',
        bodyEn='Built into Paw\'s Patch for Arcane Wars Beta with every combination of the other components. Requires the supported 1.3.72 executable and is unavailable in file-only mode. F1 provides automation, stone/wood/iron/mana income targets, a gold reserve and the persisted open-militia preference for new cities. Enter applies numeric editing; Esc or clicking outside cancels it.\n\nAll accepted manual and automatic orders are accounted for, including waiting jobs: future positive income reduces outstanding goals, while negative effects protect income. An unfinished building\'s positive effect is not treated as income already received. Payment uses current resources. Automation waits while the player\'s sent construction orders await game processing, then recomputes gold and the protected reserve. Cities work in parallel; a siege excludes its own city.\n\nMarkets of all six races are allowed when all four incomes are strictly above their targets before the order, accounting for pending negative effects. The market may cross below a target afterward; resource recovery then takes priority. Other buildings retain target protection. After economic priorities, automation continually selects a random eligible option when income permits; no separate Other buildings setting is needed. Independent mines of every race can upgrade, and different mines receive separate orders.\n\nOpen militia for new owned cities is on by default and persists on this PC. It applies to newly built and captured cities; cities already present at match start or save load are unchanged. General rules persist locally; city exceptions reset on new matches or loads. Save format is unchanged.')
    return guide


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('out', 'dotnet', 'signing-dir', 'pure', 'city-helpers'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--published-at', required=True, help='Fixed UTC YYYY-MM-DDTHH:MM:SSZ for reproducible payloads')
    parser.add_argument('--audit-sources-only', action='store_true')
    parser.add_argument('--cache', type=Path, action='append', default=[], help='Additional read-only verified archive cache; may be repeated')
    args = parser.parse_args()
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', args.published_at)
    prep = Preparation(args)
    assert not prep.out.exists() or not any(prep.out.iterdir()), 'Choose a fresh candidate directory'
    assert not prep.out.is_relative_to((REPO / 'feed').resolve()) and not prep.out.is_relative_to(args.city_helpers.resolve())
    prep.load_sources()
    if args.audit_sources_only:
        print('SOURCE AUDIT ONLY: no output files or packages written.')
        return
    assert read(args.city_helpers / 'release-ready.json').get('ready') is True, 'City packaging is on hold'
    prep.out.mkdir(parents=True, exist_ok=True)
    pure = prep.copy_pure()
    city = prep.prepare_city()
    proof = prep.compose(pure, city)
    prep.finish(proof)


if __name__ == '__main__':
    main()
