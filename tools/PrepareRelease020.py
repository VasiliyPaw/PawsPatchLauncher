"""Prepare/promote verified Beta 7 data, independent helpers and seven badge models.

Offline staging only. `prepare` builds/signs game candidates; `finalize` adds a built
launcher. Publication and canonical feed advertisement are separate explicit steps.
"""
import copy
import json
from pathlib import Path
import shutil
import sys
import zipfile
from datetime import datetime, timezone
import PrepareBeta7Release as base

REPO = base.REPO
OUT = REPO / 'release_workspace_020'
VERSIONS = {'pawpatch-core': '0.2.0', 'common-ui': '1.3.72-ui.3', 'player-colors': '0.2.0'}
TAG = 'patch-0.2.0'
ORGANIZATIONS = ('Monster', 'Nationalist', 'Council', 'Royalist', 'Ceyah', 'Fallen', 'Default')
PATCH = {'category': 'patch', 'version': '0.2.0', 'publishedAt': '2026-09-07',
    'title': {'ru': 'Возможности беты теперь в Релизе', 'en': 'Beta features graduate to Release'},
    'body': {
        'ru': 'В Релиз перенесены случайный тип карты и время суток с сохранением настроек, исправление стартового рассинхрона и общие исправления интерфейса. Доступны 49 цветов с синхронизацией лобби, проверкой занятых цветов при подключении и отображением цветов сохранения. Все переключатели независимы: цвета работают с выключенной враждой независимых и с любым режимом контроля рассинхрона. Добавлены все 7 моделей значков рот и согласованное мягкое затенение, в том числе без расширенных цветов. Служебное окно перед запуском не появляется. Beta сейчас содержит тот же набор игровых файлов. Для мультиплеера обновите лаунчер и патч на всех компьютерах; игровые настройки должны совпадать.',
        'en': 'Release now includes persistent random map type and time of day, the identified startup desync fix and common UI fixes. Includes 49 colors with lobby synchronization, occupied-color checks on reconnect and saved-game colors. All switches are independent: colors work with independent hostility disabled and with either desync mode. All 7 company badge models and consistent soft shading are included, even without extended colors. No helper window opens before launch. Beta currently uses the same gameplay files. Update the launcher and patch on every multiplayer PC; gameplay settings must match.'}}
LAUNCHER = {'category': 'launcher', 'version': '0.5.8', 'publishedAt': '2026-09-07',
    'title': {'ru': 'Независимые настройки Релиза', 'en': 'Independent Release settings'},
    'body': {
        'ru': 'Расширенные цвета доступны в Релизе. В новых пакетах цвета, вражда независимых и пропуск рассинхрона переключаются независимо. Код конфигурации и импорт поддерживают все сочетания. «О патче» обновлено для Релиза 0.2.0, включая все 7 моделей затенения значков; во вкладке беты поясняется, что отдельных новых функций пока нет. Для закреплённых старых выпусков сохраняются ограничения реально отсутствующих файлов запуска.',
        'en': 'Extended colors are available in Release. New packages allow independent color, independent-hostility and desync-bypass switches. Friend codes and import support every combination. About is updated for Release 0.2.0, including all seven badge shading models; Beta explains that no exclusive features remain. Pinned old releases keep restrictions for launch helpers they actually lack.'}}


def cached(package):
    for url in package['urls']:
        candidate = OUT / 'packages' / url.replace('\\', '/').split('/')[-1]
        if candidate.is_file() and base.sha(candidate) == package['sha256'].upper(): return candidate
        candidate = REPO / 'release_workspace_beta7_v2/packages' / url.replace('\\', '/').split('/')[-1]
        if candidate.is_file() and base.sha(candidate) == package['sha256'].upper(): return candidate
    return base.cached(package)


def unpack(package, source, exclude=()):
    archive_path = cached(package)
    assert archive_path.stat().st_size == package['size']
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read('module.json'))
        assert manifest['id'] == package['id'] and manifest['version'] == package['version']
        entries = {n.replace('\\', '/').lower(): n for n in archive.namelist()}
        for file in manifest['files']:
            name = file['path'].replace('\\', '/')
            data = archive.read(entries['payload/' + name.lower()])
            assert len(data) == file['size'] and base.hashlib.sha256(data).hexdigest().upper() == file['sha256'].upper()
            if name.lower() in exclude: continue
            target = (source / name).resolve()
            assert target.is_relative_to(source.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        if manifest.get('remove'):
            (source / '.pawpatch-remove.txt').write_text('\n'.join(manifest['remove']), encoding='utf-8')


def sign(feed, name, folder=None):
    folder = folder or OUT / 'feed'
    payload = folder / (name + '.payload.json')
    signed = folder / (name + '.signed.json')
    payload.write_text(json.dumps(feed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    base.run(base.DOTNET, base.PUBLISHER, 'sign', payload, base.KEYS / 'pawpatch-signing-private.pem', 'pawpatch-prod-2026', signed)
    assert base.read_feed(signed) == feed


def prepare():
    assert not (OUT / 'sources').exists(), 'Preserve previous package preparation.'
    for name in ('sources', 'packages', 'feed'): (OUT / name).mkdir(parents=True, exist_ok=True)
    old = {name: base.read_feed(REPO / 'feed' / (name + '.json')) for name in ('stable', 'beta')}
    packages = {p['id']: copy.deepcopy(p) for p in old['beta']['packages']}
    badge_paths = {f'data/organizations/banners/{o}/{o}playercolor.tga'.lower() for o in ORGANIZATIONS}
    for module in VERSIONS:
        unpack(packages[module], OUT / 'sources' / module, badge_paths if module == 'player-colors' else ())
    variants = json.loads((REPO / 'game/beta7/variants.json').read_bytes())
    evidence = []
    for name, defines in variants.items():
        helper = OUT / 'helpers' / name
        assert helper.is_file()
        # These modes never launch or attach to the game.
        for mode in ('--quiet-startup-self-test', '--common-ui-self-test', '--lobby-payload-test', '--features'):
            base.run(helper, mode)
        shutil.copyfile(helper, OUT / 'sources' / ('player-colors' if 'lobby_colors' in name else 'common-ui') / name)
        evidence.append({'name': name, 'defines': defines, 'sha256': base.sha(helper)})
    common = OUT / 'sources/common-ui'
    shutil.copyfile(REPO / 'game/beta7/paws_patch_versions.ini', common / 'paws_patch_versions.ini')
    badge_root = REPO / 'game/release-assets'
    assets = list(badge_root.rglob('*.NIF')) + list(badge_root.rglob('*.tga'))
    assert len(assets) == 14
    badge_evidence = []
    for asset in assets:
        rel = asset.relative_to(badge_root)
        target = common / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(asset, target)
        badge_evidence.append({'path': str(rel), 'sha256': base.sha(asset), 'size': asset.stat().st_size})
    for module, version in VERSIONS.items():
        archive = OUT / 'packages' / f'{module}-{version}.zip'
        base.run(base.DOTNET, base.PUBLISHER, 'pack', module, version, OUT / 'sources' / module, archive)
        packages[module].update(version=version, size=archive.stat().st_size, sha256=base.sha(archive),
            urls=[f'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/{TAG}/{archive.name}'])
    for package in packages.values(): package['experimental'] = False
    packages['common-ui']['description'] = {'ru': 'Обязательные исправления игры, случайные карты и время суток, 7 моделей значков с мягким затенением.',
        'en': 'Required game fixes, random maps and time of day, 7 badge models with soft shading.'}
    packages['player-colors']['description'] = {'ru': '49 цветов игроков. Работает с любым сочетанием остальных настроек текущего Релиза.',
        'en': '49 player colors. Works with any combination of other current Release settings.'}
    history = json.loads((REPO / 'feed/changelog.history.json').read_bytes())
    guide = json.loads((OUT / 'patch-guide.json').read_bytes())
    assert guide['version'] == '0.2.0' and not any(e['category'] == 'beta' for e in guide['entries'])
    for name in ('stable', 'beta'):
        feed = copy.deepcopy(old[name])
        feed.update(packages=list(packages.values()), colorDesyncContinue=True, independentColorHostility=True,
            patchGuide=guide, publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        history[name] = [PATCH] + history[name]
        feed.update(changelog=history[name], newsTitle=PATCH['title'], newsBody=PATCH['body'])
        feed['previousReleases'] = [{'label': ('Release' if name == 'stable' else 'Beta 7') + ' before 0.2.0',
            'url': f'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/history/{name}-before-release020.json'}] + feed.get('previousReleases', [])
        sign(feed, name + '.production')
        local = copy.deepcopy(feed)
        for package in local['packages']: package['urls'] = [str(cached(package))]
        sign(local, name + '.local')
        shutil.copyfile(REPO / 'feed' / (name + '.json'), OUT / ('previous-' + name + '.signed.json'))
    (OUT / 'changelog.history.json').write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'preparation.json').write_text(json.dumps({'published': False, 'variants': evidence, 'badges': badge_evidence,
        'old_feed_hashes': {n: base.sha(REPO / 'feed' / (n + '.json')) for n in old}}, indent=2) + '\n')
    print('PREPARED 0.2.0: 8 helpers, 7 NIF + 7 TGA, same game packages on both channels. Not uploaded.')


def finalize():
    publication = OUT / 'publication'
    assert not publication.exists(), 'Preserve existing publication.'
    assets = publication / 'assets'; assets.mkdir(parents=True)
    launcher = OUT / 'launcher/win-x64/PawsPatchLauncher.exe'
    shutil.copyfile(launcher, assets / launcher.name)
    with zipfile.ZipFile(assets / 'PawsPatchLauncher-v0.5.8-win-x64.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(launcher, launcher.name)
        archive.write(launcher.parent / 'launcher.config.json', 'launcher.config.json')
    prep = json.loads((OUT / 'preparation.json').read_bytes())
    history = json.loads((OUT / 'changelog.history.json').read_bytes())
    for name in ('stable', 'beta'):
        assert base.sha(REPO / 'feed' / (name + '.json')) == prep['old_feed_hashes'][name]
        feed = base.read_feed(OUT / 'feed' / (name + '.production.signed.json'))
        feed['launcher'] = {'version': '0.5.8', 'size': launcher.stat().st_size, 'sha256': base.sha(launcher),
            'urls': ['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v0.5.8/PawsPatchLauncher.exe']}
        history[name] = [LAUNCHER] + history[name]
        feed['changelog'] = history[name]
        sign(feed, name, publication)
    (publication / 'changelog.history.json').write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('FINAL CANDIDATE: Patch 0.2.0 + Launcher 0.5.8. Nothing uploaded or advertised.')


if __name__ == '__main__':
    {'prepare': prepare, 'finalize': finalize}[sys.argv[1]]()
