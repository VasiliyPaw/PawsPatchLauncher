"""Publish the accepted observer guard and recruitment control-group bindings."""
import argparse
from pathlib import Path
import PrepareDesyncBeta4 as release

release.VERSION = '0.4.0-beta.10'
release.BASELINE_VERSION = '0.4.0-beta.9'
release.AI_POLICY_REVISION = 39
release.RELEASE_DATE = '2026-09-29'
release.TAG = 'patch-' + release.VERSION
release.URL = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/' + release.TAG + '/'
release.EXTRA_CACHE_ROOTS = (release.WORK / 'outputs/release-20260927-beta9',
                             release.WORK / 'outputs/launcher-0811')
HOTKEY_PATHS = {root + '/Localization/Hotkeys/hotkeys_favorites.txt'
               for root in ('data', 'Local_base_ru', 'Local_ru')}


def checks(stage):
    report = release.read(stage / 'offline-verification.json')
    assert report['passed'] and report['nativeCases'] == 537
    assert report['transactionChecks'] == 817 and report['windowsProbeChecks'] == 52
    assert report['helperSelfTests'] == 40 and report['userAccepted']
    for path, digest in report['sourceSha256'].items():
        assert release.sha(release.REPO / path) == digest, 'Tested source changed: ' + path
    for path, digest in report['artifactSha256'].items():
        assert release.sha(stage / path) == digest, 'Tested artifact changed: ' + path
    for name in release.VARIANTS:
        f = release.feature(stage / 'beta-helpers' / name)
        assert f['observerTeamCommandGuardRevision'] == 1
        assert f['patchVersion'] == release.VERSION
        assert '--local-data-check'.encode('utf-16le') not in (stage / 'beta-helpers' / name).read_bytes()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--signing-dir', type=Path)
    parser.add_argument('--action', choices=['prepare', 'public', 'promote'], default='prepare')
    args = parser.parse_args()
    checks(args.stage)

    def transform(package, payload):
        # Common UI is present for every patched Arcane variant and wins over
        # language packages. Local_ru is the last mounted Russian hotkey layer.
        if package['id'] != 'common-ui':
            return set()
        for path in HOTKEY_PATHS:
            payload[path] = (args.stage / 'hotkeys' / path).read_bytes()
        return HOTKEY_PATHS

    release.extra_payload_transform = transform
    release.extra_payload_paths = lambda p: HOTKEY_PATHS if p['id'] == 'common-ui' else set()
    if args.action == 'promote':
        assert release.read(args.stage / 'input-package-verification.json')['passed']
    {'prepare': release.prepare, 'public': release.public, 'promote': release.promote}[args.action](args)


if __name__ == '__main__':
    main()
