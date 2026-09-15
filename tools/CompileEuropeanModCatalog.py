"""One-time catalog compilation from the audited EN/RU key inventory and official terms."""
import argparse, json, sys
from pathlib import Path
from TranslateModCatalog import Translator
from PrepareEuropeanModLanguages import table, source
from PrepareSplitLanguages import read, write

def main():
    p=argparse.ArgumentParser()
    for arg in ('review','feed','out'):p.add_argument('--'+arg,type=Path,required=True)
    args=p.parse_args();tr=Translator(read(args.review/'official-phrases.json'))
    result={}
    for row in read(args.review/'aw-catalog.json'):
        translated=tr.get(row['en']);assert translated,row
        for key in row['keys']: result[key]=dict(en=row['en'],ru=row['ru'],de=translated[0],fr=translated[1])
    packages={p['id']:p for p in read(args.feed)['packages']}
    cache=args.review/'source-packages'
    for id,paths in [('immortals',['data/Localization/strings_immortals_translation.tgi']),
                     ('immortals-text-fixes',['data/Localization/strings_immortals_fixes.tgi']),
                     ('pawpatch-core',['data/Localization/paws_patch_1368_settings.tgi'])]:
        files=source(packages[id],cache)
        for path in paths:
            for key,value in table(files[path]).items():
                translated=tr.get(value);assert translated,(key,value)
                result[key]=dict(en=value,de=translated[0],fr=translated[1])
    for key,value in table((Path(__file__).resolve().parents[1]/'game/city-assistant/localization_en.tgi').read_bytes()).items():
        translated=[value,value] if key.endswith('_icon') else tr.get(value)
        assert translated,(key,value)
        result[key]=dict(en=value,de=translated[0],fr=translated[1])
    write(args.out,dict(schemaVersion=1,entries=result))
    print('Reviewed keys',len(result))

if __name__=='__main__':main()
