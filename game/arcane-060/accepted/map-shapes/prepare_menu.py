"""Prepare nine isolated shape/climate profiles and six translated UI layouts."""
import argparse,json,re,subprocess,sys,hashlib
from pathlib import Path
from localization import TEXT,LANGUAGES,CLIMATES,SHAPES,profile_id
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'game/lobby-colors')]
from PrepareSplitLanguages import rwd_files,dec
from compact_menu import span
from rivers_data import add_ui,rule_definition

def ui_layout(source,text):
 # Preserve the native list/preview/slider widgets and their callbacks.
 start,end=span(source,'SelectPanel');panel=source[start:end]
 panel=panel.replace('num_visible_items = 15','num_visible_items = 7')
 ls,le=span(panel,'SelectListBox');node=panel[ls:le]
 node=node.replace('num_visible_items = 7','sorted = false\n num_visible_items = 7')
 node=re.sub(r'\bT\s*=\s*15\b','T = 79',node,count=1)
 panel=panel[:ls]+node+panel[le:];source=source[:start]+panel+source[end:]
 ms,me=span(source,'MapSizeDropDown');node=source[ms:me]
 if '[Listbox]' in node:
  lb,le=span(node,'Listbox');brace=node.index('{',lb)+1
  node=node[:brace]+'\n sorted = false\n'+node[brace:]
 else:
  node=node[:-1]+'\n [Listbox]\n sorted = false\n'+node[-1:]
 source=source[:ms]+node+source[me:]
 nodes=''
 for name,label,y in [('PawClimateLabel',text['labels'][0],76),('PawShapeLabel',text['labels'][1],117)]:
  width=110 if name=='PawClimateLabel' else 330
  nodes+=f'''\n [{name} Template=LabelWidget]
 {{
  [View Template=NoVE]
  {{
   L = 57
   T = {y}
   R = +{width}
   B = +20
  }}
  [Label Template=SharedSmallLeftLabelVE]
  {{
   L = 0
   T = 0
   R = +{width}
   B = +20
   text = "{label}"
  }}
 }}\n'''
 nodes+='''
 [PawClimate Template=SharedDropDownWidget]
 {
  [View]
  {
   L = 177
   T = 76
   R = +210
   B = +20
  }
  [Listbox] num_visible_items = 3
 }
'''
 start,end=span(source,'Template SharedRandomMapDialog');return add_ui(source[:end-1]+nodes+source[end-1:],next(k for k,v in TEXT.items() if v is text),span)

def main():
 p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 sandbox=a.out/'sandbox'
 subprocess.run([sys.executable,'-B',str(ROOT/'game/terrain-prototype/prepare.py'),'--game',str(a.game),'--out',str(sandbox)],check=True)
 assert (sandbox/'terrain-prototype.marker').exists() and sandbox.resolve()!=a.game.resolve()
 for name in ['Terrain/Temperate/temperate_road.tgi','Properties/properties_terrains.tgi','RandomMap/rmc_paws_terrain_probe.tgi']:(sandbox/'probe-data'/name).unlink(missing_ok=True)
 fs=rwd_files((a.game/'Data.rwd').read_bytes());sources={c:dec(fs['RandomMap/rmc_'+c+'03.tgi']).replace('\r','') for c in CLIMATES}
 ui=dec(fs['UI/Shared/random_map_dialog.tgi']).replace('\r','')
 for language,text in TEXT.items():
  base=a.out/'locales'/language
  (base/'UI/Shared').mkdir(parents=True,exist_ok=True);(base/'RandomMap').mkdir(exist_ok=True)
  (base/'UI/Shared/random_map_dialog.tgi').write_text(ui_layout(ui,text),encoding='utf-16')
  (base/'Game').mkdir(exist_ok=True)
  (base/'Game/world_rules_k2.tgi').write_text(dec(fs['Game/world_rules_k2.tgi'])+rule_definition(language),encoding='utf-16')
  svars=dec(fs['Game/SVars.tgi']);at=svars.index('{')+1
  (base/'Game/SVars.tgi').write_text(svars[:at]+'\n int PawsRivers = 17\n'+svars[at:],encoding='utf-16')
  for ci,climate in enumerate(CLIMATES):
   source=sources[climate]
   source=re.sub(r'\s*\[TerrainBlob Template=\w*(?:MountainTerrainBlob\d*|Lake(?:Frozen)?TerrainBlob)\]','',source)
   source=re.sub(r'\s*\[TerrainNoise Template=\w+\]','',source)
   for si,shape in enumerate(SHAPES[1:],1):
    ident=profile_id(shape,climate);t=source.replace('IDS = rmc_'+climate+'03','IDS = '+ident)
    t=re.sub(r'\bname\s*=\s*"#[^"]+"','name = "'+text['shapes'][si]+' — '+text['climates'][ci]+'"',t,count=1)
    t=re.sub(r'\bdescription\s*=\s*"#[^"]+"','description = "'+text['descriptions'][si]+'"',t,count=1)
    at=t.rfind('}');extra=''.join(f'\n [MapSize]\n width = {size}\n height = {size}\n recommended_kingdoms_min = 2\n recommended_kingdoms_max = 8\n' for size in [768,1024]);t=t[:at]+extra+t[at:]
    (base/'RandomMap'/('rmc_'+ident+'.tgi')).write_text(t,encoding='utf-16')
 # The helper copies one complete locale before launching its child.
 manifest={str(f.relative_to(a.out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.out/'locales').rglob('*') if f.is_file()}
 (a.out/'menu-manifest.json').write_text(json.dumps(manifest,indent=2))
 print('Prepared 9 profiles x 6 languages, native UI and isolated sandbox:',a.out)
if __name__=='__main__':main()
