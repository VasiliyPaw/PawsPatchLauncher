"""Build local review feeds and bundled mod guides. Never publishes or edits a game."""
import argparse, base64, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def guide(document):
    return dict(id=document['id'], version=document['version'], author=document['author'],
        description=document['summary'], sections=[dict(id=s['id'], title=s['title'],
        body=s.get('body') or {lang:'\n\n'.join('• '+i[lang] for i in s['items']) for lang in ('ru','en')}) for s in document['sections']])

def bundled_guides(audit):
    """Shared source for the embedded guide and signed release-feed payloads."""
    mods=[guide(read(audit/'arcane-audit/arcane-wars.help.json')), guide(read(audit/'immortals-audit/immortals-guide.json'))]
    mods.insert(0, dict(id='vanilla', version='Kohan II: Kings of War', author='TimeGate Studios',
        description=dict(ru='Оригинальная Kohan II: Kings of War с выбранным языком игры.', en='The original Kohan II: Kings of War with your selected game language.'),
        sections=[dict(id='original', title=dict(ru='Оригинальные правила',en='Original rules'),body=dict(
        ru="При применении настроек лаунчер восстанавливает оригинальные игровые файлы и удаляет изменения Arcane Wars, Immortals и Paw's Patch. Сохранения и выбранный язык игры остаются. Дополнительных компонентов для этого режима пока нет.",
        en="Applying settings restores the original game files and removes Arcane Wars, Immortals and Paw's Patch changes. Saves and your selected game language are retained. There are no optional components for this mode yet."))]))
    return mods

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args=p.parse_args()
    mods=bundled_guides(args.audit)
    write(Path(__file__).resolve().parents[1]/'src/PawsPatchLauncher/Assets/mod-guides.json', mods)
    replacements=read(args.audit/'immortals-audit/packages.json')
    replacements += [read(args.audit/'arcane-audit/arcane-wars-package.json'),read(args.audit/'arcane-audit/aw-localization-ru-package.json')]
    replacements += read(args.audit/'arcane-audit/data-only-packages.json')
    replacements += read(args.audit/'arcane-audit/standalone-packages.json')
    by_id={p['id']:p for p in replacements}
    for package in replacements:
        path=Path(package['urls'][0]); actual=hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual.lower()==package['sha256'].lower() and path.stat().st_size==package['size'], path
    for channel in ('stable','beta'):
        base=read(args.base/(channel+'.json'))
        data=json.loads(base64.b64decode(base['payload']))
        data['packages']=[by_id.get(p['id'],p) for p in data['packages']]
        existing={p['id'] for p in data['packages']}
        data['packages'] += [p for p in replacements if p['id'] not in existing]
        # This unmodified base-game bootstrap is shared by both mods. Its old AW
        # dependency was packaging metadata, not a dependency of the game files.
        for package in data['packages']:
            if package['id'] == 'startup-base': package['dependsOn'] = []
        data['modGuides']=mods
        for entry in data.get('patchGuide', {}).get('entries', []):
            if entry['id'] == 'siege':
                entry.update(
                    bodyRu='Добавляет расход 0,75 очка королевства за каждое орудие: Багровую катапульту, Чумную катапульту, Баллисту Драконьего огня и Ворпальную машину. В чистом Arcane Wars у этих четырёх машин такого расхода нет.\n\nИх стоимость в золоте, содержание в ресурсах и параметры атак остаются такими, как в Arcane Wars 0.82.1.8. При выключении компонента дополнительный расход очков королевства убирается. Для сетевой игры настройка должна совпадать у всех участников.',
                    bodyEn='Adds an upkeep of 0.75 kingdom points per engine to the Crimson Catapult, Plague Catapult, Dragonfire Ballista and Vorpal Engine. These four engines have no such upkeep in pure Arcane Wars.\n\nTheir gold cost, resource upkeep and attack parameters remain as defined in Arcane Wars 0.82.1.8. Turning this component off removes the additional kingdom-point upkeep. Every multiplayer participant must use the same setting.')
            if entry['id'] == 'localization':
                entry.update(titleRu='Локализация игры', titleEn='Game language',
                    bodyRu='Вверху компонентов можно выбрать English (original) или Русский. Язык сохраняется при переключении модов и выпусков, включая ваниллу. Он выбирается отдельно от языка лаунчера и применяется вместе с настройками.\n\nРусский перевод охватывает оригинальную игру, Arcane Wars и дополнительные настройки патча. Собственные названия и описания Immortals пока могут оставаться английскими. Локализация не меняет игровые правила.',
                    bodyEn='Choose English (original) or Русский at the top of Components. The choice is retained across mods and releases, including Vanilla. It is independent of the launcher language and is applied with your settings.\n\nRussian translation covers the base game, Arcane Wars and additional patch settings. Immortals-specific names and descriptions may remain in English. Localization does not change game rules.')
        data['changelog'].insert(0, dict(category='launcher', version='0.6.4-local.1', publishedAt='2026-09-10',
            title=dict(ru='Моды, языки и общая справка · тестовая сборка', en='Mods, languages and unified guide · test build'),
            body=dict(ru='• Immortals доступен для установки.\n• Чистый Arcane Wars сверён с исходным модом.\n• Общий язык игры сохраняется в ванилле и во всех модах.\n• Язык лаунчера перенесён в настройки.\n• Описания модов и патча объединены в справку и обновляются через канал выпусков.\n• Окно запуска появляется на мониторе лаунчера; ручное обновление открывает это же окно.\n• Улучшены анимации, диалоги и уведомления истории.\n• При удалении лаунчера можно выбрать удаление патча и модов.\n\nЛокальная тестовая сборка. Не опубликована.',
                en='• Immortals can be installed.\n• Pure Arcane Wars is verified against the original mod.\n• A shared game language is retained in Vanilla and every mod.\n• Launcher language moved to Settings.\n• Mod and patch descriptions share a guide and update through release feeds.\n• Startup uses the launcher monitor; manual updates open the same window.\n• Improved animations, dialogs and unread history notifications.\n• Launcher removal offers a choice to remove patch and mods.\n\nLocal test build. Not published.')))
        data['changelog'].insert(0, dict(category='launcher', version='0.6.4-local.2', publishedAt='2026-09-10',
            title=dict(ru='Моды без интернета и исправления · тестовая сборка', en='Offline mods and fixes · test build'),
            body=dict(ru='• Установка сохраняет мод, оба языка и все его компоненты.\n• Моды остаются на компьютере при переключении; повторная загрузка не нужна.\n• Неприменённые настройки блокируют запуск, кнопка применения выделена золотым.\n• Обновления относятся к активному моду; обновление Arcane Wars не мешает Immortals.\n• Обычный выход из игры больше не вызывает ложное восстановление.\n• Повторяющиеся вступления в справке объединены.\n• Уточнена подсказка осадного компонента и исправлено его выключение.\n\nЛокальная тестовая сборка. Не опубликована.',
                en='• Installation stores the mod, both languages and all its components.\n• Installed mods remain on this computer for switching without downloading again.\n• Unapplied settings block launch; Apply settings is highlighted in gold.\n• Updates belong to the active mod; Arcane Wars updates do not interrupt Immortals.\n• Normal game exits no longer trigger false recovery.\n• Repeated guide introductions were merged.\n• Corrected the siege component description and its off state.\n\nLocal test build. Not published.')))
        data['publishedAt']=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        write(args.out/(channel+'.payload.json'),data)
    write(args.out/'preparation.json',dict(published=False,modGuides=[dict(id=g['id'],sections=len(g['sections'])) for g in mods], packages=[p['id'] for p in replacements]))
    print('Prepared local feeds,',len(replacements),'packages and',sum(len(g['sections']) for g in mods),'guide sections; nothing published.')

if __name__=='__main__': main()
