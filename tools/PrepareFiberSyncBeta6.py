"""Stage the strategic-fiber fix through the existing signed runtime pipeline.

Validation is offline by explicit user request. This does not launch or install
the game, and does not substitute old startup evidence for a new network match.
"""
import argparse
from pathlib import Path
import PrepareDesyncBeta4 as release

release.VERSION = '0.4.0-beta.6'
release.BASELINE_VERSION = '0.4.0-beta.5'
release.AI_POLICY_REVISION = 37
release.TAG = 'patch-' + release.VERSION
release.URL = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/' + release.TAG + '/'

def checks(stage):
    native = stage / 'beta-helpers/ai-native'
    report = release.read(native / 'fiber-sync.json')
    assert report['passed'] and report['checks'] >= 1160 and report['relocationBases'] == 3
    assert report['historicalFailureReproduced'] and report['originalYieldAndSynchronizer']
    assert report['originalStrategicScheduler'] and not report['gameLaunched']
    assert report['nativeSha256'] == release.sha(native / 'ai-policy.bin')
    sync = release.read(stage / 'beta-helpers/sync-diagnostics/result.json')
    assert sync['passed'] and sync['relocations'] == 3
    assert release.read(stage / 'beta-helpers/sync-diagnostics/hardware.json')['passed']
    for name in release.VARIANTS:
        f = release.feature(stage / 'beta-helpers' / name)
        assert f.get('syncDiagnosticsRevision', 0) == (1 if f['bypass'] else 0)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--signing-dir', type=Path)
    p.add_argument('--action', choices=['prepare', 'public', 'promote'], default='prepare')
    a = p.parse_args()
    checks(a.stage)
    if a.action == 'promote':
        verification = release.read(a.stage / 'offline-verification.json')
        assert verification['passed'] and not verification['gameLaunched']
        assert verification['launcherTestsPassed'] and verification['multiplayerAcceptance'] == 'pending-user-test'
    {'prepare': release.prepare, 'public': release.public, 'promote': release.promote}[a.action](a)
