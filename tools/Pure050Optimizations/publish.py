"""Preserve the fresh global catalog; publish only three Pure beta replacements."""
from context import *
p=REPO/'tools/Pure050Release/publish_beta.py';s=p.read_text();s=s.replace('0.5.0-beta.1',PATCH).replace('0.5.0 beta 1','0.5.0 beta 2').replace("OUT/'beta-publication'","OUT/'publication'").replace("OUT/'beta-stage-r4","OUT/'stage-r3")
start=s.index('def entry():');end=s.index('\ndef prepare():',start)
replacement='''def entry():return read(REPO/('docs/release-pure-'+VERSION+'.json'))

def guide(g):
 g=copy.deepcopy(g);g['version']=VERSION
 assert not any(e['id']=='pure-optimizations'for e in g['entries'])
 g['entries'].append(dict(id='pure-optimizations',category='always',titleRu='Оптимизация отображения войск',titleEn='Army rendering optimizations',bodyRu='Исправлено распределение кэша ресурсов. Добавлены подготовка моделей и анимаций при загрузке и на паузе, удержание анимаций с проверкой памяти, переиспользование графических буферов и ускоренный поиск групп при отрисовке. Экспериментальный прогрев GPU выключен.',bodyEn='Repaired resource-cache allocation. Added model and animation preparation during loading and pause, memory-guarded animation retention, graphics-buffer reuse and faster rendering-group lookup. Experimental GPU preloading is disabled.'))
 return g
'''
s=s[:start]+replacement+s[end:];s=s.replace("len(read(STAGE/'public-assets.json'))==7","len(read(STAGE/'public-assets.json'))==3")
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
