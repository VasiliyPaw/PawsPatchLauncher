"""Create isolated game fixtures from signed candidate package selections.

Never starts a game, changes the installed game, copies credentials, or restores
old saves over newer ones. Back up shared rotating saves before live UI tests.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import PrepareCityPolicyBeta as release
import PrepareRelease020 as previous

p = argparse.ArgumentParser()
p.add_argument('stock', type=Path)
p.add_argument('name')
p.add_argument('--index', type=int, default=0)
args = p.parse_args()
assert args.name.isascii() and args.name.replace('-', '').isalnum()
stock = args.stock.resolve()
destination = release.OUT / 'live' / args.name / 'Kohan II'
assert not destination.exists(), 'Preserve the earlier live fixture.'
assert release.base.sha(stock / 'k2.exe') == '1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45'
feed = release.base.read_feed(release.OUT / 'feed/beta.local.signed.json')
audit = json.loads((release.OUT / 'audit/combinations.json').read_bytes())
profiles = [r for r in audit['configurations'] if r['channel'] == 'beta']
profile = profiles[args.index]
destination.mkdir(parents=True)
for file in stock.iterdir():
    if file.is_file() and (file.name.lower() == 'k2.exe' or file.suffix.lower() in ('.dll', '.rwd')):
        shutil.copyfile(file, destination / file.name)
if (stock / 'mss').is_dir():
    shutil.copytree(stock / 'mss', destination / 'mss')
# QA-only Steam development context; never packaged or published.
(destination / 'steam_appid.txt').write_text('97130\n', encoding='ascii')
previous.cached = release.cached
for package in sorted((p for p in feed['packages'] if p['id'] in profile['modules']), key=lambda p: (p['priority'], p['id'])):
    previous.unpack(package, destination)
(destination.parent / 'profile.json').write_text(json.dumps(profile, indent=2), encoding='utf-8')
print('ISOLATED FIXTURE', destination, profile['code'], profile['executable'])
