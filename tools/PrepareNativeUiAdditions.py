"""Update only DE/FR native labels and language help in the local test feeds."""
import argparse,base64,json
from pathlib import Path
from PrepareSlavicLanguages import native_catalog
from PrepareEuropeanModLanguages import source,ROOT
from PrepareSplitLanguages import read,write,build

def main():
    p=argparse.ArgumentParser()
    for n in ['base','out','cache','inventory','authored']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve()
    inventory=read(a.inventory);translations=read(ROOT/'game/localization/text-cs-uk.json')['entries']
    pairs=read(a.authored)['pairs'];en=next(k for k in pairs if k.startswith('Choose text and speech separately. Both choices persist'))
    replacements={};audit={}
    for channel in ['stable','beta']:
        feed=read(a.base/(channel+'.payload.json'));original_ids=[p['id'] for p in feed['packages']]
        for i,package in enumerate(feed['packages']):
            if package['id'] not in ('game-localization-de','game-localization-fr'):continue
            cachekey=package['sha256']
            if cachekey not in replacements:
                code=package['id'][-2:];old=source(package,a.cache);files=dict(old)
                files['paws_game_text.ini']=native_catalog(code,inventory,translations)
                changed=[p for p in files if files[p]!=old.get(p)]
                assert changed==['paws_game_text.ini'],changed
                decoded={base64.b64decode(k).decode():base64.b64decode(v).decode() for k,v in (s.split('\t') for s in files['paws_game_text.ini'].decode().splitlines()[1:])}
                assert len(decoded)==103
                assert all(k in decoded for k in inventory['native'])
                assert all(decoded[k]==v for k,v in {base64.b64decode(k).decode():base64.b64decode(v).decode() for k,v in (s.split('\t') for s in old['paws_game_text.ini'].decode().splitlines()[1:])}.items() if k.startswith('color:'))
                replacements[cachekey]=build(a.out,package,package['version']+'.ui.1',files)
                audit[code]=dict(nativeStrings=len(inventory['native']),colorsUnchanged=49,otherFilesUnchanged=len(files)-1)
            feed['packages'][i]=replacements[cachekey]
        def update(value):
            if isinstance(value,dict):
                if isinstance(value.get('bodyEn'),str) and value['bodyEn'].startswith('Choose text and speech separately:'):
                    value['bodyEn']=en;value['bodyRu']=pairs[en]
                if isinstance(value.get('bodyEn'),str) and 'Works with English or Russian text, including file-only mode.' in value['bodyEn']:
                    value['bodyEn']=value['bodyEn'].replace('Works with English or Russian text, including file-only mode.','Works with every supported text language, including file-only mode.')
                    value['bodyRu']='В профиле Dvorak клавиши WASD перемещают камеру, управление стрелками сохраняется. F выбирает союзную метку. Остальные позиционные привязки сохранены; прежнее действие A освобождено для движения камеры.\n\nВыберите Dvorak в настройках игры; патч не переключает профили автоматически. Работает со всеми поддерживаемыми языками текста, в том числе в режиме «Только игровые файлы». Другие профили управления не изменяются.'
                for child in value.values():update(child)
            elif isinstance(value,list):
                for child in value:update(child)
        update(feed)
        assert [p['id'] for p in feed['packages']]==original_ids
        write(a.out/'feeds'/(channel+'.payload.json'),feed)
    write(a.out/'native-ui-audit.json',audit)
    print(json.dumps(audit,ensure_ascii=False))

if __name__=='__main__':main()
