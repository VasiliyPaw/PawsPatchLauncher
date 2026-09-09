"""Verify immutable public Beta 2 assets before optional local feed promotion.

Does not retrieve credentials, upload files, commit or push. Refuses concurrent
feed changes. Stable gameplay/launcher stay unchanged; shared help is refreshed.
"""
import argparse
import hashlib
import io
import json
import re
import shutil
import urllib.request
import zipfile
import PrepareCityPolicyBeta as candidate

p = argparse.ArgumentParser()
p.add_argument('commit')
p.add_argument('--promote', action='store_true')
args = p.parse_args()
assert re.fullmatch('[0-9a-f]{40}', args.commit)
repo, out = candidate.REPO, candidate.OUT
api = 'https://api.github.com/repos/VasiliyPaw/PawsPatchLauncher'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'PawsPatchBetaAudit', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main():
    release = json.loads(fetch(api + '/releases/tags/' + candidate.TAG))
    assert release['prerelease'] and not release['draft']
    tag = json.loads(fetch(api + '/git/ref/tags/' + candidate.TAG))['object']
    for _ in range(4):
        if tag['type'] != 'tag':
            break
        tag = json.loads(fetch(api + '/git/tags/' + tag['sha']))['object']
    assert tag['type'] == 'commit' and tag['sha'] == args.commit
    assert json.loads(fetch(api + '/releases/latest'))['tag_name'] == 'v0.6.4'
    prepared = json.loads((out / 'preparation.json').read_bytes())
    old = {n: candidate.base.read_feed(out / f'previous-{n}.signed.json') for n in ('stable', 'beta')}
    feeds = {n: candidate.base.read_feed(out / f'feed/{n}.production.signed.json') for n in old}
    for name in old:
        assert feeds[name]['game'] == old[name]['game'] and feeds[name]['launcher'] == old[name]['launcher']
        assert candidate.base.sha(repo / f'feed/{name}.json') == prepared['old_feed_hashes'][name], 'Local feed moved'
        live = fetch(f'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/{name}.json')
        assert hashlib.sha256(live).hexdigest().upper() == prepared['old_feed_hashes'][name], 'Public feed moved'
    stable_unchanged = lambda f: {k: v for k, v in f.items() if k not in ('patchGuide', 'publishedAt')}
    assert stable_unchanged(feeds['stable']) == stable_unchanged(old['stable'])
    beta = feeds['beta']
    assert [v for v in beta['packages'] if v['id'] not in candidate.VERSIONS] == [v for v in old['beta']['packages'] if v['id'] not in candidate.VERSIONS]
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
            entries = {n.replace('\\', '/').lower(): n for n in archive.namelist()}
            for file in module['files']:
                body = archive.read(entries['payload/' + file['path'].replace('\\', '/').lower()])
                assert len(body) == file['size'] and hashlib.sha256(body).hexdigest().upper() == file['sha256'].upper()
        print('PUBLIC ASSET PASS', name, len(data), flush=True)
    history = json.loads((out / 'changelog.history.json').read_bytes())
    before_history = json.loads((repo / 'feed/changelog.history.json').read_bytes())
    guide = json.loads((out / 'patch-guide.json').read_bytes())
    assert history['stable'] == before_history['stable'] and history['beta'][1:] == before_history['beta']
    assert history['beta'][0]['version'] == candidate.VERSION and beta['changelog'] == history['beta']
    assert feeds['stable']['patchGuide'] == beta['patchGuide'] == guide
    backup = repo / 'feed/history/beta-before-city-beta2.json'
    assert not backup.exists(), 'Never overwrite rollback history'
    if args.promote:
        shutil.copyfile(out / 'previous-beta.signed.json', backup)
        for name in old:
            shutil.copyfile(out / f'feed/{name}.production.signed.json', repo / f'feed/{name}.json')
        shutil.copyfile(out / 'changelog.history.json', repo / 'feed/changelog.history.json')
        for name in ('patch-guide.json', 'patch-guide-beta.json'):
            shutil.copyfile(out / 'patch-guide.json', repo / 'feed' / name)
        assert candidate.base.read_feed(repo / 'feed/beta.json') == beta
        print('CANONICAL BETA 2 PROMOTED LOCALLY; public feed push/readback still required.')
    else:
        print('PUBLIC BETA 2 ASSETS VERIFIED; canonical feeds unchanged.')


if __name__ == '__main__':
    main()
