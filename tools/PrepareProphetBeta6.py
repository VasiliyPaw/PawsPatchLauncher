"""Stage hash-bound Arcane Wars beta.6 packages; never publishes or edits a game."""
import argparse
import copy
import shutil
from pathlib import Path
import PreparePatchChannels078 as base

VERSION = '0.3.0-beta.6'
TAG = 'patch-' + VERSION
VERSIONS = {'pawpatch-core': VERSION, 'common-ui': '1.3.72-ui.5-beta.6'}

class Preparation(base.Preparation):
    def prepare(self):
        for schema in base.SCHEMAS:
            for channel in base.CHANNELS:
                path = self.source_path(schema, channel)
                key = schema + '/' + channel
                self.baselines[key] = self.verify_signed(path)
                self.before_hashes[key] = base.sha(path)
                assert self.baselines[key]['launcher']['version'] == '0.8.0'
                previous = self.out / 'previous' / schema / (channel + '.signed.json')
                previous.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, previous)
        source = {p['id']: p for p in self.baselines['v2/beta']['packages']}
        assert source['pawpatch-core']['version'] == '0.3.0-beta.5'
        bound = base.read(base.REPO / 'game/prophet-animation/validation.json')
        assert bound['preservedMovementTracks'] == 572 and bound['preservedEventTracks'] == 22
        assert bound['userReplayedPreviouslyCrashingBattle'] is True
        fixes = {f['path']: f['afterSha256'] for f in bound['files']}
        assert len(fixes) == 22
        normalized_fixes = {base.normalize(p) for p in fixes}
        overlaps = []
        # Check every existing beta payload, so optional overlays cannot undo the fix.
        for package in source.values():
            audit = self.audit_archive(package)
            hits = [f['path'] for f in audit['manifest']['files'] if base.normalize(f['path']) in normalized_fixes]
            if hits:
                assert package['id'] == 'arcane-wars' and package['priority'] < source['pawpatch-core']['priority']
                overlaps.append({'id': package['id'], 'paths': hits, 'priority': package['priority']})
        assert len(overlaps) == 1 and len(overlaps[0]['paths']) == 11
        updates, scope = {}, []
        for id, version in VERSIONS.items():
            old = source[id]
            original = self.payload(old)
            files = copy.deepcopy(original)
            if id == 'pawpatch-core':
                for path, digest in fixes.items():
                    assert base.normalize(path) not in {base.normalize(p) for p in files}
                    data = (base.REPO / 'game/prophet-animation/assets' / path).read_bytes()
                    assert base.sha_bytes(data) == digest and path.lower().endswith('.kf')
                    files[path] = data
                assert {p: b for p, b in files.items() if p not in fixes} == original
            else:
                path = next(p for p in files if base.normalize(p) == 'paws_patch_versions.ini')
                old_label = b'PawPatch=0.3.0-beta.5'
                assert files[path].count(old_label) == 1
                files[path] = files[path].replace(old_label, b'PawPatch=' + VERSION.encode())
                assert {p for p in files if files[p] != original[p]} == {path}
            manifest = copy.deepcopy(self.audited[old['sha256'].upper()]['manifest'])
            assert not manifest.get('remove')
            manifest['version'] = version
            manifest['files'] = [dict(path=p, size=len(b), sha256=base.sha_bytes(b)) for p, b in sorted(files.items(), key=lambda item: item[0].lower())]
            blob = base.zip_bytes(manifest, files)
            assert blob == base.zip_bytes(manifest, files)
            archive = self.out / 'assets' / (id + '-' + version + '.zip')
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_bytes(blob)
            package = copy.deepcopy(old)
            package.update(version=version, size=len(blob), sha256=base.sha_bytes(blob), urls=[base.DOWNLOADS + TAG + '/' + archive.name])
            self.register_asset(package, TAG, archive)
            self.audit_archive(package)
            assert self.payload(package) == files
            updates[id] = package
            scope.append(dict(id=id, sourceSha256=old['sha256'], sha256=package['sha256'],
                              added={p: base.sha_bytes(b) for p, b in files.items() if p not in original},
                              changed={p: dict(before=base.sha_bytes(original[p]), after=base.sha_bytes(b)) for p, b in files.items() if p in original and original[p] != b}))
        entry = base.release_entry('release-' + TAG + '.md', VERSION, self.args.published_at[:10], 'arcane-wars', 'beta')
        feeds = {}
        for schema in base.SCHEMAS:
            before = self.baselines[schema + '/beta']
            feed = copy.deepcopy(before)
            for package in feed['packages']:
                if package['id'] in updates:
                    assert package['sha256'] == source[package['id']]['sha256']
                    for field in ('version', 'size', 'sha256', 'urls'):
                        package[field] = copy.deepcopy(updates[package['id']][field])
            feed['changelog'] = [entry] + before['changelog']
            feed['publishedAt'] = self.args.published_at
            self.sign(feed, schema, 'beta', 'production')
            assert {k: v for k, v in feed.items() if k not in ('packages', 'changelog', 'publishedAt')} == {k: v for k, v in before.items() if k not in ('packages', 'changelog', 'publishedAt')}
            assert [p for p in feed['packages'] if p['id'] not in updates] == [p for p in before['packages'] if p['id'] not in updates]
            feeds[schema] = feed
        history = base.read(base.REPO / 'feed/changelog.history.json')
        assert history['beta'] == self.baselines['v2/beta']['changelog']
        history['beta'] = feeds['v2']['changelog']
        base.write(self.out / 'changelog.history.json', history)
        notes = base.REPO / 'docs' / ('release-' + TAG + '.md')
        base.write(self.out / 'release-plan.json', dict(tag=TAG, version=VERSION, prerelease=True, launcherIncluded=False, assets=self.assets[TAG], notes=str(notes), notesSha256=base.sha(notes)))
        base.write(self.out / 'scope.json', scope)
        base.write(self.out / 'preparation.json', dict(before=self.before_hashes, historyBefore=base.sha(base.REPO / 'feed/changelog.history.json'), scope=scope,
            auditedSourcePackages=len(source), overriddenBaseFiles=overlaps,
            unchanged=['stable feeds', 'launcher', 'Vanilla', 'Immortals', 'game requirements', 'all other packages', 'all helper executables'],
            published=False, sourceScriptSha256=base.sha(Path(__file__))))
        assert all(base.sha(self.source_path(*key.split('/'))) == digest for key, digest in self.before_hashes.items())
        print('BETA 6 PREPARED: two packages; 22 animations; beta catalogs only.', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('out', 'dotnet', 'signing-dir'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--cache', type=Path, action='append', default=[])
    parser.add_argument('--published-at', required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    args.out.mkdir(parents=True)
    Preparation(args).prepare()
