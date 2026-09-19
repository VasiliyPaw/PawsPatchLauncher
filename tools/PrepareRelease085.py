"""Stage a launcher-only release, preserving every game package and patch guide."""
import argparse, copy, json, shutil
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS, RAW, key, normalize, fetch, sign
from PrepareRelease070 import read, write, sha, verify

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.8.5'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--launcher', type=Path)
    p.add_argument('--commit')
    p.add_argument('--signing-dir', type=Path)
    p.add_argument('--promote', action='store_true')
    a = p.parse_args(); out = a.out.resolve()
    if a.promote:
        proof = read(out/'preparation.json')
        for name, path in FEEDS.items():
            assert sha(ROOT/path) == proof['before'][name], 'Catalog changed: '+name
            staged = verify(read(out/'signed'/(name+'.json')), key())
            assert staged['launcher']['version'] == VERSION
        assert sha(ROOT/'feed/changelog.history.json') == proof['historyBefore']
        for name, path in FEEDS.items(): shutil.copyfile(out/'signed'/(name+'.json'), ROOT/path)
        shutil.copyfile(out/'changelog.history.json', ROOT/'feed/changelog.history.json')
        print('PROMOTED four launcher catalogs; gameplay unchanged')
        return
    assert not (out/'preparation.json').exists(), 'Use a new staging directory'
    out.mkdir(parents=True, exist_ok=True)
    artifact = read(a.launcher.parent/'launcher-artifact.json')
    assert artifact['version'] == VERSION and artifact['sourceCommit'] == a.commit
    exe = next(f for f in artifact['files'] if f['name'] == 'PawsPatchLauncher.exe')
    assert sha(a.launcher) == exe['sha256'] and a.launcher.stat().st_size == exe['size']
    private = serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(), None)
    assert private.public_key().public_numbers() == key().public_numbers()
    launcher = dict(version=VERSION, size=exe['size'], sha256=exe['sha256'],
                    urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v'+VERSION+'/PawsPatchLauncher.exe'])
    parts = (ROOT/'docs/release-0.8.5.md').read_text('utf-8').split('\n---\n')
    bodies = {lang:part.strip().split('\n',2)[2].strip() for lang,part in zip(('ru','en'),parts)}
    bodies.update(
        uk='- Виправлено відображення мода та передавання конфігурацій Vanilla й Immortals із розширеними кольорами та ігноруванням розсинхронізації.\n- Уточнено повідомлення в картці гравця, якщо налаштування або відомості про версії ще не отримано.',
        cs='- Opraveno zobrazení modu a sdílení konfigurací Vanilla a Immortals s rozšířenými barvami a pokračováním při desynchronizaci.\n- Upřesněny zprávy v kartě hráče, pokud nastavení nebo informace o verzích ještě nebyly přijaty.',
        de='- Mod-Anzeige und Konfigurationsfreigabe für Vanilla und Immortals mit erweiterten Farben und Fortsetzung bei Desynchronisation korrigiert.\n- Hinweise in der Spielerkarte bei noch fehlenden Einstellungen oder Versionsinformationen präzisiert.',
        fr='- Correction de l’affichage du mod et du partage des configurations Vanilla et Immortals avec les couleurs étendues et la poursuite malgré les désynchronisations.\n- Clarification des messages de la fiche joueur lorsque les paramètres ou les informations de version n’ont pas encore été reçus.')
    entry = dict(category='launcher',version=VERSION,publishedAt='2026-09-19',
                 title={lang:"Paw's Launcher "+VERSION for lang in bodies},body=bodies)
    history = read(ROOT/'feed/changelog.history.json'); before = {}
    allowed = {'launcher','publishedAt','changelog','newsTitle','newsBody'}
    for name,path in FEEDS.items():
        original = (ROOT/path).read_bytes()
        assert normalize(fetch(RAW+path+'?release085=baseline')) == normalize(original), 'Public catalog changed: '+name
        f = verify(json.loads(original),key()); assert f['launcher']['version']=='0.8.4'
        before[name] = sha(ROOT/path)
        previous = out/'previous'/(name+'.json'); previous.parent.mkdir(exist_ok=True); previous.write_bytes(original)
        updated = copy.deepcopy(f)
        updated.update(launcher=launcher,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       changelog=[entry]+f['changelog'],newsTitle=entry['title'],newsBody=entry['body'])
        assert {k:v for k,v in f.items() if k not in allowed} == {k:v for k,v in updated.items() if k not in allowed}
        write(out/'signed'/(name+'.json'),sign(updated,private))
        if name in ('stable','beta'):
            assert history[name] == f['changelog']; history[name] = updated['changelog']
    write(out/'changelog.history.json',history)
    write(out/'preparation.json',dict(before=before,historyBefore=sha(ROOT/'feed/changelog.history.json'),
                                    sourceCommit=a.commit,launcher=launcher,gameplayUnchanged=True))
    print('SIGNED four catalogs with exact CI artifact; all game packages and guides preserved')


if __name__ == '__main__': main()
