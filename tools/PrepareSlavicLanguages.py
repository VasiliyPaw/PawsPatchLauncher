"""Build local CS/UK text depots and multilingual patch UI without publishing."""
import argparse,base64,copy,csv,json,re
from pathlib import Path
from CollectSlavicCatalog import BLOCK,ROW,unquote
from PrepareEuropeanModLanguages import source,generate,ROOT,translated_table
from PrepareSplitLanguages import read,write,build,dec,sha
from PrepareEuropeanLanguages import decode

CODES=(('cs','Czech'),('uk','Ukrainian'))
RANDOM={'en':'Random','ru':'Случайно','de':'Zufällig','fr':'Aléatoire','cs':'Náhodně','uk':'Випадково'}
NATIVE_IDS={'en':0,'ru':1,'de':2,'fr':3,'cs':4,'uk':5}

def color_catalog(code,colors):
    with (ROOT/'game/localization/player-colors.tsv').open(encoding='utf-8') as f: names={r['English']:r for r in csv.DictReader(f,delimiter='\t')}
    result={}
    for en,ru in colors.items():
        if code in ('en','ru'):value=en if code=='en' else ru
        else:
            prefix=next((p for p in ('Light ','Dark ') if en.startswith(p)),'');base=names[en[len(prefix):]][code]
            if not prefix:value=base
            elif code=='de':value=('Hell' if prefix=='Light ' else 'Dunkel')+base.lower()
            elif code=='fr':value=base+(' clair' if prefix=='Light ' else ' foncé')
            elif code=='cs':value=('Světle ' if prefix=='Light ' else 'Tmavě ')+base.lower()
            else:value=('Світло-' if prefix=='Light ' else 'Темно-')+base.lower()
        result['color:'+en]=value
    return result

def native_catalog(code,inventory,translated):
    values=color_catalog(code,inventory['colors'])
    for en,ru in inventory['native'].items():
        values[en]=translated[en][code] if code in ('cs','uk') else ru if code=='ru' else en
    lines=['language='+code]
    for key,value in sorted(values.items()):
        lines.append(base64.b64encode(key.encode()).decode()+'\t'+base64.b64encode(value.encode()).decode())
    return ('\n'.join(lines)+'\n').encode('utf-8')

def prepare(a):
    feeds={c:read(a.base/(c+'.payload.json')) for c in ('stable','beta')}
    inventory=read(a.review/'source.json');tables=read(a.review/'english-tables.json')
    translated=read(ROOT/'game/localization/text-cs-uk.json')['entries']
    src={p['id']:p for p in feeds['stable']['packages']};bootstrap=source(src['game-localization-en'],a.cache)['startup/autoexec.txt']
    french=source(src['game-localization-fr'],a.cache)
    versions={};audit={}
    for code,language in CODES:
        depot='Local_base_'+code+'/';files={};key_count=0
        for path,content in tables.items():
            if not BLOCK.search(content):continue
            def replace_block(match):
                def row(m):
                    nonlocal key_count
                    if m[2]=='name' and not path.lower().startswith('maps/'):return m[0]
                    en=unquote(m[4]);key_count+=1
                    value=translated[en][code] if en else en
                    return m[1]+m[2]+m[3]+json.dumps(value,ensure_ascii=False)
                return re.sub(r'(\[Text\s+language\s*=)[^\]]+',r'\g<1> '+language,ROW.sub(row,match[0]))
            target=BLOCK.sub(replace_block,content)
            assert BLOCK.sub('',target)==BLOCK.sub('',content),path
            files[depot+path]=target.encode('utf-16')
        assert len(files)==60,('original string tables',len(files))
        for path,b in french.items():
            if '/Fonts/' not in path:continue
            target=depot+'Fonts/'+path.split('/Fonts/',1)[1]
            files[target]=(ROOT/'game/localization/fonts'/Path(path).name).read_bytes() if path.lower().endswith('.ttf') else b
        locale=dec(next(b for p,b in french.items() if p.endswith('/AVars_Locale.tgi')))
        locale=re.sub(r'(?m)(string\s+LanguageIDS\s*=)[^\r\n]+',r'\g<1> '+language,locale)
        locale=re.sub(r'(?m)(string\s+SKU\s*=)[^\r\n]+',r'\g<1> '+language,locale)
        locale=locale.replace('Initialisation...','Inicializace...' if code=='cs' else 'Ініціалізація...')
        locale=locale.replace('Chargement des données...','Načítání dat...' if code=='cs' else 'Завантаження даних...')
        files[depot+'AVars_Locale.tgi']=locale.encode('utf-16')
        files[depot+'Localization/paws_color_names.tgi']=translated_table('Localization/paws_color_names.tgi',language,{'paws_color_random':RANDOM[code]})
        files['startup/autoexec.txt']=bootstrap
        files['startup/autoexec_ru.txt']=('# Text only; retain the separately selected speech.\r\naddlocaledepot '+depot+'\r\n').encode('ascii')
        files['paws_game_text.ini']=native_catalog(code,inventory,translated)
        files['paws_localization_fonts_license.txt']=(ROOT/'game/localization/fonts/LICENSE_DEJAVU.txt').read_bytes()
        template=dict(id='game-localization-'+code,priority=220,required=False,experimental=False,executableIndependent=True,
            mods=['vanilla','immortals','arcane-wars'],dependsOn=[],name=dict(ru=('Чешский' if code=='cs' else 'Украинский')+' текст',en=language+' text'),
            description=dict(ru='Перевод текста игры, кампании и интерфейса. Озвучка выбирается отдельно.',en='Game, campaign and interface text. Speech is selected separately.'))
        versions[template['id']]=build(a.out,template,'1.0.0-preview.1',files)
        audit[code]=dict(tables=60,keys=key_count,files=len(files),speechFiles=0)
    # Add current-language patch labels for all six text selections. Palette IDs,
    # order and RGB values are untouched and identical across these depots.
    language_ids={'game-localization-en':'en','vanilla-localization-ru':'ru','localization-ru':'ru','game-localization-de':'de','game-localization-fr':'fr'}
    for id,code in language_ids.items():
        old=src[id];files=source(old,a.cache)
        files['paws_game_text.ini']=native_catalog(code,inventory,translated)
        # This tiny independent string table does not replace the stock UI table.
        if code=='en':depot='data/';language='Default'
        else:depot='Local_base_'+code+'/';language={'ru':'Russian','de':'Deutsch','fr':'Français'}[code]
        files[depot+'Localization/paws_color_names.tgi']=translated_table('Localization/paws_color_names.tgi',language,{'paws_color_random':RANDOM[code]})
        versions[id]=build(a.out,old,old['version']+'.text.1',files)
    for feed in feeds.values():
        feed['packages']=[versions.get(p['id'],p) for p in feed['packages']]+[versions['game-localization-'+c] for c,_ in CODES]
    # Reuse the audited mod keys and unchanged RU keyed-data substitutions.
    generate(feeds,a.out,a.cache,codes=CODES,catalog_path=ROOT/'game/localization/mod-cs-uk.json')
    runtime_audit={}
    for channel in ('stable','beta'):
        feed=read(a.out/'feeds'/(channel+'.payload.json'));runtime=a.review/('runtime-'+channel)
        updated=[]
        for package in feed['packages']:
            if package['id'] not in ('pawpatch-core','player-colors','common-ui'):updated.append(package);continue
            original=source(package,a.cache);files=dict(original);changed=[]
            for path in files:
                candidate=runtime/Path(path).name
                if path.lower().endswith('.exe') and candidate.is_file():
                    files[path]=candidate.read_bytes();changed.append(path)
                elif path.lower().endswith('/pcolors.tgi'):
                    text=dec(files[path]);text,count=re.subn(r'(\btext\s*=\s*")#staging_WorldParamsPanel_random_option_text',r'\g<1>#paws_color_random',text)
                    assert count==2,('player color label guards',path,count)
                    files[path]=text.encode('utf-16');changed.append(path)
            if not changed:updated.append(package);continue
            assert all(files[p]==b for p,b in original.items() if p not in changed)
            # The beta helper requires the matching core release identifier.
            # This local-only candidate is distinguished by its signed archive hash.
            version=package['version'] if package['id']=='pawpatch-core' else package['version']+'.text.1'
            release=build(a.out,package,version,files);updated.append(release)
            runtime_audit[channel+':'+package['id']]=dict(helpers=changed,unchangedFiles=len(files)-len(changed))
        feed['packages']=updated;write(a.out/'feeds'/(channel+'.payload.json'),feed)
    write(a.out/'slavic-audit.json',dict(base=audit,runtime=runtime_audit,colors=49,voices=['en','ru','de','fr']))

def main():
    p=argparse.ArgumentParser()
    for key in ('base','review','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();prepare(a)

if __name__=='__main__':main()
