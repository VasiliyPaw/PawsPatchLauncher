"""Validate mode-native packages and the authored roaming-company transfer."""
import argparse,json,re,sys
from pathlib import Path
from build_channels import read_archive,decode
from prepare_beta_data import authored_companies,lair_span,kingdoms,span

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--data',type=Path,required=True);a=p.parse_args()
    specs=json.loads((a.data/'packages.json').read_text());inputs=json.loads((a.stage/'source-packages.json').read_text())
    packages={s['id']:read_archive(a.data/'packages',dict(s,urls=[s['urls'][0].replace('\\','/')])) for s in specs}
    core=read_archive(a.stage/'inputs',inputs['pawpatch-core']);checks=0;report={}
    def check(value,why):
        nonlocal checks
        checks+=1
        assert value,why
    for mode in ('vanilla','immortals'):
        base=a.stage/'source'/mode;companies,_=authored_companies(core,base)
        for id,files in packages.items():
            if mode not in next(s['mods'] for s in specs if s['id']==id):continue
            for rel in files:
                check(not rel.endswith('.sai'),rel)
                check(not any(s in rel for s in ('city_assistant','settlementslots','fractional','foundation_counts')),rel)
                check(not (rel.startswith('data/units/') and rel.endswith('.tgi') and 'ambient/' not in rel),rel)
                check(not rel.startswith(('data/structures/','data/settlements/','data/special/randomactors/')),rel)
        rules=packages['pure-'+mode+'-rules'];template='data/templates/template_rmc_k2.tgi'
        rule_text=decode(rules[template])
        check(rule_text.index('game_type = PLAYABLE')<rule_text.index('[Rule]'),mode+' Rules field before child nodes')
        original_text=decode((base/template).read_bytes())
        for node in re.findall(r'\[(Template \w+)\b',original_text):
            if node in ('Template K2RMC','Template K2AllRMC'):continue
            check(original_text[slice(*span(original_text,node))].replace('\r','')==rule_text[slice(*span(rule_text,node))].replace('\r',''),mode+' unchanged '+node)
        original=kingdoms(decode((base/template).read_bytes()));new=kingdoms(decode(rules[template]))
        for id,(_,_,block) in original.items():check(new[id][2].replace('\r','')==block.replace('\r',''),mode+id)
        for frequency,multiplier in [('standard',1),('x2',2),('x4',4)]:
            for extra in (False,True):
                ident='pure-'+mode+'-roaming-'+frequency+('-with-new' if extra else '-no-new');files=packages[ident]
                unitfile='data/denizencompanies/paws_roaming_companies.tgi'
                check((unitfile in files)==extra,ident)
                if extra:
                    text=decode(files[unitfile]);used=set(re.findall(r'(?mi)^\s*IDS\s*=\s*(paws_roaming_\w+)',text))
                    check(len(used)==13,ident)
                    check(text.replace('\r','')=='\n\n'.join(companies[id] for id in sorted(used)),ident+' exact authored definitions')
                    index=decode((base/'data/index_k2.lst').read_bytes()).lower()
                    check('denizencompanies/*.tgi' in index,'company file loaded')
                for rel,raw in files.items():
                    if not rel.startswith('data/buildings/'):continue
                    stock=(base/rel).read_bytes();text=decode(raw);native=decode(stock)
                    for key in ('health','defense','resource_prefix','reward'):
                        values=lambda t:re.findall(r'(?mi)^\s*'+key+r'\s*=\s*([^\r\n]+)',t)
                        check(values(text)==values(native),ident+' native '+key)
                    if extra:check(set(re.findall(r'organization_ids\s*=\s*(paws_roaming_\w+)',text))<=used,rel)
                    standard=packages['pure-'+mode+'-roaming-standard'+('-with-new' if extra else '-no-new')].get(rel,stock)
                    def rate(b):
                        _,_,body=lair_span(decode(b));values={k:float(v) for k,v in re.findall(r'\b(event_time|event_chance|marauder_chance)\s*=\s*([\d.]+)',body)}
                        return values.get('event_chance',0)*values.get('marauder_chance',0)/values.get('event_time',1)
                    check(abs(rate(raw)-rate(standard)*multiplier)<1e-8,ident+' frequency '+rel)
        report[mode]={'authoredCompanies':13,'nativeUnitsAndCityPlansPreserved':True}
    for lang in ('en','ru','de','fr','cs','uk'):
        files=packages['pure-localization-bot-ui-'+lang]
        prefix='data' if lang=='en' else 'local_ru'
        check(any(k.lower()==prefix+'/localization/paws_nightmare.tgi' for k in files),lang)
        check(files['paws_game_text.ini'].decode('utf-8').startswith('language='+lang+'\n'),lang+' native labels')
        for name in ('paws_nightmare.tgi','paws_pure_beta.tgi'):
            check('data/localization/'+name in files,lang+' base enumeration '+name)
            check(files['data/localization/'+name]==files[prefix+'/localization/'+name],lang+' selected text '+name)
    result={'passed':True,'checks':checks,'modes':report}
    (a.data/'verification.json').write_text(json.dumps(result,indent=2));print('PURE_BETA_DATA_PASS',checks)

if __name__=='__main__':main()
