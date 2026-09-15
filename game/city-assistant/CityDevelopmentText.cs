internal static partial class PawAssistantRuntime
{
    private static readonly string[,] cityAdvice = {
        {
            "Priority: final city center upgrade, needed resources, gold, then random eligible development. If a resource target cannot be improved, the next priority is used. The gold reserve and all queued work are respected.",
            "Приоритет: последнее улучшение центра, нужные ресурсы, золото, затем случайное доступное развитие. Если повысить нужный доход ресурсов нельзя, выбирается следующий приоритет. Запас золота и вся очередь учитываются.",
            "Priorität: letzte Aufwertung des Stadtzentrums, benötigte Ressourcen, Gold, dann zufälliger zulässiger Ausbau. Ist das Ressourcenziel nicht verbesserbar, folgt die nächste Priorität. Goldreserve und gesamte Bauwarteschlange werden berücksichtigt.",
            "Priorité : dernière amélioration du centre-ville, ressources nécessaires, or, puis développement admissible aléatoire. Si le revenu requis ne peut pas augmenter, la priorité suivante est utilisée. La réserve d’or et toute la file de construction sont prises en compte.",
            "Priorita: poslední vylepšení centra města, potřebné suroviny, zlato, poté náhodný dostupný rozvoj. Pokud potřebný příjem nelze zvýšit, použije se další priorita. Zlatá rezerva a celá fronta staveb se zohledňují.",
            "Пріоритет: останнє поліпшення центру, потрібні ресурси, золото, потім випадковий доступний розвиток. Якщо потрібний дохід ресурсів підвищити неможливо, обирається наступний пріоритет. Золотий резерв і вся черга враховуються."
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
