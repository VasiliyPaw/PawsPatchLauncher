from context import *
from datetime import datetime,timezone
BODIES={
 'ru':'- Обновлены поверхности мостов всех рас и эффект строительства Теней.\n- Боты строят переправы на разведанных реках; исправлено строительство мостов на суше.\n- Исправлены самовольные атаки мостов, в том числе призванными существами.\n- Улучшено движение отрядов после переправы.\n- Сглажены переходы воды и дна; исправлена глубина небольших водоёмов на новых картах.',
 'en':'- Updated bridge surfaces for all factions and the Shadow construction effect.\n- AI builds crossings on explored rivers; fixed bridge construction on dry land.\n- Fixed unsolicited attacks on bridges, including attacks by summoned creatures.\n- Improved company movement after crossing a bridge.\n- Smoothed water and riverbed transitions; corrected small-waterbody depth on new maps.',
 'uk':'- Оновлено поверхні мостів усіх рас та ефект будівництва Тіней.\n- Боти будують переправи на розвіданих річках; виправлено будівництво мостів на суші.\n- Виправлено самовільні атаки мостів, зокрема прикликаними істотами.\n- Покращено рух загонів після переправи.\n- Згладжено переходи води й дна; виправлено глибину малих водойм на нових картах.',
 'cs':'- Upraveny povrchy mostů všech ras a stavební efekt Stínů.\n- AI staví přechody přes prozkoumané řeky; opravena stavba mostů na souši.\n- Opraveny samovolné útoky na mosty, včetně vyvolaných tvorů.\n- Vylepšen pohyb družin po překročení mostu.\n- Vyhlazeny přechody vody a dna; opravena hloubka malých vodních ploch na nových mapách.',
 'de':'- Brückenoberflächen aller Völker und der Baueffekt der Schatten wurden überarbeitet.\n- Die KI baut Übergänge über erkundete Flüsse; Brückenbau auf trockenem Land wurde korrigiert.\n- Ungewollte Angriffe auf Brücken, auch durch beschworene Kreaturen, wurden behoben.\n- Die Bewegung der Kompanien nach einer Überquerung wurde verbessert.\n- Wasser- und Grundübergänge wurden geglättet; die Tiefe kleiner Gewässer auf neuen Karten wurde korrigiert.',
 'fr':'- Surfaces des ponts de toutes les factions et effet de construction des Ombres améliorés.\n- L’IA construit des passages sur les rivières explorées ; construction des ponts sur la terre ferme corrigée.\n- Attaques spontanées contre les ponts corrigées, y compris celles des créatures invoquées.\n- Déplacement des compagnies après une traversée amélioré.\n- Transitions de l’eau et du fond adoucies ; profondeur des petits plans d’eau corrigée sur les nouvelles cartes.'}
def note():return dict(category='patch',mods=['arcane-wars'],channel='beta',version=V,publishedAt='2026-11-26',title={k:'Paw’s Patch '+V+' — Arcane Wars'for k in BODIES},body=BODIES)
def main():
 replacements={p['id']:p for p in read(O/'packages.json')};allowed=[]
 for rel in FILES[:6]:
  a=verify(read(O/'before'/rel));b=copy.deepcopy(a)
  if rel in['feed/v2/beta.json','feed/v3/beta.json']:
   assert next(p for p in a['packages']if p['id']=='pawpatch-core')['version']=='0.6.0-beta.6'
   b['packages']=[copy.deepcopy(replacements.get(p['id'],p))for p in a['packages']];b['patchGuide']['version']=V
   b['patchGuide']['entries'].insert(0,dict(id='bridge-water-20261126',category='always',titleRu='Мосты и водоёмы',titleEn='Bridges and water',bodyRu=BODIES['ru'],bodyEn=BODIES['en']))
   b['changelog']=[note()]+a['changelog'];b.update(newsTitle=note()['title'],newsBody=BODIES,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
   for k in['launcher','game','modGames','modGuides']:assert a[k]==b[k],k
   assert [p for p in a['packages']if p['id']not in replacements]==[p for p in b['packages']if p['id']not in replacements]
   allowed.append(rel);write(O/'signed'/rel,sign(b))
  else:
   target=O/'signed'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((O/'before'/rel).read_bytes())
 h=read(O/'before/feed/changelog.history.json');assert not any(x.get('version')==V and x.get('mods')==['arcane-wars']for x in h['beta']);h['beta']=[note()]+h['beta'];write(O/'signed/feed/changelog.history.json',h);allowed.append('feed/changelog.history.json')
 f=verify(read(O/'signed/feed/v3/beta.json'));write(O/'signed/feed/patch-guide-beta.json',f['patchGuide']);allowed.append('feed/patch-guide-beta.json');write(O/'scope.json',dict(allowed=allowed));assert len(allowed)==4
 for channel in['stable','beta']:
  f=verify(read(O/'signed'/f'feed/v3/{channel}.json'))
  if channel=='beta':
   for q in f['packages']:
    if q['id']in replacements:q['urls']=[read(O/'package-audit.json')[q['id']]['path']]
  write(O/'local-feeds'/f'{channel}.json',sign(f))
 write(O/'release.json',note());(O/'release-notes.md').write_text('\n\n'.join(note()['title'][k]+'\n\n'+BODIES[k]for k in BODIES)+'\n',encoding='utf-8');print('ARCANE_BETA_CATALOGS_SIGNED',flush=True)
if __name__=='__main__':main()
