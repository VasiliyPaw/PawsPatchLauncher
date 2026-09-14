"""Finalize launcher 0.7.8 over prepared patch channels, without publishing.

Default: verify local inputs, then stage four signed production feeds and backups
in a new output directory. --verify-public additionally reads public release
assets/tags/feeds. --promote requires those public checks and replaces local
canonical feeds only after rechecking every input. Never uploads, tags, commits,
pushes, retrieves credentials, builds software, or runs the launcher/game.
"""
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import uuid
import zipfile

REPO = Path(__file__).resolve().parents[1]
VERSION = '0.7.8'
KEY_ID = 'pawpatch-prod-2026'
PROJECT = 'VasiliyPaw/PawsPatchLauncher'
API = 'https://api.github.com/repos/' + PROJECT
DOWNLOAD = 'https://github.com/' + PROJECT + '/releases/download/'
FEEDS = {'legacy/stable': 'feed/stable.json', 'legacy/beta': 'feed/beta.json',
         'v2/stable': 'feed/v2/stable.json', 'v2/beta': 'feed/v2/beta.json'}
ANCILLARY = ('feed/changelog.history.json', 'feed/patch-guide.json', 'feed/patch-guide-beta.json')
EMBEDDED = 'src/PawsPatchLauncher/Assets/mod-guides.json'
RELEASES = {
    'patch-0.1.1': (False, {'pure-fixes-data': '0.1.1', 'pure-fixes-runtime': '1.3.72-pure.6'}),
    'patch-0.2.0-beta.1': (True, {'pure-fixes-data': '0.2.0-beta.1', 'pure-fixes-runtime': '1.3.72-pure.7-beta.1'}),
    'patch-0.3.0-beta.3': (True, {'pawpatch-core': '0.3.0-beta.3', 'common-ui': '1.3.72-ui.4-beta.3', 'player-colors': '0.3.0-beta.3'})}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def read(path):
    return json.loads(path.read_bytes())


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def normalized(data):
    # Match Git CRLF normalization without weakening signed-envelope identity.
    return data.replace(b'\r\n', b'\n')


def inside(path, parent):
    return path.resolve().is_relative_to(parent.resolve())


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def run(arguments, *, cwd=REPO, env=None):
    result = subprocess.run([str(a) for a in arguments], cwd=cwd, env=env,
                            capture_output=True, timeout=60,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    # Arguments can include private-key paths. Never echo commands or their output
    # on failure; callers supply the non-sensitive operation being validated.
    require(result.returncode == 0, 'Validation command failed: ' + Path(arguments[0]).name)
    return result.stdout


def safe_member(name):
    name = name.replace('\\', '/')
    require(bool(name) and not name.startswith('/') and ':' not in name
            and all(part not in ('', '.', '..') for part in name.split('/')), 'Unsafe archive member')
    return name.lower()


def verify_file(path, identity):
    require(isinstance(identity.get('size'), int) and identity['size'] > 0, 'Invalid artifact size')
    require(re.fullmatch(r'[0-9a-fA-F]{64}', identity.get('sha256', '')) is not None, 'Invalid artifact SHA-256')
    require(path.is_file() and path.stat().st_size == identity['size'] and sha(path) == identity['sha256'].upper(),
            'Artifact identity mismatch: ' + path.name)


def audit_package(path, identity):
    verify_file(path, identity)
    with zipfile.ZipFile(path) as archive:
        members = {safe_member(name): name for name in archive.namelist()}
        require(len(members) == len(archive.namelist()) and 'module.json' in members, 'Duplicate or missing package members')
        module = json.loads(archive.read(members['module.json']))
        require(module['id'] == identity['packageId'] and module['version'] == identity['version'], 'Package module identity mismatch')
        listed = set()
        for item in module['files']:
            member = 'payload/' + safe_member(item['path'])
            require(member not in listed and member in members, 'Duplicate or missing payload member')
            listed.add(member)
            require(archive.getinfo(members[member]).file_size == item['size'], 'Payload size mismatch')
            with archive.open(members[member]) as stream:
                require(hashlib.file_digest(stream, 'sha256').hexdigest().upper() == item['sha256'].upper(), 'Payload digest mismatch')
        require(set(members) == listed | {'module.json'}, 'Unmanifested package contents')
        for member in module.get('remove', []):
            safe_member(member)


def snapshot_tree(root):
    result = {}
    for path in root.rglob('*'):
        if path.is_file():
            require(inside(path, root), 'Candidate contains an external link')
            result[str(path.relative_to(root))] = sha(path)
    return result


def parse_notes(data):
    text = data.decode('utf-8-sig').replace('\r\n', '\n')
    pieces = re.split(r'^# English\s*$', text, flags=re.M)
    require(len(pieces) == 2, 'Launcher notes require one # English section')
    title, ru = pieces[0].split('\n', 1)
    require(title == "# Paw's Launcher " + VERSION, 'Launcher release-note version differs')
    ru = re.sub(r'\n---\s*$', '', ru).strip()
    en = pieces[1].strip()
    require(ru and en and max(len(ru), len(en)) <= 40000, 'Missing or oversized localized launcher notes')
    return {'ru': title[2:], 'en': title[2:]}, {'ru': ru, 'en': en}


def finalized_feed(source, launcher, title, body, date):
    require(source['launcher']['version'] == '0.7.7', 'Candidate already has another launcher generation')
    require(not any(e.get('category') == 'launcher' and e['version'] == VERSION for e in source['changelog']), 'Launcher history already contains 0.7.8')
    result = copy.deepcopy(source)
    result['launcher'].update(launcher)
    result['publishedAt'] = date
    entry = dict(category='launcher', mods=[], version=VERSION, publishedAt=date, title=title, body=body)
    result['changelog'] = [entry] + copy.deepcopy(source['changelog'])
    result['newsTitle'], result['newsBody'] = copy.deepcopy(title), copy.deepcopy(body)
    permitted = {'launcher', 'publishedAt', 'changelog', 'newsTitle', 'newsBody'}
    require({k: v for k, v in result.items() if k not in permitted} == {k: v for k, v in source.items() if k not in permitted}, 'Finalization changed patch data')
    require(result['changelog'][1:] == source['changelog'], 'Independent patch history changed')
    return result


def fetch(url, expected=None):
    request = urllib.request.Request(url, headers={'User-Agent': 'PawsPatchFinalizationAudit', 'Cache-Control': 'no-cache'})
    hasher, size, chunks = hashlib.sha256(), 0, []
    limit = expected['size'] if expected else 8 * 1024 * 1024
    with urllib.request.urlopen(request, timeout=45) as response:
        while block := response.read(1024 * 1024):
            size += len(block)
            require(size <= limit, 'Public response exceeds expected size')
            hasher.update(block)
            if expected is None:
                chunks.append(block)
    if expected is not None:
        require(size == expected['size'] and hasher.hexdigest().upper() == expected['sha256'].upper(), 'Public asset digest/size mismatch')
        return {'size': size, 'sha256': hasher.hexdigest().upper()}
    return b''.join(chunks)


def public_release(tag, commit, prerelease):
    release = json.loads(fetch(API + '/releases/tags/' + tag))
    require(release['tag_name'] == tag and not release['draft'] and release['prerelease'] is prerelease, 'Public release state differs: ' + tag)
    target = json.loads(fetch(API + '/git/ref/tags/' + tag))['object']
    for _ in range(8):
        if target['type'] != 'tag':
            break
        target = json.loads(fetch(API + '/git/tags/' + target['sha']))['object']
    require(target['type'] == 'commit' and target['sha'].lower() == commit, 'Immutable tag points at another commit: ' + tag)
    assets = {asset['name']: asset for asset in release['assets']}
    require(len(assets) == len(release['assets']), 'Duplicate release asset names')
    return assets


def public_asset(assets, tag, identity):
    name = identity['name']
    require(name in assets, 'Public asset is missing: ' + name)
    asset = assets[name]
    expected_url = DOWNLOAD + tag + '/' + name
    require(asset['browser_download_url'] == expected_url and asset['size'] == identity['size'], 'Public asset metadata differs: ' + name)
    if asset.get('digest'):
        require(asset['digest'].lower() == 'sha256:' + identity['sha256'].lower(), 'Public recorded digest differs: ' + name)
    return dict(name=name, url=expected_url, **fetch(expected_url, identity))


class Finalization:
    def __init__(self, args):
        self.args = args
        self.candidate, self.out = args.candidate.resolve(), args.out.resolve()
        self.commit = args.source_commit.lower()
        require(re.fullmatch(r'[0-9a-f]{40}', self.commit) is not None, 'Source commit must be a full SHA-1')
        require(self.candidate.is_dir(), 'Candidate directory is missing')
        require(not self.out.exists() and not inside(self.out, self.candidate) and not inside(self.out, REPO / 'feed'), 'Use a new output outside the candidate and canonical feed directories')
        require(not inside(self.candidate, self.out), 'Output must not contain the source candidate')
        self.publisher = REPO / 'tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll'
        self.public = args.signing_dir / 'pawpatch-signing-public.pem'
        self.private = args.signing_dir / 'pawpatch-signing-private.pem'
        configured = read(REPO / 'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem']
        require(re.sub(r'\s+', '', configured) == re.sub(r'\s+', '', self.public.read_text('utf-8-sig')), 'Signing public key differs from launcher trust root')
        require(self.private.is_file() and self.publisher.is_file(), 'Signing prerequisite is missing')
        self.candidate_snapshot = snapshot_tree(self.candidate)
        self.before = {}
        self.feeds, self.plan, self.public_report = {}, None, []

    def signed(self, path):
        run([self.args.dotnet, self.publisher, 'verify', path, self.public])
        envelope = read(path)
        require(envelope['keyId'] == KEY_ID, 'Unexpected signing key identity')
        return json.loads(base64.b64decode(envelope['payload'], validate=True))

    def validate_candidate(self):
        for key, relative in FEEDS.items():
            current = REPO / relative
            require(inside(current, REPO / 'feed'), 'Canonical feed escapes its directory')
            previous = self.candidate / 'previous' / (key + '.signed.json')
            before = current.read_bytes()
            require(normalized(before) == normalized(previous.read_bytes()), 'Canonical feed moved: ' + key)
            require(self.signed(current) == self.signed(previous), 'Canonical signed payload differs from rollback snapshot')
            self.before[relative] = before
            schema, channel = key.split('/')
            staged = self.candidate / 'feeds' / schema / (channel + '.production.signed.json')
            feed = self.signed(staged)
            require(feed['channel'] == channel and feed['launcher']['version'] == '0.7.7', 'Unexpected candidate channel/launcher')
            require(feed == read(staged.with_name(channel + '.production.payload.json')), 'Candidate payload differs from signed contents')
            require(len({p['id'] for p in feed['packages']}) == len(feed['packages']), 'Duplicate feed package identities')
            self.feeds[key] = feed
        for relative in (*ANCILLARY, EMBEDDED):
            path = REPO / relative
            require(inside(path, REPO / ('feed' if relative in ANCILLARY else 'src')), 'Tracked source escapes its directory')
            self.before[relative] = path.read_bytes()
        self.plan = read(self.candidate / 'release-plan.json')
        require(self.plan.get('published') is False and not self.plan.get('launcherIncluded'), 'Candidate is not a patch-only unpublished plan')
        releases = {r['tag']: r for r in self.plan['releases']}
        require(len(releases) == 3 and set(releases) == set(RELEASES), 'Unexpected patch releases')
        for tag, (prerelease, versions) in RELEASES.items():
            release = releases[tag]
            require(release['prerelease'] is prerelease and release['makeLatest'] is False, 'Patch release flags differ')
            require({a['packageId']: a['version'] for a in release['assets']} == versions and len(release['assets']) == len(versions), 'Unexpected patch asset set')
            for asset in release['assets']:
                path = Path(asset['path']).resolve()
                require(inside(path, self.candidate / 'releases') and path.name == asset['name'] == asset['packageId'] + '-' + asset['version'] + '.zip', 'Patch asset escapes candidate or has unexpected name')
                audit_package(path, asset)
                matching = [p for feed in self.feeds.values() for p in feed['packages'] if p['id'] == asset['packageId'] and p['version'] == asset['version']]
                require(matching and all(p['sha256'].upper() == asset['sha256'].upper() and p['size'] == asset['size'] and p['urls'] == [DOWNLOAD + tag + '/' + asset['name']] for p in matching), 'Patch plan differs from signed release metadata')
            notes = Path(release['notes']).resolve()
            require(inside(notes, REPO / 'docs') and sha(notes) == release['notesSha256'], 'Patch release notes changed since preparation')
        history = read(self.candidate / 'changelog.history.json')
        require(all(history[c] == self.feeds['v2/' + c]['changelog'] for c in ('stable', 'beta')), 'Candidate V2 history differs from signed feeds')
        guide = read(self.candidate / 'patch-guide.json')
        require(all(self.feeds['v2/' + c]['patchGuide'] == guide for c in ('stable', 'beta')), 'Candidate V2 shared guide differs')

    def validate_launcher(self):
        require(run(['git', 'cat-file', '-t', self.commit]).strip() == b'commit', 'Source revision is not a local commit')
        project = run(['git', 'show', self.commit + ':src/PawsPatchLauncher/PawsPatchLauncher.csproj']).decode('utf-8-sig')
        require('<Version>' + VERSION + '</Version>' in project, 'Source commit is not launcher 0.7.8')
        notes = run(['git', 'show', self.commit + ':docs/release-' + VERSION + '.md'])
        require(normalized(notes) == normalized((REPO / ('docs/release-' + VERSION + '.md')).read_bytes()), 'Launcher notes differ from source commit')
        self.title, self.body = parse_notes(notes)
        self.notes = notes
        artifact_path, executable = self.args.launcher_artifact.resolve(), self.args.launcher_exe.resolve()
        artifact_bytes = artifact_path.read_bytes()
        self.artifact = json.loads(artifact_bytes)
        self.external_snapshot = {artifact_path: digest(artifact_bytes), executable: sha(executable)}
        require(self.artifact['version'] == VERSION and self.artifact['sourceCommit'].lower() == self.commit, 'CI artifact version/source differs')
        files = {f['name']: f for f in self.artifact['files']}
        require(len(files) == len(self.artifact['files']) and set(files) == {'PawsPatchLauncher.exe', 'PawsPatchLauncher-v0.7.8-win-x64.zip', 'launcher.config.json'}, 'Unexpected CI distribution contents')
        for file in files.values():
            require(isinstance(file.get('size'), int) and file['size'] > 0 and re.fullmatch(r'[0-9a-fA-F]{64}', file.get('sha256', '')) is not None, 'Invalid CI artifact identity')
        require(executable.name == 'PawsPatchLauncher.exe', 'Expected the final CI executable')
        verify_file(executable, files['PawsPatchLauncher.exe'])
        require(executable.read_bytes()[:2] == b'MZ', 'Launcher is not a PE executable')
        shell = shutil.which('pwsh') or shutil.which('powershell')
        require(shell is not None, 'PowerShell is required for read-only executable metadata verification')
        script = '''$ErrorActionPreference='Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$item=Get-Item -LiteralPath $env:PAWS_FINALIZE_EXE
$signature=Get-AuthenticodeSignature -LiteralPath $item.FullName
[ordered]@{fileVersion=$item.VersionInfo.FileVersion;productVersion=$item.VersionInfo.ProductVersion;productName=$item.VersionInfo.ProductName;authenticodeStatus=$signature.Status.ToString();publisher=$(if($signature.SignerCertificate){$signature.SignerCertificate.Subject}else{$null});certificateThumbprint=$(if($signature.SignerCertificate){$signature.SignerCertificate.Thumbprint}else{$null});timestamped=($null -ne $signature.TimeStamperCertificate)} | ConvertTo-Json -Compress
'''
        environment = os.environ.copy()
        environment['PAWS_FINALIZE_EXE'] = str(executable)
        metadata = json.loads(run([shell, '-NoProfile', '-NonInteractive', '-Command', script], env=environment).decode('utf-8-sig'))
        require(metadata['fileVersion'] == VERSION + '.0' and metadata['productVersion'] == VERSION and metadata['productName'] == 'PawsPatchLauncher', 'Executable product/version metadata differs')
        require(isinstance(self.artifact['authenticodeRequired'], bool), 'Invalid CI signing policy')
        expected_status = 'Valid' if self.artifact['authenticodeRequired'] else 'NotSigned'
        require(metadata['authenticodeStatus'] == expected_status, 'Executable does not satisfy the CI signing policy')
        for field in ('authenticodeStatus', 'publisher', 'certificateThumbprint', 'timestamped'):
            require(metadata[field] == self.artifact[field], 'Executable signature metadata differs from CI artifact')
        if self.artifact['authenticodeRequired']:
            require(metadata['publisher'] and metadata['certificateThumbprint'] and metadata['timestamped'], 'Signed CI artifact lacks publisher or timestamp')
        self.launcher = dict(version=VERSION, size=files['PawsPatchLauncher.exe']['size'], sha256=files['PawsPatchLauncher.exe']['sha256'].upper(), urls=[DOWNLOAD + 'v' + VERSION + '/PawsPatchLauncher.exe'])
        self.launcher_assets = [files['PawsPatchLauncher.exe'], files['PawsPatchLauncher-v0.7.8-win-x64.zip'],
                                dict(name='launcher-artifact.json', size=artifact_path.stat().st_size, sha256=sha(artifact_path))]
        require(all(sha(path) == value for path, value in self.external_snapshot.items()), 'CI artifact changed while it was being verified')
        self.launcher_metadata = metadata

    def validate_public(self):
        for release in self.plan['releases']:
            tag = release['tag']
            assets = public_release(tag, self.commit, release['prerelease'])
            self.public_report.extend(public_asset(assets, tag, a) for a in release['assets'])
        launcher_assets = public_release('v' + VERSION, self.commit, False)
        self.public_report.extend(public_asset(launcher_assets, 'v' + VERSION, a) for a in self.launcher_assets)
        self.unchanged_public_feeds()
        require(len(self.public_report) == 10, 'Incomplete public asset verification')

    def unchanged_public_feeds(self):
        for key, relative in FEEDS.items():
            live = fetch('https://raw.githubusercontent.com/' + PROJECT + '/main/' + relative)
            require(normalized(live) == normalized(self.before[relative]), 'Public canonical feed moved: ' + key)

    def unchanged(self):
        require(all((REPO / relative).read_bytes() == data for relative, data in self.before.items()), 'A canonical feed, history, guide or embedded guide changed during finalization')
        require(snapshot_tree(self.candidate) == self.candidate_snapshot, 'Candidate changed during finalization')
        require(all(sha(path) == value for path, value in self.external_snapshot.items()), 'CI artifact changed during finalization')

    def stage(self):
        self.unchanged()
        self.out.mkdir(parents=True, exist_ok=False)
        self.targets = {}
        self.final = {}
        date = self.args.published_at or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', date) is not None, 'Use an explicit UTC publication timestamp')
        datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
        for key, relative in FEEDS.items():
            feed = finalized_feed(self.feeds[key], self.launcher, self.title, self.body, date)
            schema, channel = key.split('/')
            payload = self.out / 'feeds' / schema / (channel + '.production.payload.json')
            signed = payload.with_name(channel + '.production.signed.json')
            write_new(payload, encode(feed))
            run([self.args.dotnet, self.publisher, 'sign', payload, self.private, KEY_ID, signed])
            require(self.signed(signed) == feed, 'Final signed feed differs from staged payload')
            self.final[key] = feed
            self.targets[relative] = signed.read_bytes()
        history = {c: self.final['v2/' + c]['changelog'] for c in ('stable', 'beta')}
        self.targets['feed/changelog.history.json'] = encode(history)
        guide = encode(self.final['v2/stable']['patchGuide'])
        self.targets['feed/patch-guide.json'] = self.targets['feed/patch-guide-beta.json'] = guide
        for relative, data in self.targets.items():
            if relative in ANCILLARY:
                write_new(self.out / 'canonical' / relative, data)
            write_new(self.out / 'rollback' / relative, self.before[relative])
        write_new(self.out / 'release-notes.md', self.notes)
        self.unchanged()
        self.report = dict(version=VERSION, sourceCommit=self.commit, published=False, promoted=False,
                           candidate=str(self.candidate), candidateUnchanged=True, launcher=self.launcher,
                           launcherArtifactSha256=sha(self.args.launcher_artifact), launcherSignature=self.launcher_metadata,
                           verifiedPatchArchives=7, verifiedSignedCandidates=4, verifiedCanonicalFeeds=4,
                           publicChecks=self.args.verify_public or self.args.promote, publicAssets=self.public_report,
                           publishedAt=date, preservedEmbeddedGuideSha256=digest(self.before[EMBEDDED]),
                           promotionTargets={relative: dict(beforeSha256=digest(self.before[relative]), afterSha256=digest(data)) for relative, data in self.targets.items()},
                           rollbackDirectory=str(REPO / 'feed/history' / ('before-launcher-0.7.8-' + self.commit[:12])),
                           noBuild=True, noGame=True, noUpload=True)
        write_new(self.out / 'finalization.json', encode(self.report))

    def promote(self):
        require(self.args.promote and len(self.public_report) == 10, 'Promotion requires explicit request and all public checks')
        self.unchanged_public_feeds()
        self.unchanged()
        feed_root = REPO / 'feed'
        backup = Path(self.report['rollbackDirectory'])
        require(inside(backup, feed_root / 'history') and not backup.exists(), 'Never overwrite rollback history')
        for relative in self.targets:
            require(inside(REPO / relative, feed_root), 'Promotion target escapes the feed directory')
        # One exclusive directory reserves the rollback generation. It is never
        # reused, including after an interrupted attempt.
        backup.mkdir(parents=True, exist_ok=False)
        for relative in self.targets:
            write_new(backup / Path(relative).relative_to('feed'), self.before[relative])
        self.unchanged()
        token = uuid.uuid4().hex
        temps, applied = {}, []
        try:
            for relative, data in self.targets.items():
                target = REPO / relative
                temp = target.with_name('.' + target.name + '.finalize-078-' + token + '.tmp')
                require(inside(temp, feed_root), 'Staging target escapes feed directory')
                write_new(temp, data)
                temps[relative] = temp
            self.unchanged()
            for relative in self.targets:
                target = REPO / relative
                require(target.read_bytes() == self.before[relative], 'Canonical target changed before replacement')
                os.replace(temps[relative], target)
                applied.append(relative)
            require(all((REPO / relative).read_bytes() == data for relative, data in self.targets.items()), 'Promoted bytes differ')
            require((REPO / EMBEDDED).read_bytes() == self.before[EMBEDDED], 'Embedded mod guide changed')
            for key, relative in FEEDS.items():
                require(self.signed(REPO / relative) == self.final[key], 'Promoted signature verification failed')
        except BaseException as error:
            unrestored = []
            for relative in reversed(applied):
                target = REPO / relative
                # Never overwrite another writer's intervening change.
                try:
                    if target.is_file() and target.read_bytes() == self.targets[relative]:
                        rollback_temp = target.with_name('.' + target.name + '.rollback-' + token + '.tmp')
                        write_new(rollback_temp, self.before[relative])
                        os.replace(rollback_temp, target)
                    else:
                        unrestored.append(relative)
                except OSError:
                    unrestored.append(relative)
            if unrestored:
                raise RuntimeError('Promotion failed; inspect retained rollback history. These targets changed concurrently or could not be restored: ' + ', '.join(unrestored)) from error
            raise
        finally:
            for temp in temps.values():
                if temp.is_file():
                    temp.unlink()
        write_new(self.out / 'promotion.json', encode(dict(promoted=True, publicPublished=False, rollbackDirectory=str(backup), targets=self.report['promotionTargets'])))


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate', 'launcher-artifact', 'launcher-exe', 'dotnet', 'signing-dir', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--published-at', help='Optional fixed UTC timestamp, YYYY-MM-DDTHH:MM:SSZ')
    parser.add_argument('--verify-public', action='store_true', help='Read and verify immutable public tags/assets and unchanged public feeds')
    parser.add_argument('--promote', action='store_true', help='After public verification, replace local canonical feeds and preserve rollback history')
    return parser.parse_args()


def main():
    args = arguments()
    task = Finalization(args)
    task.validate_candidate()
    task.validate_launcher()
    if args.verify_public or args.promote:
        task.validate_public()
    task.stage()
    if args.promote:
        task.promote()
        print('PROMOTED LOCALLY: four feeds and shared history/guide; rollback retained. No upload/commit/push.')
    else:
        print('FINALIZATION STAGED: four verified signed feeds; canonical files and candidate unchanged. No publication.')


if __name__ == '__main__':
    main()
