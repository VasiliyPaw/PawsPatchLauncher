"""Prepare two beta.7 packages and signed candidate feeds. No upload or game launch."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
WORK = REPO.parent
OUT = REPO / 'release_workspace_beta7_v2'
HELPERS = WORK / 'beta_game_1372/release-beta7'
DOTNET = Path(r'C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe')
PUBLISHER = REPO / 'tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll'
KEYS = REPO / '.local/signing'
TAG = 'beta.7'
VERSIONS = {'common-ui': '1.3.72-ui.2-beta.7', 'player-colors': '0.1.0-beta.7'}
ENTRY = {
    'category': 'patch', 'version': '0.1.0-beta.7', 'publishedAt': '2026-09-07',
    'title': {'ru': 'Случайные карты, время суток и сетевые цвета', 'en': 'Random maps, time of day and multiplayer colors'},
    'body': {
        'ru': 'Добавлен случайный выбор типа карты и времени суток с сохранением настроек. Исправлена найденная причина стартового рассинхрона после повторных матчей. Хост меняет цвета всех игроков, клиент только свой. Цвета сохраняются при возврате в лобби и повторном подключении; занятый цвет возвращающегося игрока заменяется на «Случайно». В лобби сохранения отображаются цвета королевств из сейва без возможности изменения. Расширенные цвета можно сочетать с пропуском рассинхрона в лаунчере 0.5.7. Служебное окно перед запуском больше не появляется. Для сетевой игры обновите бету на всех компьютерах. Игровые пакеты Релиза не изменены.',
        'en': 'Adds random map type and time of day with persistent settings. Fixes the identified startup desync cause after repeated matches. Hosts can change all player colors, clients only their own. Colors survive lobby returns and reconnects; a returning player whose old color is occupied becomes Random. Saved-game lobbies show the saved kingdom colors read-only. Extended colors can be combined with desync bypass in launcher 0.5.7. No helper window appears before launch. All multiplayer peers must update Beta. Release gameplay packages are unchanged.'
    }
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(*args):
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    p = subprocess.run(list(map(str, args)), cwd=REPO, capture_output=True, startupinfo=startup,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    print((p.stdout + p.stderr).decode('utf-8', errors='replace'), end='')
    p.check_returncode()


def read_feed(path):
    run(DOTNET, PUBLISHER, 'verify', path, KEYS / 'pawpatch-signing-public.pem')
    return json.loads(base64.b64decode(json.loads(path.read_bytes())['payload']))


def cached(package):
    name = package['urls'][0].replace('\\', '/').split('/')[-1]
    for folder in ('packages', 'release_workspace_20260905/packages',
                   'release_workspace_056/combination-fix/packages', 'release_workspace_056/publication/assets'):
        p = REPO / folder / name
        if p.is_file() and p.stat().st_size == package['size'] and sha(p) == package['sha256'].upper():
            return p
    raise FileNotFoundError('No verified local archive: ' + name)


def unpack(package, source):
    with zipfile.ZipFile(cached(package)) as archive:
        manifest = json.loads(archive.read('module.json'))
        assert manifest['id'] == package['id'] and manifest['version'] == package['version']
        assert not manifest.get('remove'), 'Explicit removal migration needed'
        entries = {n.replace('\\', '/').lower(): n for n in archive.namelist()}
        for file in manifest['files']:
            name = file['path'].replace('\\', '/')
            target = (source / name).resolve()
            assert target.is_relative_to(source.resolve())
            data = archive.read(entries['payload/' + name.lower()])
            assert len(data) == file['size'] and hashlib.sha256(data).hexdigest().upper() == file['sha256'].upper()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def sign(feed, name):
    payload = OUT / 'feed' / (name + '.payload.json')
    signed = OUT / 'feed' / (name + '.signed.json')
    payload.write_text(json.dumps(feed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    run(DOTNET, PUBLISHER, 'sign', payload, KEYS / 'pawpatch-signing-private.pem', 'pawpatch-prod-2026', signed)
    run(DOTNET, PUBLISHER, 'verify', signed, KEYS / 'pawpatch-signing-public.pem')


def main():
    assert not OUT.exists(), 'Preserve an existing candidate; choose a new staging directory if rebuilding.'
    for name in ('feed', 'sources', 'packages'):
        (OUT / name).mkdir(parents=True, exist_ok=True)
    beta = read_feed(REPO / 'feed/beta.json')
    stable = read_feed(REPO / 'feed/stable.json')
    before = copy.deepcopy(beta)
    stable_hash = sha(REPO / 'feed/stable.json')
    build = json.loads((HELPERS / 'build.json').read_bytes())
    for variant in build['variants']:
        assert sha(HELPERS / variant['name']) == variant['sha256']
    packages = {p['id']: p for p in beta['packages']}
    for module in VERSIONS:
        unpack(packages[module], OUT / 'sources' / module)
    common = OUT / 'sources/common-ui'
    colors = OUT / 'sources/player-colors'
    for variant in build['variants']:
        destination = colors if 'lobby_colors' in variant['name'] else common
        shutil.copyfile(HELPERS / variant['name'], destination / variant['name'])
    shutil.copyfile(WORK / 'beta_game_1372/paws_patch_versions.ini', common / 'paws_patch_versions.ini')
    for source, relative in (
        (WORK / 'time_of_day_1372/candidate/data/Game/world_rules_k2.tgi', 'data/Game/world_rules_k2.tgi'),
        (WORK / 'time_of_day_1372/candidate/data/Templates/template_rmc_k2.tgi', 'data/Templates/template_rmc_k2.tgi'),
        (WORK / 'random_map_1372/candidate/data/RandomMap/rmc_temperate03.tgi', 'data/RandomMap/rmc_temperate03.tgi'),
    ):
        target = common / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for module, version in VERSIONS.items():
        archive = OUT / 'packages' / (module + '-' + version + '.zip')
        run(DOTNET, PUBLISHER, 'pack', module, version, OUT / 'sources' / module, archive)
        package = packages[module]
        package.update(version=version, size=archive.stat().st_size, sha256=sha(archive),
            urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/' + TAG + '/' + archive.name])
    packages['common-ui']['name'] = {'ru': 'Общие исправления игры', 'en': 'Common game fixes'}
    packages['common-ui']['description'] = {
        'ru': 'Случайные карты и время суток, исправление стартового рассинхрона, версии модов и вывод нуля. Всегда включено в бете.',
        'en': 'Random maps and time of day, startup desync fix, mod versions and zero display. Always enabled in Beta.'}
    packages['player-colors']['description'] = {
        'ru': '49 цветов игроков, синхронизация лобби, проверка занятого цвета при входе и цвета сохранений.',
        'en': '49 player colors, synchronized lobbies, occupied-color checks on reconnect and saved-game colors.'}
    history = json.loads((REPO / 'feed/changelog.history.json').read_bytes())
    assert all(e['version'] != ENTRY['version'] for e in history['beta'])
    beta['changelog'] = [ENTRY] + history['beta']
    beta['colorDesyncContinue'] = True
    beta['patchGuide'] = json.loads((REPO / 'feed/patch-guide.json').read_bytes())
    beta['newsTitle'], beta['newsBody'] = ENTRY['title'], ENTRY['body']
    beta['publishedAt'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    beta['previousReleases'] = [{'label': 'Beta before beta.7', 'url':
        'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/history/beta-before-beta7.json'}] + beta['previousReleases']
    assert beta['launcher'] == before['launcher'] and beta['game'] == before['game']
    assert [p for p in beta['packages'] if p['id'] not in VERSIONS] == [p for p in before['packages'] if p['id'] not in VERSIONS]
    sign(beta, 'beta.production')
    for channel, source in (('stable', stable), ('beta', beta)):
        local = copy.deepcopy(source)
        for package in local['packages']:
            candidate = OUT / 'packages' / (package['id'] + '-' + package['version'] + '.zip')
            package['urls'] = [str(candidate if candidate.exists() else cached(package))]
        sign(local, channel + '.local')
    history['beta'] = [ENTRY] + history['beta']
    (OUT / 'changelog.history.json').write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(REPO / 'feed/beta.json', OUT / 'previous-beta.signed.json')
    (OUT / 'preparation.json').write_text(json.dumps({'stable_sha256': stable_hash,
        'old_beta_sha256': sha(REPO / 'feed/beta.json'), 'launcher': beta['launcher'],
        'changed_modules': list(VERSIONS), 'tag': TAG, 'published': False}, indent=2) + '\n')
    print('CANDIDATE READY: two Beta packages, unchanged Release and launcher; nothing published.')


if __name__ == '__main__':
    main()
