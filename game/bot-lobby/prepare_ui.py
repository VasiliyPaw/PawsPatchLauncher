import argparse,json,re,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'lobby-colors'))
from compact_menu import span
TEXT={
 'en':['All bots: Race','All bots: Faction','All bots: Difficulty','Applies to current and new bots. Custom leaves this setting unchanged.'],
 'ru':['Все боты: Раса','Все боты: Фракция','Все боты: Сложность','Применяется к существующим и новым ботам. Пользовательский — оставить этот параметр без изменений.'],
 'de':['Alle KI: Volk','Alle KI: Fraktion','Alle KI: Schwierigkeit','Gilt für vorhandene und neue KI-Spieler. Benutzerdefiniert lässt diese Einstellung unverändert.'],
 'fr':['IA : Peuple','IA : Faction','IA : Difficulté','Pour les IA actuelles et nouvelles. Personnalisé conserve ce réglage.'],
 'cs':['Všichni boti: Rasa','Všichni boti: Frakce','Všichni boti: Obtížnost','Platí pro stávající i nové boty. Vlastní ponechá toto nastavení beze změny.'],
 'uk':['Усі боти: Раса','Усі боти: Фракція','Усі боти: Складність','Застосовується до наявних і нових ботів. Користувацький — залишити цей параметр без змін.']}
def transform(raw,language):
 enc='utf-16' if raw[:2]==b'\xff\xfe' else 'utf-8-sig';s=raw.decode(enc);assert 'PawBotsRace' not in s
 start,end=span(s,'Slots');block=s[start:end];block,n=re.subn(r'B\s*=\s*\+405\b','B = +365',block,count=1);assert n==1;s=s[:start]+block+s[end:]
 nodes=[];labels=TEXT[language]
 for i,kind in enumerate(['Race','Faction','Difficulty']):
  left=55+i*246
  nodes.append(f'''\n    [PawBots{kind}Label Template=LabelWidget]
    {{
        [View Template=NoVE]
        {{
            L = {left}
            T = 428
            R = +233
            B = +20
        }}
        [Label Template=SharedSmallLeftLabelVE]
        {{
            L = 0
            T = 0
            R = +233
            B = +20
            text = "{labels[i]}"
        }}
    }}
    [PawBots{kind} Template=SharedDropDownWidget]
    {{
        ToolTip = "{labels[3]}"
        [View]
        {{
            L = {left}
            T = 448
            R = +233
            B = +20
        }}
        [Listbox]
        num_visible_items = 10
    }}\n''')
 start,end=span(s,'StagingMenu');s=s[:end-1]+''.join(nodes)+s[end-1:]
 return s.encode('utf-16')
def main():
 p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--language',choices=TEXT,required=True);a=p.parse_args()
 for name in ['pcolors','staging']:
  raw=(a.game/'data/UI/Menus'/f'{name}.tgi').read_bytes()
  target=a.out/'after/data/UI/Menus'/f'{name}.tgi';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(transform(raw,a.language))
 print('BOT_LOBBY_UI_PASS',a.language)
if __name__=='__main__':main()
