"""Keep control-group digits active over the in-game favorites recruitment list.

Accept a verified stock hotkeys_favorites.txt and emit the base and Russian
localization layers. Local_ru is mounted after Local_base_ru and overrides it.
Do not change editor shortcuts, the company-composition dialog, or Shift-digit
favorites. The normal game bindings already provide SelectGroup and SaveGroup.
"""
import argparse
import re
from pathlib import Path


def prepare(source):
    prefix = '# Paw: digits select control groups; Ctrl+digits assign them.\n'
    pattern = re.compile(r'^map (ctrl-)?([0-9]) FavoritesDisplay\|1 "(RecruitFavorite|SaveToFavorite) ([0-9]+)"\s*$')
    found = set()
    lines = []
    for line in source.splitlines(keepends=True):
        match = pattern.fullmatch(line)
        if match:
            modifier, digit, command, slot = match.groups()
            assert command == ('SaveToFavorite' if modifier else 'RecruitFavorite')
            assert int(slot) == (int(digit) - 1) % 10
            key = (bool(modifier), digit)
            assert key not in found, 'Duplicate recruitment shortcut'
            found.add(key)
            lines.append('# Paw control groups: ' + line)
        else:
            lines.append(line)
    assert found == {(modifier, str(digit)) for modifier in (False, True) for digit in range(10)}, 'Unexpected stock favorites bindings'
    return prefix + ''.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stock', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raw = args.stock.read_bytes()
    encoding = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'
    result = prepare(raw.decode(encoding)).encode('utf-8')
    for root in ('data', 'Local_base_ru', 'Local_ru'):
        target = args.out / root / 'Localization/Hotkeys/hotkeys_favorites.txt'
        assert not target.exists(), 'Choose a fresh output directory'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result)
    print('RECRUITMENT_HOTKEYS_PASS 20 conflicting bindings disabled; other bindings retained; base and both Russian layers emitted')
