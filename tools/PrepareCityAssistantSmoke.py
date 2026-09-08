"""Create an isolated all-off game from verified Beta packages. Does not launch.

Original local game archives/DLLs are copied read-only. No saves, credentials,
installation state or untracked test helpers are copied from the user's game.
"""
import json
from pathlib import Path
import shutil
import sys
import PrepareCityAssistantBeta as release
import PrepareRelease020 as previous

stock = Path(sys.argv[1]).resolve()
destination = release.OUT / 'live-all-off' / 'Kohan II'
assert stock.is_dir() and (stock / 'k2.exe').is_file()
assert not destination.exists(), 'Preserve an existing live test.'
destination.mkdir(parents=True)
for file in stock.iterdir():
    if file.is_file() and (file.name.lower() == 'k2.exe' or file.suffix.lower() in ('.dll', '.rwd')):
        shutil.copyfile(file, destination / file.name)
if (stock / 'mss').is_dir():
    shutil.copytree(stock / 'mss', destination / 'mss')
# Standard Steam development launch context for the owned local game. Without
# this, Steam relaunches the installed folder and the helper correctly refuses it.
# This file is QA-only and is never included in published packages.
(destination / 'steam_appid.txt').write_text('97130\n', encoding='ascii')
feed = release.base.read_feed(release.OUT / 'feed/beta.local.signed.json')
audit = json.loads((release.OUT / 'audit/combinations.json').read_bytes())
profile = next(row for row in audit['configurations'] if row['channel'] == 'beta')
assert profile['executable'] == 'k2_paws_ui_1372.exe'
assert not set(profile['modules']) & {'player-colors', 'localization-ru', 'desync-continue'}
previous.cached = release.cached
for package in sorted((p for p in feed['packages'] if p['id'] in profile['modules']), key=lambda p: (p['priority'], p['id'])):
    previous.unpack(package, destination)
print('ISOLATED LIVE FIXTURE', destination, profile['code'])
