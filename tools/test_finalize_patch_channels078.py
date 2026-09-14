"""Offline guards and transformations; never stage/promote a production feed."""
import argparse
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import FinalizePatchChannels078 as final

parser = argparse.ArgumentParser(description=__doc__)
for name in ('candidate', 'dotnet', 'signing-dir', 'report'):
    parser.add_argument('--' + name, required=True, type=Path)
ARGS = parser.parse_args()
SOURCE = ARGS.candidate.resolve()
BEFORE_CANDIDATE = final.snapshot_tree(SOURCE)
BEFORE_CANONICAL = {p: (final.REPO / p).read_bytes() for p in (*final.FEEDS.values(), *final.ANCILLARY, final.EMBEDDED)}


class Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='paws-finalizer-guards-')
        cls.scratch = Path(cls.temp.name)
        cls.args = SimpleNamespace(candidate=SOURCE, out=cls.scratch / 'unused-staging', source_commit='a' * 40,
                                   launcher_artifact=cls.scratch / 'absent-artifact.json', launcher_exe=cls.scratch / 'absent.exe',
                                   dotnet=ARGS.dotnet, signing_dir=ARGS.signing_dir, published_at='2026-09-14T00:00:00Z',
                                   verify_public=False, promote=False)
        cls.task = final.Finalization(cls.args)
        cls.task.validate_candidate()
        cls.title, cls.body = final.parse_notes((final.REPO / 'docs/release-0.7.8.md').read_bytes())
        cls.launcher = dict(version='0.7.8', size=123, sha256='B' * 64, urls=[final.DOWNLOAD + 'v0.7.8/PawsPatchLauncher.exe'])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_candidate_verified_without_output(self):
        self.assertEqual(len(self.task.feeds), 4)
        self.assertEqual(sum(len(r['assets']) for r in self.task.plan['releases']), 7)
        self.assertFalse(self.args.out.exists())

    def test_existing_output_rejected(self):
        args = copy.copy(self.args)
        args.out = self.scratch
        with self.assertRaisesRegex(RuntimeError, 'new output'):
            final.Finalization(args)

    def test_candidate_descendant_output_rejected(self):
        args = copy.copy(self.args)
        args.out = SOURCE / 'must-not-be-created'
        with self.assertRaisesRegex(RuntimeError, 'new output'):
            final.Finalization(args)

    def test_canonical_descendant_output_rejected(self):
        args = copy.copy(self.args)
        args.out = final.REPO / 'feed/must-not-be-created'
        with self.assertRaisesRegex(RuntimeError, 'new output'):
            final.Finalization(args)

    def test_commit_format_rejected(self):
        args = copy.copy(self.args)
        args.source_commit = 'main'
        with self.assertRaisesRegex(RuntimeError, 'full SHA'):
            final.Finalization(args)

    def test_promotion_requires_flag_before_network_or_writes(self):
        with patch.object(final, 'fetch', side_effect=AssertionError('Unexpected public request')):
            with self.assertRaisesRegex(RuntimeError, 'explicit request'):
                self.task.promote()

    def test_promotion_requires_complete_public_evidence(self):
        with patch.object(self.task.args, 'promote', True), patch.object(self.task, 'public_report', [{}] * 9):
            with self.assertRaisesRegex(RuntimeError, 'all public checks'):
                self.task.promote()

    def test_all_four_transformations_preserve_patch_fields(self):
        allowed = {'launcher', 'publishedAt', 'changelog', 'newsTitle', 'newsBody'}
        for name, source in self.task.feeds.items():
            with self.subTest(feed=name):
                untouched = copy.deepcopy(source)
                result = final.finalized_feed(source, self.launcher, self.title, self.body, self.args.published_at)
                self.assertEqual({k: v for k, v in result.items() if k not in allowed}, {k: v for k, v in source.items() if k not in allowed})
                self.assertEqual(result['changelog'][1:], source['changelog'])
                self.assertEqual(result['changelog'][0]['category'], 'launcher')
                self.assertEqual(result['newsBody'], self.body)
                result['packages'][0]['version'] = 'TEST-ONLY'
                self.assertEqual(source, untouched)

    def test_duplicate_launcher_history_rejected(self):
        source = copy.deepcopy(self.task.feeds['v2/beta'])
        source['changelog'].insert(0, {'category': 'launcher', 'version': '0.7.8'})
        with self.assertRaisesRegex(RuntimeError, 'already contains'):
            final.finalized_feed(source, self.launcher, self.title, self.body, self.args.published_at)

    def test_wrong_launcher_generation_rejected(self):
        source = copy.deepcopy(self.task.feeds['legacy/stable'])
        source['launcher']['version'] = '0.7.8'
        with self.assertRaisesRegex(RuntimeError, 'generation'):
            final.finalized_feed(source, self.launcher, self.title, self.body, self.args.published_at)

    def test_notes_are_bilingual_and_strip_only_section_wrappers(self):
        self.assertEqual(self.title, {'ru': "Paw's Launcher 0.7.8", 'en': "Paw's Launcher 0.7.8"})
        self.assertIn('Нажмите', self.body['ru'])
        self.assertIn('Click', self.body['en'])
        self.assertNotIn('# English', self.body['en'])
        self.assertFalse(self.body['ru'].endswith('---'))
        for malformed in (b'# Wrong\nRU\n# English\nEN', b"# Paw's Launcher 0.7.8\nNo English section"):
            with self.assertRaises(RuntimeError):
                final.parse_notes(malformed)

    def test_normalization_does_not_relax_envelope_contents(self):
        self.assertEqual(final.normalized(b'{\r\n"signature":"ABC"\r\n}'), b'{\n"signature":"ABC"\n}')
        self.assertNotEqual(final.normalized(b'{"signature":"ABC"}'), final.normalized(b'{"signature":"DEF"}'))

    def test_concurrent_canonical_change_rejected_before_signature_reads(self):
        fake_repo = self.scratch / 'concurrent-repo'
        (fake_repo / 'feed').mkdir(parents=True)
        (fake_repo / 'feed/stable.json').write_bytes(b'changed')
        task = final.Finalization.__new__(final.Finalization)
        task.candidate = SOURCE
        with patch.object(final, 'REPO', fake_repo), patch.object(task, 'signed', side_effect=AssertionError('Too late')):
            with self.assertRaisesRegex(RuntimeError, 'Canonical feed moved'):
                task.validate_candidate()

    def test_invalid_signed_envelope_rejected(self):
        path = self.scratch / 'invalid.signed.json'
        value = final.read(SOURCE / 'feeds/v2/beta.production.signed.json')
        value['signature'] = 'AAAA'
        path.write_bytes(final.encode(value))
        with self.assertRaisesRegex(RuntimeError, 'Validation command failed'):
            self.task.signed(path)

    def test_public_annotated_tag_resolves_to_commit(self):
        release = dict(tag_name='v0.7.8', draft=False, prerelease=False, assets=[])
        responses = [release, {'object': {'type': 'tag', 'sha': 'b' * 40}}, {'object': {'type': 'commit', 'sha': 'a' * 40}}]
        with patch.object(final, 'fetch', side_effect=[final.encode(r) for r in responses]):
            self.assertEqual(final.public_release('v0.7.8', 'a' * 40, False), {})

    def test_public_wrong_source_or_release_flags_rejected(self):
        release = dict(tag_name='v0.7.8', draft=False, prerelease=False, assets=[])
        with patch.object(final, 'fetch', side_effect=[final.encode(release), final.encode({'object': {'type': 'commit', 'sha': 'b' * 40}})]):
            with self.assertRaisesRegex(RuntimeError, 'another commit'):
                final.public_release('v0.7.8', 'a' * 40, False)
        for field in ('draft', 'prerelease'):
            changed = dict(release, **{field: True})
            with patch.object(final, 'fetch', return_value=final.encode(changed)):
                with self.assertRaisesRegex(RuntimeError, 'release state'):
                    final.public_release('v0.7.8', 'a' * 40, False)

    def test_public_asset_metadata_cannot_redirect_download(self):
        identity = dict(name='x.zip', size=3, sha256=final.digest(b'abc'))
        asset = dict(name='x.zip', size=3, browser_download_url='https://example.invalid/x.zip')
        with patch.object(final, 'fetch', side_effect=AssertionError('Unexpected download')):
            with self.assertRaisesRegex(RuntimeError, 'metadata differs'):
                final.public_asset({'x.zip': asset}, 'patch-0.1.1', identity)

    def test_public_download_checks_actual_size_and_digest(self):
        identity = dict(size=3, sha256=final.digest(b'abc'))
        for data, passed in ((b'abc', True), (b'abd', False), (b'abcd', False), (b'ab', False)):
            with patch.object(final.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                if passed:
                    self.assertEqual(final.fetch('https://example.invalid/test', identity)['sha256'], identity['sha256'])
                else:
                    with self.assertRaises(RuntimeError):
                        final.fetch('https://example.invalid/test', identity)

    def test_package_payload_digest_and_extra_files_checked(self):
        for mode in ('valid', 'bad-payload-digest', 'unlisted'):
            path = self.scratch / (mode + '.zip')
            module = dict(id='fixture', version='1', files=[dict(path='data/a.txt', size=3, sha256=final.digest(b'abc' if mode != 'bad-payload-digest' else b'xyz'))])
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('module.json', final.encode(module))
                archive.writestr('payload/data/a.txt', b'abc')
                if mode == 'unlisted':
                    archive.writestr('unexpected.txt', b'abc')
            identity = dict(packageId='fixture', version='1', size=path.stat().st_size, sha256=final.sha(path))
            if mode == 'valid':
                final.audit_package(path, identity)
            else:
                with self.assertRaises(RuntimeError):
                    final.audit_package(path, identity)

    def test_package_traversal_paths_rejected(self):
        for name in ('../x', '/x', 'C:/x', 'a//b', 'a/./b', 'a\\..\\b'):
            with self.assertRaises(RuntimeError):
                final.safe_member(name)

    def fixture_transaction(self, name):
        # Synthetic files only. No production feed or public request is used.
        repo = self.scratch / name
        (repo / 'feed').mkdir(parents=True)
        task = final.Finalization.__new__(final.Finalization)
        task.args = SimpleNamespace(promote=True)
        task.public_report = [{}] * 10
        task.unchanged_public_feeds = lambda: None
        task.unchanged = lambda: None
        task.before = {'feed/stable.json': b'old-stable', 'feed/beta.json': b'old-beta'}
        task.targets = {'feed/stable.json': b'new-stable', 'feed/beta.json': b'new-beta'}
        task.report = {'rollbackDirectory': str(repo / 'feed/history/fixture-backup')}
        for name, data in task.before.items():
            (repo / name).write_bytes(data)
        return repo, task

    def test_fixture_partial_replace_restores_owned_files(self):
        repo, task = self.fixture_transaction('rollback-fixture')
        real_replace = final.os.replace
        def fail_second(source, target):
            if Path(target).name == 'beta.json':
                raise OSError('Injected replacement failure')
            return real_replace(source, target)
        with patch.object(final, 'REPO', repo), patch.object(final.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'Injected'):
                task.promote()
        self.assertEqual((repo / 'feed/stable.json').read_bytes(), b'old-stable')
        self.assertEqual((repo / 'feed/beta.json').read_bytes(), b'old-beta')
        self.assertEqual((repo / 'feed/history/fixture-backup/stable.json').read_bytes(), b'old-stable')

    def test_fixture_rollback_retains_another_writers_bytes(self):
        repo, task = self.fixture_transaction('concurrent-rollback-fixture')
        real_replace = final.os.replace
        def fail_after_concurrent_change(source, target):
            if Path(target).name == 'beta.json':
                (repo / 'feed/stable.json').write_bytes(b'concurrent-writer')
                raise OSError('Injected concurrent writer')
            return real_replace(source, target)
        with patch.object(final, 'REPO', repo), patch.object(final.os, 'replace', side_effect=fail_after_concurrent_change):
            with self.assertRaisesRegex(RuntimeError, 'changed concurrently'):
                task.promote()
        self.assertEqual((repo / 'feed/stable.json').read_bytes(), b'concurrent-writer')
        self.assertEqual((repo / 'feed/beta.json').read_bytes(), b'old-beta')
        self.assertEqual((repo / 'feed/history/fixture-backup/stable.json').read_bytes(), b'old-stable')

    def test_fixture_existing_rollback_directory_is_never_overwritten(self):
        repo, task = self.fixture_transaction('existing-rollback-fixture')
        backup = Path(task.report['rollbackDirectory'])
        backup.mkdir(parents=True)
        (backup / 'sentinel').write_bytes(b'prior-evidence')
        with patch.object(final, 'REPO', repo):
            with self.assertRaisesRegex(RuntimeError, 'Never overwrite'):
                task.promote()
        self.assertEqual((backup / 'sentinel').read_bytes(), b'prior-evidence')
        self.assertEqual((repo / 'feed/stable.json').read_bytes(), b'old-stable')


result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Guards))
final.require(final.snapshot_tree(SOURCE) == BEFORE_CANDIDATE, 'Audit changed the candidate')
final.require(all((final.REPO / path).read_bytes() == data for path, data in BEFORE_CANONICAL.items()), 'Audit changed canonical files')
report = dict(passed=result.wasSuccessful(), tests=result.testsRun, signedCanonicalFeedsVerified=4,
              signedPreviousFeedsVerified=4, signedCandidateFeedsVerified=4, candidateArchivesVerified=7,
              candidateUnchanged=True, canonicalUnchanged=True, networkUsed=False, promoted=False,
              fullFinalizationExecuted=False, limitation='Full finalization awaits the verified CI launcher 0.7.8 artifact and committed release source.')
final.write_new(ARGS.report.resolve(), final.encode(report))
raise SystemExit(0 if result.wasSuccessful() else 1)
