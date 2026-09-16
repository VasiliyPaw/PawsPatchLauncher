"""Authored six-language help for the scoped patch releases."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEXTS={
'options':[
"\n\nДополнительные переключатели беты: 48 цветов с компактным выбором и игнорирование рассинхронов. Для них требуется совместимый EXE игры. При выключении Paw's Patch оба переключателя отключаются.",
"\n\nOptional Beta switches: 48 colors with a compact picker and Ignore desyncs. Both require a supported game executable. Turning Paw's Patch off disables both switches.",
"\n\nOptionale Beta-Schalter: 48 Farben mit kompakter Auswahl und Desynchronisationen ignorieren. Beide erfordern eine unterstützte Spiel-EXE. Beim Ausschalten von Paw's Patch werden beide Schalter deaktiviert.",
"\n\nOptions de la bêta : 48 couleurs avec un sélecteur compact et Ignorer les désynchronisations. Elles nécessitent un exécutable du jeu compatible. Désactiver Paw's Patch désactive ces deux options.",
"\n\nVolitelné přepínače betaverze: 48 barev s kompaktním výběrem a ignorování desynchronizací. Obě funkce vyžadují podporovaný spustitelný soubor hry. Vypnutím Paw's Patch se oba přepínače vypnou.",
"\n\nДодаткові перемикачі бети: 48 кольорів із компактним вибором та ігнорування розсинхронізацій. Для них потрібен сумісний EXE гри. Вимкнення Paw's Patch вимикає обидва перемикачі."],
'rules':[
"\n\nПравила и баланс выбранного режима сохраняются. По умолчанию используется стандартная обработка рассинхронов.",
"\n\nThe selected mode's rules and balance are preserved. Standard desync handling is used by default.",
"\n\nRegeln und Balance des gewählten Modus bleiben erhalten. Standardmäßig gilt die normale Behandlung von Desynchronisationen.",
"\n\nLes règles et l'équilibrage du mode choisi sont conservés. La gestion normale des désynchronisations est utilisée par défaut.",
"\n\nPravidla a vyvážení zvoleného režimu zůstávají zachovány. Ve výchozím stavu se desynchronizace zpracovávají standardně.",
"\n\nПравила та баланс вибраного режиму зберігаються. За замовчуванням використовується стандартна обробка розсинхронізацій."],
'transfer':[
"Ускоряет штатную передачу сохранений участникам сетевого лобби. Включается вместе с Paw's Patch; отдельный переключатель не нужен. Доступно в релизе 0.2.0 и бете 0.3.0.\n\nТребуется поддерживаемый EXE Kohan II 1.3.72. В режиме «Только игровые файлы» и при выключенном патче передача остаётся обычной.",
"Speeds up the game's native saved-game transfers to multiplayer lobby participants. Included with Paw's Patch; no separate switch is needed. Available in Release 0.2.0 and Beta 0.3.0.\n\nRequires the supported Kohan II 1.3.72 executable. Transfer stays at regular speed in file-only mode and with the patch disabled.",
"Beschleunigt die spieleigene Übertragung von Spielständen an Teilnehmer der Mehrspieler-Lobby. In Paw's Patch enthalten; kein eigener Schalter nötig. Verfügbar in Release 0.2.0 und Beta 0.3.0.\n\nErfordert die unterstützte Kohan-II-EXE 1.3.72. Im Modus Nur Spieldateien und bei ausgeschaltetem Patch bleibt die Übertragung unverändert.",
"Accélère le transfert natif des sauvegardes aux participants du salon multijoueur. Inclus dans Paw's Patch, sans option séparée. Disponible dans la version stable 0.2.0 et la bêta 0.3.0.\n\nNécessite l'exécutable compatible de Kohan II 1.3.72. Le transfert conserve sa vitesse habituelle en mode Fichiers du jeu uniquement et lorsque le patch est désactivé.",
"Zrychluje přenos uložených her účastníkům lobby prostřednictvím samotné hry. Je součástí Paw's Patch, bez samostatného přepínače. Dostupné ve vydání 0.2.0 a betaverzi 0.3.0.\n\nVyžaduje podporovaný spustitelný soubor Kohan II 1.3.72. V režimu Pouze herní soubory a při vypnutém patchi zůstává běžná rychlost přenosu.",
"Прискорює штатну передачу збережень учасникам мережевого лобі. Входить до Paw's Patch; окремий перемикач не потрібен. Доступно в релізі 0.2.0 і бета-версії 0.3.0.\n\nПотрібен підтримуваний EXE Kohan II 1.3.72. У режимі «Лише файли гри» та з вимкненим патчем швидкість передачі залишається звичайною."],
'colors':[
"48 цветов и вариант «Случайно». Компактный список открывается стрелкой возле кружка цвета и не занимает вторую строку игрока. Светло-красный убран из выбора; старые сохранения с ним поддерживаются.\n\nЦвет следует за участником при смене места и переходе в наблюдатели. Новый участник не наследует цвет прежнего владельца места. После нового подключения цвет выбирается заново.\n\nХост может менять все цвета, клиент — только свой. В загруженных сохранениях цвета королевств доступны только для просмотра. Требуется совместимый EXE; версии патча и настройки участников должны совпадать.",
"48 colors plus Random. The compact list opens from the arrow beside the color circle without adding a second player row. Light Red is removed from the picker; older saves using it remain supported.\n\nColors follow participants when changing seats or spectating. A new participant does not inherit the previous occupant's color. Reconnecting starts a new color choice.\n\nHosts can change all colors; clients only their own. Kingdom colors in loaded saves are read-only. Requires a supported executable and matching patch versions and participant settings.",
"48 Farben sowie Zufällig. Die kompakte Liste öffnet sich über den Pfeil neben dem Farbkreis, ohne eine zweite Spielerzeile zu belegen. Hellrot ist nicht mehr auswählbar; ältere Spielstände damit bleiben unterstützt.\n\nFarben folgen den Teilnehmern beim Platzwechsel und im Zuschauermodus. Neue Teilnehmer übernehmen nicht die Farbe des vorherigen Platzinhabers. Nach erneutem Verbinden wird die Farbe neu gewählt.\n\nDer Host kann alle Farben ändern, Clients nur ihre eigene. Königreichsfarben geladener Spielstände sind schreibgeschützt. Eine unterstützte EXE sowie gleiche Patchversionen und Teilnehmereinstellungen sind erforderlich.",
"48 couleurs et Aléatoire. La liste compacte s'ouvre avec la flèche près du cercle de couleur, sans ajouter de deuxième ligne par joueur. Le rouge clair est retiré du sélecteur ; les anciennes sauvegardes qui l'utilisent restent compatibles.\n\nLa couleur suit le participant lors d'un changement de place ou du passage en spectateur. Un nouveau participant n'hérite pas de la couleur de l'occupant précédent. Une reconnexion réinitialise le choix.\n\nL'hôte peut modifier toutes les couleurs, les clients uniquement la leur. Dans une sauvegarde chargée, les couleurs des royaumes sont en lecture seule. Un exécutable compatible et des versions du patch et réglages identiques sont requis.",
"48 barev a možnost Náhodně. Kompaktní seznam se otevírá šipkou vedle barevného kolečka a nezabírá druhý řádek hráče. Světle červená byla z nabídky odebrána; starší uložené hry s touto barvou zůstávají podporovány.\n\nBarva následuje účastníka při změně místa i přechodu mezi diváky. Nový účastník nepřebírá barvu předchozího hráče. Po novém připojení se barva volí znovu.\n\nHostitel může měnit všechny barvy, klient pouze vlastní. V načtených uložených hrách jsou barvy království jen pro čtení. Vyžaduje podporovaný spustitelný soubor a shodné verze patche i nastavení účastníků.",
"48 кольорів і варіант «Випадково». Компактний список відкривається стрілкою біля кольорового кружечка й не займає другий рядок гравця. Світло-червоний прибрано з вибору; старі збереження з ним підтримуються.\n\nКолір слідує за учасником під час зміни місця та переходу в спостерігачі. Новий учасник не успадковує колір попереднього власника місця. Після нового підключення колір обирається заново.\n\nХост може змінювати всі кольори, клієнт — лише свій. У завантажених збереженнях кольори королівств доступні лише для перегляду. Потрібен сумісний EXE та однакові версії патча й налаштування учасників."],
'terrain':[
"При создании карты инициализирует параметр рельефа, который мог содержать случайные данные памяти. Размеры карт и игровые правила не меняются. Требуется поддерживаемый EXE 1.3.72.",
"Initializes a terrain parameter that could contain uninitialized memory during map generation. Map sizes and gameplay rules are unchanged. Requires the supported 1.3.72 executable.",
"Initialisiert einen Geländeparameter, der bei der Kartenerstellung nicht initialisierten Speicher enthalten konnte. Kartengrößen und Spielregeln bleiben unverändert. Erfordert die unterstützte EXE 1.3.72.",
"Initialise un paramètre du terrain qui pouvait contenir des données mémoire non initialisées lors de la création de la carte. Les tailles de carte et règles du jeu sont inchangées. Nécessite l'exécutable compatible 1.3.72.",
"Při vytváření mapy inicializuje parametr terénu, který mohl obsahovat neinicializovanou paměť. Velikosti map a herní pravidla se nemění. Vyžaduje podporovaný spustitelný soubor 1.3.72.",
"Під час створення карти ініціалізує параметр рельєфу, який міг містити неініціалізовані дані пам’яті. Розміри карт та правила гри не змінюються. Потрібен підтримуваний EXE 1.3.72."]}

def apply():
    for i,code in enumerate(('ru','en','de','fr','cs','uk')):
        if i<2:continue
        path=ROOT/'src/PawsPatchLauncher/Assets/Languages'/(code+'.json');catalog=json.loads(path.read_text('utf-8'))
        for texts in TEXTS.values():catalog[texts[1]]=texts[i]
        path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':apply()
