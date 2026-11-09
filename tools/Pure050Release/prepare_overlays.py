"""Preserve biome/map additions under higher-priority optional Pure overlays."""
import re,zipfile,shutil
from context import *
from prepare_world import alias,BIOMES,block,clean
from rwd import entries,decode
from PrepareRelease070 import validate_package

def expand(text):
 _,end,_=block(text,'[Template K2AllRMC');extra=''
 for size in range(1280,2049,128):
  assert not re.search(r'\bwidth\s*=\s*'+str(size)+r'\b',text)
  extra+=f'\n[MapSize]\nwidth = {size}\nheight = {size}\nrecommended_kingdoms_min = 2\nrecommended_kingdoms_max = 16\n'
 return text[:end-1]+extra+text[end-1:]

def main():
 out=OUT/'optional-data-r1';out.mkdir(exist_ok=False);stock=entries(OUT/'stable-fixtures/vanilla/game/Data.rwd')
 terrains={b:re.findall(r'(?im)^\s*terrain_ids\s*=\s*(\w+)',clean(decode(stock['data/terrain/'+b+'.tgi'])))for b in BIOMES}
 rows=read(OUT/'before/feed/v3/beta.payload.json')['packages'];report={}
 for row in rows:
  if not any(row['id'].startswith('pure-'+m+'-')for m in ['vanilla','immortals'])or not any(x in row['id']for x in ['roaming','hostility']):continue
  original=WS/'outputs/release-pure-040-20261013/publication-final/packages'/row['urls'][0].rsplit('/',1)[1];validate_package(original,row)
  target=out/'inputs'/original.name;target.parent.mkdir(exist_ok=True);shutil.copy2(original,target)
  changed={}
  with zipfile.ZipFile(original)as z:
   for n in z.namelist():
    if not n.startswith('payload/')or not n.lower().endswith('.tgi'):continue
    text=decode(z.read(n));result=expand(text)if n.lower().endswith('/template_rmc_k2.tgi')else alias.aliases(text,terrains)
    if result!=text:
     dest=out/row['id']/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(result,encoding='utf-16');changed[n[8:]]=sha(dest)
  report[row['id']]=dict(original=row,input=str(target),changed=changed)
 write(out/'preparation.json',report);print('PURE_OPTIONAL_OVERLAYS',len(report),'checked;',sum(bool(r['changed'])for r in report.values()),'need updated payloads')
if __name__=='__main__':main()
