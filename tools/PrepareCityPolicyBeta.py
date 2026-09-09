"""Prepare Beta 2 packages and signed candidates; never upload or promote.

Stable gameplay and launcher metadata stay unchanged. Only the shared About
guide is refreshed in Stable, so switching channels never shows older help.
"""
import copy
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import PrepareCityAssistantBeta as prior
import PrepareBeta7Release as base
import PrepareRelease020 as pack

REPO = base.REPO
OUT = REPO / 'release_workspace_city_beta2_v2'
HELPERS = OUT / 'helpers-final-r2'
VERSION = '0.3.0-beta.2'
TAG = 'patch-' + VERSION
VERSIONS = {'pawpatch-core': VERSION, 'common-ui': '1.3.72-ui.4-beta.2', 'player-colors': VERSION}
ENTRY = {
    'category': 'patch', 'version': VERSION, 'publishedAt': '2026-09-09',
    'title': {'ru': 'Умное автоулучшение городов и быстрая передача сейвов',
              'en': 'Advanced city upgrades and faster save transfers'},
    'body': {
        'ru': 'Расширенное автоулучшение городов и ускоренная штатная передача сохранений в сетевом лобби встроены в бету при любых настройках компонентов. В F1 под галочками расположены четыре поля порогов дохода с иконками камня, дерева, железа и кристаллов. Enter применяет значение, Esc или щелчок вне поля отменяет ввод. Резерв золота задаётся отдельно. Автоулучшение не снижает доход ресурса ниже порога и не усугубляет существующий дефицит. Если безопасно устранить нехватку сейчас невозможно, другие города могут повышать доход золота. Города строятся параллельно: учитываются уже начатые и ручные постройки; осада блокирует только осаждённый город. В отдельном окне доступны правила строительства, ветки улучшений и исключения городов. Выбираются выгодные золотые ветки рынков, если хватает ресурсов. Сохранения в лобби передаются штатным протоколом, без дружбы и ручного принятия: используется проверенный вариант R2 с ограниченными пакетами. Для мультиплеера обновите бету у всех участников. Формат сейвов не меняется; новая партия и загрузка начинают с включённым автоулучшением и резервом 2000. Пороги ресурсов и общие правила сохраняются на этом компьютере, исключения городов сбрасываются. Релиз 0.2.0 и лаунчер 0.6.4 не обновляются.',
        'en': 'Advanced city upgrades and faster native saved-game transfers in multiplayer lobbies are built into Beta with every component configuration. F1 has four income-target fields with stone, wood, iron and mana icons beneath the checkboxes. Enter applies a value; Esc or clicking outside cancels editing. The gold reserve is separate. Automation never lowers resource income below its target or worsens an existing shortage. If no safe remedy is currently available, other cities can still grow gold income. Cities build in parallel, accounting for active and manual construction; a siege only excludes its own city. A separate settings window offers construction rules, exact upgrade branches and city exceptions. Profitable market conversion branches are chosen when resource targets permit. Lobby saves use the native protocol with no friendship or manual acceptance required, using the tested bounded R2 tuning. All multiplayer participants must update Beta. Save format is unchanged; new matches and loaded saves start with automation on and a 2000 reserve. Resource targets and general rules persist locally; city exceptions reset. Release 0.2.0 and launcher 0.6.4 are not updated.'}}


def cached(package):
    candidate = OUT / 'packages' / package['urls'][0].replace('\\', '/').rsplit('/', 1)[-1]
    if candidate.is_file() and candidate.stat().st_size == package['size'] and base.sha(candidate) == package['sha256'].upper():
        return candidate
    return prior.cached(package)


def guide_update(original):
    guide = copy.deepcopy(original)
    guide['version'] = VERSION
    city = next(e for e in guide['entries'] if e['id'] == 'city-assistant')
    city.update(titleRu='Автоулучшение городов', titleEn='Automatic city upgrades',
        bodyRu='Встроено в бету и доступно при любых настройках компонентов. В F1 находятся галочка автоулучшения, четыре порога дохода ресурсов с иконками и отдельный резерв золота. Enter применяет ввод; Esc или щелчок вне поля отменяет его. В окне «Настройки» доступны правила постройки, ветки улучшений и исключения городов.\n\nСначала устраняются нехватки ресурсов, затем повышается доход золота без снижения дохода ресурсов ниже порога. Если безопасно устранить нехватку сейчас невозможно, разрешён рост золота в других городах. Учитываются уже строящиеся здания и ручные приказы; города строятся параллельно, осада одного не блокирует остальные. Рынки выбирают выгодную золотую ветку только при достаточном доходе ресурсов.\n\nПри новой партии и загрузке автоулучшение включено, резерв — 2000. Пороги ресурсов и общие правила сохраняются на компьютере, исключения городов сбрасываются; формат сейвов не меняется. Галочка в самой игре отключает автоматические приказы, но компонент патча не отключается в лаунчере. При включённом игнорировании рассинхронов штатное сообщение со звуком предупреждает не чаще раза в 5 минут; это не исправление рассинхрона.',
        bodyEn='Built into Beta and available with every component configuration. F1 contains the automation checkbox, four resource-income targets with icons, and a separate gold reserve. Enter applies editing; Esc or clicking outside cancels it. Settings offers construction rules, upgrade branches and city exceptions.\n\nResource shortages take priority, then gold growth without dropping resource income below targets. If no safe remedy is currently available, other cities may still grow gold income. Active construction and manual orders are accounted for; cities build in parallel, and one siege does not block other cities. Markets use profitable gold conversion branches only when resource income permits.\n\nNew matches and loaded saves start with automation on and a 2000 reserve. Resource targets and general rules persist on this PC; city exceptions reset and the save format is unchanged. The in-game checkbox stops automatic orders, but the patch feature cannot be removed in the launcher. When desync bypass is enabled, a native message and error sound warn at most once every 5 minutes; this does not repair desyncs.')
    assert not any(e['id'] == 'fast-save-transfer' for e in guide['entries'])
    guide['entries'].insert(1, {'id': 'fast-save-transfer', 'category': 'beta',
        'titleRu': 'Быстрая передача сохранений в игре', 'titleEn': 'Faster in-game save transfers',
        'bodyRu': 'Всегда включена в бете, независимо от остальных компонентов. Когда хост выбирает сохранение в сетевом лобби, игра сама передаёт его участникам, у которых оно отсутствует или отличается. Добавлять игроков в друзья и принимать файл в лаунчере не нужно.\n\nИспользуется проверенный вариант R2: ограничение 1200 байт на файловую часть пакета и до 16 пакетов участнику за проход отправки. Штатные подтверждения, повторы, размер блоков и формат сейва сохраняются. В проверке ПК → виртуалка файл 1,6 МБ передался примерно за 9 секунд; реальная скорость зависит от сети. Все участники должны обновить бету и использовать совместимые игровые настройки.',
        'bodyEn': 'Always enabled in Beta, independently of other components. When the host selects a save in a multiplayer lobby, the game transfers it to participants who lack it or have a different copy. No friendship or launcher acceptance is needed.\n\nUses the tested R2 tuning: a 1200-byte file-stage ceiling and at most 16 packets per participant per send pass. Native acknowledgements, retries, block sizes and save format remain unchanged. A PC-to-VM test transferred a 1.6 MB file in about 9 seconds; actual speed depends on the network. All participants should update Beta and use compatible gameplay settings.'})
    return guide


def main():
    assert not (OUT / 'sources').exists(), 'Preserve previous package candidates.'
    for name in ('sources', 'packages', 'feed'):
        (OUT / name).mkdir(parents=True, exist_ok=True)
    old = {n: base.read_feed(REPO / f'feed/{n}.json') for n in ('stable', 'beta')}
    current = copy.deepcopy(old)
    beta = current['beta']
    packages = {p['id']: p for p in beta['packages']}
    pack.cached = cached
    for module in VERSIONS:
        pack.unpack(packages[module], OUT / 'sources' / module)
    variants = json.loads((REPO / 'game/beta7/variants.json').read_bytes())
    evidence = []
    for name, defines in variants.items():
        exe = HELPERS / name
        features = json.loads(prior.helper_output(exe, '--features'))
        assert all(features[n] for n in ('cityAssistant', 'advancedCityPolicy', 'fastSaveTransfer', 'commonFixes', 'quiet'))
        for feature, flag in (('colors', 'PAW_COLORS'), ('bypass', 'SYNC_CONTINUE'), ('hostility', 'HERD_RELATIONS_ONLY')):
            assert features[feature] == (flag in defines)
        modes = ('--quiet-startup-self-test', '--common-ui-self-test', '--lobby-payload-test', '--assistant-self-test', '--fast-transfer-self-test')
        tests = {m: prior.helper_output(exe, m) for m in modes}
        target = OUT / 'sources' / ('player-colors' if 'lobby_colors' in name else 'common-ui') / name
        shutil.copyfile(exe, target)
        evidence.append({'name': name, 'sha256': base.sha(exe), 'features': features, 'tests': tests})
    common = OUT / 'sources/common-ui'
    for path in ('data/UI/Game/paw_city_en.tgi', 'data/UI/Game/paw_city_ru.tgi',
                 'data/Localization/paw_city_policy.tgi', 'Local_ru/Localization/paw_city_policy.tgi'):
        target = common / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HELPERS / path, target)
    versions = (common / 'paws_patch_versions.ini').read_text(encoding='utf-8')
    assert versions.count('PawPatch=0.3.0-beta.1') == 1
    (common / 'paws_patch_versions.ini').write_text(versions.replace('PawPatch=0.3.0-beta.1', 'PawPatch=' + VERSION), encoding='utf-8')
    for module, version in VERSIONS.items():
        archive = OUT / 'packages' / f'{module}-{version}.zip'
        base.run(base.DOTNET, base.PUBLISHER, 'pack', module, version, OUT / 'sources' / module, archive)
        packages[module].update(version=version, size=archive.stat().st_size, sha256=base.sha(archive), experimental=True,
            urls=[f'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/{TAG}/{archive.name}'])
    packages['common-ui']['description'] = {'ru': 'Обязательные исправления, расширенное автоулучшение городов и ускоренная передача сейвов. Всегда включено в бете.',
        'en': 'Required fixes, advanced city upgrades and faster save transfers. Always enabled in Beta.'}
    packages['player-colors']['description'] = {'ru': '49 цветов игроков. Сохраняет все встроенные функции беты при любых остальных настройках.',
        'en': '49 player colors. Preserves every built-in Beta feature with all other settings.'}
    guide = guide_update(old['beta']['patchGuide'])
    history = json.loads((REPO / 'feed/changelog.history.json').read_bytes())
    assert not any(e['category'] == 'patch' and e['version'] == VERSION for e in history['beta'])
    history['beta'].insert(0, ENTRY)
    beta.update(changelog=history['beta'], newsTitle=ENTRY['title'], newsBody=ENTRY['body'])
    beta['previousReleases'].insert(0, {'label': 'Beta before ' + VERSION,
        'url': 'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/history/beta-before-city-beta2.json'})
    for name, feed in current.items():
        feed.update(patchGuide=guide, publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        assert feed['launcher'] == old[name]['launcher'] and feed['game'] == old[name]['game']
        pack.sign(feed, name + '.production', OUT / 'feed')
        local = copy.deepcopy(feed)
        for package in local['packages']:
            package['urls'] = [str(cached(package))]
        pack.sign(local, name + '.local', OUT / 'feed')
        shutil.copyfile(REPO / f'feed/{name}.json', OUT / f'previous-{name}.signed.json')
    assert current['stable']['packages'] == old['stable']['packages']
    assert len(beta['packages']) == len(old['beta']['packages'])
    assert packages['common-ui']['required'] and packages['pawpatch-core']['required']
    assert [p for p in beta['packages'] if p['id'] not in VERSIONS] == [p for p in old['beta']['packages'] if p['id'] not in VERSIONS]
    for name, value in (('patch-guide.json', guide), ('changelog.history.json', history), ('preparation.json', {
        'published': False, 'version': VERSION, 'variants': evidence,
        'old_feed_hashes': {n: base.sha(REPO / f'feed/{n}.json') for n in old}})):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PREPARED', VERSION, ': 8 built-in policy + R2 variants; 3 packages; no publication.')


if __name__ == '__main__':
    main()
