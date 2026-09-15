internal static partial class PawAssistantRuntime
{
    private static readonly string[,] cityAdvice = {
        {
            "Final city center upgrade first. Then choose the greatest gold income gain after resource shortage costs, counting all queued work. Resource targets and random development follow when no profitable action is available. Markets use only their greatest gold-increasing upgrade; otherwise they are not upgraded. The gold reserve is protected. Settings are saved per match; new matches use defaults.",
            "Сначала последнее улучшение центра. Затем выбирается наибольший прирост дохода золота после расходов на дефицит ресурсов с учётом всей очереди. Если прибыльных действий нет, выполняются цели по ресурсам и случайное развитие. Рынки улучшаются только по ветке с наибольшим приростом золота; без такой ветки не улучшаются. Запас золота защищён. Настройки сохраняются для партии; новая партия начинается со стандартных.",
            "Zuerst die letzte Aufwertung des Stadtzentrums. Danach zählt der größte zusätzliche Goldertrag nach Abzug der Kosten für Ressourcendefizite und unter Berücksichtigung der gesamten Bauwarteschlange. Ohne rentable Aktion folgen Ressourcenziele und zufälliger Ausbau. Märkte erhalten nur die Aufwertung mit dem höchsten Goldzuwachs; ohne eine solche bleiben sie unverändert. Die Goldreserve bleibt geschützt. Einstellungen gelten pro Partie; neue Partien starten mit Standardwerten.",
            "Priorité à la dernière amélioration du centre-ville, puis au meilleur gain d’or après déduction du coût des pénuries, en tenant compte de toute la file de construction. Sans action rentable, les objectifs de ressources puis le développement aléatoire prennent le relais. Les marchés ne reçoivent que l’amélioration offrant le plus d’or supplémentaire ; sans elle, ils restent inchangés. La réserve d’or est protégée. Réglages propres à chaque partie ; valeurs par défaut pour une nouvelle partie.",
            "Nejprve poslední vylepšení centra města. Potom se volí nejvyšší přírůstek příjmu zlata po odečtení nákladů na nedostatek surovin se započtením celé fronty. Bez výnosné možnosti následují cíle surovin a náhodný rozvoj. Tržiště dostanou pouze vylepšení s nejvyšším přírůstkem zlata; bez takové větve se nevylepšují. Zlatá rezerva je chráněna. Nastavení se ukládá pro každou partii; nová partie začíná s výchozími hodnotami.",
            "Спочатку останнє поліпшення центру. Потім обирається найбільший приріст доходу золота після витрат на дефіцит ресурсів з урахуванням усієї черги. Якщо прибуткових дій немає, виконуються цілі щодо ресурсів і випадковий розвиток. Ринки поліпшуються лише за гілкою з найбільшим приростом золота; без такої гілки не поліпшуються. Золотий резерв захищено. Налаштування зберігаються для партії; нова партія починається зі стандартних."
        },
        {
            "No available order currently meets the resource protection and queue constraints.",
            "Сейчас нет доступного приказа, допустимого с учётом защиты ресурсов и очереди строительства.",
            "Derzeit erfüllt kein verfügbarer Auftrag die Anforderungen des Ressourcenschutzes und der Bauwarteschlange.",
            "Aucun ordre disponible ne respecte actuellement la protection des ressources et la file de construction.",
            "Žádný dostupný příkaz nyní nesplňuje podmínky ochrany surovin a fronty staveb.",
            "Зараз немає доступного наказу, допустимого з урахуванням захисту ресурсів і черги будівництва."
        },
        {"Could not read match settings", "Не удалось прочитать настройки партии", "Partieeinstellungen konnten nicht gelesen werden", "Impossible de lire les réglages de la partie", "Nastavení partie se nepodařilo načíst", "Не вдалося прочитати налаштування партії"},
        {"Auto-upgrade is paused. See the Paw’s Patch log for details.", "Автоулучшение приостановлено. Подробности в журнале Paw’s Patch.", "Der automatische Ausbau ist pausiert. Einzelheiten stehen im Protokoll von Paw’s Patch.", "L’amélioration automatique est suspendue. Consultez le journal de Paw’s Patch.", "Automatická vylepšení jsou pozastavena. Podrobnosti jsou v protokolu Paw’s Patch.", "Автополіпшення призупинено. Подробиці в журналі Paw’s Patch."}
    };
    private static string CityAdvice(int index) {return cityAdvice[index,(int)PawGameText.LanguageId];}
}
