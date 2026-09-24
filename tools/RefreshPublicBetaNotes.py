"""Refresh concise public beta.2/beta.3 notes and re-sign the beta catalog."""
import argparse
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from PrepareRelease081 import key, sign
from PrepareRelease070 import read, verify, write


REPO = Path(__file__).resolve().parents[1]


BETA3 = {
    "ru": "## Изменения ботов\n\nРаботают при включённой опции «Улучшения ботов».\n\n- При заполненном лимите боты могут заменить слабую боевую роту на доступную роту минимум на 35% сильнее. Герои возвращаются обычным способом при расформировании.\n- Исправлены повторный найм строителей и приказы на строительство.\n- Харунам достаточно одной многоразовой роты строителей. Строители харунов и нежити могут идти строить с одним живым рабочим. Герои не попадают в роты строителей.\n- Бот может передать менее развитый город союзнику, если у него как минимум на пять городов больше.\n- Новые боты по умолчанию получают сложность «Кошмар». Предупреждения о превышении времени работы ИИ появляются не чаще одного раза в пять минут.\n\n## Интерфейс и баланс\n\n- Сложность ботов сохраняется при смене типа карты. В общей панели фракция остаётся случайной, пока не выбрана раса; у клиентов панель больше не перекрывает список игроков.\n- Убраны лишние подсказки общей панели. Подсказки сложности кратко показывают разницу стоимости найма и строительства.\n- Повторные нажатия на кнопку звука золотого рудника воспроизводятся сразу и не прерывают предыдущий звук.\n- В списке сетевых игр поле карты/сохранения помечается «Paws Launcher».\n- Водоворот гаури со стоимостью 0,75 очка королевства требует построенного королевства гаури.",
    "en": "## AI changes\n\nApply when “AI improvements” is enabled.\n\n- At the company cap, bots can replace a weak military company with an available company at least 35% stronger. Heroes return through normal disbanding.\n- Fixed duplicate builder recruitment and construction orders.\n- Haroun keeps one reusable settlement company. Haroun and Undead builders can set out with one living worker. Builders do not receive heroes.\n- A bot can give a less developed city to an ally when it owns at least five more cities.\n- New bots default to Nightmare. AI time-limit warnings appear at most once every five minutes.\n\n## Interface and balance\n\n- Bot difficulty survives map-type changes. Bulk faction selection stays Random until a race is chosen; the client panel no longer obstructs the player list.\n- Removed redundant bulk-panel tooltips. Difficulty tooltips briefly show recruitment and construction cost differences.\n- Repeated clicks on the gold-mine sound button play immediately and overlap previous playback.\n- The multiplayer map/save display field reads “Paws Launcher”.\n- The Gauri Maelstrom costing 0.75 kingdom points requires a Gauri kingdom.",
    "uk": "## Зміни ботів\n\nПрацюють з опцією «Покращення ботів».\n\n- За повного ліміту боти можуть замінити слабку бойову роту доступною ротою, сильнішою щонайменше на 35%. Герої повертаються звичайним способом під час розформування.\n- Виправлено повторний найм будівельників і накази на будівництво.\n- Харунам достатньо однієї багаторазової роти будівельників. Харуни й нежить можуть будувати з одним живим робітником. Герої не потрапляють до рот будівельників.\n- Бот може передати менш розвинене місто союзнику, якщо має щонайменше на п’ять міст більше.\n- Нові боти типово отримують «Кошмар». Попередження про час роботи ШІ з’являються не частіше ніж раз на п’ять хвилин.\n\n## Інтерфейс і баланс\n\n- Складність зберігається після зміни типу карти. Загальний вибір фракції лишається випадковим до вибору раси; клієнтська панель більше не перекриває список гравців.\n- Прибрано зайві підказки панелі. Підказки складності коротко показують різницю вартості найму й будівництва.\n- Повторні натискання кнопки звуку золотої копальні відтворюються одразу й не переривають попередній звук.\n- Поле карти/збереження в списку ігор показує «Paws Launcher».\n- Водоверт гаурі за 0,75 очка королівства потребує королівства гаурі.",
    "de": "## KI-Änderungen\n\nGelten bei aktivierten „KI-Verbesserungen“.\n\n- Bei vollem Kompanielimit können Bots eine schwache Kampfkompanie durch eine verfügbare, mindestens 35 % stärkere ersetzen. Helden kehren beim normalen Auflösen zurück.\n- Doppelter Bautrupp-Rekrutierung und Bauaufträge wurden korrigiert.\n- Haroun behalten einen wiederverwendbaren Siedlungsbautrupp. Haroun und Untote können mit einem lebenden Arbeiter bauen. Bautrupps erhalten keine Helden.\n- Ein Bot kann einem Verbündeten eine weniger ausgebaute Stadt geben, wenn er mindestens fünf Städte mehr besitzt.\n- Neue Bots erhalten standardmäßig „Albtraum“. KI-Zeitwarnungen erscheinen höchstens alle fünf Minuten.\n\n## Oberfläche und Balance\n\n- Bot-Schwierigkeiten bleiben beim Kartenwechsel erhalten. Die gemeinsame Fraktionsauswahl bleibt bis zur Volkswahl zufällig; bei Clients verdeckt das Panel die Spielerliste nicht mehr.\n- Überflüssige Panelhinweise entfernt. Schwierigkeits-Hinweise zeigen kurz die Kostenunterschiede für Rekrutierung und Bau.\n- Wiederholte Klicks auf die Goldminen-Tonschaltfläche werden sofort abgespielt und überlagern vorherige Wiedergaben.\n- Das Karten-/Spielstandfeld der Mehrspielerliste zeigt „Paws Launcher“.\n- Der Gauri-Maelstrom für 0,75 Königreichspunkte benötigt ein Gauri-Königreich.",
    "fr": "## Modifications des bots\n\nAvec l’option « Améliorations de l’IA » activée.\n\n- À la limite de compagnies, les bots peuvent remplacer une compagnie militaire faible par une compagnie disponible au moins 35 % plus forte. Les héros reviennent par la dissolution normale.\n- Correction du recrutement en double des bâtisseurs et des ordres de construction.\n- Les Haroun conservent une seule compagnie de bâtisseurs réutilisable. Haroun et morts-vivants peuvent construire avec un ouvrier vivant. Les bâtisseurs ne reçoivent pas de héros.\n- Un bot peut donner une ville moins développée à un allié s’il possède au moins cinq villes de plus.\n- Les nouveaux bots utilisent « Cauchemar » par défaut. Les avertissements de temps de l’IA apparaissent au plus toutes les cinq minutes.\n\n## Interface et équilibrage\n\n- La difficulté persiste lors d’un changement de type de carte. La faction commune reste aléatoire avant le choix d’une race ; le panneau client ne masque plus la liste des joueurs.\n- Suppression des infobulles superflues du panneau. Celles des difficultés indiquent brièvement les écarts de coût du recrutement et de la construction.\n- Les clics répétés sur le bouton du son de mine d’or sont joués immédiatement et se superposent aux sons précédents.\n- Le champ carte/sauvegarde de la liste multijoueur affiche « Paws Launcher ».\n- Le Maelstrom gauri coûtant 0,75 point de royaume nécessite un royaume gauri.",
    "cs": "## Změny botů\n\nPlatí se zapnutou volbou „Vylepšení botů“.\n\n- Při plném limitu mohou boti nahradit slabou bojovou rotu dostupnou rotou alespoň o 35 % silnější. Hrdinové se vracejí běžným rozpuštěním roty.\n- Opraven dvojitý nábor stavitelů a stavební příkazy.\n- Haroun si ponechávají jednu opakovaně použitelnou stavební rotu. Haroun a nemrtví mohou stavět s jedním živým dělníkem. Stavitelé nedostávají hrdiny.\n- Bot může dát méně rozvinuté město spojenci, pokud má alespoň o pět měst více.\n- Noví boti mají standardně obtížnost „Noční můra“. Upozornění na čas AI se zobrazí nejvýše jednou za pět minut.\n\n## Rozhraní a vyvážení\n\n- Obtížnost botů zůstává při změně typu mapy. Společná frakce je náhodná, dokud není vybrána rasa; klientský panel již nezakrývá seznam hráčů.\n- Odstraněny nadbytečné nápovědy panelu. Nápovědy obtížnosti stručně ukazují rozdíly ceny náboru a výstavby.\n- Opakovaná kliknutí na tlačítko zvuku zlatého dolu se přehrají hned a překrývají předchozí zvuk.\n- Pole mapy/uložené hry v seznamu her zobrazuje „Paws Launcher“.\n- Gauri Maelstrom za 0,75 bodu království vyžaduje království Gauri.",
}

BETA_GUIDE = {
    "ru": "Работают при включённой опции «Улучшения ботов».\n\n- Добавлена сложность «Кошмар»: строительство и найм дешевле на 90%.\n- Ускорены разведка, зачистка мест поселений и отправка строителей. Боты используют до пяти разведчиков.\n- Исправлен найм с учётом ополчения, свободных площадок и лимитов рот. Рот снабжения нанимается не более двух.\n- Строители не получают героев и плановых боевых задач. Лишние рабочие могут расформировываться; строителям нежити и харунов достаточно одного живого рабочего.\n- Улучшены планы городов всех рас, подготовка королевства и приоритет улучшений ополчения. Большие логова откладываются до третьего города.\n- При заполненном лимите боты могут заменить слабую боевую роту на доступную роту минимум на 35% сильнее. Герои возвращаются обычным способом при расформировании.\n- Исправлены повторный найм строителей и приказы на строительство.\n- Бот может передать менее развитый город союзнику, если у него как минимум на пять городов больше.\n- Новые боты по умолчанию получают сложность «Кошмар». Предупреждения о превышении времени работы ИИ появляются не чаще одного раза в пять минут.",
    "en": "Apply when “AI improvements” is enabled.\n\n- Added Nightmare difficulty: construction and recruitment cost 90% less.\n- Faster exploration, settlement clearing and builder dispatch. Bots use up to five scouts.\n- Fixed recruitment accounting for militia, available sites and company limits. Bots recruit no more than two supply companies.\n- Builders receive no heroes or planned combat tasks. Surplus workers can be disbanded; Undead and Haroun builders need only one living worker.\n- Improved city plans for all races, kingdom preparation and militia upgrade priorities. Large lairs are postponed until the third city.\n- At the company cap, bots can replace a weak military company with an available company at least 35% stronger. Heroes return through normal disbanding.\n- Fixed duplicate builder recruitment and construction orders.\n- A bot can give a less developed city to an ally when it owns at least five more cities.\n- New bots default to Nightmare. AI time-limit warnings appear at most once every five minutes.",
}


def concise_beta2(body):
    replacements = {
        "ru": ("Строители закрепляются за разными площадками, не получают героев и плановых боевых задач. Лишние рабочие могут расформировываться; строителям нежити достаточно 20% здоровья.", "Строители не получают героев и плановых боевых задач. Лишние рабочие могут расформировываться."),
        "en": ("Builders keep separate settlement assignments and receive no heroes or planned combat tasks. Surplus workers can be disbanded; Undead builders need only 20% health.", "Builders receive no heroes or planned combat tasks. Surplus workers can be disbanded."),
        "uk": ("Будівельники закріплюються за різними місцями, не отримують героїв і планових бойових завдань. Зайвих робітників можна розформувати; будівельникам нежиті достатньо 20% здоров’я.", "Будівельники не отримують героїв і планових бойових завдань. Зайвих робітників можна розформувати."),
        "de": ("Bautrupps behalten unterschiedliche Bauplätze und erhalten weder Helden noch geplante Kampfaufträge. Überzählige Arbeiter können aufgelöst werden; untote Bautrupps benötigen nur 20 % Gesundheit.", "Bautrupps erhalten weder Helden noch geplante Kampfaufträge. Überzählige Arbeiter können aufgelöst werden."),
        "fr": ("Les bâtisseurs conservent des sites distincts et ne reçoivent ni héros ni missions de combat planifiées. Les ouvriers excédentaires peuvent être dissous ; les bâtisseurs morts-vivants n’ont besoin que de 20 % de santé.", "Les bâtisseurs ne reçoivent ni héros ni missions de combat planifiées. Les ouvriers excédentaires peuvent être dissous."),
        "cs": ("Stavitelé si drží různá stavební místa a nedostávají hrdiny ani plánované bojové úkoly. Přebytečné pracovníky lze rozpustit; nemrtvým stavitelům stačí 20 % zdraví.", "Stavitelé nedostávají hrdiny ani plánované bojové úkoly. Přebytečné pracovníky lze rozpustit."),
    }
    old, new = replacements[body[0]]
    if new in body[1]:
        return body[1]
    assert old in body[1], body[0]
    return body[1].replace(old, new)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--signing-dir", type=Path, required=True)
    parser.add_argument("--publish", action="store_true", help="Update the two immutable release pages after local verification.")
    args = parser.parse_args()
    private = serialization.load_pem_private_key((args.signing_dir / "pawpatch-signing-private.pem").read_bytes(), None)
    assert private.public_key().public_numbers() == key().public_numbers()

    feed_path = REPO / "feed/v2/beta.json"
    feed = verify(read(feed_path), key())
    original_feed = deepcopy(feed)
    assert feed["patchGuide"]["version"] == "0.4.0-beta.3"
    note = next(x for x in feed["changelog"] if x["version"] == "0.4.0-beta.3")
    note["body"] = deepcopy(BETA3)
    previous_note = next(x for x in feed["changelog"] if x["version"] == "0.4.0-beta.2")
    previous_note["body"] = {
        language: concise_beta2((language, body)) for language, body in previous_note["body"].items()
    }
    guide = next(x for x in feed["patchGuide"]["entries"] if x["id"] == "ai-improvements")
    guide["bodyRu"] = BETA_GUIDE["ru"]
    guide["bodyEn"] = BETA_GUIDE["en"]
    if feed != original_feed:
        write(feed_path, sign(feed, private))

    source_path = REPO / "docs/release-20260924.json"
    source = read(source_path)
    source_guide = next(x for x in source["guide"] if x["id"] == "ai-improvements")
    source_guide["bodyRu"] = BETA_GUIDE["ru"]
    source_guide["bodyEn"] = BETA_GUIDE["en"]
    write(source_path, source)

    history_path = REPO / "feed/changelog.history.json"
    history = read(history_path)
    refreshed = {entry["version"]: entry for entry in feed["changelog"]}
    history["beta"] = [deepcopy(refreshed.get(entry["version"], entry)) for entry in history["beta"]]
    write(history_path, history)
    write(REPO / "feed/patch-guide-beta.json", feed["patchGuide"])
    if args.publish:
        credential = subprocess.run(
            ["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
            text=True, capture_output=True, check=True,
        )
        fields = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)
        token = os.environ.get("GH_TOKEN", fields.get("password"))
        if not token:
            raise RuntimeError("No configured GitHub credential")
        api = "https://api.github.com/repos/VasiliyPaw/PawsPatchLauncher"
        headers = {"Authorization": "Bearer " + token, "User-Agent": "PawsPatchPublisher",
                   "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "Content-Type": "application/json"}
        for version in ("0.4.0-beta.2", "0.4.0-beta.3"):
            tag = "patch-" + version
            request = urllib.request.Request(api + "/releases/tags/" + urllib.parse.quote(tag), headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                release = json.load(response)
            body = (REPO / "docs" / ("release-patch-" + version + ".md")).read_text(encoding="utf-8")
            request = urllib.request.Request(api + "/releases/" + str(release["id"]),
                data=json.dumps({"body": body}).encode("utf-8"), headers=headers, method="PATCH")
            with urllib.request.urlopen(request, timeout=60) as response:
                updated = json.load(response)
            if updated["body"] != body or updated["tag_name"] != tag or updated["draft"]:
                raise RuntimeError("Release-note update verification failed: " + tag)
            print("RELEASE_NOTES_UPDATED", tag)
    print("REFRESHED_PUBLIC_NOTES", feed["patchGuide"]["version"])


if __name__ == "__main__":
    main()
