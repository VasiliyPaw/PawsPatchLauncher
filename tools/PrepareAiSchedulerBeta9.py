"""Publish the verified AI scheduler fix through the runtime-only beta pipeline."""
import argparse
from pathlib import Path
import PrepareDesyncBeta4 as release
from PrepareFiberSyncBeta6 import checks as retained_checks

release.VERSION = '0.4.0-beta.9'
release.BASELINE_VERSION = '0.4.0-beta.8'
release.AI_POLICY_REVISION = 39
release.RELEASE_DATE = '2026-09-27'
release.TAG = 'patch-' + release.VERSION
release.URL = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/' + release.TAG + '/'


def checks(stage):
    retained_checks(stage)
    report = release.read(stage / 'offline-verification.json')
    assert report['passed'] and not report['gameLaunched']
    assert report['launcherTestsPassed'] and report['helperSelfTests'] == 40
    assert report['aiNativeSuitesPassed'] == 30
    assert report['nativeInstallationTransactionChecks'] == 66568
    queue = release.read(stage / 'beta-helpers/ai-native/strategic-queue.json')
    assert queue['passed'] and queue['checks'] >= 127643
    live = release.read(stage / 'live-review/report.json')
    assert live['passed'] and live['readOnly'] and not live['gameRestarted']
    assert live['runtime']['revision'] == 39 and live['runtime']['hooks'] == 63
    assert len(live['players']) == 4
    for p in live['players']:
        assert p['strategic'][1] > p['strategic'][0]
        assert p['tactical'][1] > p['tactical'][0]
    for path, digest in report['sourceSha256'].items():
        assert release.sha(release.REPO / path) == digest, 'Tested source changed: ' + path
    for name, digest in report['helperSha256'].items():
        assert release.sha(stage / 'beta-helpers' / name) == digest, 'Tested helper changed: ' + name


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--signing-dir', type=Path)
    p.add_argument('--action', choices=['prepare', 'public', 'promote'], default='prepare')
    a = p.parse_args()
    checks(a.stage)
    if a.action == 'promote':
        assert release.read(a.stage / 'scheduler-package-verification.json')['passed']
    {'prepare': release.prepare, 'public': release.public, 'promote': release.promote}[a.action](a)
