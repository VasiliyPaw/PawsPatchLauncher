"""Authored game terminology and proper-name corrections, applied after drafts."""
import csv,json,re
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
@lru_cache(maxsize=1)
def keyed_entries():
    return json.loads((ROOT/'game/localization/slavic-key-corrections.json').read_text('utf-8-sig'))

def keyed(path,key,source,language,fallback):
    row=keyed_entries().get(path,{}).get(key)
    if row is None:return fallback
    assert row['en']==source,(path,key,source,row['en'])
    return row[language]

def corrections():
    folder=ROOT/'game/localization';out={}
    for name in ('slavic-name-corrections.json','slavic-format-strings.json'):
        out.update(json.loads((folder/name).read_text('utf-8-sig')))
    with (folder/'slavic-gameplay-review.tsv').open(encoding='utf-8') as f:
        seen=set()
        for row in csv.DictReader(f,delimiter='\t'):
            assert row['English'] not in seen,row['English'];seen.add(row['English'])
            out[row['English']]={c:row[c] for c in ('cs','uk')}
    with (folder/'player-colors.tsv').open(encoding='utf-8') as f:
        colors=list(csv.DictReader(f,delimiter='\t'))
    for r in colors:
        for prefix in ('','Light ','Dark '):
            en=prefix+r['English'];values={c:r[c] for c in ('cs','uk')}
            if prefix:
                values['cs']=('Světle ' if prefix=='Light ' else 'Tmavě ')+r['cs'].lower()
                values['uk']=('Світло-' if prefix=='Light ' else 'Темно-')+r['uk'].lower()
            out[en]=values
    return out

def spacing(value,language):
    if language=='uk':
        value=re.sub(r"(?<=[А-Яа-яІіЇїЄєҐґ])[’']\s+(?=[А-Яа-яІіЇїЄєҐґ])","'",value)
        value=re.sub(r'(?<=[А-Яа-яІіЇїЄєҐґ])-\s+(?=[А-Яа-яІіЇїЄєҐґ])','-',value)
        value=value.replace('« ','«').replace(' »','»')
    return value
