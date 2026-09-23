"""Prefer the final center garrison upgrades in every improved-AI ego."""
from pathlib import Path
import json, hashlib
from prepare_data import owners, blocks, prop

ROOT = Path(__file__).resolve().parent
UPGRADES = json.loads((ROOT / 'militia-upgrades.json').read_text())

def transform(text, race):
    edits = []; changes = []
    targets = [key for key in UPGRADES if key.startswith(race + '_')]
    assert targets, race
    for key, (start, end, owner) in owners(text).items():
        if not owner.startswith('[Ego '): continue
        engines = list(blocks(owner, r'^\s*\[GoalEngine\]'))
        assert len(engines) == 1, key
        a, b, engine = engines[0]
        existing = {prop(v, 'actor_IDS'): prop(v, 'value')
                    for _, _, v in blocks(engine, r'^\s*\[ActorPriority\]')}
        additions = ''
        for target in targets:
            if target in existing:
                assert existing[target] == '100000', (key, target)
                continue
            additions += ('\n\t\t[ActorPriority]\n\t\t{\n'
                          f'\t\t\tactor_IDS = {target}\n\t\t\tvalue = 100000\n\t\t}}\n')
            changes.append(dict(owner=key, field='final_militia_upgrade_priority', target=target, after=100000))
        if additions:
            engine = engine[:-1] + additions + engine[-1:]
            edits.append((start, end, owner[:a] + engine + owner[b:]))
    for a, b, value in reversed(edits): text = text[:a] + value + text[b:]
    return text, changes

if __name__ == '__main__':
    folder = ROOT / 'data'
    manifest = json.loads((folder / 'manifest.json').read_text())
    total = 0
    for entry in manifest:
        if not entry['path'].startswith('data/SAI/'): continue
        path = folder / entry['path']; raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry['after'], path
        text, changes = transform(raw.decode('utf-8-sig'), path.stem.split('_')[0])
        if changes:
            path.write_bytes(text.encode('utf-8'))
            entry['after'] = hashlib.sha256(path.read_bytes()).hexdigest()
            entry['changes'] += changes; total += len(changes)
        assert transform(text, path.stem.split('_')[0]) == (text, [])
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('MILITIA_PRIORITY', total, 'overrides; every native upgrade prerequisite remains active')
