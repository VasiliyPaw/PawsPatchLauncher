from context import *
def main():
 s=(WS/'work/ui-fullres-release-20261117/catalog_check.py').read_text()
 s=s.replace('Check(files[common].Keys.Count(n=>n.StartsWith("paws-hd-ui/"))==645,"HD priority depot incomplete");','Check(!files[common].Keys.Any(n=>n.StartsWith("paws-hd-ui")),"HD payload retained");Check(files[common].Keys.Count(n=>n.Contains("pawuniform")&&n.EndsWith(".tga"))==63,"old frame paths missing");Check(files[common].Keys.Count(n=>n.StartsWith("skins/")&&n.EndsWith(".rwd"))==6,"stock skins missing");')
 (P/'catalog_check.py').write_text(s)
 s=(WS/'work/ui-fullres-release-20261117/catalogs.py').read_text();start=s.index('BODIES={');end=s.index('\ndef note(',start)
 bodies={'ru':'- Возвращены прежние иконки и оформление интерфейса всех рас.','en':'- Restored the previous icons and interface artwork for every faction.','uk':'- Повернуто попередні іконки та оформлення інтерфейсу всіх рас.','cs':'- Obnoveny původní ikony a vzhled rozhraní všech ras.','de':'- Frühere Symbole und das Oberflächendesign aller Völker wiederhergestellt.','fr':'- Rétablissement des anciennes icônes et de l’habillage de l’interface de toutes les factions.'}
 s=s[:start]+'BODIES='+repr(bodies)+s[end:];s=s.replace('2026-11-17','2026-11-18').replace("=='0.6.0-beta.3'","=='0.6.0-beta.5'").replace("=='0.5.0-beta.7'","=='0.5.0-beta.9'")
 s=s.replace("id='fullres-ui-20261117'","id='legacy-ui-20261118'").replace("titleRu='Чёткий HD-интерфейс',titleEn='Sharper HD interface'","titleRu='Прежние иконки и интерфейс',titleEn='Previous icons and interface'")
 s=s.replace("b['patchGuide']['version']=ARC","b['patchGuide']['version']=ARC;b['patchGuide']['entries']=[e for e in b['patchGuide']['entries']if e['id']not in ['fullres-ui-20261117','compact-ui-20261117']]")
 s=s.replace("g['patchGuide']['version']=PURE;g['patchGuide']['entries'].insert(0,copy.deepcopy(entry))","g['patchGuide']['version']=PURE;g['patchGuide']['entries']=[e for e in g['patchGuide']['entries']if e['id']not in ['fullres-ui-20261117','compact-ui-20261117']];g['patchGuide']['entries'].insert(0,copy.deepcopy(entry))")
 s=s.replace('Paw’s Patch — HD UI','Paw’s Patch — UI');(P/'catalogs.py').write_text(s);print('REVERT_CHECKS_READY')
if __name__=='__main__':main()
