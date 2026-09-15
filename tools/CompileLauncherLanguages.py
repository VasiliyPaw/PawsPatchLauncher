"""Apply launcher-language editorial corrections and audit all authored/current guide keys."""
import argparse,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
TOKEN=re.compile(r'\{[^{}]*\}')
def numbers(s):
    s=TOKEN.sub('',s)
    for word,digit in [('zero','0'),('five','5'),('six','6'),('seven','7')]:
        s=re.sub(r'\b'+word+r'\b',digit,s,flags=re.I)
    s=re.sub(r'(?<=\d)[ ,\u00a0\u202f](?=\d{3}(?!\d))','',s)
    s=re.sub(r'(?<=\d),\s*(?=\d)', '.',s)
    return sorted(re.findall(r'\d+(?:\.\d+)*',s))

def main():
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);a=p.parse_args()
    source=read(a.review/'source-keys.json');overrides=read(ROOT/'tools/uk-ui-corrections.json')
    common=read(ROOT/'tools/ui-language-corrections.json') if (ROOT/'tools/ui-language-corrections.json').exists() else {}
    issues=[];numeric_review=[];result={}
    for code in ['uk','cs','de','fr']:
        values=read(a.review/(code+'-draft.json'))
        for en in source:
            if en not in values and en in common and code in common[en]:values[en]=common[en][code]
            if en not in values:issues.append((code,'missing',en));continue
            value=values[en]
            # Remove spacing artifacts inside format specifiers without touching
            # the external arguments that are substituted at runtime.
            for token in TOKEN.findall(en):
                pattern='\\s*'.join(map(re.escape,token))
                value=re.sub(pattern,lambda m:token,value)
            value=re.sub(r"Paw['’] ?s (Patch|Launcher|Team)",lambda m:"Paw's "+m[1],value)
            for number in re.findall(r'\d+(?:\.\d+)+',en):
                value=re.sub(re.escape(number).replace(r'\.',r'\s*[.,]\s*'),number,value)
            if code=='uk':
                value=re.sub(r"(?<=[А-Яа-яІіЇїЄєҐґ])['’]\s+(?=[А-Яа-яІіЇїЄєҐґ])","'",value)
                value=re.sub(r'«\s+','«',value);value=re.sub(r'\s+»','»',value)
                value=value.replace('лоббі','лобі').replace('Лоббі','Лобі')
                value=value.replace('бета- верс','бета-верс').replace('будь- як','будь-як')
                value=value.replace('запускач','лаунчер').replace('Запускач','Лаунчер')
                if re.search(r'patch',en,re.I):
                    forms={'латка':'патч','латки':'патча','латку':'патч','латок':'патчів','латкою':'патчем','латкам':'патчам','латками':'патчами','латці':'патчі','латках':'патчах'}
                    value=re.sub(r'\b(?:'+ '|'.join(forms)+r')\b',lambda m:forms[m[0]],value)
                    value=re.sub(r'\b(сумісного|нового|старого|вибраного|поточного|обраного) патч\b',r'\1 патча',value)
                    value=value.replace("обов'язкової патча","обов'язкового патча")
                if 'Arcane Wars' in en:value=value.replace('Таємничих воєн','Arcane Wars').replace('Арканські війни','Arcane Wars')
                if 'Dvorak' in en:value=value.replace('Дворака','Dvorak').replace('Дворак','Dvorak')
                if en in overrides:value=overrides[en]
            if en in common and code in common[en]:value=common[en][code]
            if not value.strip():issues.append((code,'empty',en,value))
            if sorted(TOKEN.findall(en))!=sorted(TOKEN.findall(value)):issues.append((code,'format',en,value))
            if numbers(en)!=numbers(value):numeric_review.append((code,en,value))
            if code=='uk' and re.search('[ыэъё]',value,re.I):issues.append((code,'Russian letters',en,value))
            if code in ('cs','de','fr') and re.search('[\u0400-\u04ff]',value):issues.append((code,'Cyrillic',en,value))
            if '\x00' in value or len(value)>max(160,len(en)*3) or re.search(r'(.{6,}?)\1\1',value):issues.append((code,'length/repetition',en,value))
            if re.search(r'Pinterest|Список астерої|wikipedia|Systémové požadavky|Call of Duty|Дискографія',value,re.I):issues.append((code,'unrelated text',en,value))
            values[en]=value
        result[code]=dict(sorted(values.items()))
    save(a.review/'editorial-issues.json',issues)
    save(a.review/'number-review.json',numeric_review)
    print('UI KEYS',len(source),'issues',len(issues))
    for i,x in enumerate(issues):print(i,x[0],x[1],repr(x[2][:100]))
    if issues:raise SystemExit(1)
    for code,values in result.items():save(ROOT/('src/PawsPatchLauncher/Assets/Languages/'+code+'.json'),values)
    save(a.review/'catalog-audit.json',dict(keys=len(source),languages=list(result),missingAuthoredOrGuideKeys=0,invalidPlaceholders=0,numericPhrasesForHumanReview=len(numeric_review)))

if __name__=='__main__':main()
