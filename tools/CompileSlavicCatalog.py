"""Apply editorial corrections and reject lost numbers, formatting or missing text."""
import argparse,csv,json,re
from pathlib import Path
from DraftSlavicTranslation import terms,invariant
from PrepareSplitLanguages import read,write,sha
from PrepareEuropeanModLanguages import ROOT

TOKENS=re.compile(r'%\d+|%[-+0#]*(?:\d+)?(?:\.\d+)?[sdifugxX]|%%|\{\d+(?::[^}]+)?\}')
NUMBERS=re.compile(r'\d+(?:\.\d+)?')

def main():
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);a=p.parse_args()
    src=read(a.review/'source.json');glossary=terms();corrections=read(ROOT/'game/localization/slavic-corrections.json')
    with (ROOT/'game/localization/slavic-tutorials.tsv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f,delimiter='\t'):
            matches=[en for en in src['phrases'] if en.startswith(row['EnglishPrefix'])]
            assert len(matches)==1,('tutorial correction must have one exact source',row['EnglishPrefix'],matches)
            corrections[matches[0]]={'cs':row['cs'],'uk':row['uk']}
    with (ROOT/'game/localization/slavic-spells.tsv').open(encoding='utf-8') as f:spells={r['English']:r for r in csv.DictReader(f,delimiter='\t')}
    with (ROOT/'game/localization/slavic-missions.tsv').open(encoding='utf-8') as f:missions={r['English']:r for r in csv.DictReader(f,delimiter='\t')}
    result={};issues=[];unchanged=[]
    drafts={c:read(a.review/(c+'-refined.json')) for c in ('cs','uk')}
    long_text={c:read(a.review/(c+'-long.json')) if (a.review/(c+'-long.json')).exists() else {} for c in ('cs','uk')}
    first_pass={c:read(a.review/(c+'-draft.json')) for c in ('cs','uk')}
    for en,e in src['phrases'].items():
        values={}
        for c in ('cs','uk'):
            value=drafts[c].get(en)
            # Map-local keys such as kingdom_1 are reused with different names.
            # Their Russian reference must never be borrowed from another map.
            if not any(k.startswith(('Localization/','mod:','native:','palette:')) for k in e['keys']):value=first_pass[c].get(en)
            if en in long_text[c]:value=long_text[c][en]
            if value is None and en.strip().casefold() in glossary:value=glossary[en.strip().casefold()][c]
            if value is None:issues.append((c,'missing',en));continue
            if en.strip().casefold() in glossary:
                value=en[:len(en)-len(en.lstrip())]+glossary[en.strip().casefold()][c]+en[len(en.rstrip()):]
            if en in corrections:value=corrections[en][c]
            mission=re.fullmatch(r'Mission (\d+)(?: : (.+?))?\s*',en)
            if mission:
                value=('Mise ' if c=='cs' else 'Місія ')+mission[1]
                if mission[2]:value+=' : '+missions[mission[2]][c]
                value+=en[len(en.rstrip()):]
            numbered=re.fullmatch(r'(Team|Kingdom|Independent) (\d+)',en)
            if numbered:
                labels={'Team':('Tým','Команда'),'Kingdom':('Království','Королівство'),'Independent':('Nezávislí','Незалежні')}
                value=labels[numbered[1]][0 if c=='cs' else 1]+' '+numbered[2]
            if re.fullmatch(r'[A-Z]|F\d+|0x[0-9A-Fa-f]+|\d+x\d+',en) or en in ('Enter','Tab','Esc','Insert','PageUp','PageDown','End','PrintScreen','MouseX','MouseY','MouseZ','Alt','Shift','Ctrl','RMC','IDS','[data]'):
                value=en
            spell=re.fullmatch(r'(.+?)(\s{3,}Cost:\s*)(\d+)\s+khaldunite shards',en)
            if spell:
                value=spells[spell[1]][c]+'  '+('Cena: '+spell[3]+' khaldunitských střepů' if c=='cs' else 'Вартість: '+spell[3]+' осколків халдуніту')
            numeric_option=re.fullmatch(r'(Very Slow|Slow|Medium|Large|Small|Fast|Very Fast|Cavalry Fast) \((\d+\.\d+)\)',en)
            if numeric_option:
                labels={'Very Slow':('Velmi pomalé','Дуже повільно'),'Slow':('Pomalé','Повільно'),'Medium':('Střední','Середній'),'Large':('Velké','Великий'),'Small':('Malé','Малий'),'Fast':('Rychlé','Швидко'),'Very Fast':('Velmi rychlé','Дуже швидко'),'Cavalry Fast':('Rychlá jízda','Швидка кіннота')}
                value=labels[numeric_option[1]][0 if c=='cs' else 1]+' ('+numeric_option[2]+')'
            elif re.search(r'\d+\.\d+',en):value=re.sub(r'(\d)[,.]\s*(\d)',r'\1.\2',value)
            value=re.sub(r'%\s+(\d+)',r'%\1',value)
            for token in TOKENS.findall(en):
                if ' '+token in en:value=re.sub(r'(?<=[\w])'+re.escape(token),lambda m:' '+m[0],value)
            # Placeholder order follows each language's grammar. Check their
            # identities separately while retaining the exact literal numbers.
            if NUMBERS.findall(TOKENS.sub('',en))!=NUMBERS.findall(TOKENS.sub('',value)):issues.append((c,'numbers',en,value))
            if sorted(TOKENS.findall(en))!=sorted(TOKENS.findall(value)):issues.append((c,'placeholders',en,value))
            if re.findall(r'<[^>]+>',en)!=re.findall(r'<[^>]+>',value):issues.append((c,'markup',en,value))
            if c=='cs' and re.search('[\u0400-\u04ff]',value):issues.append((c,'Cyrillic',en,value))
            if '\x00' in value or len(value)>max(150,len(en)*3) or re.search(r'(.{4,}?)\1\1',value):issues.append((c,'invalid/repetition/length',en,value))
            if re.search(r'pinterest|wikip|Systémové požadavky|Call of Duty|Shadow of the Colossus|Wrath of the Lich King|Список астероїдів',value,re.I):issues.append((c,'unrelated boilerplate',en,value))
            if en and not value:issues.append((c,'empty',en))
            if en==value and re.search('[A-Za-z]',en) and not invariant(en):unchanged.append((c,en,e['keys']))
            values[c]=value
        result[en]=values
    write(a.review/'editorial-issues.json',issues);write(a.review/'unchanged-review.json',unchanged)
    print('Coverage',len(result),'per language; blocking issues',len(issues),'unchanged names/terms',len(unchanged))
    for issue in issues[:25]:print(repr(issue))
    if issues:raise SystemExit(1)
    write(ROOT/'game/localization/text-cs-uk.json',dict(schemaVersion=1,sourceSha256=sha((a.review/'source.json').read_bytes()),entries=result))
    mod=read(ROOT/'game/localization/mod-de-fr.json')['entries'];out={}
    for key,e in mod.items():out[key]=dict(e,**result[e['en']])
    write(ROOT/'game/localization/mod-cs-uk.json',dict(schemaVersion=1,entries=out))
    write(a.review/'catalog-audit.json',dict(uniquePhrases=len(result),modKeys=len(out),languages=['cs','uk'],blockingIssues=0,unchangedNamesAndTerms=len(unchanged),nativeStrings=len(src['native'])))

if __name__=='__main__':main()
