"""Reuse the verified runtime-only release pipeline for first-desync diagnostics.
Stable, other mods, launcher, gameplay data and the AI payload stay unchanged.
"""
import argparse
from pathlib import Path
import PrepareDesyncBeta4 as release

release.VERSION = '0.4.0-beta.5'
release.BASELINE_VERSION = '0.4.0-beta.4'
release.TAG = 'patch-' + release.VERSION
release.URL = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/' + release.TAG + '/'

def checks(stage):
    report = release.read(stage / 'beta-helpers/sync-diagnostics/result.json')
    assert report['passed'] and report['relocations'] == 3
    assert release.read(stage / 'beta-helpers/sync-diagnostics/hardware.json')['passed']
    native = release.sha(stage / 'beta-helpers/ai-native/ai-policy.bin')
    assert native == '55B7237E31DBC2CE643AEC8190EDF546C88F6853D888C80D4AF7C8E777483236'
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
        assert release.read(a.stage / 'startup-verification.json')['passed']
    {'prepare': release.prepare, 'public': release.public, 'promote': release.promote}[a.action](a)
