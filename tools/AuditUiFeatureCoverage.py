"""Check shipped launcher resources against the selected local patch-guide feeds."""
import argparse,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text('utf-8-sig'))
def main():
    p=argparse.ArgumentParser();p.add_argument('--feeds',type=Path,required=True);p.add_argument('--review',type=Path,required=True);a=p.parse_args()
    authored=read(a.review/'authored-pairs.json')['pairs'];features=set()
    def collect(value):
        if isinstance(value,dict):
            for key,child in value.items():
                if key in ('titleEn','bodyEn') and isinstance(child,str):features.add(child)
                else:collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    for channel in ('stable','beta'):
        feed=read(a.feeds/(channel+'.payload.json'));collect(feed['patchGuide'])
        for mod in feed.get('modGuides',[]):collect(mod.get('patchGuide',{}))
    result={}
    for code in ('uk','cs','de','fr'):
        catalog=read(ROOT/('src/PawsPatchLauncher/Assets/Languages/'+code+'.json'))
        missing=sorted((set(authored)|features)-set(catalog))
        assert not missing,(code,missing)
        result[code]=dict(catalogEntries=len(catalog),authoredUiKeys=len(authored),currentPatchFeatureKeys=len(features),missing=0)
    (a.review/'feature-coverage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
