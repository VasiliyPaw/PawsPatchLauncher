"""Publish one authored guide to both current signed channels, without package changes.

Use an unused output directory. The default stages signed candidates and backups;
--apply also copies them to canonical feeds after verifying both candidates.
Pinned historical releases are intentionally preserved.
"""
import argparse
import copy
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import PrepareBeta7Release as base
import PrepareRelease020 as signing

parser = argparse.ArgumentParser()
parser.add_argument('output')
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
out = Path(args.output).resolve()
assert not out.exists(), 'Use a new staging directory; do not overwrite an earlier candidate.'
out.mkdir(parents=True)
guide = json.loads((base.REPO / 'feed/patch-guide.json').read_bytes())
assert guide['schemaVersion'] == 1 and 0 < len(guide['entries']) <= 100
assert len({e['id'] for e in guide['entries']}) == len(guide['entries'])
assert all(e['category'] in ('always', 'optional', 'beta') for e in guide['entries'])
old = {}
for channel in ('stable', 'beta'):
    original = base.REPO / 'feed' / (channel + '.json')
    old[channel] = original.read_bytes()
    shutil.copyfile(original, out / (channel + '.before.signed.json'))
    manifest = base.read_feed(original)
    updated = copy.deepcopy(manifest)
    updated['patchGuide'] = guide
    updated['publishedAt'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    assert {k: v for k, v in updated.items() if k not in ('patchGuide', 'publishedAt')} == {
        k: v for k, v in manifest.items() if k not in ('patchGuide', 'publishedAt')}
    signing.sign(updated, channel, out)
assert base.read_feed(out / 'stable.signed.json')['patchGuide'] == base.read_feed(out / 'beta.signed.json')['patchGuide'] == guide
if args.apply:
    # Check both before any canonical write; never replace a concurrent publication.
    assert all((base.REPO / 'feed' / (c + '.json')).read_bytes() == old[c] for c in old)
    for channel in old:
        shutil.copyfile(out / (channel + '.signed.json'), base.REPO / 'feed' / (channel + '.json'))
    # Retain this existing authoring path as an identical compatibility mirror.
    shutil.copyfile(base.REPO / 'feed/patch-guide.json', base.REPO / 'feed/patch-guide-beta.json')
    print('SHARED GUIDE APPLIED: both current channels; packages, launcher and historical feeds unchanged.')
else:
    print('SHARED GUIDE STAGED: both current channels; canonical feeds unchanged.')
