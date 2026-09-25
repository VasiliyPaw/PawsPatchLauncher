"""Verify public launcher 0.8.7 and sign its four launcher-only catalogs.

Uses the existing P1363 catalog signing process. Stage first, then promote;
no upload, Git push, package replacement or game installation is performed.
"""
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, key, sign, fetch, normalize
from PrepareRelease070 import read, write, sha, verify

REPO = Path(__file__).resolve().parents[1]
VERSION = '0.8.7'
TAG = 'v' + VERSION
API = 'https://api.github.com/repos/VasiliyPaw/PawsPatchLauncher'
RAW = 'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/'
DOWNLOAD = 'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/' + TAG + '/'
CHANGED = {'launcher', 'publishedAt', 'changelog', 'newsTitle', 'newsBody'}

def unchanged(before, after):
    assert {k:v for k,v in before.items() if k not in CHANGED} == {
        k:v for k,v in after.items() if k not in CHANGED}, 'Game/catalog data changed'

def public_release(commit):
    release = json.loads(fetch(API + '/releases/tags/' + TAG))
    assert not release['draft'] and not release['prerelease']
    assert json.loads(fetch(API + '/releases/latest'))['tag_name'] == TAG
    ref = json.loads(fetch(API + '/git/ref/tags/' + TAG))['object']
    while ref['type'] == 'tag':
        ref = json.loads(fetch(API + '/git/tags/' + ref['sha']))['object']
    assert ref['type'] == 'commit' and ref['sha'] == commit
    return {a['name']:a for a in release['assets']}

def stage(a):
    out = a.out.resolve()
    assert not out.exists(), 'Use a new staging directory'
    assets = public_release(a.source_commit)
    artifact = json.loads(fetch(DOWNLOAD + 'launcher-artifact.json'))
    assert artifact['version'] == VERSION and artifact['sourceCommit'] == a.source_commit
    if artifact['authenticodeRequired']:
        assert artifact['authenticodeStatus'] == 'Valid' and artifact['timestamped']
    else:
        assert a.allow_unsigned_launcher and artifact['authenticodeStatus'] == 'NotSigned', 'Acknowledge current unsigned EXE policy explicitly'
    out.mkdir(parents=True)
    write(out / 'launcher-artifact.json', artifact)
    for name in ('PawsPatchLauncher.exe', f'PawsPatchLauncher-{TAG}-win-x64.zip'):
        record = next(f for f in artifact['files'] if f['name'] == name)
        assert assets[name]['size'] == record['size']
        assert assets[name]['digest'].lower() == 'sha256:' + record['sha256'].lower()
        path = out / name
        path.write_bytes(fetch(DOWNLOAD + name))
        assert path.stat().st_size == record['size'] and sha(path) == record['sha256'].upper()
    with zipfile.ZipFile(out / f'PawsPatchLauncher-{TAG}-win-x64.zip') as archive:
        for record in artifact['files']:
            if record['name'].endswith('.zip'): continue
            data = archive.read(record['name'])
            assert len(data) == record['size'] and hashlib.sha256(data).hexdigest().upper() == record['sha256'].upper()
    entry = read(REPO / 'docs/release-0.8.7.json')
    assert entry['category'] == 'launcher' and entry['version'] == VERSION
    history = read(REPO / 'feed/changelog.history.json')
    record = next(f for f in artifact['files'] if f['name'] == 'PawsPatchLauncher.exe')
    launcher = dict(version=VERSION, size=record['size'], sha256=record['sha256'], urls=[DOWNLOAD + record['name']])
    private = serialization.load_pem_private_key(a.private_key.read_bytes(), password=None)
    assert private.public_key().public_numbers() == key().public_numbers()
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    baseline = {}
    for name, path in FEEDS.items():
        raw = (REPO / path).read_bytes()
        assert normalize(fetch(RAW + path + '?release087=stage')) == normalize(raw), 'Public feed moved: ' + path
        before = verify(read(REPO / path), key())
        assert before['launcher']['version'] == '0.8.6'
        assert not any(e['category'] == 'launcher' and e['version'] == VERSION for e in before['changelog'])
        final = copy.deepcopy(before)
        final.update(launcher=launcher, publishedAt=stamp, changelog=[entry] + before['changelog'], newsTitle=entry['title'], newsBody=entry['body'])
        unchanged(before, final)
        write(out / 'previous' / (name + '.json'), read(REPO / path))
        write(out / 'signed' / (name + '.json'), sign(final, private))
        baseline[path] = sha(REPO / path)
        if not name.startswith('legacy-'):
            # Older history-file entries differ from signed feed entries. Keep
            # each existing timeline intact in this launcher-only publication.
            assert not any(e['category'] == 'launcher' and e['version'] == VERSION for e in history[name])
            history[name] = [entry] + history[name]
    baseline['feed/changelog.history.json'] = sha(REPO / 'feed/changelog.history.json')
    write(out / 'changelog.history.json', history)
    write(out / 'plan.json', dict(sourceCommit=a.source_commit, baseline=baseline, notesSha256=sha(REPO / 'docs/release-0.8.7.json'), launcher=launcher))
    print('STAGED: public EXE/ZIP verified; 4 signed catalogs; all game packages and previous notes preserved')

def promote(a):
    out = a.out.resolve(); plan = read(out / 'plan.json')
    public_release(plan['sourceCommit'])
    assert sha(REPO / 'docs/release-0.8.7.json') == plan['notesSha256']
    for path, digest in plan['baseline'].items():
        assert sha(REPO / path) == digest, 'Local baseline moved: ' + path
        assert normalize(fetch(RAW + path + '?release087=promote')) == normalize((REPO / path).read_bytes()), 'Public baseline moved: ' + path
    for name, path in FEEDS.items():
        final = verify(read(out / 'signed' / (name + '.json')), key())
        unchanged(verify(read(REPO / path), key()), final)
        assert final['launcher'] == plan['launcher']
    for name, path in FEEDS.items(): shutil.copyfile(out / 'signed' / (name + '.json'), REPO / path)
    shutil.copyfile(out / 'changelog.history.json', REPO / 'feed/changelog.history.json')
    print('PROMOTED LOCALLY: commit/push and public readback still required')

def readback(a):
    out = a.out.resolve(); plan = read(out / 'plan.json')
    public_release(plan['sourceCommit'])
    # Pin the final repository commit to bypass stale main-branch CDN caches.
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    assert json.loads(fetch(API + '/git/ref/heads/main'))['object']['sha'] == head
    root = RAW.replace('/main/', '/' + head + '/')
    for name, path in FEEDS.items():
        public = verify(json.loads(fetch(root + path)), key())
        assert public == verify(read(REPO / path), key())
        assert public['launcher'] == plan['launcher']
        unchanged(verify(read(out / 'previous' / (name + '.json')), key()), public)
    assert json.loads(fetch(root + 'feed/changelog.history.json')) == read(REPO / 'feed/changelog.history.json')
    print('PUBLICATION PASS: v0.8.7; 4 signed catalogs; history; game data unchanged; catalog commit ' + head)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage', 'promote', 'readback'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-commit')
    parser.add_argument('--private-key', type=Path)
    parser.add_argument('--allow-unsigned-launcher', action='store_true')
    args = parser.parse_args()
    globals()[args.action](args)
