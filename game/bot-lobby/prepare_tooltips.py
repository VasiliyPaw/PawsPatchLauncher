"""Presentation strings only; never changes handicap definitions or costs."""
from pathlib import Path
import argparse,re

TEXT={
 'en':('Recruitment and construction cost {n}% more.','Recruitment and construction cost {n}% less.','Recruitment and construction: standard cost (0%).','Boobes'),
 'ru':('Найм и строительство дороже на {n}%.','Найм и строительство дешевле на {n}%.','Найм и строительство: обычная стоимость (0%).','Сиске'),
 'de':('Rekrutierung und Bau kosten {n}% mehr.','Rekrutierung und Bau kosten {n}% weniger.','Rekrutierung und Bau: normale Kosten (0%).','Brüstee'),
 'fr':('Recrutement et construction : {n}% plus chers.','Recrutement et construction : {n}% moins chers.','Recrutement et construction : coût normal (0%).','Nénésse'),
 'cs':('Nábor a výstavba jsou o {n}% dražší.','Nábor a výstavba jsou o {n}% levnější.','Nábor a výstavba: běžná cena (0%).','Kozyy'),
 'uk':('Найм і будівництво дорожчі на {n}%.','Найм і будівництво дешевші на {n}%.','Найм і будівництво: звичайна вартість (0%).','Цицьке'),
}
COSTS={'tutor':60,'easy':30,'medium':0,'hard':-30,'impossible':-60}

def transform(raw,language):
 encoding='utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig'
 text=raw.decode(encoding);more,less,normal,body=TEXT[language]
 for key,n in COSTS.items():
  value=normal if n==0 else (more if n>0 else less).format(n=abs(n))
  text,count=re.subn(r'(\bhandicaps_handicap_'+key+r'_description\s*=\s*)"[^"\r\n]*"',lambda m:m[1]+'"'+value+'"',text)
  assert count==1,(key,count)
 key='paws_gold_sound_tooltip'
 if re.search(r'\b'+key+r'\s*=',text):
  text,count=re.subn(r'(\b'+key+r'\s*=\s*)"[^"\r\n]*"',lambda m:m[1]+'"'+body+'"',text);assert count==1
 else:
  end=text.rfind('}');assert end>=0
  text=text[:end]+'\t'+key+' = "'+body+'"\r\n'+text[end:]
 return text.encode(encoding)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--language',choices=TEXT,required=True);a=p.parse_args()
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(transform(a.input.read_bytes(),a.language))
 print('LOCALIZED_TOOLTIPS',a.language)
