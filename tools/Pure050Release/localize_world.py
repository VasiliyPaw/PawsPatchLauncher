"""Add separate text resources so native locale tables remain intact."""
from context import *
def main():
 out=OUT/'world-data-r2';texts=read(REPO/'game/world-options/localization.json')
 extra={
 'en':['Mixed biomes','Large temperate, arctic and desert regions, using the objects of the selected game mode.','Lairs','Technology sites','All: all three native biomes. Random: one, two or three biomes with equal probability. Objects match their biome.'],
 'ru':['Смешанные биомы','Крупные области лета, зимы и пустыни с родными объектами выбранного режима.','Логова','Технологические постройки','Все: три родных биома. Случайно: с равной вероятностью выбирает один, два или три биома. Объекты соответствуют своему биому.'],
 'de':['Gemischte Biome','Große gemäßigte, arktische und Wüstengebiete mit den Objekten des gewählten Spielmodus.','Lager','Technologiegebäude','Alle: alle drei ursprünglichen Biome. Zufällig: ein, zwei oder drei Biome mit gleicher Wahrscheinlichkeit. Objekte passen zu ihrem Biom.'],
 'fr':['Biomes mixtes','Grandes régions tempérées, arctiques et désertiques avec les objets du mode choisi.','Repaires','Sites technologiques','Tous : les trois biomes natifs. Aléatoire : un, deux ou trois biomes avec la même probabilité. Les objets correspondent à leur biome.'],
 'cs':['Smíšené biomy','Rozsáhlé mírné, arktické a pouštní oblasti s objekty zvoleného herního režimu.','Doupata','Technologické stavby','Všechny: všechny tři původní biomy. Náhodně: jeden, dva nebo tři biomy se stejnou pravděpodobností. Objekty odpovídají svému biomu.'],
 'uk':['Змішані біоми','Великі області літа, зими та пустелі з рідними об’єктами вибраного режиму.','Лігва','Технологічні споруди','Усі: три рідні біоми. Випадково: з однаковою ймовірністю вибирає один, два або три біоми. Об’єкти відповідають своєму біому.']}
 files={}
 for lang,values in extra.items():
  text=dict(texts[lang]);text.update(zip(['paws_mixed_name','paws_mixed_description','paws_mixed_lairs','paws_mixed_tech','paws_biomes_description'],values))
  data=('[Text language=default]\n{\n ids = Localization/strings_paws_world.tgi\n name = "@Localization/strings_paws_world.tgi"\n'+''.join(' '+k+' = '+json.dumps(v,ensure_ascii=False)+'\n'for k,v in text.items())+'}\n').encode('utf-16')
  paths=['data/localization/strings_paws_world.tgi']if lang=='en'else['local_'+lang+'/localization/strings_paws_world.tgi','local_immortals_'+lang+'/localization/strings_paws_world.tgi']
  for rel in paths:
   p=out/'common/payload'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);files[rel]=sha(p)
 write(out/'localization.json',dict(languages=list(extra),files=files));print('PURE_WORLD_LOCALIZED',len(extra),len(files),'separate resources')
if __name__=='__main__':main()
