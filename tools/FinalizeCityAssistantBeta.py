"""Verify public immutable Beta assets; optionally advertise the signed feed.

No credential access or release upload. Stable bytes and launcher metadata are
invariants. Canonical files change only after every public asset is verified.
"""
import argparse
import hashlib
import io
import json
import shutil
import urllib.request
import zipfile
import PrepareCityAssistantBeta as candidate

parser = argparse.ArgumentParser()
parser.add_argument('commit', help='Published source commit for the immutable patch tag')
parser.add_argument('--promote', action='store_true')
args = parser.parse_args()
repo, out = candidate.REPO, candidate.OUT
api = 'https://api.github.com/repos/VasiliyPaw/PawsPatchLauncher'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'PawsPatchReleaseAudit', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


release = json.loads(fetch(api + '/releases/tags/' + candidate.TAG))
assert release['prerelease'] and not release['draft'] and release['tag_name'] == candidate.TAG
tag = json.loads(fetch(api + '/git/ref/tags/' + candidate.TAG))['object']
for _ in range(4):
    if tag['type'] != 'tag':
        break
    tag = json.loads(fetch(api + '/git/tags/' + tag['sha']))['object']
assert tag['type'] == 'commit' and tag['sha'] == args.commit, 'Wrong immutable tag revision'
assert json.loads(fetch(api + '/releases/latest'))['tag_name'] == 'v0.6.3', 'Launcher latest unexpectedly changed'
prepared = json.loads((out / 'preparation.json').read_bytes())
old = {channel: candidate.base.read_feed(out / ('previous-' + channel + '.signed.json')) for channel in ('stable', 'beta')}
beta = candidate.base.read_feed(out / 'feed/beta.production.signed.json')
assert beta['launcher'] == old['beta']['launcher'] and beta['game'] == old['beta']['game']
assert [p for p in beta['packages'] if p['id'] not in candidate.VERSIONS] == [p for p in old['beta']['packages'] if p['id'] not in candidate.VERSIONS]
assets = {a['name']: a for a in release['assets']}
for package in (p for p in beta['packages'] if p['id'] in candidate.VERSIONS):
    assert package['version'] == candidate.VERSIONS[package['id']]
    url = package['urls'][0]
    name = url.rsplit('/', 1)[-1]
    assert url == assets[name]['browser_download_url']
    data = fetch(url)
    assert len(data) == package['size'] and hashlib.sha256(data).hexdigest().upper() == package['sha256'].upper()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        module = json.loads(archive.read('module.json'))
        assert module['id'] == package['id'] and module['version'] == package['version']
        entries = {name.replace('\\', '/').lower(): name for name in archive.namelist()}
        for file in module['files']:
            body = archive.read(entries['payload/' + file['path'].replace('\\', '/').lower()])
            assert len(body) == file['size'] and hashlib.sha256(body).hexdigest().upper() == file['sha256'].upper()
    print('PUBLIC ASSET PASS', name, len(data), flush=True)

assert candidate.base.sha(repo / 'feed/stable.json') == prepared['old_feed_hashes']['stable']
assert candidate.base.sha(repo / 'feed/beta.json') == prepared['old_feed_hashes']['beta'], 'Canonical Beta moved since preparation'
history = json.loads((out / 'changelog.history.json').read_bytes())
current_history = json.loads((repo / 'feed/changelog.history.json').read_bytes())
assert history['stable'] == current_history['stable']
assert history['beta'][1:] == current_history['beta'] and history['beta'][0]['version'] == candidate.VERSION
guide = json.loads((out / 'patch-guide-beta.json').read_bytes())
assert guide == beta['patchGuide'] and history['beta'] == beta['changelog']
target = repo / 'feed/history/beta-before-city-beta1.json'
assert not target.exists(), 'Refuse to overwrite a rollback feed'
if args.promote:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out / 'previous-beta.signed.json', target)
    shutil.copyfile(out / 'feed/beta.production.signed.json', repo / 'feed/beta.json')
    shutil.copyfile(out / 'changelog.history.json', repo / 'feed/changelog.history.json')
    shutil.copyfile(out / 'patch-guide-beta.json', repo / 'feed/patch-guide-beta.json')
    assert candidate.base.sha(repo / 'feed/stable.json') == prepared['old_feed_hashes']['stable']
    assert candidate.base.read_feed(repo / 'feed/beta.json') == beta
    print('CANONICAL BETA PROMOTED LOCALLY; commit/push and public feed verification remain.')
else:
    print('PUBLIC BETA VERIFIED; canonical feeds unchanged.')
