from pathlib import Path
import importlib.util,re,json
p=Path(__file__).resolve().parent/'prepare.py';spec=importlib.util.spec_from_file_location('mixed_prepare',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
t=m.read(m.GAME/'data/RandomMap/rmc_temperate03.tgi');a=t.index('IDS = paws_mixed_biomes');t=t[a:];nodes={}
for x in re.finditer(r'\[ActorGroup Template=(\w+)\]\s*\{([^{}]*)\}',t):nodes[x[1]]=x[2]
climate=json.loads((m.OUT/'preparation.json').read_text())['climateGroups'];visible=[];structures=[]
for group in climate:
 node=nodes[group]
 if 'Lair' in group or 'Tech' in group:
  structures.append(group);limit=3.0 if 'LargeLair' in group else 2.0 if 'Tech' in group else 4.5
  lo,hi=map(float,re.search(r'range\s*=\s*([\d.]+),([\d.]+)',node).groups());assert (lo,hi)==(0.,limit),(group,lo,hi)
 if re.search(r'show_ui\s*=\s*true',node):visible.append(group)
assert len(visible)==3 and len(structures)==12,(visible,structures)
(m.OUT/'data-tests.json').write_text(json.dumps(dict(passed=True,visibleClimateControls=visible,internalClimateStructures=structures,fullRangesValidated=True),indent=2));print('SHARED_CONTROLS_DATA_PASS',len(visible),'visible;',len(structures),'native groups')
