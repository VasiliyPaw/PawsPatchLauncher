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
VERSION = '0.3.0-beta.8-test.5'


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
        version = VERSION if ident != 'common-ui' else '1.3.72-ui.7-beta.8-test.5'
        if ident.startswith('localization-'):
            version = package['version']+'-city-test.5'
        package.update(build(a.out, package, version, files))
    assert len(changed) == 7
    feed['patchGuide']['version'] = VERSION
    for entry in feed['patchGuide']['entries']:
        if entry.get('id') == 'city-assistant':
            entry['bodyRu'] = "Встроено в Paw's Patch для беты Arcane Wars при любых сочетаниях остальных компонентов. В F1: автоулучшение, пороги дохода четырёх ресурсов, запас золота и настройка ополчения над автоулучшением. Кнопка «Правила» удалена. Enter применяет число; Esc или клик вне поля отменяет ввод.\n\nПосле последнего доступного улучшения центра города постройки и улучшения сравниваются по приросту дохода золота с учётом расходов на дефицит ресурсов и всей очереди. Если прибыльных действий нет, выполняются цели по ресурсам, затем случайное доступное развитие. Рынки улучшаются только по ветке с наибольшим приростом золота; без такой ветки не улучшаются. Рынки всех рас можно строить и улучшать даже с усилением дефицита ресурсов, если приказ повышает доход золота. Другие постройки сохраняют защиту ресурсов. Запас золота не расходуется.\n\nУчитывается вся ручная и автоматическая очередь, включая ожидающие постройки и улучшения. Будущий доход учитывается при выборе цели, но не считается уже полученным. Отправленные приказы должны быть обработаны игрой до следующего расхода. Независимые рудники тоже участвуют в улучшениях.\n\nНастройки автоулучшения сохраняются локально для каждой партии и связанных с ней сейвов. Новая партия: автоулучшение включено, запас золота 2000, пороги дохода 0. Через сетевую передачу сейва настройки других игроков пока не переносятся.\n\nНастройка ополчения сохраняется между партиями. Она применяется к стартовому городу, новым и захваченным городам, а также новым городским зданиям с ополчением после постройки. Ручные изменения уже обработанных зданий сохраняются. При загрузке готовые здания не перенастраиваются."
            entry['bodyEn'] = "Built into Paw's Patch for Arcane Wars Beta with every combination of the other components. F1 provides auto-upgrade, four resource-income targets, a gold reserve and the militia option above auto-upgrade. The Rules button is removed. Enter applies a number; Esc or clicking outside cancels editing.\n\nAfter the final city-center upgrade, construction and upgrades are compared by gold income gain after resource shortage costs and all queued effects. Resource targets and random eligible development follow when no profitable action is available. Markets use only the branch with the greatest positive gold increase; without one, they are never upgraded. Markets of every race may be built and upgraded even if they deepen resource deficits, provided the order increases gold income. Other buildings retain resource protection. The gold reserve is protected.\n\nAll manual and automatic queued work is counted, including waiting construction and upgrades. Future income guides priorities but is not treated as already available. Sent orders must be processed by the game before another expense. Independent mines also participate in upgrades.\n\nAuto-upgrade settings are stored locally per match and its associated saves. New matches start with auto-upgrade on, a gold reserve of 2000 and zero income targets. Network save transfer does not yet carry other players' settings.\n\nThe militia preference persists across matches. It applies to starting, new and captured cities, and newly completed city buildings with militia. Manual changes to previously handled buildings are preserved. Completed buildings are not reconfigured when a save is loaded."
    feed['changelog'].insert(0, dict(category='patch', mod='arcane-wars', channel='beta', version=VERSION,
        publishedAt='2026-09-15', title={'ru':'Автоулучшение городов — локальный тест', 'en':'City automation — local test'},
        body={'ru':'Автоулучшение сравнивает прирост дохода золота после расходов на дефицит ресурсов и с учётом очереди. Рынки улучшаются только по лучшей золотой ветке. Запас золота и проверки строительства сохранены.',
              'en':'City automation compares actual gold income gains after resource shortage costs and queued work. Markets use only their best gold-increasing upgrade. Gold reserve and construction guards remain in effect.'}))
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
