"""Prepare local DE/FR review packages. No game writes, downloads or publishing."""
import argparse, base64, copy, json, re
from pathlib import Path
from PrepareSplitLanguages import build, read, write, readpkg, sha


def decode(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return raw.decode('utf-16')
    if raw.startswith(b'\xef\xbb\xbf'):
        return raw.decode('utf-8-sig')
    return raw.decode('cp1252')


def prepare(assets, base, out, english):
    bootstrap = readpkg(english)['startup/autoexec.txt']
    index = read(assets / 'de-rwd-files.json')
    raw = (assets / 'de-extracted/app/Local_de.rwd').read_bytes()
    sources = {'de': {p: raw[v['offset']:v['offset'] + v['size']] for p, v in index.items()}}
    for code, directory in [('de', 'de-extracted/app/Data'), ('fr', 'fr-extracted/Data')]:
        sources.setdefault(code, {}).update({p.relative_to(assets / directory).as_posix(): p.read_bytes()
                                            for p in (assets / directory).rglob('*') if p.is_file()})
    packages, audit = [], {}
    for code, language, ru, en in [('de', 'Deutsch', 'Немецкий', 'German'), ('fr', 'Français', 'Французский', 'French')]:
        depot = 'Local_base_' + code + '/'
        text, voice, omitted = {}, {}, []
        tables = 0
        for path, data in sources[code].items():
            suffix = Path(path).suffix.lower()
            if suffix in ('.mp3', '.wav'):
                assert path.lower().startswith('audio/')
                voice['data/' + path] = data
            elif suffix == '.tgi' and re.search(r'^\s*\[Text\s+language\s*=', decode(data), re.M):
                content = re.sub(r'(\[Text\s+language\s*=)[^\]]+', r'\g<1> ' + language, decode(data))
                # These are localized string tables, never gameplay definitions.
                assert not re.search(r'^\s*\[(?!Text\b)', content, re.M), path
                text[depot + path] = content.encode('utf-16')
                tables += 1
            elif code == 'fr' and path.lower().startswith('fonts/') and suffix in ('.tgi', '.ttf'):
                if suffix == '.tgi':
                    content = decode(data)
                    # Load bundled fonts privately through the engine, not Windows-installed names.
                    for font in ('VILLAGE', 'LBRITED', 'DANIELA'):
                        content = re.sub(r'(?im)(\bfont\s*=\s*)' + font + r'(\s*(?:;;[^\r\n]*)?$)', r'\g<1>TrueType/' + font + '.TTF' + r'\g<2>', content)
                    data = content.encode('utf-16')
                text[depot + path] = data
            else:
                # Old hotkey definitions would replace modern Dvorak/fix bindings.
                omitted.append(path)
        assert tables == 62, (code, tables)
        assert len(voice) == {'de': 1119, 'fr': 1106}[code]
        for path, data in text.items():
            if '/Fonts/' in path and path.endswith('.tgi'):
                for font in re.findall(r'(?im)^\s*font\s*=\s*(\S+\.ttf)', decode(data)):
                    resolved = depot + (font.lstrip('/') if font.startswith('/') else 'Fonts/' + font)
                    assert resolved.lower() in {p.lower() for p in text}, (path, font)
        # A locale depot replaces this entire file; a LanguageIDS-only file loses
        # required startup variables such as ApplicationName and crashes the game.
        locale = decode(sources['fr']['AVars_Locale.tgi'])
        locale = re.sub(r'(?m)(string\s+LanguageIDS\s*=)[^\r\n]+', r'\g<1> ' + language, locale)
        if code == 'de':
            locale = re.sub(r'(?m)(string\s+SKU\s*=)[^\r\n]+', r'\g<1> German', locale)
            locale = re.sub(r'(GameSpyDistributionID\s*=\s*)997', r'\g<1>998', locale)
            locale = locale.replace('Initialisation...', 'Initialisierung...').replace('Chargement des données...', 'Spieldaten werden geladen...')
        assert all(name in locale for name in ('ApplicationName', 'LanguageIDS', 'GameSpyDistributionID'))
        text[depot + 'AVars_Locale.tgi'] = locale.encode('utf-16')
        text['startup/autoexec.txt'] = bootstrap
        # The Steam executable reads this locale bootstrap name regardless of UI language.
        text['startup/autoexec_ru.txt'] = ('# Text only. Speech is selected independently.\r\naddlocaledepot ' + depot + '\r\n').encode('ascii')
        template = dict(priority=220, required=False, experimental=False, executableIndependent=True,
                        mods=['vanilla', 'immortals', 'arcane-wars'], dependsOn=[])
        text_template = dict(template, id='game-localization-' + code,
                             name=dict(ru=ru + ' текст', en=en + ' text'),
                             description=dict(ru='Перевод оригинальной игры. Дополнительные тексты модов пока остаются на английском.',
                                              en='Original game translation. Additional mod text remains in English for now.'))
        voice_template = dict(template, id='game-voice-' + code, priority=230,
                              name=dict(ru=ru + ' — озвучка', en=en + ' speech'),
                              description=dict(ru='Озвучка оригинальной игры. Язык текста выбирается отдельно.',
                                               en='Original game speech, independent of text language.'))
        packages += [build(out, text_template, '1.0.0-preview.2' if code == 'de' else '1.0.0-preview.3', text), build(out, voice_template, '1.0.0-preview.1', voice)]
        audit[code] = dict(textTables=tables, textFiles=len(text), audioFiles=len(voice), omitted=omitted)
    for channel in ('stable', 'beta'):
        feed = json.loads(base64.b64decode(read(base / (channel + '.json'))['payload']))
        feed['packages'] += copy.deepcopy(packages)
        # A local candidate must not auto-update itself to a public binary during review.
        feed['launcher'] = dict(version='0.0.0', size=0, sha256='', urls=[])
        write(out / 'feeds' / (channel + '.payload.json'), feed)
    write(out / 'language-audit.json', audit)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('assets', 'base', 'out', 'english-package'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    english = dict(urls=[str(args.english_package.resolve())], sha256=sha(args.english_package.read_bytes()), size=args.english_package.stat().st_size)
    prepare(args.assets, args.base, args.out.resolve(), english)
