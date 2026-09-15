"""Compile reviewed DE/FR terms and compositional labels; never guess missing terms."""
import argparse, json, re, struct, zipfile
from pathlib import Path
from PrepareEuropeanLanguages import decode

ROOT = Path(__file__).resolve().parents[1]
RX = re.compile(r'^\s*([\w.]+)\s*=\s*"((?:\\.|[^"\\])*)"', re.M)
def normalize(s):
    return ' '.join(s.strip().split()).casefold()

SUFFIXES = {
    'gate lanterns': ('Torleuchten', 'lanternes de porte'),
    'wall lantern': ('Mauerleuchte', 'lanterne murale'),
    'gate lantern': ('Torleuchte', 'lanterne de porte'),
    'fire decal': ('Feuermarkierung', 'marque de feu'),
    'ice decal': ('Eismarkierung', 'marque de glace'),
    'fire effect': ('Feuereffekt', 'effet de feu'),
    'ice effect': ('Eiseffekt', 'effet de glace'),
    'ring effect': ('Ringeffekt', "effet d'anneau"),
    'shock effect': ('Schockeffekt', 'effet de choc'),
    'chill effect': ('Kälteeffekt', 'effet de froid'),
    'cloud effect': ('Wolkeneffekt', 'effet de nuage'),
    'hit effect': ('Treffereffekt', "effet d'impact"),
    'melee hit': ('Nahkampftreffer', 'impact au corps à corps'),
    'hand mist': ('Handnebel', 'brume des mains'),
    'spine mist': ('Rückennebel', 'brume dorsale'),
    'head fire effect': ('Kopfflammen', 'flammes de la tête'),
    'spine fire effect': ('Rückenflammen', 'flammes dorsales'),
    'fiery slash effect': ('Feuriger Hieb', 'entaille ardente'),
    'decal ground': ('Bodenmarkierung', 'marque au sol'),
    'decal large': ('Große Markierung', 'grande marque'),
    'decal medium': ('Mittlere Markierung', 'marque moyenne'),
    'cloud large': ('Große Wolke', 'grand nuage'),
    'cloud small': ('Kleine Wolke', 'petit nuage'),
    'burning loop': ('Brennender Dauereffekt', 'embrasement continu'),
    'smallflameloop': ('Kleine Dauerflamme', 'petite flamme continue'),
    'smallflame loop': ('Kleine Dauerflamme', 'petite flamme continue'),
    'flameloop': ('Dauerflamme', 'flamme continue'),
    'flame loop': ('Dauerflamme', 'flamme continue'),
    'chestflame loop': ('Brustflammen', 'flammes du torse'),
    'chest loop': ('Brust-Dauereffekt', 'effet continu du torse'),
    'fidget1 effect': ('Ruheanimation 1', "animation d'attente 1"),
    'swing effect': ('Schwungeffekt', 'effet de frappe'),
    'birth effect name': ('Erscheinungseffekt', "effet d'apparition"),
    'ondeath effect': ('Todeseffekt', 'effet de mort'),
    'visual effect': ('Visueller Effekt', 'effet visuel'),
    'hiteffect': ('Treffereffekt', "effet d'impact"),
    'hit_effect_name': ('Treffereffekt', "effet d'impact"),
    'hit effect name': ('Treffereffekt', "effet d'impact"),
    'effect': ('Effekt', 'effet'), 'loop': ('Dauereffekt', 'effet continu'),
    'portrait': ('Porträt', 'portrait'), 'decal': ('Markierung', 'marque'),
    'object': ('Objekt', 'objet'), 'empty': ('Leeres Objekt', 'objet vide'),
    'projectile': ('Geschoss', 'projectile'), 'volley': ('Salve', 'salve'),
    'sign': ('Zeichen', 'signe'), 'sfx': ('Soundeffekt', 'effet sonore'),
    'smoke': ('Rauch', 'fumée'), 'smallflame': ('Kleine Flamme', 'petite flamme'),
    'glow': ('Leuchten', 'lueur'), 'summon': ('Beschwörung', 'invocation'),
    'death': ('Tod', 'mort'), 'tail': ('Schweif', 'traînée'),
    'flame': ('Flamme', 'flamme'), 'explosion': ('Explosion', 'explosion'),
    'lightning': ('Blitz', 'éclair'), 'bombard': ('Bombardierung', 'bombardement'),
    'body': ('Körper', 'corps'), 'melee': ('Nahkampf', 'corps à corps'),
    'ability': ('Fähigkeit', 'capacité'), 'property': ('Eigenschaft', 'propriété'),
    'enchantment': ('Verzauberung', 'enchantement'), 'cast': ('Zauberwirken', 'incantation'),
    'bolt': ('Bolzen', 'carreau'), 'bolts': ('Bolzen', 'carreaux'),
    'arrow': ('Pfeil', 'flèche'), 'bow': ('Bogen', 'arc'),
    'sword': ('Schwert', 'épée'), 'javelin': ('Wurfspieß', 'javelot'),
    'harpoon': ('Harpune', 'harpon'), 'cloud': ('Wolke', 'nuage'),
    'plague': ('Seuche', 'peste'), 'scorpion glow': ('Skorpionleuchten', 'lueur du scorpion'),
    'spider glow': ('Spinnenleuchten', "lueur de l'araignée"),
    'flames': ('Flammen', 'flammes'), 'shock': ('Schock', 'choc'),
    'company': ('Kompanie', 'compagnie'), 'companies': ('Kompanien', 'compagnies'),
    'detachment': ('Abteilung', 'détachement'), 'militia': ('Miliz', 'milice'),
    'defenders': ('Verteidiger', 'défenseurs'), 'guardians': ('Wächter', 'gardiens'),
    'guardian': ('Wächter', 'gardien'), 'guard': ('Wache', 'garde'),
    'horde': ('Horde', 'horde'), 'minions': ('Diener', 'serviteurs'),
    'pack': ('Rudel', 'meute'), 'swarm': ('Schwarm', 'nuée'),
    'youngling': ('Jungtier', 'jeune'), 'younglings': ('Jungtiere', 'jeunes'),
    'wanderer': ('Wanderer', 'errant'), 'companion': ('Begleiter', 'compagnon'),
    'founders': ('Gründer', 'fondateurs'), 'pilgrims': ('Pilger', 'pèlerins'),
    'boneweavers': ('Knochenweber', "tisseurs d'os"),
    'lair': ('Unterschlupf', 'antre'), 'cavern': ('Höhle', 'caverne'),
    'crag': ('Felsklippe', 'escarpement'), 'nest': ('Nest', 'nid'),
    'dwelling': ('Behausung', 'demeure'), 'gate': ('Tor', 'porte'),
    'tower': ('Turm', 'tour'), 'wall': ('Mauer', 'mur'), 'wall post': ('Mauerpfosten', 'poteau mural'),
    'settlement': ('Siedlung', 'colonie'), 'spot': ('Standort', 'emplacement'),
    'post': ('Posten', 'poste'), 'outpost': ('Außenposten', 'avant-poste'),
    'camps': ('Lager', 'camps'), 'sabat': ('Sabbat', 'sabbat'),
    'globe': ('Kugel', 'globe'), 'upgrade': ('Verbesserung', 'amélioration'),
    'fortified': ('Befestigt', 'fortifié'), 'large': ('Groß', 'grand'),
    'medium': ('Mittel', 'moyen'), 'peak': ('Gipfel', 'sommet'),
    'trans': ('Geländeübergang', 'transition de terrain'),
    'foresttrans': ('Waldübergang', 'transition de forêt'),
    'corrupttrans': ('Verderbnisübergang', 'transition corrompue'),
    'grasstrans': ('Grasübergang', "transition d'herbe"),
    'corrupt': ('Verderbnis', 'corruption'), 'grass': ('Gras', 'herbe'),
    'river': ('Fluss', 'rivière'), 'road': ('Straße', 'route'), 'shore': ('Ufer', 'rive'),
    'beam': ('Strahl', 'rayon'), 'manifestation': ('Manifestation', 'manifestation'),
    'crackling': ('Knistern', 'crépitement'), 'swirl': ('Wirbel', 'tourbillon'),
    'rock': ('Felsgeschoss', 'projectile rocheux'),
}
NAMES = """Abaddon Laught|Amon Koth|Ashavir|Balché|Ceyahdev|Cyrus Naadev|Ethan Delroba|Gideon|Hss'Rak|Ikaris|Ilyana Aswan|Jilla Jannat|Kerberos|Kharga|Lyssa Edan|Maghnus|Martyn Kyrkwood|Mausallas Bahram|Moggok|Qasim Majere|Sadira Bahhrum|Sar Lashkar|Sarai Marusek|Shohn Maht|Slyys'Stok|Syrad Amon|Xerxes Mehrdad|Yss'Tok|Z'ha'dum|Haroun|Drauga|Gauri|Rhaksha|Kohan|Saiyar|Bashkar""".split('|')

class Translator:
    def __init__(self, official):
        self.terms = {normalize(k): v for k,v in official.items()}
        for name in NAMES: self.terms[normalize(name)] = [name,name]
        for file in [ROOT/'game/localization/european-terms.tsv', ROOT/'game/localization/european-terms-extra.tsv']:
            for line in file.read_text('utf-8').splitlines():
                if line and not line.startswith('#'):
                    en,de,fr=line.split('|');self.terms[normalize(en)]=[de,fr]
        self.missing = set()
    def get(self,s,depth=0):
        s=' '.join(s.strip().split());key=normalize(s)
        if key in self.terms:return self.terms[key]
        if depth>16:return None
        def child(v):return self.get(v,depth+1)
        # Original typo aliases are retained in the keys, corrected in displayed text.
        aliases={'drake lighnting 1':'Drake Lightning 1','falling_stars empty':'Falling Stars Empty',
            'sakarrs voice portrait':"Sakarr's Voice portrait",'breaker_hit_effect_name':'Breaker Hit Effect',
            'siegemaster_hit_effect_name':'Siegemaster Hit Effect'}
        if key in aliases:return child(aliases[key])
        m=re.fullmatch(r'Kingdom (\d+)',s,re.I)
        if m:return [f'Königreich {m[1]}',f'Royaume {m[1]}']
        m=re.fullmatch(r'(.+?)\s+(\d+)',s)
        if m:
            t=child(m[1])
            if t:return [x+' '+m[2] for x in t]
        m=re.fullmatch(r'(.+?)\s+\(([\d.]+)\)',s)
        if m:
            t=child(m[1])
            if t:return [x+' ('+m[2]+')' for x in t]
        m=re.fullmatch(r'(.+?) \(Nation - (.+)\)',s)
        if m:
            a,b=child(m[1]),child(m[2])
            if a and b:return [a[0]+' (Volk: '+b[0]+')',a[1]+' (peuple : '+b[1]+')']
        if ' - ' in s:
            a,b=map(child,s.split(' - ',1))
            if a and b:return [a[i]+' — '+b[i] for i in range(2)]
        for suffix,(de,fr) in sorted(SUFFIXES.items(),key=lambda p:-len(p[0])):
            if key.endswith(' '+suffix):
                t=child(s[:-len(suffix)].strip())
                if t:return [t[0]+' — '+de,t[1]+' — '+fr]
        prefixes={
            'Greater ':(' (verstärkt)',' (version supérieure)'),
            'Lesser ':(' (schwach)',' (version mineure)'),
            'Empowered ':(' (ermächtigt)',' (version renforcée)'),
            'Random ':(' (zufällig)',' (aléatoire)'),
            'Sovereign ':(' des Herrschers',' du souverain'),
            'Kingdom ':(' des Reiches',' du royaume'),
            'Graveyard ':(' (Friedhof)',' (cimetière)'),
            'Garden ':(' (Garten)',' (jardin)'),
            'Miningpost ':(' (Bergbauposten)',' (poste minier)'),
            'Merchant Post ':(' (Handelsposten)',' (comptoir marchand)'),
        }
        for prefix,tail in prefixes.items():
            if key.startswith(prefix.casefold()):
                t=child(s[len(prefix):])
                if t:return [t[i]+tail[i] for i in range(2)]
        for prefix,de,fr in [('Call ',' rufen','Appeler : '),('Summon ',' beschwören','Invoquer : ')]:
            if key.startswith(prefix.casefold()):
                t=child(s[len(prefix):])
                if t:return [t[0]+de,fr+t[1]]
        groups={ 'Drauga':('Drauga','Drauga'),'Gauri':('Gauri','Gauri'),'Haroun':('Haroun','Haroun'),
            'Human':('Menschen','Humains'),'Undead':('Untote','Morts-vivants'),'Shadow':('Schatten','Ombres'),
            'Rhaksha':('Rhaksha','Rhaksha'),'Slaanri':('Slaanri','Slaanri'),
            'Council':('Rat','Conseil'),'Royalist':('Royalisten','Royalistes'),
            'Nationalist':('Nationalisten','Nationalistes'),'Ceyah':('Ceyah','Ceyah'),
            'Fallen':('Gefallene','Déchus') }
        for prefix,labels in groups.items():
            if key.startswith(prefix.casefold()+' '):
                t=child(s[len(prefix)+1:])
                if t:return [t[i]+' ('+labels[i]+')' for i in range(2)]
        for prefix,de,fr in [('Tower ','Turm','Tour'), ('Wall ','Mauer','Mur'), ('Gate ','Tor','Porte')]:
            if key.startswith(prefix.casefold()):
                t=child(s[len(prefix):])
                if t:return [de+' — '+t[0],fr+' — '+t[1]]
        return None

def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--official',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    rows=json.loads(args.catalog.read_text('utf-8'));tr=Translator(json.loads(args.official.read_text('utf-8')))
    results={};missing=[]
    for r in rows:
        value=tr.get(r['en'])
        if value:results[r['en']]=value
        else:missing.append({'en':r['en'],'ru':r['ru']})
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'translated-phrases.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.out/'missing-phrases.json').write_text(json.dumps(missing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Translated',len(results),'missing',len(missing))
    for r in missing:print(r['en']+' | '+r['ru'])

if __name__=='__main__':main()
