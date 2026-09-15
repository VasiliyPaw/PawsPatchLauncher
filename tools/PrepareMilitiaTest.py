"""Extend the current local 48-color beta with city development and party preferences.

Only stages signed local files; no installation, launch or publication.
"""
import argparse, base64, copy, json, re
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from PrepareRelease081 import verify
from PrepareSplitLanguages import read, write, encoded, build, dec
from PrepareEuropeanModLanguages import source
from GameTextValidation import validate_engine_text

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.3.0-beta.8-test.3'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('base', 'out', 'helpers', 'cache', 'signing-dir'):
        parser.add_argument('--'+arg, type=Path, required=True)
    a = parser.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    config = read(a.base/'launcher.config.json')
    public = serialization.load_pem_public_key(config['publicKeyPem'].encode())
    private = serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(), password=None)
    before = verify(read(a.base/'beta.json'), public)
    assert before['playerColorCount'] == 48
    feed = copy.deepcopy(before)
    catalog = read(ROOT/'game/localization/mod-cs-uk.json')['entries']
    changed = {}
    for package in feed['packages']:
        ident = package['id']
        if ident not in ('pawpatch-core', 'common-ui', 'player-colors',
                         'localization-de', 'localization-fr', 'localization-cs', 'localization-uk'):
            continue
        original = source(package, a.cache)
        files = dict(original)
        for path, raw in original.items():
            replacement = a.helpers/path
            if replacement.is_file():
                files[path] = replacement.read_bytes()
            elif ident.startswith('localization-') and path.lower().endswith('/paw_city_policy.tgi'):
                code = ident.rsplit('-', 1)[1]
                text = dec(raw)
                for key in ('paw_city_new_militia', 'paw_city_new_militia_tip', 'paw_city_auto_tip'):
                    value = catalog[key][code]
                    validate_engine_text(catalog[key]['en'], value)
                    text, count = re.subn(r'(?m)(^\s*'+key+r'\s*=\s*)"(?:\\.|[^"\\])*"',
                                         lambda match: match[1]+json.dumps(value, ensure_ascii=False), text)
                    assert count == 1, (ident, path, key)
                files[path] = text.encode('utf-16')
        changed[ident] = [path for path in files if files[path] != original[path]]
        assert changed[ident], ident
        assert all(path.endswith('.exe') or path.endswith('paws_patch_versions.ini') or
                   path.endswith(('paw_city_ru.tgi', 'paw_city_en.tgi', 'paw_city_policy.tgi'))
                   for path in changed[ident]), changed[ident]
        version = VERSION if ident != 'common-ui' else '1.3.72-ui.7-beta.8-test.3'
        if ident.startswith('localization-'):
            version = package['version']+'-city-test.3'
        package.update(build(a.out, package, version, files))
    assert len(changed) == 7
    feed['patchGuide']['version'] = VERSION
    feed['changelog'].insert(0, dict(category='patch', mod='arcane-wars', channel='beta', version=VERSION,
        publishedAt='2026-09-15', title={'ru':'Автоулучшение городов — локальный тест', 'en':'City automation — local test'},
        body={'ru':'Удалена кнопка «Правила» из F1. Настройки автоулучшения сохраняются локально для каждой партии и её сейвов; новые партии начинаются со стандартных значений. Последнее улучшение центра города имеет высший приоритет. Если повысить нужный доход ресурсов нельзя, развивается экономика, затем доступные случайные постройки.',
              'en':'Removed the Rules button from F1. Auto-upgrade settings are saved locally per match and its saves; new matches use defaults. The final city center upgrade has highest priority. When needed resource income cannot be raised, automation improves the economy, then chooses random eligible buildings.'}))
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
    print('LOCAL_MILITIA_FEED_PASS; 7 changed packages; stable and remaining packages unchanged')


if __name__ == '__main__':
    main()
