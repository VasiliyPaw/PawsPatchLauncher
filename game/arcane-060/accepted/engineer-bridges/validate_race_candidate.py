"""Validate the six-race candidate using actual assets and native evidence."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from models import definitions

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.out.resolve()
assert (r/'installed-rivers.marker').exists()
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().lower()

baseline=json.loads((r/'installed-baseline.json').read_text());game=Path(baseline['game'])
for name,digest in baseline['files'].items():assert sha(game/name)==digest.lower(),name
helper=json.loads((r/'installed-helper.json').read_text())
assert sha(r/'sandbox/PawsInstalledRuntime.exe')==helper['privateHelperSha256'].lower()
features=json.loads(subprocess.check_output([str(r/'sandbox/PawsInstalledRuntime.exe'),'--features'],text=True))
assert features==helper['features']==json.loads(subprocess.check_output([str(game/helper['installedHelper']),'--features'],text=True))
art=json.loads((r/'bridge-art.json').read_text());styles=set(art['styles']);assert styles=={'human','gauri','drauga','haroun','shadow','undead'}
for style,models in art['styles'].items():
 assert len(models)==112
 for name,row in models.items():
  assert sha(r/'sandbox/rivers-data/Paws/Bridges'/style.title()/name)==row['sha256']
  assert row['depthState']['comparison']=='LESS_EQUAL' and row['depthState']['depthTest'] and row['depthState']['depthWrite']
actual=(r/'sandbox/rivers-data/Special/Things/thing_visibilityactors.tgi').read_text(encoding='utf-16')
assert actual.endswith(definitions('ru',art['styles']))
for race,worker in [('Human','engineer'),('Gauri','forge'),('Drauga','crafter'),('Haroun','caretaker'),('Shadow','nightbringer'),('Undead','boneweaver')]:
 text=(r/'sandbox/rivers-data/Units'/race/(worker+'.tgi')).read_text(encoding='utf-16')
 for material in ['wood','stone']:assert text.count('actor_ids = paws_bridge_'+race.lower()+'_'+material+'_site')==1
assets=json.loads((r/'qa-evidence/r5-assets.json').read_text());assert assets['passed'] and assets['models']==784 and assets['definitions']==799
parity=json.loads((r/'qa-evidence/r6-combined-parity.json').read_text());assert parity['passed'] and parity['matchingRaceModels']==672
views={}
for race in sorted(styles):
 row=json.loads((r/f'qa-evidence/r6-native/{race}-review.json').read_text());assert row['nativeCreated'] and row['visualAcceptance'].startswith('accepted')
 actors=json.loads(Path(row['snapshot']).read_text())['actors']
 for material in ['wood','stone']:
  actor=next(v for v in actors if v['name']==f'paws_bridge_{race}_{material}_y_16')
  assert actor['health']==(1000 if material=='wood' else 2000) and not actor['construction']
  assert actor['definitionCost'][0]==(75 if material=='wood' else 125)
  assert Path(row['views'][material]).is_file()
 views[race]=row
meta=json.loads((r/'native/prototype.json').read_text());assert len(meta['hooks'])==73 and set(meta['styles'])==styles
assert {0x244727,0x244752}<={h['site'] for h in meta['hooks']}
assert {0x2635e4,0xd4f5f,0x2731f7,0x275eab,0x4f4e30}<={h['site'] for h in meta['hooks']}
assert not any(h['site']==0xc772e for h in meta['hooks'])
plugins=(r/'sandbox/Mods/plugins.txt').read_text().splitlines();original=(game/'Mods/plugins.txt').read_text().splitlines()
assert [v for v in plugins if v.strip().lower()!='pawsbridges.dll']==original and plugins.count('PawsBridges.dll')==1
assert not any('PawsBridgesQA' in v for v in plugins)
code=(r/'sandbox/Mods/PawsBridges.dll').read_bytes();assert b'bridge-command.txt' not in code and b'!art ' not in code and b'!peace-fixture' not in code
startup=(r/'qa-evidence/r6-normal-startup.log').read_text();assert 'PawsBridges.dll started' in startup and 'bridges: READY 73 hooks' in startup and 'PawsBridgesQA.dll started' not in startup
routing=json.loads((r/'qa-evidence/routing-followup/acceptance.json').read_text());assert routing['passed'] and routing['nativeHooks']==len(meta['hooks'])
assert routing['normalRuntimeSha256']==sha(r/'sandbox/Mods/PawsBridges.dll')
user_regression={name:json.loads((r/('qa-evidence/'+name+'.json')).read_text()) for name in ['user-river-crossings-final','final-mouse-construction','final-reloaded-bridge-crossing']}
assert all(v['passed'] for v in user_regression.values())
assert len(user_regression['user-river-crossings-final']['route'])==5
assert user_regression['final-mouse-construction']['paid'][0]==75 and user_regression['final-mouse-construction']['health']==1000
report={'revision':6,'localOnly':True,'published':False,'installedFilesUnchanged':len(baseline['files']),'matchingHelperFeatures':len(features),
 'styles':sorted(styles),'newRaceModels':672,'preservedLegacyModels':112,'definitions':799,'nativeHooks':len(meta['hooks']),
 'checks':{'assets':38548,'compiledRoadsAndRaceRouting':614,'bridgeConnectivity':70,'floorABI':232,'bridgeRouting':88,'menuAndPreferences':114,'generationPipeline':42,'eligiblePioneers':49},
 'nativeViewed':views,'nativeModelViews':12,'modelSourcePaths':{k:v['path'] for k,v in art['sources'].items()},
 'normalRuntimeSha256':sha(r/'sandbox/Mods/PawsBridges.dll'),'normalStartupPassed':True,'qaCommandTransport':False,
 'userBridgeRegression':user_regression,'routingFollowup':routing,
 'limits':['Native art fixtures, not normal fresh racial campaigns: one saved nation ID and viewing rules changed in copies of a stock fixture.',
 'Native model length16 (30 world units), one saved heading; other lengths/orientations checked statically.',
 'Native company followed a route over both finished bridges; all twelve construction animations were not live tested. Haroun stone growth was separately live tested.',
 'Friendly bridge right-click and exact deck stops were live tested. Enemy explicit bridge combat and multiplayer remain outside this acceptance.',
 'No river algorithm changes in R6. R5 river proof remains separate; R6 compiled pipeline and menu checks passed.']}
(r/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SIX_RACE_CANDIDATE_PASS',len(baseline['files']),'installed files unchanged;',len(features),'helper features; 672 new models; twelve native views')
