"""Localized river controls and stable native WorldRule enum definitions."""
RIVER_TEXT={
 'en':('Rivers','Random','Number of generated rivers. Random selects anything from zero to the map-size maximum.'),
 'ru':('Реки','Случайно','Количество рек. Случайно: любое количество от нуля до максимума для размера карты.'),
 'de':('Flüsse','Zufällig','Anzahl der Flüsse. Zufällig wählt von null bis zum Maximum der Kartengröße.'),
 'fr':('Rivières','Aléatoire','Nombre de rivières. Aléatoire choisit de zéro au maximum pour la taille de la carte.'),
 'cs':('Řeky','Náhodně','Počet řek. Náhodně vybírá od nuly po maximum pro velikost mapy.'),
 'uk':('Річки','Випадково','Кількість річок. Випадково: від нуля до максимуму для розміру мапи.')}

def rule_definition(language):
 label,random,description=RIVER_TEXT[language]
 return f'''\n[WorldRule Template=WorldRule]
{{
 ids = PawsRivers
 name = "{label}"
 description = "{description}"
 type = enum
 default = paws_rivers_random
 never_editable = true
'''+''.join(f' [EnumValue]\n ids = paws_rivers_{i}\n name = "{i}"\n' for i in range(17))+f''' [EnumValue]
 ids = paws_rivers_random
 name = "{random}"
}}
'''

def add_ui(source,language,span):
 if '[PawRivers Template=' in source:
  for name in ('PawRivers','PawRiversLabel'):
   a,b=span(source,name);source=source[:a]+source[b:]
 label,random,description=RIVER_TEXT[language]
 start,end=span(source,'ObjectsSlidersPanel');panel=source[start:end]
 a,b=span(panel,'ObjectsSliders');block=panel[a:b];block=block.replace('T = 9','T = 39',1);panel=panel[:a]+block+panel[b:]
 controls=f'''
 [PawRiversLabel Template=LabelWidget]
 {{
  [View Template=NoVE]
  {{
   L = 14
   T = 12
   R = +195
   B = +20
  }}
  [Label Template=SharedMediumLeftLabelVE]
  {{
   L = 0
   T = 0
   R = +195
   B = +20
   text = "{label}"
  }}
 }}
 [PawRivers Template=SharedDropDownWidget]
 {{
  tooltip_name = "{label}"
  tooltip = "{description}"
  [View]
  {{
   L = 225
   T = 9
   R = +165
   B = +22
  }}
  [Listbox]
  {{
   sorted = false
   num_visible_items = 8
  }}
 }}
'''
 panel=panel[:-1]+controls+panel[-1:]
 return source[:start]+panel+source[end:]

SHAPE_TEXT={
 'en':('Map shape',['Classic','Pangaea','Mediterranean','Random']),
 'ru':('Форма карты',['Обычная','Пангея','Средиземноморье','Случайно']),
 'de':('Kartenform',['Klassisch','Pangäa','Mittelmeer','Zufällig']),
 'fr':('Forme de carte',['Classique','Pangée','Méditerranée','Aléatoire']),
 'cs':('Tvar mapy',['Klasická','Pangea','Středomoří','Náhodně']),
 'uk':('Форма мапи',['Звичайна','Пангея','Середземномор’я','Випадково'])}

def shape_rule(language):
 label,values=SHAPE_TEXT[language]
 return f'''\n[WorldRule Template=WorldRule]
{{
 ids = PawsMapShape
 name = "{label}"
 type = enum
 default = paws_shape_classic
 never_editable = true
'''+''.join(f' [EnumValue]\n ids = paws_shape_{key}\n name = "{name}"\n' for key,name in zip(['classic','pangaea','mediterranean','random'],values))+'}\n'

def installed_ui(source,language,span):
 import re
 # Rivers occupy the unused third row under time of day. Native object and
 # terrain scroll panels retain all their original space and positioning.
 a,b=span(source,'SelectListBox');block=source[a:b]
 block=re.sub(r'num_visible_items = \d+','num_visible_items = 7',block,count=1)
 block=re.sub(r'(?m)^(\s*)T = 15\s*$',r'\1T = 49',block,count=1);source=source[:a]+block+source[b:]
 river_label,_,description=RIVER_TEXT[language]
 label,_=SHAPE_TEXT[language]
 nodes=f'''
 [PawMapShapeLabel Template=LabelWidget]
 {{
  [View Template=NoVE]
  {{
   L = 57
   T = 76
   R = +110
   B = +20
  }}
  [Label Template=SharedSmallLeftLabelVE]
  {{
   L = 0
   T = 0
   R = +110
   B = +20
   text = "{label}"
  }}
 }}
 [PawMapShape Template=SharedDropDownWidget]
 {{
  [View]
  {{
   L = 177
   T = 76
   R = +210
   B = +20
  }}
  [Listbox]
  {{
   sorted = false
   num_visible_items = 4
  }}
 }}
 [PawRiversLabel Template=LabelWidget]
 {{
  [View Template=NoVE]
  {{
   L = 428
   T = 624
   R = +175
   B = +20
  }}
  [Label Template=SharedMediumLeftLabelVE]
  {{
   L = 0
   T = 0
   R = +175
   B = +20
   text = "{river_label}"
  }}
 }}
 [PawRivers Template=SharedDropDownWidget]
 {{
  tooltip_name = "{river_label}"
  tooltip = "{description}"
  [View]
  {{
   L = 608
   T = 621
   R = +150
   B = +22
  }}
  [Listbox]
  {{
   sorted = false
   num_visible_items = 8
  }}
 }}
'''
 a,b=span(source,'Template SharedRandomMapDialog');return source[:b-1]+nodes+source[b-1:]


def river_terrain(biome):
    # Match each native lake's surface and tint. Arctic lakes use pack ice
    # under their animated water; overriding their tint made rivers neon blue.
    native={'temperate':('Temperate','TemperateWater','TemperateWater','TemperateWater01.tga','0.000, 0.306, 0.408'),
            'arctic':('Arctic','ArcticWater','ArcticPackIce','ArcticPackIce01.tga','0.231, 0.345, 0.412'),
            'desert':('Desert','DesertWater','DesertWater','DesertWater01.tga','0.059, 0.275, 0.428'),
            'cursed':('Cursed','CursedWater','CursedWater','CursedWater01.tga','0.000, 0.306, 0.408')}[biome]
    priority={'temperate':50550,'arctic':50550,'desert':90000,'cursed':130100}[biome]
    folder,water,surface,texture,tint=native
    color='0.000, 0.250, 0.750' if biome=='desert' else '0.000, 0.000, 1.000'
    return f"""[Terrain Template=WaterTerrain]
{{
 IDS = paws_river_{biome}
 name = "River"
 base_priority = {priority}
 terrain_color = {tint}
 terrain_group = water
 land = false
 water = true
 doodad_frequency = 0
 primary_doodad_frequency = 0
 paint_slope = 1
 max_slope = 1
 paint_max_step = 8
 max_depth = 12
 anim_textures_path_prefix = /Terrain/{folder}/{water}/WaterFrames%04d.dds
 anim_fps = 10
 color = {color}
 [Variation]
 {{
  IDS = paws_river_{biome}01
  name = "River"
  texture = /Terrain/{folder}/{surface}/{texture}
  texture_width = 8
  texture_height = 8
  terrain_color = {tint}
  weight = 1
 }}
}}
"""
