"""Stage the mandatory city-assistant Beta. No upload or canonical feed change.

Build first with game/beta7/build.ps1 -CityAssistant. Existing signed packages
are verified before unpacking; stable and launcher metadata are kept unchanged.
"""
import copy
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import PrepareBeta7Release as base
import PrepareRelease020 as previous
import BuildPowersShardsSources as powers

REPO = base.REPO
OUT = REPO / 'release_workspace_city_beta1_v2'
VERSION = '0.3.0-beta.1'
TAG = 'patch-' + VERSION
VERSIONS = {'pawpatch-core': VERSION, 'common-ui': '1.3.72-ui.4-beta.1', 'player-colors': VERSION,
            'powers-shards-original': '1.3.72-powers.2-beta.1'}
ENTRY = {
    'category': 'patch', 'version': VERSION, 'publishedAt': '2026-09-08',
    'title': {'ru': 'Автоулучшение городов и предупреждение о рассинхроне',
              'en': 'Automatic city upgrades and desync notification'},
    'body': {
        'ru': 'Автоулучшение городов встроено в бету и работает со всеми компонентами. Управление находится в F1: галочка, резерв золота и состояние очереди. Сначала устраняются дефициты ресурсов, затем повышается доход золота, затем выбирается другое доступное улучшение. Города обслуживаются по очереди с учётом стоимости, резерва и ручных приказов. Enter применяет введённый резерв, Esc и щелчок вне поля отменяют ввод; кнопки меняют его на 100. При новой партии и загрузке сохранения автоулучшение включено, резерв равен 2000; в сейв эти параметры пока не записываются. При включённом игнорировании рассинхронов предупреждение появляется в игровом чате со штатным звуком ошибки не чаще раза в 5 минут. Это предупреждение, а не исправление самого рассинхрона. Для мультиплеера обновите бету у всех участников. Релиз 0.2.0 и лаунчер 0.6.3 не изменены.',
        'en': 'Automatic city upgrades are built into Beta and work with every component combination. F1 contains the toggle, gold reserve and queue status. Resource deficits take priority, followed by gold income and then another legal upgrade. Cities are processed fairly with affordability, the reserve and manual orders respected. Enter applies the typed reserve; Esc or clicking outside cancels editing; buttons adjust it by 100. New matches and loaded saves start with automation enabled and a 2000 reserve; these preferences are not yet stored in saves. With Ignore desyncs enabled, a native chat warning and game error sound play at most once every 5 minutes. This warns about desyncs; it does not fix them. Update Beta on every multiplayer PC. Release 0.2.0 and launcher 0.6.3 are unchanged.'}}


def cached(package):
    name = package['urls'][0].replace('\\', '/').split('/')[-1]
    folders = ('release_workspace_city_beta1_v2/packages', 'release_workspace_city_beta1/packages', 'release_workspace_059/components-v2/packages',
               'release_workspace_020/packages', 'release_workspace_beta7_v2/packages', 'packages',
               'release_workspace_20260905/packages', 'release_workspace_056/powers-shards/packages',
               'release_workspace_056/combination-fix/packages', 'release_workspace_056/publication/assets')
    for folder in folders:
        candidate = REPO / folder / name
        if candidate.is_file() and candidate.stat().st_size == package['size'] and base.sha(candidate) == package['sha256'].upper():
            return candidate
    raise FileNotFoundError('No verified archive: ' + name)


def helper_output(exe, mode):
    process = subprocess.run([str(exe), mode], capture_output=True, cwd=exe.parent,
                             creationflags=subprocess.CREATE_NO_WINDOW, timeout=30, check=True)
    return process.stdout.decode('utf-8').strip()


def main():
    assert not (OUT / 'sources').exists(), 'Preserve the previous candidate.'
    for folder in ('sources', 'packages', 'feed'):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    old = {name: base.read_feed(REPO / 'feed' / (name + '.json')) for name in ('stable', 'beta')}
    beta = copy.deepcopy(old['beta'])
    packages = {p['id']: p for p in beta['packages']}
    # Use the validated unpacker, including any explicit removal manifest.
    previous.cached = cached
    for module in VERSIONS:
        previous.unpack(packages[module], OUT / 'sources' / module)
    resources = 'Game/resources.tgi'
    repaired = powers.restore(resources, (powers.ORIGINAL / resources).read_bytes(),
                              (OUT / 'sources/pawpatch-core/data' / resources).read_bytes())
    (OUT / 'sources/powers-shards-original/data' / resources).write_bytes(repaired)
    evidence = []
    variants = json.loads((REPO / 'game/beta7/variants.json').read_bytes())
    for name, defines in variants.items():
        exe = OUT / 'helpers' / name
        features = json.loads(helper_output(exe, '--features'))
        assert features['cityAssistant'] and features['commonFixes'] and features['quiet']
        assert features['colors'] == ('PAW_COLORS' in defines)
        assert features['bypass'] == ('SYNC_CONTINUE' in defines)
        assert features['hostility'] == ('HERD_RELATIONS_ONLY' in defines)
        tests = {mode: helper_output(exe, mode) for mode in
                 ('--quiet-startup-self-test', '--common-ui-self-test', '--lobby-payload-test', '--assistant-self-test')}
        target = OUT / 'sources' / ('player-colors' if 'lobby_colors' in name else 'common-ui') / name
        shutil.copyfile(exe, target)
        evidence.append({'name': name, 'sha256': base.sha(exe), 'features': features, 'tests': tests})
    common = OUT / 'sources/common-ui'
    for language in ('en', 'ru'):
        relative = Path('data/UI/Game/paw_city_' + language + '.tgi')
        target = common / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OUT / 'helpers' / relative, target)
    version_text = (REPO / 'game/beta7/paws_patch_versions.ini').read_text(encoding='utf-8')
    assert version_text.count('PawPatch=0.2.0') == 1
    (common / 'paws_patch_versions.ini').write_text(version_text.replace('PawPatch=0.2.0', 'PawPatch=' + VERSION), encoding='utf-8')
    for module, version in VERSIONS.items():
        archive = OUT / 'packages' / f'{module}-{version}.zip'
        assert not archive.exists()
        base.run(base.DOTNET, base.PUBLISHER, 'pack', module, version, OUT / 'sources' / module, archive)
        packages[module].update(version=version, size=archive.stat().st_size, sha256=base.sha(archive), experimental=True,
            urls=[f'https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/{TAG}/{archive.name}'])
    assert packages['common-ui']['required'] and packages['pawpatch-core']['required']
    packages['common-ui']['description'] = {
        'ru': 'Обязательные исправления игры и встроенное автоулучшение городов в F1. Доступно при любых настройках беты.',
        'en': 'Required game fixes and built-in automatic city upgrades in F1. Available with every Beta configuration.'}
    packages['player-colors']['description'] = {
        'ru': '49 цветов игроков. Сохраняет встроенное автоулучшение при любом сочетании настроек беты.',
        'en': '49 player colors. Preserves built-in city upgrades with every Beta setting combination.'}
    ENTRY['body']['ru'] += ' Исправлен запуск с возвращёнными Powers и Shards: ресурс Shards теперь регистрируется вне комментария и соответствует порядку статистики.'
    ENTRY['body']['en'] += ' Fixed startup with restored Powers and Shards: the Shards resource is now registered outside the comment and matches scoring order.'
    guide = copy.deepcopy(beta['patchGuide'])
    guide['version'] = VERSION
    guide['entries'].insert(0, {'id': 'city-assistant', 'category': 'beta',
        'titleRu': ENTRY['title']['ru'], 'titleEn': ENTRY['title']['en'],
        'bodyRu': ENTRY['body']['ru'], 'bodyEn': ENTRY['body']['en']})
    history = json.loads((REPO / 'feed/changelog.history.json').read_bytes())
    assert not any(e['category'] == 'patch' and e['version'] == VERSION for e in history['beta'])
    history['beta'].insert(0, ENTRY)
    beta.update(patchGuide=guide, changelog=history['beta'], newsTitle=ENTRY['title'], newsBody=ENTRY['body'],
                publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    beta['previousReleases'].insert(0, {'label': 'Beta before ' + VERSION,
        'url': 'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/history/beta-before-city-beta1.json'})
    assert beta['launcher'] == old['beta']['launcher'] and beta['game'] == old['beta']['game']
    assert [p for p in beta['packages'] if p['id'] not in VERSIONS] == [p for p in old['beta']['packages'] if p['id'] not in VERSIONS]
    assert len(beta['packages']) == len(old['beta']['packages']), 'The assistant is not an optional component.'
    previous.sign(beta, 'beta.production', OUT / 'feed')
    for name, feed in (('stable', old['stable']), ('beta', beta)):
        local = copy.deepcopy(feed)
        for package in local['packages']:
            package['urls'] = [str(cached(package))]
        previous.sign(local, name + '.local', OUT / 'feed')
        shutil.copyfile(REPO / 'feed' / (name + '.json'), OUT / ('previous-' + name + '.signed.json'))
    (OUT / 'patch-guide-beta.json').write_text(json.dumps(guide, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'changelog.history.json').write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'preparation.json').write_text(json.dumps({'published': False, 'version': VERSION, 'variants': evidence,
        'old_feed_hashes': {name: base.sha(REPO / 'feed' / (name + '.json')) for name in old}}, indent=2) + '\n')
    print('PREPARED', VERSION, ': 8 mandatory assistant variants; 4 changed packages; stable/launcher unchanged. Nothing uploaded.')


if __name__ == '__main__':
    main()
