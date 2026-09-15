"""Authored corrections for current patch features; rebuild exact English-key catalogs."""
import argparse,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);a=p.parse_args()
    source=json.loads((a.review/'source-keys.json').read_text('utf-8-sig'))
    out={}
    def add(prefix,uk=None,cs=None,de=None,fr=None,many=False):
        keys=[k for k in source if k.startswith(prefix)]
        assert keys and (many or len(keys)==1),(prefix,keys)
        for key in keys:out[key]={c:v for c,v in [('uk',uk),('cs',cs),('de',de),('fr',fr)] if v is not None}

    add("Built into Paw's Patch for Arcane Wars Beta with every combination",
uk="""Вбудовано в Paw's Patch для Arcane Wars у каналі «Бета» за будь-якого поєднання інших компонентів. Потрібен підтримуваний EXE 1.3.72; у режимі «Тільки ігрові файли» функція недоступна. F1 відкриває налаштування автоматики, порогів доходу каменю, деревини, заліза й мани, резерву золота та відкритого ополчення для нових міст. Enter застосовує введене число; Esc або натискання поза полем скасовує введення.

Враховуються всі прийняті ручні й автоматичні накази, зокрема ті, що чекають у черзі: майбутній додатний дохід зменшує залишковий дефіцит, а від'ємні ефекти враховуються для захисту доходу. Додатний ефект недобудованої будівлі не вважається вже отриманим доходом. Для оплати використовуються поточні ресурси. Поки гра не обробить надіслані гравцем накази на будівництво, автоматика чекає, а потім перераховує золото й захищений резерв. Міста працюють паралельно; облога виключає лише обложене місто.

Ринки всіх шести рас дозволено будувати, якщо перед наказом усі чотири доходи перевищують свої пороги з урахуванням очікуваних від'ємних ефектів. Після цього ринок може знизити дохід нижче порогу; тоді відновлення ресурсів знову стає пріоритетом. Для інших будівель захист порогів зберігається. Після економічних пріоритетів автоматика постійно вибирає випадковий дозволений варіант, якщо дохід це дозволяє; окреме налаштування «Інші будівлі» не потрібне. Незалежні копальні всіх рас можна поліпшувати, причому різні копальні отримують окремі накази.

Відкрите ополчення для нових власних міст увімкнено за замовчуванням; вибір зберігається на цьому ПК. Він діє для стартового міста нового матчу, а також новозбудованих і захоплених міст. Завантаження поточного матчу не відкриває ополчення в наявних містах повторно; подальше ручне закриття ополчення враховується. Загальні правила зберігаються локально; винятки для міст скидаються під час нового матчу або завантаження. Формат збережень не змінюється.""",
cs="""Součást Paw's Patch pro Arcane Wars Beta při libovolné kombinaci ostatních komponent. Vyžaduje podporovaný EXE 1.3.72 a není dostupná v režimu Pouze herní soubory. F1 otevře automatizaci, cílové příjmy kamene, dřeva, železa a many, zlatou rezervu a uloženou volbu otevřené domobrany nových měst. Enter potvrdí zadané číslo; Esc nebo kliknutí mimo pole zadávání zruší.

Započítávají se všechny přijaté ruční i automatické příkazy, včetně čekajících úloh: budoucí kladný příjem snižuje zbývající deficit a záporné účinky se zohledňují při ochraně příjmů. Kladný účinek nedokončené budovy se nepovažuje za již získaný příjem. Platí se ze současných zdrojů. Automatizace čeká na zpracování hráčových odeslaných stavebních příkazů hrou a pak znovu vypočítá zlato a chráněnou rezervu. Města pracují souběžně; obléhání vyřadí pouze obléhané město.

Trhy všech šesti ras jsou povoleny, pokud před zadáním příkazu všechny čtyři příjmy přesahují své cíle po započtení čekajících záporných účinků. Trh pak smí snížit příjem pod cíl; obnova zdrojů následně získá přednost. U ostatních budov ochrana cílů zůstává. Po ekonomických prioritách automatizace stále náhodně vybírá přípustnou možnost, dovolují-li to příjmy; samostatná volba Ostatní budovy není potřeba. Lze vylepšovat nezávislé doly všech ras a různé doly dostávají samostatné příkazy.

Otevřená domobrana nových vlastních měst je standardně zapnutá a volba se ukládá na tomto PC. Platí pro počáteční město nového zápasu i pro nově postavená a dobytá města. Načtení rozehraného zápasu neotevírá domobranu stávajících měst znovu; pozdější ruční uzavření domobrany se respektuje. Obecná pravidla se ukládají místně; městské výjimky se při novém zápasu nebo načtení zruší. Formát uložených her se nemění.""",
de="""In Paw's Patch für Arcane Wars Beta bei jeder Kombination der anderen Komponenten enthalten. Erfordert die unterstützte EXE 1.3.72 und ist im Modus Nur Spieldateien nicht verfügbar. F1 öffnet die Automatisierung, Einkommensziele für Stein, Holz, Eisen und Mana, eine Goldreserve und die gespeicherte Einstellung für offene Milizen in neuen Städten. Enter übernimmt eine Zahl; Esc oder ein Klick außerhalb bricht die Eingabe ab.

Alle angenommenen manuellen und automatischen Aufträge werden berücksichtigt, auch wartende: Künftige positive Einnahmen verringern den verbleibenden Bedarf; negative Auswirkungen werden beim Schutz der Einnahmen berücksichtigt. Ein positiver Effekt eines unfertigen Gebäudes gilt noch nicht als erzieltes Einkommen. Bezahlt wird mit vorhandenen Ressourcen. Die Automatik wartet, bis das Spiel die gesendeten Bauaufträge des Spielers verarbeitet hat, und berechnet dann Gold und geschützte Reserve neu. Städte arbeiten parallel; eine Belagerung schließt nur die belagerte Stadt aus.

Märkte aller sechs Rassen sind erlaubt, wenn vor dem Auftrag alle vier Einkommen unter Berücksichtigung ausstehender negativer Effekte über ihren Zielwerten liegen. Der Markt darf danach ein Einkommen unter den Zielwert senken; anschließend hat die Wiederherstellung der Ressourcen Vorrang. Bei anderen Gebäuden bleibt der Zielwertschutz bestehen. Nach den wirtschaftlichen Prioritäten wählt die Automatik fortlaufend eine zufällige zulässige Möglichkeit, sofern die Einnahmen es erlauben. Eine eigene Einstellung Andere Gebäude ist nicht nötig. Unabhängige Minen aller Rassen können ausgebaut werden; verschiedene Minen erhalten getrennte Aufträge.

Offene Milizen für neue eigene Städte sind standardmäßig aktiviert; die Einstellung wird auf diesem PC gespeichert. Sie gilt für die Startstadt eines neuen Spiels sowie für neu errichtete und eroberte Städte. Beim Laden einer laufenden Partie werden bestehende Milizen nicht erneut geöffnet; eine spätere manuelle Schließung wird respektiert. Allgemeine Regeln bleiben lokal gespeichert; Stadtausnahmen werden bei neuen Partien oder beim Laden zurückgesetzt. Das Speicherformat bleibt unverändert.""",
fr="""Inclus dans Paw's Patch pour Arcane Wars Bêta, quelle que soit la combinaison des autres composants. Nécessite l'EXE 1.3.72 pris en charge et n'est pas disponible en mode Fichiers de jeu uniquement. F1 ouvre l'automatisation, les seuils de revenus de pierre, de bois, de fer et de mana, la réserve d'or et l'option mémorisée de milice ouverte pour les nouvelles villes. Entrée valide la valeur saisie ; Échap ou un clic à l'extérieur annule la saisie.

Tous les ordres manuels et automatiques acceptés sont pris en compte, y compris ceux en attente : les futurs revenus positifs réduisent les besoins restants, tandis que les effets négatifs sont pris en compte pour protéger les revenus. L'effet positif d'un bâtiment inachevé n'est pas considéré comme un revenu déjà acquis. Le paiement utilise les ressources actuelles. L'automatisation attend que le jeu traite les ordres de construction envoyés par le joueur, puis recalcule l'or et la réserve protégée. Les villes travaillent en parallèle ; un siège exclut uniquement la ville assiégée.

Les marchés des six races sont autorisés si, avant l'ordre, les quatre revenus dépassent leurs seuils après prise en compte des effets négatifs en attente. Le marché peut ensuite faire descendre un revenu sous son seuil ; le rétablissement des ressources redevient alors prioritaire. Les autres bâtiments conservent la protection des seuils. Après les priorités économiques, l'automatisation choisit continuellement une option autorisée au hasard si les revenus le permettent ; aucun réglage distinct Autres bâtiments n'est nécessaire. Les mines indépendantes de toutes les races peuvent être améliorées, et les différentes mines reçoivent des ordres séparés.

La milice ouverte pour les nouvelles villes possédées est activée par défaut ; ce choix est conservé sur ce PC. Il s'applique à la ville de départ d'une nouvelle partie ainsi qu'aux villes nouvellement construites ou conquises. Charger une partie en cours ne rouvre pas la milice des villes existantes ; toute fermeture manuelle ultérieure est respectée. Les règles générales sont enregistrées localement ; les exceptions des villes sont réinitialisées au début d'une partie ou lors d'un chargement. Le format des sauvegardes ne change pas.""")

    add('Standard uses normal appearance intervals and chances.',many=True,
uk="""Стандартний режим використовує звичайні інтервали появи й шанси. ×2 скорочує інтервал на 25% і підвищує шанс події на 50%. ×4 удвічі скорочує інтервал і подвоює шанс. У середньому роти з'являються приблизно вдвічі або вчетверо частіше, але кожна окрема поява залишається випадковою.

Усі три режими працюють з увімкненими й вимкненими додатковими ротами. Натисніть «Застосувати налаштування», щоб зберегти вибір без запуску гри.

Виняток: на ×4 Темний лорд із Темного розлому (Брами тіней) використовує частоту ×2: одна спроба кожні 6 ігрових хвилин із шансом 30%. Додаткові мандрівні роти мають бути ввімкнені.""",
cs="""Standardní režim používá běžné intervaly a šance výskytu. ×2 zkracuje interval o 25% a zvyšuje šanci události o 50%. ×4 zkracuje interval na polovinu a zdvojnásobuje šanci. V průměru se roty objevují přibližně dvakrát či čtyřikrát častěji, jednotlivé výskyty však zůstávají náhodné.

Všechny tři režimy fungují se zapnutými i vypnutými dodatečnými rotami. Tlačítkem Použít nastavení použijete volbu bez spuštění hry.

Výjimka: při ×4 používá Temný pán z Temné trhliny (Brány stínů) četnost ×2: jeden pokus každých 6 herních minut se šancí 30%. Dodatečné potulné roty musí být zapnuté.""",
de="""Standard verwendet die normalen Intervalle und Erscheinungschancen. ×2 verkürzt das Intervall um 25% und erhöht die Ereignischance um 50%. ×4 halbiert das Intervall und verdoppelt die Chance. Im Durchschnitt erscheinen Kompanien etwa zwei- oder viermal so häufig; einzelne Erscheinungen bleiben jedoch zufällig.

Alle drei Modi funktionieren mit ein- und ausgeschalteten zusätzlichen Kompanien. Mit Einstellungen anwenden übernehmen Sie die Auswahl, ohne das Spiel zu starten.

Ausnahme: Bei ×4 verwendet der Schattenlord aus dem Dunklen Riss (Tor der Schatten) die Häufigkeit ×2: ein Versuch alle 6 Spielminuten mit einer Chance von 30%. Zusätzliche umherziehende Kompanien müssen aktiviert sein.""",
fr="""Le mode standard utilise les intervalles et les chances d'apparition habituels. ×2 réduit l'intervalle de 25% et augmente la chance d'événement de 50%. ×4 divise l'intervalle par deux et double la chance. En moyenne, les compagnies apparaissent environ deux ou quatre fois plus souvent, mais chaque apparition reste aléatoire.

Les trois modes fonctionnent avec ou sans compagnies supplémentaires. Utilisez Appliquer les paramètres pour valider votre choix sans lancer le jeu.

Exception : à ×4, le Seigneur des Ombres de la Faille sombre (Porte des Ombres) utilise la fréquence ×2 : une tentative toutes les 6 minutes de jeu, avec une chance de 30%. Les compagnies errantes supplémentaires doivent être activées.""")

    add('Adds roaming companies from bandit, barbarian, Rhaksha and Slaan camps',many=True,
uk="""Додає мандрівні роти з таборів бандитів, варварів, ракшів і слаанів на місцях для поселень і фундаментів. Джерелами рот також стають лігва павуків і скорпіонів, Темний розлом і руїни нежиті.

Для доданих рот налаштовано параметри появи, бойового духу й відновлення. Цю опцію можна вимкнути зі стандартною частотою, ×2 або ×4; початкові джерела мандрівних рот залишаться.""",
cs="""Přidává potulné roty z táborů banditů, barbarů, Rhaksha a Slaan na místech pro osady a základy. Zdrojem se stávají také pavoučí a štíří doupata, Temná trhlina a ruiny nemrtvých.

Přidané roty mají upravené parametry výskytu, morálky a obnovy. Volbu lze vypnout při standardní četnosti i při ×2 nebo ×4; původní zdroje potulných rot zůstanou zachovány.""",
de="""Fügt umherziehende Kompanien aus Banditen-, Barbaren-, Rhaksha- und Slaan-Lagern auf Siedlungs- und Fundamentplätzen hinzu. Auch Spinnen- und Skorpionhöhlen, der Dunkle Riss und Ruinen der Untoten werden zu Quellen.

Für diese Kompanien sind Erscheinungs-, Moral- und Erholungswerte angepasst. Die Option kann bei Standard, ×2 oder ×4 ausgeschaltet werden; die ursprünglichen Quellen umherziehender Kompanien bleiben erhalten.""",
fr="""Ajoute des compagnies errantes issues des camps de bandits, de barbares, de Rhaksha et de Slaan sur les emplacements de colonies et de fondations. Les repaires d'araignées et de scorpions, la Faille sombre et les ruines des morts-vivants deviennent aussi des sources.

Les compagnies ajoutées ont des paramètres d'apparition, de moral et de récupération adaptés. Cette option peut être désactivée avec la fréquence standard, ×2 ou ×4, tout en conservant les sources d'origine des compagnies errantes.""")

    add('Always enabled in Beta, independently of other components.',
uk="""Завжди ввімкнено в каналі «Бета», незалежно від інших компонентів. Коли господар вибирає збереження в мережевому лобі, гра передає його учасникам, у яких воно відсутнє або відрізняється. Додавати гравців до друзів або приймати файл у лаунчері не потрібно.

Використовується перевірене налаштування R2: до 1200 байтів файлових даних і не більше 16 пакетів кожному учаснику за один прохід надсилання. Штатні підтвердження, повторні спроби, розміри блоків і формат збережень залишаються незмінними. У тесті ПК → віртуальна машина файл розміром 1.6 МБ передано приблизно за 9 секунд; реальна швидкість залежить від мережі. Усім учасникам потрібні оновлена бета й сумісні ігрові налаштування.""",
cs="""V Betě je vždy zapnuto, nezávisle na ostatních komponentách. Když hostitel vybere uloženou hru v síťové lobby, hra ji přenese účastníkům, kterým chybí nebo mají jinou kopii. Přátelství ani přijetí souboru v launcheru není potřeba.

Používá ověřené nastavení R2: nejvýše 1200 bajtů souborových dat a nejvýše 16 paketů na účastníka během jednoho průchodu odesílání. Původní potvrzení, opakované pokusy, velikosti bloků a formát uložených her se nemění. Při testu PC → virtuální stroj trval přenos souboru 1.6 MB přibližně 9 sekund; skutečná rychlost závisí na síti. Všichni účastníci musí mít aktuální Betu a kompatibilní herní nastavení.""",
de="""In Beta immer aktiviert, unabhängig von anderen Komponenten. Wenn der Gastgeber in einer Mehrspieler-Lobby einen Spielstand auswählt, überträgt das Spiel ihn an Teilnehmer, denen er fehlt oder deren Kopie abweicht. Eine Freundschaft oder eine Dateibestätigung im Launcher ist nicht nötig.

Verwendet die getestete R2-Abstimmung: höchstens 1200 Byte Dateidaten und maximal 16 Pakete pro Teilnehmer und Sendedurchlauf. Die ursprünglichen Bestätigungen, Wiederholungen, Blockgrößen und das Spielstandformat bleiben unverändert. Im Test PC → virtuelle Maschine wurde eine Datei mit 1.6 MB in etwa 9 Sekunden übertragen; die tatsächliche Geschwindigkeit hängt vom Netzwerk ab. Alle Teilnehmer benötigen eine aktuelle Beta und kompatible Spieleinstellungen.""",
fr="""Toujours activé en Bêta, indépendamment des autres composants. Quand l'hôte choisit une sauvegarde dans une salle multijoueur, le jeu la transmet aux participants qui ne l'ont pas ou qui en possèdent une copie différente. Il n'est pas nécessaire d'être amis ni d'accepter le fichier dans le launcher.

Utilise le réglage R2 testé : un plafond de 1200 octets de données de fichier et au plus 16 paquets par participant à chaque passage d'envoi. Les accusés de réception, les tentatives répétées, les tailles de blocs et le format des sauvegardes restent inchangés. Un test PC → machine virtuelle a transféré un fichier de 1.6 Mo en environ 9 secondes ; la vitesse réelle dépend du réseau. Tous les participants doivent disposer d'une Bêta à jour et de paramètres de jeu compatibles.""")

    add('Adds an upkeep of 0.75 kingdom points per engine',
uk="""Додає витрати 0.75 очка королівства на утримання кожної з чотирьох облогових машин: Багряної катапульти, Чумної катапульти, Балісти драконячого вогню й Ворпальної машини. У чистому Arcane Wars ці машини не мають таких витрат.

Їхня ціна в золоті, витрати ресурсів на утримання й параметри атаки залишаються такими, як в Arcane Wars 0.82.1.8. Вимкнення компонента прибирає додаткові витрати очок королівства. У всіх учасників мережевої гри має бути однакове налаштування.""")

    add('When launched through the launcher, the game checks game,',
uk="""Під час запуску через лаунчер гра перед входом у лобі перевіряє версії гри, Arcane Wars і Paw's Patch, активні EXE та застосовані ігрові компоненти. У разі розбіжності вікно показує вашу конфігурацію та версії господаря лобі. У всіх гравців мають збігатися версії бети й ігрові налаштування. Мови інтерфейсу, тексту й озвучки не впливають на цю додаткову перевірку. Штатні перевірки ігрових файлів і Steam залишаються ввімкненими.""",
cs="""Při spuštění přes launcher hra před vstupem do lobby kontroluje verze hry, Arcane Wars a Paw's Patch, aktivní EXE a použité herní komponenty. Při neshodě dialog ukáže vaši konfiguraci a verze hostitele. Všichni hráči musí mít shodné verze Bety a herní nastavení. Jazyk rozhraní, textu a dabingu tuto dodatečnou kontrolu neovlivňuje. Původní kontroly herních souborů a Steamu zůstávají zapnuté.""",
de="""Beim Start über den Launcher prüft das Spiel vor dem Lobby-Beitritt die Versionen des Spiels, von Arcane Wars und Paw's Patch, die aktiven EXEs und die angewendeten Spielkomponenten. Bei Abweichungen zeigt ein Dialog Ihre Konfiguration und die Versionen des Gastgebers. Alle Spieler benötigen gleiche Beta-Versionen und Spieleinstellungen. Die Sprachen von Oberfläche, Text und Sprachausgabe beeinflussen diese zusätzliche Prüfung nicht. Die ursprünglichen Spieldatei- und Steam-Prüfungen bleiben aktiv.""",
fr="""Lors d'un lancement depuis le launcher, le jeu vérifie les versions du jeu, d'Arcane Wars et de Paw's Patch, les EXE actifs et les composants de jeu appliqués avant l'entrée dans une salle. En cas de différence, la fenêtre affiche votre configuration et les versions de l'hôte. Tous les joueurs doivent avoir les mêmes versions Bêta et paramètres de jeu. Les langues de l'interface, du texte et des voix n'affectent pas cette vérification supplémentaire. Les contrôles d'origine des fichiers du jeu et de Steam restent actifs.""")

    add('Choose text and speech separately. Both choices persist',
uk="""Вибирайте текст і озвучку окремо. Обидва варіанти зберігаються під час перемикання модів і застосовуються разом із налаштуваннями. Завантажуються лише вибрані мови; збережені файли використовуються повторно, доки не з'явиться оновлення.

Переклади тексту охоплюють оригінальну гру, Immortals, Arcane Wars і Paw's Patch. Набір мов озвучки може відрізнятися від набору мов тексту. Мова лаунчера налаштовується окремо. Локалізація не змінює ігрових характеристик.""",
cs="""Text a dabing vybírejte zvlášť. Obě volby se zachovají při přepínání modů a použijí se spolu s nastavením. Stahují se pouze vybrané jazyky; uložené soubory se používají znovu, dokud není dostupná aktualizace.

Překlady textu zahrnují původní hru, Immortals, Arcane Wars a Paw's Patch. Dostupné jazyky dabingu se mohou lišit od jazyků textu. Jazyk launcheru se nastavuje samostatně. Lokalizace nemění herní parametry.""",
de="""Wählen Sie Text und Sprachausgabe getrennt. Beide Einstellungen bleiben beim Modwechsel erhalten und werden zusammen mit Ihren Einstellungen angewendet. Nur ausgewählte Sprachen werden heruntergeladen; gespeicherte Dateien werden bis zur nächsten Aktualisierung wiederverwendet.

Die Textübersetzungen umfassen das Originalspiel, Immortals, Arcane Wars und Paw's Patch. Die verfügbaren Sprachen für die Sprachausgabe können von den Textsprachen abweichen. Die Sprache des Launchers wird separat eingestellt. Die Lokalisierung verändert keine Spielwerte.""",
fr="""Choisissez le texte et les voix séparément. Les deux choix sont conservés lors des changements de mod et appliqués avec vos paramètres. Seules les langues sélectionnées sont téléchargées ; les fichiers enregistrés sont réutilisés jusqu'à la disponibilité d'une mise à jour.

Les traductions du texte couvrent le jeu d'origine, Immortals, Arcane Wars et Paw's Patch. Les langues disponibles pour les voix peuvent différer de celles du texte. La langue du launcher se règle séparément. La localisation ne modifie pas les caractéristiques du jeu.""")

    add('Function requests including errors.',uk="Запити до обробників, зокрема з помилками. Це вимірювання за 24 години, а не рахунок за місяць.")
    for key in source:
        if not key.startswith("The main menu shows Arcane Wars and Paw's Patch versions beneath the game version."):continue
        beta='current Beta' in key
        out[key]={
            'uk':"У головному меню під версією гри показано версії Arcane Wars і Paw's Patch. У відображенні ліміту рот виправлено від'ємний нуль: замість −0 показується 0.\n\nЦі виправлення автоматично входять до поточної "+('бети' if beta else 'релізної версії')+", навіть якщо розширені кольори й інші додаткові функції вимкнено. Змінюється лише відображення, а не самі значення ліміту.",
            'cs':"Hlavní nabídka pod verzí hry zobrazuje verze Arcane Wars a Paw's Patch. Záporná nula v zobrazení limitu rot je opravena: místo −0 se ukazuje 0.\n\nTyto opravy jsou automaticky součástí aktuální "+('Bety' if beta else 'stabilní verze')+", i když jsou rozšířené barvy a další volitelné funkce vypnuté. Mění se pouze zobrazení, nikoli skutečné hodnoty limitu.",
            'de':"Im Hauptmenü stehen die Versionen von Arcane Wars und Paw's Patch unter der Spielversion. Die negative Null in der Anzeige des Kompanielimits wird korrigiert: Statt −0 erscheint 0.\n\nDiese Korrekturen sind automatisch in der aktuellen "+('Beta' if beta else 'Release-Version')+" enthalten, auch wenn erweiterte Farben und andere optionale Funktionen deaktiviert sind. Nur die Anzeige ändert sich; die tatsächlichen Grenzwerte bleiben gleich.",
            'fr':"Le menu principal affiche les versions d'Arcane Wars et de Paw's Patch sous celle du jeu. Le zéro négatif dans l'affichage de la limite de compagnies est corrigé : −0 devient 0.\n\nCes corrections sont automatiquement incluses dans la "+('Bêta actuelle' if beta else 'version stable actuelle')+", même si les couleurs étendues et les autres fonctions optionnelles sont désactivées. Seul l'affichage change, sans modifier les valeurs réelles de la limite."
        }
    old=next(k for k in source if k.startswith('In the Dvorak profile, WASD moves the camera') and 'English or Russian text' in k)
    current=old.replace('Works with English or Russian text, including file-only mode.','Works with every supported text language, including file-only mode.')
    out[current]={
        'uk':"У профілі Dvorak клавіші WASD переміщують камеру; керування стрілками також доступне. F вибирає союзну мітку. Інші позиційні прив'язки збережено; колишню дію A звільнено для руху камери.\n\nВиберіть Dvorak у налаштуваннях гри; патч не перемикає профілі автоматично. Працює з усіма підтримуваними мовами тексту, зокрема в режимі «Тільки ігрові файли». Інші профілі керування не змінюються.",
        'cs':"V profilu Dvorak pohybují klávesy WASD kamerou a ovládání šipkami zůstává dostupné. F vybere spojeneckou značku. Ostatní poziční vazby jsou zachovány; původní akce A je uvolněna pro pohyb kamery.\n\nVyberte Dvorak v nastavení hry; patch profily automaticky nepřepíná. Funguje se všemi podporovanými jazyky textu, včetně režimu Pouze herní soubory. Ostatní profily ovládání se nemění.",
        'de':"Im Profil Dvorak bewegt WASD die Kamera; die Pfeiltasten bleiben verfügbar. F wählt die Verbündetenmarkierung. Andere positionsbezogene Belegungen bleiben erhalten; die bisherige Aktion auf A wird für die Kamerabewegung freigegeben.\n\nWählen Sie Dvorak in den Spieleinstellungen; der Patch wechselt Profile nicht automatisch. Funktioniert mit allen unterstützten Textsprachen, auch im Modus Nur Spieldateien. Andere Steuerungsprofile bleiben unverändert.",
        'fr':"Dans le profil Dvorak, WASD déplace la caméra et les flèches restent disponibles. F sélectionne le marqueur allié. Les autres raccourcis de position sont conservés ; l'ancienne action A est libérée pour le déplacement de la caméra.\n\nSélectionnez Dvorak dans les paramètres du jeu ; le patch ne change pas automatiquement de profil. Fonctionne avec toutes les langues de texte prises en charge, y compris en mode Fichiers de jeu uniquement. Les autres profils de commandes restent inchangés."
    }
    if current not in source:
        source[current]='В профиле Dvorak клавиши WASD перемещают камеру, управление стрелками сохраняется. F выбирает союзную метку. Остальные позиционные привязки сохранены; прежнее действие A освобождено для движения камеры.\n\nВыберите Dvorak в настройках игры; патч не переключает профили автоматически. Работает со всеми поддерживаемыми языками текста, в том числе в режиме «Только игровые файлы». Другие профили управления не изменяются.'
        (a.review/'source-keys.json').write_text(json.dumps(dict(sorted(source.items())),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'tools/ui-language-corrections.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Authored feature corrections:',len(out))

if __name__=='__main__':main()
