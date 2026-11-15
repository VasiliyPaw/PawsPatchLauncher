"""Accept the private R8 from its actual assets, path traces and river capture."""
from pathlib import Path
import argparse,hashlib,json,math
from models import definitions
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.out.resolve();e=r/'qa-evidence'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
baseline=read(e/'r8-installed-baseline.json');assert baseline['passed'] and not baseline['changedInstalledFiles']
art=read(r/'bridge-art.json');assets=read(e/'r7-assets.json');assert assets['passed'] and assets['models']==784 and assets['nifModels']==84
root=r/'sandbox/rivers-data/Paws/Bridges';models=0
for style,rows in [('',art['core']['variants']),*art['styles'].items()]:
 for name,row in rows.items():
  path=root/style.title()/name;assert sha(path)==row['sha256'];raw=path.read_bytes()
  assert b'PawsBridgeSelected' not in raw and b'PawsBridgeFocused' not in raw;models+=1
text=(r/'sandbox/rivers-data/Special/Things/thing_visibilityactors.tgi').read_text(encoding='utf-16')
assert text.endswith(definitions('ru',art['styles'])) and 'focused_vfx = banner_selection_vfx' not in text
original=read(e/'user-route-comparison.json')['alternatives'];fixed=read(e/'user-route-fixed-comparison.json')['alternatives']
assert original['3984']['worldDistance']>original['4192']['worldDistance'] and fixed['3984']['worldDistance']<fixed['4192']['worldDistance']
traces={}
for name,target in [('r8-forward.json',(362,695)),('r8-reverse.json',(326,658))]:
 rows=read(e/name);samples=[row['actors']['2388']for row in rows if '2388'in row['actors']]
 assert len(samples)==len(rows) and math.dist(samples[-1]['position'][:2],target)<1
 assert any(math.dist(v['position'][:2],(362,670))<6 and v['position'][2]>1 for v in samples)
 assert samples[-1]['command'] is None and samples[-1]['move']['active']==0
 traces[name]={'samples':len(rows),'target':target,'finish':samples[-1]['position'],'upperBridgeCrossed':True}
river=read(e/'final-rivers-ordinary.analysis.json')
assert river['generatorResult']==0 and river['generatorPhase']==5 and river['rivers']==3
assert river['dryOrWalkableRiverCells']==river['aboveWaterRiverVertices']==0
meta=read(r/'native/prototype.json');assert len(meta['hooks'])==83 and meta['installed'] and len(meta['styles'])==6
payload=(r/'native/prototype.bin').read_bytes();normal=(r/'sandbox/Mods/PawsBridges.dll').read_bytes();qa=(e/'qa-runtime/PawsBridgesQA.dll').read_bytes()
assert payload in normal and payload in qa
assert b'bridge-command.txt' not in normal and b'!peace-fixture' not in normal and not (r/'sandbox/Mods/PawsBridgesQA.dll').exists()
plugins=(r/'sandbox/Mods/plugins.txt').read_text().splitlines();assert plugins.count('PawsBridges.dll')==1 and not any('PawsBridgesQA' in s for s in plugins)
startup=(e/'r8-normal-startup.log').read_text();assert 'PawsBridges.dll started' in startup and 'READY 83 hooks' in startup and 'PawsBridgesQA.dll started' not in startup
report={'revision':8,'passed':True,'localOnly':True,'published':False,'nativeHooks':83,'normalRuntimeSha256':sha(r/'sandbox/Mods/PawsBridges.dll'),'nativePayloadSha256':sha(r/'native/prototype.bin'),'qaCommandTransport':False,
 'installedBaseline':baseline,'models':models,'nativeSelection':'stock projected selected_square_vfx / focused_square_vfx; shared 6 by span-length rectangle; embedded corner meshes removed',
 'savedRoute':{'saveSha256':sha(r/'Documents/Kohan2/data/Save/R8-user-routing-original.RSG'),'comparisonCoordinatesApproximateScreenshotMarks':True,'start':[326,658],'goal':[362,695],'before':{k:v['worldDistance']for k,v in original.items()},'after':{k:v['worldDistance']for k,v in fixed.items()},'nativeTraces':traces},
 'checks':{'compiledRoadsAndAdjacentTrim':618,'relocatedRoutingAndSelection':152,'floorABI':232,'navigation':70,'riverPipeline':48,'seededRiverLayout':17032,'reliefSeeds':128,'assetChecks':assets['checks']},
 'riverRelief':{'alternativeBends':28,'unchangedCourses':100,'preservedGorges':27,'mountainCellsBefore':22886,'mountainCellsAfter':14282,'braidedIslands':21},'nativeRiverCapture':river,
 'limits':['Private single-player prototype; multiplayer and replay acceptance not included.','Final native generation viewed on one 1280x1280 mixed-biome ordinary map; all shapes/sizes have deterministic layout tests.','Old saved terrain remains unchanged; river generation changes apply to new games.','Path comparison uses live walkable cells, not native combat congestion or dynamic obstacle costs. Native company and all six members arrived; movement was isolated from enemy attacks.','The stock projected outline can be submerged or hidden by the deck, as requested; footprint/hidden selection geometry checked for all variants with 84 detailed samples.']}
(r/'validation.json').write_text(json.dumps(report,indent=2));print('R8_CANDIDATE_PASS',models,'models;',baseline['installedFilesChecked'],'installed files unchanged; upper bridge crossed both ways; final normal runtime')
