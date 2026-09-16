"""Stage the local saved-owner fix on top of the accepted test.9 feed."""
import argparse
import base64
import copy
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from PrepareRelease081 import verify
from PrepareSplitLanguages import read, write, encoded, build
from PrepareEuropeanModLanguages import source

VERSION = '0.3.0-beta.8-test.10'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('base', 'out', 'helpers', 'cache', 'signing-dir'):
        p.add_argument('--'+arg, type=Path, required=True)
    a = p.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    config = read(a.base/'launcher.config.json')
    public = serialization.load_pem_public_key(config['publicKeyPem'].encode())
    private = serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(), password=None)
    before = verify(read(a.base/'beta.json'), public)
    assert before['patchGuide']['version'] == '0.3.0-beta.8-test.9'
    feed = copy.deepcopy(before)
    changed = {}
    for package in feed['packages']:
        ident = package['id']
        if ident not in ('pawpatch-core', 'common-ui', 'player-colors'):
            continue
        original = source(package, a.cache)
        files = dict(original)
        for path in files:
            if path.endswith('.exe') or path == 'paws_patch_versions.ini':
                replacement = a.helpers/path
                if replacement.is_file():
                    files[path] = replacement.read_bytes()
        changed[ident] = [path for path in files if files[path] != original[path]]
        assert changed[ident] and all(path.endswith('.exe') or path == 'paws_patch_versions.ini' for path in changed[ident])
        version = VERSION if ident != 'common-ui' else '1.3.72-ui.7-beta.8-test.10'
        package.update(build(a.out, package, version, files))
    assert len(changed) == 3
    feed['patchGuide']['version'] = VERSION
    feed['changelog'].insert(0, dict(category='patch', mod='arcane-wars', channel='beta', version=VERSION, publishedAt='2026-09-16',
        title={'ru':'Сохранение владельцев при загрузке', 'en':'Preserve saved ownership'},
        body={'ru':'При загрузке сохранения владельцы объектов остаются такими, как записаны в сейве. Распределение независимых по королевствам в загруженной партии отключено, в том числе для старых сохранений. Новые партии сохраняют прежние правила.',
              'en':'Loading preserves the exact saved owners. Independent family reassignment is disabled throughout loaded games, including old saves. Fresh matches retain the existing rules.'}))
    payload = encoded(feed)
    r, s = utils.decode_dss_signature(private.sign(payload, ec.ECDSA(hashes.SHA256())))
    signed = dict(keyId='pawpatch-prod-2026', payload=base64.b64encode(payload).decode(),
                  signature=base64.b64encode(r.to_bytes(32, 'big')+s.to_bytes(32, 'big')).decode())
    assert verify(signed, public) == feed
    write(a.out/'beta.json', signed)
    write(a.out/'beta.payload.json', feed)
    (a.out/'stable.json').write_bytes((a.base/'stable.json').read_bytes())
    config.update(feedUrls=[str(a.out/'stable.json')], betaFeedUrls=[str(a.out/'beta.json')])
    write(a.out/'launcher.config.json', config)
    assert [p for p in before['packages'] if p['id'] not in changed] == [p for p in feed['packages'] if p['id'] not in changed]
    write(a.out/'scope.json', dict(localOnly=True, published=False, changedFiles=changed))
    print('LOCAL_SAVED_OWNERS_FEED_PASS; 3 packages; stable, localization and gameplay data unchanged')

if __name__ == '__main__':
    main()
