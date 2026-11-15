"""Translations for the prototype's new controls; no installed locale is edited."""
LANGUAGES=['en','ru','de','fr','cs','uk']
TEXT={
 'en':dict(labels=['Climate','Map shape'],climates=['Temperate','Arctic','Desert'],shapes=['Classic','Pangaea','Mediterranean','Rivers'],descriptions=['The original map generator.','One connected continent with coastal bays and an outer sea.','A central inland sea with broad, connected shores.','Winding rivers with three broad land crossings.']),
 'ru':dict(labels=['Климат','Форма карты'],climates=['Умеренный','Снежный','Пустынный'],shapes=['Обычная','Пангея','Средиземноморье','Реки'],descriptions=['Обычная генерация карты.','Единый материк с прибрежными заливами и морем вокруг.','Внутреннее море с широкими соединёнными берегами.','Извилистые реки с тремя широкими сухопутными переходами.']),
 'de':dict(labels=['Klima','Kartenform'],climates=['Gemäßigt','Arktisch','Wüste'],shapes=['Klassisch','Pangäa','Mittelmeer','Flüsse'],descriptions=['Der ursprüngliche Kartengenerator.','Ein zusammenhängender Kontinent mit Buchten und umgebendem Meer.','Ein Binnenmeer mit breiten, verbundenen Ufern.','Gewundene Flüsse mit drei breiten Landübergängen.']),
 'fr':dict(labels=['Climat','Forme de la carte'],climates=['Tempéré','Arctique','Désertique'],shapes=['Classique','Pangée','Méditerranée','Rivières'],descriptions=['Le générateur de cartes original.','Un continent unique bordé de baies et entouré par la mer.','Une mer intérieure avec de larges rives reliées entre elles.','Des rivières sinueuses avec trois larges passages terrestres.']),
 'cs':dict(labels=['Podnebí','Tvar mapy'],climates=['Mírné','Arktické','Pouštní'],shapes=['Klasická','Pangea','Středomoří','Řeky'],descriptions=['Původní generátor map.','Jeden propojený kontinent se zálivy a okolním mořem.','Vnitrozemské moře se širokými propojenými břehy.','Klikaté řeky se třemi širokými pozemními přechody.']),
 'uk':dict(labels=['Клімат','Форма мапи'],climates=['Помірний','Сніговий','Пустельний'],shapes=['Звичайна','Пангея','Середземномор’я','Річки'],descriptions=['Звичайна генерація мапи.','Єдиний материк із прибережними затоками та морем навколо.','Внутрішнє море із широкими з’єднаними берегами.','Звивисті річки з трьома широкими сухопутними переходами.'])
}
CLIMATES=['temperate','arctic','desert']
SHAPES=['classic','pangaea','mediterranean','rivers']
for _lang,_description in {
 'en':'Open terrain with rivers controlled by the Rivers setting.',
 'ru':'Открытая местность. Количество рек задаётся настройкой «Реки».',
 'de':'Offenes Gelände. Flüsse werden separat eingestellt.',
 'fr':'Terrain ouvert. Les rivières se règlent séparément.',
 'cs':'Otevřený terén. Počet řek se nastavuje samostatně.',
 'uk':'Відкрита місцевість. Кількість річок задається окремо.'}.items():TEXT[_lang]['descriptions'][3]=_description
def profile_id(shape,climate):
 if shape=='classic':return 'rmc_'+climate+'03'
 return 'paws_shape_'+shape+('_'+climate if climate!='temperate' else '')
def c_header():
 # TinyCC accepts a variable-length \u escape; a following hex letter can
 # become part of it (Pang\u00e4a). Terminate every codepoint explicitly.
 def wide(s):return 'L"'+''.join('\\x%04x'%ord(c) for c in s)+'"'
 s='/* Generated from localization.py by build.py. */\n'
 for name,key in [('shape_names','shapes'),('climate_names','climates')]:
  s+=f'static const wchar_t *{name}[6][{len(TEXT["en"][key])}]={{\n'+',\n'.join('{'+','.join(wide(v) for v in TEXT[l][key])+'}' for l in LANGUAGES)+'};\n'
 s+='static const char *climate_ids[]={"temperate","arctic","desert"};\n'
 s+='static const wchar_t *climate_wids[]={L"temperate",L"arctic",L"desert"};\n'
 return s
