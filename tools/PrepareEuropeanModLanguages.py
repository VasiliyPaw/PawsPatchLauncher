"""Build local-only mod text packages from reviewed keys and verified release inputs."""
import argparse, copy, json, re, urllib.request
from pathlib import Path
from PrepareSplitLanguages import build, read, write, readpkg, sha, dec
from PrepareEuropeanLanguages import decode

ROOT = Path(__file__).resolve().parents[1]
RX = re.compile(r'^\s*([\w.]+)\s*=\s*"((?:\\.|[^"\\])*)"', re.M)

def table(raw):
    return {k: v for k, v in RX.findall(dec(raw)) if k != 'name'}

def source(package, cache):
    local = copy.deepcopy(package)
    url = package['urls'][0]
    if url.startswith('https://'):
        path = cache / (package['id']+'-'+package['version']+'.zip')
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with urllib.request.urlopen(url, timeout=90) as response: raw=response.read()
            assert len(raw)==package['size'] and sha(raw)==package['sha256'].upper(), package['id']
            path.write_bytes(raw)
        local['urls']=[str(path)]
    return readpkg(local)

def translated_table(path, language, values):
    assert all(not re.search(r'[\r\n"]', key) for key in values)
    lines=['[Text language = '+language+']','{','\tids = '+path,'\tname = "@'+path+'"']
    # Values from existing TGI tables already contain escaped strings.
    lines += ['\t'+k+' = "'+v+'"' for k,v in values.items()]
    return ('\r\n'.join(lines+['}'])+'\r\n').encode('utf-16')

def generate(feeds, out, cache, codes=(('de','Deutsch'),('fr','Français')), catalog_path=None):
    catalog=read(catalog_path or ROOT/'game/localization/mod-de-fr.json')['entries']
    audit={};built={}
    for channel,feed in feeds.items():
        packages={p['id']:p for p in feed['packages']}
        src={id:source(packages[id],cache) for id in ('pawpatch-core','aw-localization-ru','pawpatch-data-ru','immortals','immortals-text-fixes')}
        english=table(src['pawpatch-core']['data/Localization/strings_data_K2.tgi'])
        additions=[]
        for code,language in codes:
            base=source(packages['game-localization-'+code],cache)
            official=table(next(v for k,v in base.items() if k.lower().endswith('strings_data_k2.tgi')))
            def dictionary(path, reference, complete=False):
                values=dict(official) if complete else {}
                for key,en in reference.items():
                    if key in catalog:
                        entry=catalog[key]
                        assert entry['en']==en,(key,en,entry['en'])
                        value=entry[code]
                        assert value and (code=='uk' or not re.search('[\u0400-\u04ff]',value)),(key,value)
                        # No altered costs, numeric labels, or printf/string placeholders.
                        assert re.findall(r'\d+(?:\.\d+)?',en)==re.findall(r'\d+(?:\.\d+)?',value),(key,en,value)
                        assert re.findall(r'%(?:\d+\$)?[-+0-9.]*[sdif]|\{\d+\}',en)==re.findall(r'%(?:\d+\$)?[-+0-9.]*[sdif]|\{\d+\}',value),(key,en,value)
                        values[key]=json.dumps(value,ensure_ascii=False)[1:-1]
                    elif key in official:values[key]=official[key]
                    else:
                        assert not key.startswith(('awloc_','immortals_','paws_patch_')),key
                        values[key]=en
                raw=translated_table(path,language,values)
                assert table(raw)==values and len(RX.findall(dec(raw)))==len(values)+1,path
                return raw
            for variant in ('immortals-localization','localization','aw-localization','pawpatch-data'):
                id=variant+'-'+code
                mod='immortals' if variant=='immortals-localization' else 'arcane-wars'
                depot='Local_'+('immortals' if mod=='immortals' else 'aw')+'_'+code+'/'
                files={};priority=225;depends=[mod,'game-localization-'+code]
                if variant=='immortals-localization':
                    for part,name in [('immortals','strings_immortals_translation.tgi'),('immortals-text-fixes','strings_immortals_fixes.tgi')]:
                        path='Localization/'+name
                        files[depot+path]=dictionary(path,table(src[part]['data/'+path]))
                else:
                    reference=english
                    if variant=='aw-localization':
                        # Reuse the reviewed RU display-reference substitutions exactly.
                        # No runtime, fonts, voices, hotkeys, or gameplay values are changed.
                        files={k:v for k,v in src['aw-localization-ru'].items() if k.lower().startswith('data/')}
                        keys=table(src['aw-localization-ru']['Local_aw_ru/Localization/strings_data_K2.tgi'])
                        assert all(k in english for k in keys)
                        reference={k:english[k] for k in keys}
                    elif variant=='pawpatch-data':
                        files=dict(src['pawpatch-data-ru']);priority=900
                        # The language choice only selects existing keyed names in this template.
                        # Other content remains byte-identical to the released RU file-only patch.
                        depends+=['aw-localization-'+code]
                    else:depends+=['pawpatch-core']
                    path='Localization/strings_data_K2.tgi'
                    files[depot+path]=dictionary(path,reference,complete=True)
                    if variant!='aw-localization':
                        path='Localization/paws_patch_1368_settings.tgi'
                        files[depot+path]=dictionary(path,table(src['pawpatch-core']['data/'+path]))
                        path='Localization/paw_city_policy.tgi'
                        files[depot+path]=dictionary(path,table((ROOT/'game/city-assistant/localization_en.tgi').read_bytes()))
                files['startup/autoexec_ru.txt']=('# Text only; speech is selected independently.\r\naddlocaledepot Local_base_'+code+'/\r\naddlocaledepot '+depot+'\r\n').encode('ascii')
                assert not any(k.lower().endswith(('.exe','.dll','.rwd','.wav','.mp3','.ttf')) for k in files)
                # A translated file-only package must not replace any additional gameplay bytes.
                originals=src.get('aw-localization-ru' if variant=='aw-localization' else 'pawpatch-data-ru' if variant=='pawpatch-data' else '',{})
                for path,raw in files.items():
                    if path.lower().startswith('data/'):assert originals[path]==raw,path
                # Every added mod reference in gameplay data must resolve in its mounted text.
                resolved={k for p,b in files.items() if p.startswith(depot) for k in table(b)}
                for path,raw in files.items():
                    if path.lower().startswith('data/') and path.lower().endswith('.tgi'):
                        refs=set(re.findall(r'#((?:awloc_|immortals_)[\w]+)',dec(raw)))
                        assert refs<=resolved,(path,refs-resolved)
                version='1.0.0-preview.1'
                template=dict(id=id,priority=priority,required=False,experimental=False,executableIndependent=True,mods=[mod],dependsOn=depends,
                    name=dict(ru={'de':'Немецкий','fr':'Французский','cs':'Чешский','uk':'Украинский'}[code]+' текст — '+('Immortals' if mod=='immortals' else 'Arcane Wars'),en=language+' — '+mod),
                    description=dict(ru='Перевод названий, описаний и подсказок мода. Озвучка выбирается отдельно.',en='Translated mod names, descriptions and tooltips. Speech is selected independently.'))
                if id in built:
                    assert built[id][0]==files,(channel,id,'different channel text requires a distinct package version')
                    release=copy.deepcopy(built[id][1])
                else:
                    release=build(out,template,version,files);built[id]=(files,release)
                additions.append(release)
                audit[id]=dict(files=len(files),translatedKeys=len(resolved & set(catalog)),gameplayFilesUnchanged=sum(p.lower().startswith('data/') for p in files))
        ids={p['id'] for p in additions}
        feed['packages']=[p for p in feed['packages'] if p['id'] not in ids]+additions
        for p in feed['packages']:
            if p['id'] in ('game-localization-de','game-localization-fr'):
                p['description']=dict(ru='Перевод оригинальной игры. Перевод выбранного мода подключается отдельно.',en='Original game translation. The selected mod translation is added separately.')
        write(out/'feeds'/(channel+'.payload.json'),feed)
    write(out/'mod-language-audit.json',dict(keys=len(catalog),packages=audit))

def main():
    p=argparse.ArgumentParser()
    for name in ('base','out','source-cache'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    feeds={c:read(args.base/(c+'.payload.json')) for c in ('stable','beta')}
    generate(feeds,args.out.resolve(),args.source_cache)

if __name__=='__main__':main()
