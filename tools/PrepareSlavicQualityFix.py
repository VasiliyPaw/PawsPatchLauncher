"""Build a local-only text correction on the current feed, preserving runtime files."""
import argparse,csv,json,re,copy
from pathlib import Path
from CollectSlavicCatalog import BLOCK,ROW,unquote
from PrepareEuropeanModLanguages import source,ROOT,table,translated_table,generate
from PrepareSplitLanguages import read,write,build,dec
from PrepareSlavicLanguages import native_catalog
from GameTextValidation import validate_engine_text,validate_format_tokens
from SlavicEditorial import keyed

LANGUAGES={'en':'Default','ru':'Russian','cs':'Czech','uk':'Ukrainian','de':'Deutsch','fr':'Français'}
SAI_NAME=re.compile(r'(\[SAI\s+template\s*=\s*SAI\]\s*\{\s*IDS\s*=\s*[^\r\n]+\s*name\s*=\s*)"([^"]+)"',re.I)

def prepare(a):
    feeds={c:read(a.base/(c+'.payload.json')) for c in ('stable','beta')}
    packages={p['id']:p for p in feeds['stable']['packages']};versions={};audit={}
    tables=read(a.review/'english-tables.json');inventory=read(a.review/'source.json')
    catalog=read(ROOT/'game/localization/text-cs-uk.json')['entries']
    formats=read(ROOT/'game/localization/slavic-format-strings.json')
    for code in ('cs','uk'):
        old=packages['game-localization-'+code];original=source(old,a.cache);files=dict(original);row_count=0;typed_count=0
        for path,content in tables.items():
            def block(m):
                def row(r):
                    nonlocal row_count,typed_count
                    if r[2]=='name' and not path.lower().startswith('maps/'):return r[0]
                    en=unquote(r[4]);value=catalog[en][code] if en else en
                    value=keyed(path,r[2],en,code,value)
                    validate_engine_text(en,value)
                    if '|' in r[2]:
                        validate_format_tokens(en,value);typed_count+=1
                    row_count+=1
                    return r[1]+r[2]+r[3]+json.dumps(value,ensure_ascii=False)
                return re.sub(r'(\[Text\s+language\s*=)[^\]]+',r'\g<1> '+LANGUAGES[code],ROW.sub(row,m[0]))
            output=BLOCK.sub(block,content)
            assert BLOCK.sub('',output)==BLOCK.sub('',content),path
            files['Local_base_'+code+'/'+path]=output.encode('utf-16')
        files['paws_game_text.ini']=native_catalog(code,inventory,catalog)
        changed=[p for p in files if files[p]!=original[p]]
        assert all(p.lower().endswith('.tgi') and '/fonts/' not in p.lower() or p=='paws_game_text.ini' for p in changed),changed
        versions[old['id']]=build(a.out,old,'1.0.0-preview.3',files)
        audit[code]=dict(rows=row_count,typedRows=typed_count,changedFiles=changed,unchangedFiles=len(files)-len(changed))
    for feed in feeds.values():feed['packages']=[versions.get(p['id'],p) for p in feed['packages']]
    # Regenerate every CS/UK mod string table from the corrected base and terms.
    generate(feeds,a.out,a.cache,codes=(('cs','Czech'),('uk','Ukrainian')),catalog_path=ROOT/'game/localization/mod-cs-uk.json',version='1.0.0-preview.2')
    feeds={c:read(a.out/'feeds'/(c+'.payload.json')) for c in feeds}
    # Name-only changes belong in the shared display-fix package, so every text
    # language uses byte-identical AI definitions. No AI behavior is translated.
    with (ROOT/'game/localization/immortals-ai-names.tsv').open(encoding='utf-8') as f:ai={r['Original']:r for r in csv.DictReader(f,delimiter='\t')}
    imm=source(packages['immortals'],a.cache);fix=source(packages['immortals-text-fixes'],a.cache);fixed=dict(fix);keys={};names_audit=[]
    for path,raw in imm.items():
        if '/sai/' not in path.lower() or not path.lower().endswith('.tgi'):continue
        content=dec(raw);matches=list(SAI_NAME.finditer(content));assert len(matches)==1,path
        original_name=matches[0][2];assert original_name in ai,(path,original_name)
        key='immortals_ai_'+str(len(keys)+1);keys[key]=ai[original_name]
        replacement=SAI_NAME.sub(lambda m:m[1]+'"#'+key+'"',content)
        # The complete original data except this single presentation value must
        # survive. Preserve original encoding and line endings as well.
        encoding='utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8'
        try:raw.decode(encoding)
        except UnicodeDecodeError:encoding='cp1251'
        fixed[path]=replacement.encode(encoding)
        assert dec(fixed[path]).replace('"#'+key+'"','"'+original_name+'"')==content
        assert dec(fixed[path]).replace('"#'+key+'"','"'+original_name+'"').encode(encoding)==raw
        names_audit.append(dict(path=path,old=original_name,key=key))
    assert len(keys)==len(ai)==15
    # Append a dedicated table to each locale; the English fallback is shared.
    path='Localization/strings_immortals_ai.tgi'
    fixed['data/'+path]=translated_table(path,'Default',{k:v['en'] for k,v in keys.items()})
    versions={'immortals-text-fixes':build(a.out,packages['immortals-text-fixes'],'1.0.1-preview.1',fixed)}
    for code in ('ru','cs','uk','de','fr'):
        id='immortals-localization-'+code
        old=next(p for p in feeds['stable']['packages'] if p['id']==id)
        files=source(old,a.cache);files['Local_immortals_'+code+'/'+path]=translated_table(path,LANGUAGES[code],{k:v[code] for k,v in keys.items()})
        versions[id]=build(a.out,old,old['version']+'.names.1',files)
    for channel,feed in feeds.items():
        feed['packages']=[versions.get(p['id'],p) for p in feed['packages']]
        assert len(feed['packages'])==len({p['id'] for p in feed['packages']})==59
        write(a.out/'feeds'/(channel+'.payload.json'),feed)
    audit.update(formattedPhrases=len(formats),aiNames=names_audit,runtimeChanged=False,voiceChanged=False,fontsChanged=False)
    write(a.out/'quality-audit.json',audit)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('base','out','review','cache'):p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();args.out=args.out.resolve();prepare(args)
