"""Mode-native beta assets. Stock/Immortals rules are inputs, never AW city plans."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

import build as packaging
from build_channels import decode, read_archive

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'game/lobby-colors'))
from PrepareRelease081 import fetch
from compact_menu import span
from GameplayPresentationData import hide_ambient, AMBIENT

def module(folder,file):
    spec=importlib.util.spec_from_file_location(folder.replace('-','_')+'_'+file,ROOT/'game'/folder/(file+'.py'))
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded);return loaded

button=module('gold-sound-button','prepare')
botui=module('bot-lobby','prepare_ui')
tooltips=module('bot-lobby','prepare_tooltips')
nightmare=module('nightmare-difficulty','prepare')
hotkeys=module('hotkeys','prepare_recruitment_groups')
PATCH='0.4.0-beta.1'

def encoded(text):return text.replace('\r\n','\n').replace('\n','\r\n').encode('utf-16')

def map_template(raw):
    text=decode(raw)
    assert 'paws_random_map' not in text
    # Only declarations and selectable kingdoms/teams/sizes are added. Actor
    # groups, placement weights, camp counts and settlement spacing stay native.
    where=text.index('{',text.index('[Template K2RMC'))+1
    text=text[:where]+'\n\tstring sun = sun_afternoon,sun_morning,sun_dusk,sun_night\n'+text[where:]
    # A bracketless child owns subsequent fields until the next node. Insert
    # after the Rules fields so game_type does not become a Rule field.
    rules=text.index('[Rule]',text.index('[Rules]'))
    text=text[:rules]+'[Rule]\nids = Sun\ndefault = sun_afternoon\n\n'+text[rules:]
    additions=''
    for size in (768,896,1024,1152):
        if re.search(r'\bwidth\s*=\s*'+str(size)+r'\b',text):continue
        additions+=f'\n[MapSize]\nwidth = {size}\nheight = {size}\nrecommended_kingdoms_min = 2\nrecommended_kingdoms_max = 16\n'
    for i in range(9,17):
        assert not re.search(r'IDS\s*=\s*kingdom'+str(i)+r'\b',text,re.I)
        additions+=f'\n[Kingdom Template=RMCKingdomMajor]\n{{\nIDS = kingdom{i:02}\nname = "#paws_pure_kingdom_{i}"\ncolor = blue\nteam = null\nplayable = true\nrequired = false\nSAI_default_ids = null\n}}\n'
    for i in range(5,9):
        assert not re.search(r'IDS\s*=\s*team'+str(i).zfill(2)+r'\b',text,re.I)
        additions+=f'\n[Team]\nIDS = team{i:02}\nname = "#paws_pure_team_{i}"\n'
    _,end=span(text,'Template K2AllRMC')
    return encoded(text[:end-1]+additions+text[end-1:])

def kingdoms(text):
    result={}
    for m in re.finditer(r'\[Kingdom\b[^\]]*\]',text):
        start=m.start();brace=text.index('{',m.end());end=brace+1;depth=1
        while depth:
            depth+=(text[end]=='{')-(text[end]=='}');end+=1
        block=text[start:end];id=re.search(r'(?mi)^\s*IDS\s*=\s*(\S+)',block)[1]
        assert id not in result,id
        result[id]=(start,end,block)
    return result

def hostility(raw,common):
    text=decode(raw);native=kingdoms(text);families=kingdoms(decode(common))
    # Only the three existing independent relation tables and additional
    # nonplayable families are copied, never AW placement, recipes or rules.
    originals=('kingdom_herd','kingdom_indie','kingdom_enemy')
    for id in originals:
        assert id in families and id in native,id
    for id in sorted(originals,key=lambda x:native[x][0],reverse=True):
        a,b,_=native[id];text=text[:a]+families[id][2]+text[b:]
    _,end=span(text,'Template K2RMC')
    labels={'barbarian':'Barbarian_Thing_name','fire_dragon':'dragon_fire_Thing_name','storm':'storm_drake_Thing_name',
            'wolf':'snow_wolf_Thing_name','spider':'spider_giant_name','scorpion':'scorpion_name','rhaksha':'Rhaksha_Thing_name',
            'undead':'skeleton_name','slaan':'slaan_Thing_name','dark_rift':'shadow_name',
            **{n:n+'_name' for n in ('human','haroun','drauga','gauri')}}
    extras=[]
    for id,(_,_,block) in families.items():
        if not id.startswith('paws_'):continue
        assert 'Template=RMCKingdomMinor' in block and not re.search(r'playable\s*=\s*true',block)
        label=labels.get(id.removeprefix('paws_war_'),'template_rmc_k2_kingdom_indie_name')
        block,n=re.subn(r'(?mi)^(\s*name\s*=\s*)"[^"]*"',lambda m:m[1]+'"#'+label+'"',block);assert n==1
        extras.append(block)
    additions='\n'.join(extras);assert len(extras)==18
    return encoded(text[:end-1]+additions+'\n'+text[end-1:])

def lair_span(text):
    m=re.search(r'\[LairComponent\]',text);assert m
    start=m.start();body=m.end()
    tail=re.match(r'\s*',text[body:]).end()+body
    if text[tail]=='{':
        end=tail+1;depth=1
        while depth:
            depth+=(text[end]=='{')-(text[end]=='}');end+=1
        return start,end,text[tail+1:end-1]
    end=body
    while end<len(text) and text[end] not in '[}':end+=1
    return start,end,text[body:end]

def component(text,name):
    m=re.search(r'\['+re.escape(name)+r'(?:\s[^\]]*)?\]',text);assert m,name
    start=m.start();brace=text.index('{',m.end());end=brace+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return start,end,text[start:end]

def authored_companies(core,base):
    # Import only the already authored company definitions. Their units,
    # templates and layouts are supplied by the selected game mode.
    native='\n'.join(decode(p.read_bytes()) for p in (base/'data').rglob('*.tgi'))
    ids={s.lower() for s in re.findall(r'(?mi)^\s*ids\s*=\s*([^\s;]+)',native)}
    templates={s.lower() for s in re.findall(r'\[Template\s+(\w+)',native,re.I)}
    result={}
    for path,raw in sorted(core.items()):
        if not path.startswith('data/units/') or not path.endswith('.tgi'):continue
        text=decode(raw).replace('\r','')
        for m in re.finditer(r';; PAW[^\n]*ROAMING COMPANY BEGIN\n(.*?)\n;; PAW[^\n]*ROAMING COMPANY END',text,re.S):
            block=m[1];id=re.search(r'(?mi)^\s*IDS\s*=\s*(\S+)',block)[1]
            refs={s.lower() for s in re.findall(r'(?mi)^\s*(?:element_IDS|layout_IDS|banner_IDS)\s*=\s*(\S+)',block)}-{'null'}
            parents={s.lower() for s in re.findall(r'\btemplate\s*=\s*(\w+)',block,re.I)}
            if not refs<=ids or not parents<=templates:continue
            assert id.startswith('paws_roaming_') and id not in ids and id not in result,id
            result[id]=block
    return result,ids

def additional_roaming(raw,authored,companies,ids):
    text=decode(raw);source=decode(authored)
    refs=set(re.findall(r'organization_ids\s*=\s*(paws_roaming_\w+)',source,re.I))
    if not refs:return raw,set()
    assert refs<=companies.keys(),refs-companies.keys()
    a,b,_=component(text,'DenizenComponent');_,_,replacement=component(source,'DenizenComponent')
    assert set(re.findall(r'actor_ids\s*=\s*(\w+)',replacement))<=ids
    text=text[:a]+replacement+text[b:]
    a,b,body=lair_span(text);_,_,authored_body=lair_span(source)
    # Keep native rewards and non-spawning lair properties.
    for key in ('event_time','event_chance','marauder_chance','spawn_max'):
        m=re.search(r'\b'+key+r'\s*=\s*([\d.]+)',authored_body)
        if not m:continue
        if re.search(r'\b'+key+r'\s*=',body):body=re.sub(r'(\b'+key+r'\s*=\s*)[\d.]+',lambda n:n[1]+m[1],body)
        else:body+='\n'+key+' = '+m[1]+'\n'
    return encoded(text[:a]+'[LairComponent]\n{'+body+'}\n'+text[b:]),refs

def roaming(raw,multiplier):
    text=decode(raw)
    if '[LairComponent]' not in text:return raw
    start,end,body=lair_span(text)
    def field(name):
        m=re.search(r'\b'+name+r'\s*=\s*([\d.]+)',body);return float(m[1]) if m else 0
    time=field('event_time');chance=field('event_chance');marauder=field('marauder_chance')
    if multiplier==1 or not(time and chance and marauder):return raw
    new_chance=min(chance*(1.5 if multiplier==2 else 2),1)
    new_time=time*new_chance/chance/multiplier
    for key,value in [('event_time',new_time),('event_chance',new_chance)]:
        body=re.sub(r'(\b'+key+r'\s*=\s*)[\d.]+',lambda m:m[1]+format(value,'.8g'),body)
    assert abs((new_chance/new_time)/(chance/time)-multiplier)<1e-8
    return encoded(text[:start]+'[LairComponent]\n{'+body+'}\n'+text[end:])

def random_map(raw):
    text=decode(raw); clone=text[text.index('[RMC'):]
    clone,n=re.subn(r'(?mi)^(\s*IDS\s*=\s*)\S+',r'\1paws_random_map',clone,count=1);assert n==1
    clone=re.sub(r'(?mi)^(\s*(?:name|description)\s*=\s*)"[^"\r\n]*"',r'\1"#staging_WorldParamsPanel_random_option_text"',clone,count=2)
    clone=re.sub(r'(\[Terrain(?:Blob|Streak)\s+[^\]]+\])',r'\1\n\tbool show_ui = false\n\tbool override_same = false',clone)
    return encoded(text+'\n'+clone)

LABELS={
 'en':('Time of day','Day','Morning','Dusk','Night','Kingdom','Team'),
 'ru':('Время суток','День','Утро','Сумерки','Ночь','Королевство','Команда'),
 'de':('Tageszeit','Tag','Morgen','Abenddämmerung','Nacht','Königreich','Team'),
 'fr':('Heure du jour','Jour','Matin','Crépuscule','Nuit','Royaume','Équipe'),
 'cs':('Denní doba','Den','Ráno','Soumrak','Noc','Království','Tým'),
 'uk':('Час доби','День','Ранок','Сутінки','Ніч','Королівство','Команда')}

def locale(language):
    names=LABELS[language];pairs={f'paws_pure_sun_{i}':names[i] for i in range(5)}
    pairs.update({f'paws_pure_kingdom_{i}':names[5]+' '+str(i) for i in range(9,17)})
    pairs.update({f'paws_pure_team_{i}':names[6]+' '+str(i) for i in range(5,9)})
    return encoded('[Text language=default]\n{\nids = Localization/paws_pure_beta.tgi\nname = "@Localization/paws_pure_beta.tgi"\n'+''.join(f'{k} = "{v}"\n' for k,v in pairs.items())+'}\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','source','out','packages'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);packages=json.loads(a.packages.read_text())
    def archive(id):
        spec=packages[id];path=a.inputs/Path(spec['urls'][0]).name
        if not path.exists():path.write_bytes(fetch(spec['urls'][0]))
        return read_archive(a.inputs,spec)
    pure=archive('pure-fixes-data');common=archive('common-ui');colors=archive('pure-player-colors');aw=archive('pawpatch-core')
    additional=archive('roaming-profile-standard-with-new')
    result=[]
    def emit(id,files,priority,name,mods=('vanilla','immortals'),deps=()):
        spec=packaging.package(a.out,id,PATCH,files,False,priority,{'en':name,'ru':name},{'en':name,'ru':name})
        spec.update(mods=list(mods),dependsOn=list(deps),experimental=True);result.append(spec)
    # Existing Pure data are retained. Native-only enhancements live elsewhere
    # so file-only mode remains valid for older game executables.
    spec=packaging.package(a.out,'pure-fixes-data',PATCH,pure,True,900,packages['pure-fixes-data']['name'],packages['pure-fixes-data']['description']);result.append(spec)
    shared={n:v for n,v in common.items() if re.fullmatch(r'data/ui/(?:800/|1280/)?game/controlpanel/background\.tga',n)}
    assert len(shared)==3
    shared.update({'data/ui/game/pawgoldsound.png':(ROOT/'game/gold-sound-button/PawGoldSound.png').read_bytes(),
                   'data/audio/paws_gold_button.tgi':(ROOT/'game/gold-sound-button/audio.tgi').read_bytes()})
    base=a.source/'vanilla'
    shared['data/ui/game/game_interface.tgi']=button.add_button((base/'data/ui/game/game_interface.tgi').read_bytes(),(ROOT/'game/gold-sound-button/button.tgi').read_text())
    # Input fixes cover the base language and both Russian mount paths.
    for n,v in common.items():
        if n.endswith('/hotkeys/hotkeys_favorites.txt'):shared[n]=v
    # Guard and animation resources only: never AW units, balance or SAI files.
    shared['d3d9.dll']=aw['d3d9.dll']
    for n,v in aw.items():
        if n.startswith(('data/units/human/ranger/','data/units/ceyah/prophet/')) and n.endswith('.kf'):shared[n]=v
    emit('pure-beta-common',shared,930,"Paw's Patch beta: shared engine and interface",deps=('menu-runtime',))
    ai={'data/game/handicaps_paws_nightmare.tgi':encoded(nightmare.DEFINITION),
        'data/properties/paws_handicap_nightmare.tgi':encoded(nightmare.PROPERTY)}
    emit('pure-ai-improvements',ai,960,'Improved bots',deps=('pure-beta-common',))
    emit('pure-lair-recovery',{'paws_pure_lair.ini':b'[PawPure]\nWoundedDefenders=1\n'},961,'Wounded lair defenders',deps=('pure-beta-common',))
    emit('pure-independent-hostility',{'paws_pure_hostility.ini':b'[PawPure]\nIndependentHostility=1\n'},962,'Independent hostility',deps=('pure-beta-common',))
    for language in LABELS:
        files={};menus={}
        # Native UI labels are read independently of the mounted game depot.
        # Vanilla Russian has no catalog; the helper has built-in RU/EN text.
        text_package='vanilla-localization-ru' if language=='ru' else 'game-localization-'+language
        files['paws_game_text.ini']=archive(text_package).get('paws_game_text.ini',('language='+language+'\n').encode('utf-8'))
        for name,raw in [('staging',(base/'data/ui/menus/staging.tgi').read_bytes()),('pcolors',colors['data/ui/menus/pcolors.tgi'])]:
            menus['data/ui/menus/'+name+'.tgi']=botui.transform(raw,language)
        files.update(menus)
        if language=='en':strings=(base/'data/localization/strings_data_k2.tgi').read_bytes()
        else:
            id='vanilla-localization-ru' if language=='ru' else 'game-localization-'+language
            candidates=[v for n,v in archive(id).items() if n.endswith('/strings_data_k2.tgi')]
            assert candidates and all(v==candidates[0] for v in candidates),language
            strings=candidates[0]
        prefix='data' if language=='en' else 'Local_ru'
        files[prefix+'/Localization/strings_data_k2.tgi']=tooltips.transform(strings,language)
        files[prefix+'/Localization/paws_pure_beta.tgi']=locale(language)
        # The definitions are optional; extra localized names alone add no handicap.
        files[prefix+'/Localization/paws_nightmare.tgi']=encoded(nightmare.locale(language))
        # The engine enumerates new localization files in the base depot,
        # then applies language overlays. An overlay-only file is not loaded.
        for name in ('paws_pure_beta.tgi','paws_nightmare.tgi'):
            files['data/Localization/'+name]=files[prefix+'/Localization/'+name]
        emit('pure-localization-bot-ui-'+language,files,1450,'Bot interface: '+language,deps=('pure-beta-common',))
    for mode in ('vanilla','immortals'):
        base=a.source/mode
        companies,native_ids=authored_companies(aw,base)
        changes={}
        rel='data/templates/template_rmc_k2.tgi';changes[rel]=map_template((base/rel).read_bytes())
        rel='data/randommap/rmc_temperate03.tgi';changes[rel]=random_map((base/rel).read_bytes())
        rel='data/game/svars.tgi';text=decode((base/rel).read_bytes())
        text,n=re.subn(r'(\bKingdomsMax\s*=\s*)\d+',r'\g<1>16',text);assert n==1
        changes[rel]=encoded(text)
        rel='data/game/world_rules_k2.tgi';text=decode((base/rel).read_bytes())
        assert not re.search(r'\bids\s*=\s*Sun\b',text,re.I)
        text+='\n[WorldRule Template=WorldRule]\n{\nids = Sun\nname = "#paws_pure_sun_0"\ndescription = "#paws_pure_sun_0"\ntype = enum\ndefault = sun_random\n'
        for i,id in enumerate(('sun_afternoon','sun_morning','sun_dusk','sun_night'),1):text+=f'[EnumValue]\nids = {id}\nname = "#paws_pure_sun_{i}"\n'
        text+='[EnumValue]\nids = sun_random\nname = "#staging_WorldParamsPanel_random_option_text"\n}\n';changes[rel]=encoded(text)
        for rel in sorted(AMBIENT):
            if (base/rel).is_file():changes[rel]=hide_ambient(rel,(base/rel).read_bytes())
        emit('pure-'+mode+'-rules',changes,935,'Maps and limits: '+mode,(mode,),('pure-beta-common',))
        template='data/templates/template_rmc_k2.tgi'
        emit('pure-'+mode+'-hostility',{template:hostility(changes[template],common[template])},970,'Independent families: '+mode,(mode,),('pure-independent-hostility',))
        for frequency,multiplier in [('standard',1),('x2',2),('x4',4)]:
            for extra in (False,True):
                files={};used=set()
                for path in sorted((base/'data/buildings').rglob('*.tgi')):
                    if path.parent.name not in ('lairsmonster','camps'):continue
                    if path.name.startswith('tutorial_'):continue
                    rel=path.relative_to(base).as_posix();raw=path.read_bytes();changed=raw
                    if extra and rel in additional:
                        changed,refs=additional_roaming(raw,additional[rel],companies,native_ids);used.update(refs)
                    changed=roaming(changed,multiplier)
                    if changed!=raw:files[rel]=changed
                if extra:
                    assert len(used)==13,(mode,used)
                    files['data/denizencompanies/paws_roaming_companies.tgi']=encoded('\n\n'.join(companies[id] for id in sorted(used)))
                # Even ×1/original has an identity so switching back removes
                # every optional overlay through the normal installer ledger.
                files['paws_pure_roaming.ini']=f'[PawPure]\nMode={mode}\nFrequency={frequency}\nAdditional={int(extra)}\n'.encode()
                emit('pure-'+mode+'-roaming-'+frequency+('-with-new' if extra else '-no-new'),files,980,'Roaming '+frequency+': '+mode,(mode,),('pure-beta-common',))
    (a.out/'packages.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('PURE_BETA_DATA_PREPARED',len(result),'packages')

if __name__=='__main__':main()
