"""Accept the private R7 from actual artifacts and bounded native evidence."""
from pathlib import Path
import argparse,hashlib,json
from models import definitions,construction_effect
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.out.resolve();e=r/'qa-evidence'
def read(name):return json.loads((e/name).read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
baseline=read('r7-installed-baseline.json');assert baseline['passed']
art=json.loads((r/'bridge-art.json').read_text());outlines=json.loads((r/'bridge-outline-installed.json').read_text());root=r/'sandbox/rivers-data/Paws/Bridges';seen=set()
assert outlines['passed'] and len(outlines['variants'])==784
for name,row in outlines['variants'].items():
 raw=(root/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
 for mesh in row['meshNames']:assert mesh not in seen and raw.count(mesh.encode())==1;seen.add(mesh)
 for node in [b'PawsBridgeSelected',b'PawsBridgeFocused']:
  i=raw.index(node)+len(node);assert raw[i:i+10]==bytes.fromhex('00000000ffffffff1000')
 assert row['runtimeVisibility'] and row['depthTest'] and row['depthWrite']
actual=(r/'sandbox/rivers-data/Special/Things/thing_visibilityactors.tgi').read_text(encoding='utf-16');assert actual.endswith(definitions('ru',art['styles']))
effects=(r/'sandbox/rivers-data/Effects/construction.tgi').read_text(encoding='utf-16');assert effects.endswith(construction_effect())
growth=json.loads((r/'haroun-growth-art.json').read_text());assert growth
assets=read('r7-assets.json');assert assets['passed'] and assets['models']==784 and assets['nifModels']==84 and assets['languages']==6
views={}
for race in ['human','gauri','drauga','shadow','haroun']:
 row=read(f'r6-native/{race}-review.json');assert row['nativeCreated'] and row['visualAcceptance'].startswith('accepted')
 assert len(row['engineerRoute'])==3
 for file in row['views'].values():assert Path(file).is_file()
 views[race]=row
paused=read('final-reloaded-decay-paused.json');assert paused[0]['time']==paused[1]['time'] and paused[0]['actors']==paused[1]['actors'];assert paused[0]['actors']['7160']['states']=='0x40000000'
cancel=read('final-cancel-paused.json')[0];assert cancel['actors']['7160']['health']==paused[0]['actors']['7160']['health'] and cancel['actors']['7160']['states']=='0x8000000'
healing=read('final-cancel-regeneration.json');assert abs((healing[1]['actors']['7160']['health']-healing[0]['actors']['7160']['health'])/(healing[1]['time']-healing[0]['time'])-2)<.001
wood=read('final-wood-decay-rate.json');assert abs((wood[0]['actors']['2624']['health']-wood[1]['actors']['2624']['health'])/(wood[1]['time']-wood[0]['time'])-10)<.001
collapsed=read('final-wood-after-collapse.json')[0];assert collapsed['actors']['2624'] is None and collapsed['cell']['variant']=='paws_river_desert01' and int(collapsed['cell']['flags'],16)&0x100
build=read('final-real-caretaker-construction.json');site=next(v for v in build['actors'] if v['id']==6336);assert site['construction'] and site['health']>1 and site['paidConstructionCost'][0]==75
completed=read('final-haroun-completed-health.json')[0]['actors']['6336'];assert completed['health']==completed['maxHealth']==1000 and int(completed['states'],16)&0x200000==0
rivers=read('final-river-profile.json');assert rivers['passed'] and rivers['nativeView'].startswith('accepted') and rivers['rivers']==2 and rivers['dryOrWalkableRiverCells']==rivers['aboveWaterRiverVertices']==0
meta=json.loads((r/'native/prototype.json').read_text());assert len(meta['hooks'])==83 and meta['installed']
plugins=(r/'sandbox/Mods/plugins.txt').read_text().splitlines();assert plugins.count('PawsBridges.dll')==1 and not any('PawsBridgesQA' in s for s in plugins)
binary=(r/'sandbox/Mods/PawsBridges.dll').read_bytes();assert b'bridge-command.txt' not in binary and b'!art ' not in binary and b'!peace-fixture' not in binary
startup=(e/'r7-normal-startup.log').read_text();assert 'PawsBridges.dll started' in startup and 'bridges: READY 83 hooks' in startup and 'PawsBridgesQA.dll started' not in startup
report={'revision':7,'passed':True,'localOnly':True,'published':False,'installedBaseline':baseline,'models':784,'definitions':799,'geometrySamples':84,'modelSourcePaths':{k:v['path']for k,v in art['sources'].items()},'nativeHooks':83,'normalRuntimeSha256':sha(r/'sandbox/Mods/PawsBridges.dll'),'qaCommandTransport':False,
 'checks':{'compiledRoads':614,'relocatedRoutingSelectionDecay':158,'floorABI':232,'navigation':70,'riverPipeline':48,'eligiblePioneers':49,'assetChecks':assets['checks']},
 'nativeEvidence':{'newRaceViews':views,'cancelPreservesHealth':True,'decaySurvivesSaveLoad':True,'pauseStopsDecay':True,'woodDecayHPPerGameSecond':10,'harounStoneRegenHPPerGameSecond':2,'woodCollapseRestoresWater':collapsed,'paidCaretakerConstruction':site,'completedCaretakerBridge':completed,'riverProfile':rivers},
 'limits':['Single-player private prototype; multiplayer and replay acceptance are not included.',
 'Ten completed-model native views use isolated art fixtures; real construction was separately checked with the original Haroun caretakers.',
 'All 784 model hashes and six-language definitions checked; detailed post-outline geometry sampled at lengths 5, 13, 32, both axes and materials (84 NIF files).',
 'New bed/shore profile checked on one new 1280x1280 mixed-biome map with two rivers; old saved terrain is preserved.',
 'Decoration clearing calls the native building ClearDoodads API only when work begins; a separate planted-tree gameplay fixture was not created.',
 'Non-Haroun no-regeneration and repair eligibility checked in compiled/native adapters and content; a separate live manual-repair acceptance is not included.']}
(r/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('R7_CANDIDATE_PASS',baseline['installedFilesChecked'],'installed files unchanged;',len(views)*2,'native model views; normal runtime without QA transport')
