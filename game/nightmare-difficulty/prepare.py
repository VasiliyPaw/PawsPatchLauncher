"""Add a stable sixth economic handicap. Existing definitions are untouched."""
import argparse,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
TEXT={
 'en':('Nightmare','Recruitment and construction cost 90% less. Uses the hard AI behavior. Upkeep, build times and company and kingdom-point limits are unchanged.'),
 'ru':('Кошмар','Найм и строительство дешевле на 90%. Используется сложный профиль поведения ботов. Содержание, время строительства и лимиты рот и очков королевства не меняются.'),
 'de':('Albtraum','Rekrutierung und Bau kosten 90% weniger. Verwendet das schwere KI-Verhalten. Unterhalt, Bauzeiten sowie Kompanie- und Königreichspunktelimits bleiben unverändert.'),
 'fr':('Cauchemar','Le recrutement et la construction coûtent 90% de moins. Utilise le comportement difficile de l’IA. L’entretien, les temps de construction et les limites de compagnies et de points de royaume restent inchangés.'),
 'cs':('Noční můra','Nábor a výstavba jsou o 90% levnější. Používá obtížné chování AI. Údržba, doba výstavby a limity rot a bodů království se nemění.'),
 'uk':('Кошмар','Найм і будівництво дешевші на 90%. Використовується складний профіль поведінки ботів. Утримання, час будівництва та ліміти рот і очок королівства не змінюються.'),
}
DEFINITION='''[Handicap Template=Handicap]
{
    IDS = handicap_paws_nightmare
    name = "#paws_handicap_nightmare_name"
    description = "#paws_handicap_nightmare_description"
    property_ids = property_handicap_paws_nightmare
}
'''
PROPERTY='''[Property Template=SharedProperty]
{
    IDS = property_handicap_paws_nightmare
    name = "#paws_handicap_nightmare_name"
    icon = /Properties/%s/PropertyIcons/IconPropertyEconomic.png
    required_properties = settlement
    is_technology = true
    [Modifier Template=MultiplyModifier]
    attribute = STRUCTURE_COST
    amount = +0.90
    [Modifier Template=MultiplyModifier]
    attribute = RECRUIT_COST
    amount = +0.90
}
'''
def locale(code):
 name,desc=TEXT[code]
 return '[Text language = default]\n{\n    ids = Localization/paws_nightmare.tgi\n    name = "@Localization/paws_nightmare.tgi"\n    paws_handicap_nightmare_name = "'+name+'"\n    paws_handicap_nightmare_description = "'+desc+'"\n}\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--language',choices=TEXT,default='ru');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 # index_k2.lst loads Game/handicaps*.tgi, not every file in Game/.
 files={'data/Game/handicaps_paws_nightmare.tgi':DEFINITION,'data/Properties/paws_handicap_nightmare.tgi':PROPERTY,'data/Localization/paws_nightmare.tgi':locale('en')}
 if a.language!='en':files['Local_ru/Localization/paws_nightmare.tgi']=locale(a.language)
 manifest=[]
 for path,content in files.items():
  dest=a.out/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content.replace('\n','\r\n').encode('utf-16'))
  manifest.append(dict(path=path,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
 for code in TEXT:
  dest=a.out/'localization'/f'{code}.tgi';dest.parent.mkdir(exist_ok=True);dest.write_bytes(locale(code).replace('\n','\r\n').encode('utf-16'))
 src='using System; using System.IO; using System.Text;\ninternal static class NightmareDifficultyData {\n'
 src+='internal static readonly string[] Languages={'+','.join(json.dumps(c) for c in TEXT)+'};\n'
 src+='internal static readonly byte[][] Locales={'+','.join('Convert.FromBase64String('+json.dumps(__import__('base64').b64encode((a.out/'localization'/f'{c}.tgi').read_bytes()).decode())+')' for c in TEXT)+'};\n'
 src+='internal static void Validate(string root,bool enabled){\n'
 for row in manifest[:2]:
  path=json.dumps(row['path'])
  src+='if(enabled ? (!File.Exists(Path.Combine(root,'+path+')) || ReleaseStartup.Hash(Path.Combine(root,'+path+')) != '+json.dumps(row['sha256'].upper())+') : File.Exists(Path.Combine(root,'+path+'))) throw new InvalidDataException("Nightmare difficulty data differs from the AI option. Apply settings in the launcher: '+row['path']+'");\n'
 src+='}\ninternal static void Prepare(string root,string language,bool enabled){Validate(root,enabled);if(!enabled)return;\n'
 src+='int index=Array.IndexOf(Languages,language);if(index<0)index=0;string path=Path.Combine(root,index==0?"data/Localization/paws_nightmare.tgi":"Local_ru/Localization/paws_nightmare.tgi");byte[] expected=Locales[index];\n'
 src+='if(!File.Exists(path)||Convert.ToBase64String(File.ReadAllBytes(path))!=Convert.ToBase64String(expected))throw new InvalidDataException("Missing or modified Nightmare localization. Apply the selected language in the launcher.");\n}\n}\n'
 (a.out/'NightmareDifficultyData.cs').write_text(src,encoding='utf-8')
 (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2));print('NIGHTMARE_DATA_PREPARED',len(manifest),'files;',len(TEXT),'languages')
if __name__=='__main__':main()
