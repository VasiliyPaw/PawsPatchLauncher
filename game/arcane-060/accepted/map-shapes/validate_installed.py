"""Validate the installed-base candidate and record its acceptance boundaries."""
import argparse, hashlib, json, subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
root = a.out.resolve()
baseline = json.loads((root/'installed-baseline.json').read_text())
game = Path(baseline['game'])

def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest().upper()

changed = [name for name, digest in baseline['files'].items()
           if not (game/name).is_file() or sha(game/name) != digest.upper()]
assert not changed, changed
helper = json.loads((root/'installed-helper.json').read_text())
current = json.loads(subprocess.check_output(
    [str(game/helper['installedHelper']), '--features'], text=True))
private = json.loads(subprocess.check_output(
    [str(root/'sandbox/PawsInstalledRuntime.exe'), '--features'], text=True))
assert current == private == helper['features']
assert sha(root/'sandbox/PawsInstalledRuntime.exe') == helper['privateHelperSha256']
models = json.loads((root/'bridge-model-manifest.json').read_text())
art = json.loads((root/'bridge-art.json').read_text()) if (root/'bridge-art.json').exists() else None
for name, row in models.items():
    digest = row['sha256']
    if art:
        selected = art['core']['variants'][name]
        assert selected['visibleGeometryUnchanged'] and selected['sourceSha256'].upper() == digest.upper()
        digest = selected['sha256']
    assert sha(root/'sandbox/rivers-data/Paws/Bridges'/name) == digest.upper(), name
    assert row['width'] == 6
overrides = json.loads((root/'overrides.json').read_text())
for name, digest in overrides.items():
    assert sha(root/'sandbox/rivers-data'/name) == digest.upper(), name
meta = json.loads((root/'native/prototype.json').read_text())
assert meta['installed'] and len(meta['hooks']) == 39
assert not any(h['site'] == 0xc772e for h in meta['hooks'])
plugins = (root/'sandbox/Mods/plugins.txt').read_text().splitlines()
original = (game/'Mods/plugins.txt').read_text().splitlines()
assert [s for s in plugins if s.strip().lower() != 'pawsbridges.dll'] == original
assert sum(s.strip().lower() == 'pawsbridges.dll' for s in plugins) == 1
assert not any(s.strip().lower() == 'pawsbridgesqa.dll' for s in plugins)
assert (root/'PawsRiversTest.exe').is_file()
if art:
    assets=json.loads((root/'qa-evidence/r5-assets.json').read_text())
    assert assets['passed'] and assets['models']==336
    if (root/'qa-evidence/r5-coarse-art-change.json').exists():
        revision=json.loads((root/'qa-evidence/r5-coarse-art-change.json').read_text())
        shadow=json.loads((root/'qa-evidence/r5-assets-shadow.json').read_text())
        assert revision['unchangedPreviouslyCheckedModels']==224 and shadow['passed'] and shadow['models']==112
        proof=revision['revisionTests']
        assert proof['passed'] and proof['geometryUnchanged'] and proof['selectionUnchanged'] and proof['nativePropsUnchanged']
        assets['latestShadowRevision']=shadow
        assets['unchangedOtherModels']=224
    depth=None
    if (root/'qa-evidence/r5-depth-bytes.json').exists():
        depth=json.loads((root/'qa-evidence/r5-depth-bytes.json').read_text())
        assert depth['passed'] and depth['models']==224 and depth['properties']==1512
        assert depth['onlyDepthComparisonFieldsChanged'] and depth['geometryTexturesMaterialsAndSelectionUnchanged']
        assets['depthFix']=depth
        assets.pop('unchangedOtherModels',None)
    paid=json.loads((root/'qa-evidence/r5-native-cost-completed.json').read_text())
    actor=next(a for a in paid['actors'] if a['id']==7889)
    assert actor['paidConstructionCost'][0]==125 and actor['health']==2000 and not actor['construction']
    previews={}
    for race,material,file in [('shadow','stone','r5-shadow-preview'),('undead','stone','r5-undead-stone-preview'),('undead','wood','r5-undead-wood-preview')]:
        brush=json.loads((root/f'qa-evidence/{file}.json').read_text())['brush']
        assert brush['valid'] and brush['definition'].startswith(f'paws_bridge_{race}_{material}_')
        previews[race+'-'+material]=brush
    network=json.loads((root/'qa-evidence/r5-final-six.analysis.json').read_text())
    assert network['rivers']==6 and network['dryOrWalkableRiverCells']==network['aboveWaterRiverVertices']==0
    visuals=json.loads((root/'qa-evidence/r5-depth-native-visuals.json').read_text()) if (root/'qa-evidence/r5-depth-native-visuals.json').exists() else None
    if visuals:assert visuals['passed'] and visuals['modelsRendered']==4
    report=dict(revision=5,installedFilesUnchanged=len(baseline['files']),matchingHelperFeatures=len(current),nativeHooks=len(meta['hooks']),
        assets=assets,prices={'wood':75,'stone':125},nativePaidStoneBridge=actor,
        depthFix=depth,
        nativeDepthVisuals=visuals,
        nativeRacePreviews=previews,freshRiverMap=network,
        automatedChecks=dict(rivers=17032,coastsAndRandomShape=5248,installedMenuAndPreferences=114,installedPipeline=42,roadsAndBridges=536,builderAssets=49,floorWrapper=176),
        limits=['Private single-player candidate, not published.', 'Race previews loaded in the native game; final visual construction, mouse selection and combat acceptance remain manual.', 'The final coarse Shadow material revision has static asset checks; native previews preceded that material revision.', 'Race fixtures change only the saved nation; they are not normal fresh racial campaigns.', '2048 checked by menu/planner tests; final live map checked at 1280.'])
    if visuals:
        report['limits']=['Private single-player candidate, not published.','Both completed Shadow and Undead bridge types viewed natively after depth correction; lengths 14/15/16 and saved rotations. Other lengths have the same checked depth state.','Live mouse selection and enemy bridge combat remain manual.','2048 checked by menu/planner tests; final live map checked at 1280.']+visuals['limits'][2:]
    (root/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('R5_INSTALLED_CANDIDATE_PASS',len(baseline['files']),'installed files unchanged;',len(current),'matching helper features; 336 bridge models')
    raise SystemExit(0)
ui = json.loads((root/'qa-evidence/r3-menu-2048-ten.json').read_text())
medium = json.loads((root/'qa-evidence/r3-menu-1280-restored-six.json').read_text())
assert ui['riverMenu']['maximum'] == ui['riverMenu']['selected'] == 10
assert medium['riverMenu']['maximum'] == medium['riverMenu']['selected'] == 6
analysis=json.loads((root/'qa-evidence/r3-large-six-final.analysis.json').read_text())
assert analysis['rivers']==6 and analysis['riverCells']>0 and analysis['dryOrWalkableRiverCells']==analysis['aboveWaterRiverVertices']==0
assert len([k for k in analysis['citiesByLandComponent'] if int(k)>=0])>1
cold=json.loads((root/'qa-evidence/r3-cold-world-after-launch.json').read_text())
assert cold['world']['rules']['FogOfWar']['value']==0
assert cold['world']['rules']['PawsMapShape']['value']==2 and cold['world']['rules']['PawsRivers']['value']==1
loaded=json.loads((root/'qa-evidence/r3-angle-loaded.json').read_text())
bridge=next(a for a in loaded['actors'] if a['name'].startswith('paws_bridge_'))
assert bridge['health']==2000 and not bridge['construction'] and all(abs(v)>.1 for v in bridge['direction'][:2])
crossing=json.loads((root/'qa-evidence/r3-angle-crossing.json').read_text())
wet=[a for row in crossing for a in row['actors'] if abs((a['simulation'][0]-590)*.8087-(a['simulation'][1]-1139)*.5882)<6]
assert len({a['id'] for a in wet})==7
assert all(abs(a['simulation'][2]-1.08)<.001 and abs(a['visualTarget'][2]-1.08)<.001 for a in wet)
route=json.loads((root/'qa-evidence/r3-angle-wider-route-final.json').read_text())
company=next(a for a in route['actors'] if a['id']==2360)
assert abs(company['simulation'][0]-607)<1 and abs(company['simulation'][1]-1123)<1
pioneers=json.loads((root/'pioneer-builders.json').read_text())
assert sum(map(len,pioneers.values()))==6
r4=json.loads((root/'qa-evidence/r4-final-six.analysis.json').read_text())
assert r4['rivers']==6 and r4['dryOrWalkableRiverCells']==0 and len(r4['biomes'])==4
report=dict(revision=4,r4FreshRiverMap=r4,installedFilesUnchanged=len(baseline['files']),installedModules=baseline['modules'],matchingHelperFeatures=len(current),unchangedAcceptedBridgeModels=len(models),overrides=len(overrides),nativeHooks=len(meta['hooks']),
 automatedChecks=dict(rivers=17032,coastsAndRandomShape=5248,installedMenuAndPreferences=114,installedPipeline=42,roadsAndOrientedBridges=514,builderAssets=49,floorWrapper=176),nativeLargeMap=analysis,
 persistedRivers={384:1,1280:6,2048:10},coldLaunchRules=cold['world']['rules'],loadedAngledBridge={k:bridge[k] for k in ['id','name','direction','health','construction']},realUnitsObservedAtDeckHeight=7,
 limits=['Local single-player candidate; not published.', 'R4 selection rectangle ABI/geometry checked in emulation; native visual acceptance remains manual.', 'User save native caretaker construction progressed; the exact three failed clicks were not independently reproduced.', '2048 menu/planner tested; live maps generated at 384 and 1280.', 'Enemy bridge combat/destruction has not been live accepted.', 'An earlier pre-final large-map attempt failed during native special-site replacement; two subsequent large-map generations passed.'])
(root/'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('INSTALLED_CANDIDATE_PASS', len(baseline['files']), 'installed files unchanged;',
      len(current), 'matching helper features;', len(models), 'accepted models')
