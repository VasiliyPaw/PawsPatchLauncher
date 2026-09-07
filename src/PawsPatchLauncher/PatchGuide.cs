namespace PawsPatchLauncher;

// Current authored feature guide. Keep RU/EN together; do not derive prose from executable names.
public sealed record PatchGuideEntry(string Id, string Category, string TitleRu, string TitleEn, string BodyRu, string BodyEn)
{
    public string Title(string language) => language == "en" ? TitleEn : TitleRu;
    public string Body(string language) => language == "en" ? BodyEn : BodyRu;
}

public static class PatchGuide
{
    public const int PlayerColorCount = 49;
    public const string DesyncHelpRu = "Официальный режим останавливает матч при рассинхроне. Режим «Продолжать игру» пропускает все обнаруженные рассинхроны, в том числе серьёзные, которые могут заметно повлиять на ход матча. Он не исправляет расхождения: у игроков могут отличаться события, положение и действия рот, ресурсы и исход боя.";
    public const string DesyncHelpEn = "Official handling stops the match on a desync. Continue the game skips all detected desyncs, including serious ones that can substantially affect the match. It does not repair divergent states: players may see different events, company positions and actions, resources or battle outcomes.";
    public static string CategoryName(string category, string language) => (category, language == "en") switch
    {
        ("optional", false) => "Настраиваемое", ("optional", true) => "Configurable",
        ("beta", false) => "В бете", ("beta", true) => "In Beta",
        (_, false) => "Всегда включено", _ => "Always included"
    };
    public static string CategoryDescription(string category, string language) => (category, language == "en") switch
    {
        ("optional", false) => "Эти функции выбираются в разделе «Компоненты». Изменения применяются при установке или перед запуском игры. Здесь только описание, настройки не переключаются.",
        ("optional", true) => "Choose these features in Components. Changes are applied when installing or before launching the game. This page only describes them; it does not change settings.",
        ("beta", false) => "Дополнения текущей беты патча. Просмотр этой вкладки не включает бета-канал. Для сетевой игры всем участникам нужна совместимая версия и одинаковые игровые настройки.",
        ("beta", true) => "Additions in the current patch Beta. Reading this tab does not enable the Beta channel. Multiplayer peers need compatible versions and matching gameplay settings.",
        (_, false) => "Обязательная основа Paw's Patch, доступная и в релизе, и в бете. Эти изменения устанавливаются вместе с патчем и не имеют отдельных переключателей.",
        _ => "The required Paw's Patch base, included in both Release and Beta. These changes are installed with the patch and have no separate switches."
    };

    // Retained for pinned, signed releases made before the feed carried its own guide.
    public static IReadOnlyList<PatchGuideEntry> LegacyEntries { get; } = [
        new("base", "always", "Paw's Patch и Arcane Wars", "Paw's Patch and Arcane Wars",
            "Лаунчер устанавливает Arcane Wars как основу и применяет изменения Paw's Patch: общие исправления, дополнительные настройки и функции бета-канала.\n\nЗдесь собраны действующие возможности патча. Список отдельных обновлений с датами и версиями доступен в «Истории изменений» справа.",
            "The launcher installs Arcane Wars as the base mod and applies Paw's Patch changes: shared fixes, optional settings and Beta features.\n\nThis guide covers the patch's current features. Individual updates with dates and versions are listed in the Changelog on the right."),
        new("powers-shards", "optional", "Отключение Powers и Shards", "Disable Powers and Shards",
            "Включённый переключатель убирает глобальные способности Arcane Wars и ресурс Shards: их меню, применение игроками и компьютером, производство и расход осколков. Это стандартный режим Paw's Patch.\n\nВыключите его, чтобы вернуть обе механики Arcane Wars вместе. Остальные выбранные изменения патча сохраняются. Настройка применяется перед запуском игры; для сетевого матча она должна совпадать у всех участников. После переключения начинайте новый матч: сохранения с другим набором ресурсов могут быть несовместимы.",
            "When enabled, this option removes Arcane Wars global powers and the Shards resource: their menu, use by players and AI, shard production and spending. This is the default Paw's Patch mode.\n\nTurn it off to restore both Arcane Wars mechanics together. Other selected patch changes are preserved. The setting is applied before launching the game and must match for every multiplayer participant. Start a new match after switching: saves made with a different resource set may be incompatible."),
        new("kingdoms", "always", "До 16 королевств и 8 команд", "Up to 16 kingdoms and 8 teams",
            "На случайных картах доступны до 16 игровых королевств и до 8 команд. Можно собирать крупные матчи с людьми и компьютером. Независимые семейства используют отдельные служебные королевства и не являются дополнительными местами для игроков.",
            "Random maps support up to 16 playable kingdoms and up to 8 teams, allowing larger matches with humans and AI. Independent families use separate internal kingdoms; these are not extra player slots."),
        new("maps", "always", "Большие случайные карты", "Larger random maps",
            "Добавлены два размера: 1024×1024 и 1152×1152. Они доступны постоянно, без отдельного переключателя. Большая карта даёт больше пространства для исследования и развёртывания армий, но дольше создаётся и требует больше ресурсов компьютера.\n\nНа самой большой карте, 1152×1152, игра работает на пределе своих возможностей и особенно склонна к вылетам. Для более надёжной игры выбирайте меньший размер.",
            "Two sizes are added: 1024×1024 and 1152×1152. They are always available without a separate switch. Larger maps provide more room for exploration and armies, but take longer to generate and require more system resources.\n\nOn the largest map, 1152×1152, the game runs at the limits of its capabilities and is particularly prone to crashes. Choose a smaller size for more reliable play."),
        new("dvorak", "always", "Управление в профиле Dvorak", "Dvorak control profile",
            "В профиль управления Dvorak добавлено движение камеры на WASD; управление стрелками также сохраняется. Клавиша F ставит союзную метку на карте.\n\nИзменения относятся именно к профилю Dvorak в настройках самой игры. Они не означают, что клавиши принудительно меняются во всех профилях.",
            "The Dvorak control profile adds WASD camera movement while retaining the arrow keys. F places an allied map marker.\n\nThese changes apply specifically to the Dvorak profile selected in the game's settings. They do not forcibly change keys in every profile."),
        new("independent", "optional", "Вражда независимых", "Independent faction hostility",
            "Логова, лагеря и независимые города распределяются по командам семейств. Разные семейства могут сражаться друг с другом и с игроками, а выбранные монстры охотятся на животных.\n\nРаспределение выполняется после генерации карты. Захваченные владения сохраняют своего владельца при загрузке сохранения. Для игроков за Нежить и Тень применяется враждебность к животным. Старые механики нейтралитета по совпадению расы и провокации не используются.\n\nПри отключении не применяется распределение независимых объектов по командам семейств. В сетевом матче эта настройка должна совпадать у участников.",
            "Lairs, camps and independent towns are assigned to family factions. Different families can fight each other and players, while selected monsters hunt wildlife.\n\nAssignment happens after map generation. Captured holdings retain their owner when loading a save. Players using Undead or Shadow are hostile to wildlife. The old matching-race neutrality and provocation mechanics are not used.\n\nDisabling this option skips family-faction assignment for independent objects. Multiplayer participants must use the same setting."),
        new("frequency", "optional", "Частота блуждающих рот", "Roaming company frequency",
            "Стандартный режим использует обычные интервалы и шансы появления. Режим ×4 вдвое сокращает интервал между проверками и удваивает шанс события. В среднем роты появляются примерно в четыре раза чаще, но конкретное появление остаётся случайным.\n\nЧастота и добавление новых типов блуждающих рот настраиваются отдельно.",
            "Standard uses normal appearance intervals and chances. ×4 halves the interval between checks and doubles the event chance. On average, companies appear about four times as often, but individual appearances remain random.\n\nFrequency and the addition of new roaming-company types are configured separately."),
        new("roaming", "optional", "Новые блуждающие роты", "Additional roaming companies",
            "Добавляет выход рот из лагерей бандитов, варваров, ракшасов и слаан на местах поселений и фундаментов. Дополнительными источниками становятся логова пауков и скорпионов, Тёмный разлом и руины нежити.\n\nДля добавленных рот настроены параметры выхода, боевого духа и восстановления. Опцию можно отключить как при стандартной частоте, так и при ×4; тогда остаётся исходный набор источников блуждающих рот.",
            "Adds roaming companies from bandit, barbarian, Rhaksha and Slaan camps on settlement and foundation sites. Spider and scorpion lairs, the Dark Rift and undead ruins also become sources.\n\nThe added companies have tuned spawning, morale and recovery parameters. The option can be disabled with either Standard or ×4 frequency, leaving the original roaming-company sources."),
        new("siege", "optional", "Баланс осадных машин", "Siege engine balance",
            "Переключает весь набор изменений осадного баланса Paw's Patch. Багровая и Чумная катапульты, Баллиста Драконьего огня и Ворпальная машина используют по 0,75 очка королевства за одно орудие. У баллисты и Ворпальной машины также меняются урон, минимальная дальность и параметры атак, включая бомбардировку. Баланс в основном рассчитан на игры против компьютера.\n\nПри отключении возвращается исходный баланс всех четырёх машин из Arcane Wars, а не только их стоимость. Перевод и остальные выбранные компоненты сохраняются.",
            "Toggles the complete Paw's Patch siege rebalance. Crimson and Plague Catapults, Dragonfire Ballista and Vorpal Engine each use 0.75 kingdom points per engine. Ballista and Vorpal Engine damage, minimum range and attack settings, including bombardment, also change. The balance is mainly intended for matches against AI.\n\nDisabling it restores the original Arcane Wars balance for all four engines, not just their cost. Localization and other selected components are preserved."),
        new("localization", "optional", "Русская локализация", "Russian localization",
            "Устанавливает русский перевод оригинальной игры, Arcane Wars и дополнительных настроек патча. Язык игры выбирается отдельно от языка лаунчера.\n\nПри отключении используются исходные языковые файлы установленной игры и мода. Сама локализация не меняет игровую симуляцию.",
            "Installs Russian translations for the base game, Arcane Wars and additional patch settings. The game language is independent of the launcher language.\n\nDisabling it uses the underlying language files of the installed game and mod. Localization itself does not change the game simulation."),
        new("desync", "optional", "Продолжение после рассинхрона", "Continue after desync",
            DesyncHelpRu + "\n\nРежим доступен в релизе и в бете. Его можно выбрать независимо от вражды независимых. При включённых расширенных цветах текущая сборка использует официальную обработку рассинхрона, поэтому продолжение недоступно.",
            DesyncHelpEn + "\n\nAvailable in both Release and Beta, independently of independent-faction hostility. With extended player colors enabled, the current build uses official desync handling, so continuing after a desync is unavailable."),
        new("colors", "beta", "Расширенные цвета игроков", "Extended player colors",
            $"В текущей палитре {PlayerColorCount} цветов и вариант «Случайно». Оттенки идут группами: обычные, светлые и тёмные. Названия в списке окрашены в соответствующие цвета.\n\nВ лобби значок игрока отражает его выбор, а свободные слоты и «Случайно» обозначаются серым. Случайный выбор распределяет цвета перед матчем. Затенение значков рот смягчено, чтобы оттенки оставались различимыми.\n\nЭто тестируемая функция беты. Всем участникам нужны совместимые версии модуля цветов. В текущей сборке включение цветов также включает вражду независимых и оставляет официальную обработку рассинхрона.",
            $"The current palette contains {PlayerColorCount} colors plus Random, arranged in regular, light and dark groups. List labels are tinted to match each color.\n\nLobby badges reflect player choices; empty slots and Random use gray. Random selection assigns colors before the match. Company-badge shading is softened to keep colors distinguishable.\n\nThis Beta feature is still being tested. All participants need compatible color-module versions. In the current build, enabling colors also enables independent hostility and keeps official desync handling."),
        new("common-ui", "beta", "Версии в меню и правильный ноль", "Menu versions and correct zero display",
            "Под версией игры в главном меню показаны Arcane Wars и Paw's Patch с их версиями. В отображении лимитов исправлен отрицательный ноль: вместо -0 выводится 0.\n\nЭти исправления входят в текущую бету автоматически, даже если расширенные цвета и остальные дополнительные функции выключены. Меняется только отображение, а не сами значения лимитов.",
            "The main menu shows Arcane Wars and Paw's Patch versions beneath the game version. Negative zero in limit displays is corrected: -0 is shown as 0.\n\nThese fixes are automatically included in the current Beta even when extended colors and other optional features are disabled. Only the display changes, not the underlying limit values.")
    ];

    public static IReadOnlyList<PatchGuideEntry> Entries { get; } = LegacyEntries.Select(entry => entry.Id switch
    {
        "desync" => entry with {
            BodyRu = DesyncHelpRu + "\n\nРежим доступен в релизе и в бете, независимо от вражды независимых. Начиная с беты 7 его можно использовать вместе с расширенными цветами. В старых закреплённых бетах это сочетание недоступно.",
            BodyEn = DesyncHelpEn + "\n\nAvailable in Release and Beta, independently of independent hostility. From Beta 7 onward it can be used with extended colors. Older pinned Betas do not support this combination."
        },
        "colors" => entry with {
            BodyRu = $"В палитре {PlayerColorCount} цветов и вариант «Случайно». Оттенки сгруппированы по обычной, светлой и тёмной палитре; названия окрашены в соответствующие цвета. Свободные слоты и «Случайно» отмечены серым. Затенение значков рот смягчено с сохранением объёма.\n\nХост может менять цвета всех участников, клиент только свой. Случайные цвета распределяются перед матчем без повторений. Выбор сохраняется при возврате в лобби и повторном подключении. Если прежний цвет вернувшегося игрока уже занят, ему назначается «Случайно», а цвет другого участника сохраняется.\n\nПри выборе сохранения список игроков показывает цвета королевств из сейва. Изменять их нельзя; при перестановке игроков цвет остаётся у королевства. При переходе к новой игре выбор снова доступен.\n\nЦвета включают вражду независимых. Начиная с беты 7 можно выбрать как официальную обработку рассинхрона, так и пропуск. Всем участникам сетевой игры нужна одинаковая бета и совместимые настройки.",
            BodyEn = $"The palette has {PlayerColorCount} colors plus Random, grouped into regular, light and dark shades. Labels match their colors. Empty slots and Random are gray. Company-badge shading is softened while retaining depth.\n\nHosts may change all player colors, clients only their own. Random colors are assigned without duplicates before the match. Choices survive lobby returns and reconnects. If a returning player's former color is occupied, that player becomes Random and the incumbent keeps their color.\n\nSaved-game lobbies show saved kingdom colors read-only. Moving players between slots keeps colors attached to kingdoms. Color selection is available again when switching to a new game.\n\nColors enable independent hostility. From Beta 7 onward either official desync handling or bypass may be selected. All multiplayer peers need the same Beta and compatible settings."
        },
        _ => entry
    }).Concat(new PatchGuideEntry[] {
        new("random-map", "beta", "Случайный тип карты", "Random map type",
            "Пятый вариант «Случайно» выбирает один из четырёх типов карт: обычный, пустынный, зимний или добавленный Arcane Wars. Для него используется отдельный общий набор настроек размера, числа игроков, времени суток, ресурсов и логов.\n\nЭти настройки сохраняются после перезапуска. Особенности местности выбранного типа, например снег и лёд, используют стандартные значения. Собственные настройки четырёх обычных типов карт сохраняются отдельно. В сетевой игре тип карты выбирается согласованно у всех участников.",
            "A fifth Random option selects one of the four map types: regular, desert, winter or the Arcane Wars type. It has a separate common set of size, player count, time-of-day, resource and lair settings.\n\nThese settings persist after restarting. Type-specific terrain, such as snow and ice, uses its default values. The four regular map types retain their separate settings. Multiplayer peers select the same map type."),
        new("random-time", "beta", "Случайное время суток", "Random time of day",
            "В настройках случайной карты добавлено «Случайно» для времени суток. Игра выбирает один из вариантов освещения Arcane Wars при создании карты. Сам выбор «Случайно» сохраняется вместе с остальными настройками карты, в том числе после перезапуска игры.\n\nРаботает как с конкретным типом карты, так и со случайным. Вариант добавлен через игровые файлы.",
            "Random is added to the time-of-day setting for generated maps. The game selects one of the Arcane Wars lighting options during map creation. The Random preference persists with the other map settings, including after restarting the game.\n\nWorks with a specific map type or Random. This option is implemented through game data files."),
        new("terrain-startup", "beta", "Исправление стартового рассинхрона", "Startup desync fix",
            "Исправлена инициализация параметра генерации рельефа, который мог приводить к разной карте у участников после повторных матчей или аварийного завершения игры. Исправление применяется автоматически при запуске через лаунчер, независимо от выбора цветов и пропуска рассинхрона.\n\nОно исправляет найденную причину, но не отключает проверку синхронизации и не гарантирует отсутствие любых других рассинхронов. Дополнительное служебное окно перед запуском не появляется.",
            "Fixes initialization of a terrain-generation parameter that could produce different maps after repeated matches or an abnormal game exit. Applied automatically when starting through the launcher, regardless of color or desync-bypass settings.\n\nIt addresses the identified cause, does not disable synchronization checks, and cannot guarantee that all other desync causes are absent. No additional helper window appears before launch.")
        ,new("badge-lighting", "always", "Цвет и затенение значков рот", "Company badge colors and shading",
            "Все семь типов значков используют исправленное освещение цветного фона. Цвет меньше искажается дополнительным освещением, при этом мягкое затенение сохраняет объём. Золотая рамка и обозначение типа роты не меняются.\n\nМодели и текстуры входят в обязательную часть патча, в том числе при выключенных расширенных цветах. Они устанавливаются одинаково у всех игроков.",
            "All seven badge types use corrected lighting for the player-color background. Extra lighting no longer distorts the tint as much, while soft shading preserves depth. The gold frame and company-type symbol are unchanged.\n\nModels and textures are part of the required patch, including when extended colors are disabled. All players receive the same assets.")
    }).Select(Promote).ToArray();

    private static PatchGuideEntry Promote(PatchGuideEntry entry)
    {
        entry = entry with { Category = entry.Category == "beta" ? (entry.Id == "colors" ? "optional" : "always") : entry.Category };
        return entry.Id switch
        {
            "base" => entry with {
                BodyRu = "Лаунчер устанавливает Arcane Wars как основу и применяет Paw's Patch. Релиз 0.2.0 включает возможности прежней беты: случайные карты и время суток, исправление стартового рассинхрона, сетевые цвета и общие исправления интерфейса.\n\nВсе переключатели компонентов независимы. Для сетевой игры участникам нужны одинаковые версии и совместимые настройки. История отдельных обновлений доступна справа.",
                BodyEn = "The launcher installs Arcane Wars as the base mod and applies Paw's Patch. Release 0.2.0 includes the former Beta features: random maps and time of day, the startup desync fix, multiplayer colors and shared interface fixes.\n\nAll component switches are independent. Multiplayer participants need matching versions and compatible settings. Individual updates are listed in the changelog."
            },
            "desync" => entry with {
                BodyRu = DesyncHelpRu + "\n\nВ текущем релизе сочетается с любыми другими настройками, включая расширенные цвета и выключенную вражду независимых. Ограничения сохраняются только для старых закреплённых выпусков без нужных файлов запуска.",
                BodyEn = DesyncHelpEn + "\n\nThe current release supports every other setting, including extended colors with independent hostility disabled. Compatibility restrictions apply only to older pinned releases without the required launch files."
            },
            "colors" => entry with {
                BodyRu = entry.BodyRu.Replace("Цвета включают вражду независимых. Начиная с беты 7 можно выбрать как официальную обработку рассинхрона, так и пропуск. Всем участникам сетевой игры нужна одинаковая бета и совместимые настройки.", "Настройка доступна в релизе и не включает другие компоненты. Вражду независимых и обработку рассинхрона можно выбирать отдельно. Всем участникам сетевой игры нужны одинаковые версии патча и совместимые настройки."),
                BodyEn = entry.BodyEn.Replace("Colors enable independent hostility. From Beta 7 onward either official desync handling or bypass may be selected. All multiplayer peers need the same Beta and compatible settings.", "Available in Release without enabling other components. Independent hostility and desync handling are chosen separately. All multiplayer peers need matching patch versions and compatible settings.")
            },
            "common-ui" => entry with {
                BodyRu = entry.BodyRu.Replace("в текущую бету", "в текущий релиз"),
                BodyEn = entry.BodyEn.Replace("current Beta", "current Release")
            },
            _ => entry
        };
    }

    public static PatchGuideDocument Current() => new() { Version = "0.2.0", Entries = Entries.ToList() };

    public static PatchGuideDocument Resolve(ChannelManifest? channel)
    {
        if (IsValid(channel?.PatchGuide)) return channel!.PatchGuide!;
        return channel is null ? Current() : new() { Version = "", Entries = LegacyEntries.ToList() };
    }

    public static bool IsValid(PatchGuideDocument? guide)
        => guide is { SchemaVersion: 1, Version.Length: > 0 and <= 80, Entries.Count: > 0 and <= 100 }
        && guide.Entries.All(e => e is not null && e.Id is { Length: > 0 and <= 64 }
            && e.Id.All(c => c is >= 'a' and <= 'z' or >= '0' and <= '9' or '-')
            && e.Category is "always" or "optional" or "beta"
            && new[] { e.TitleRu, e.TitleEn }.All(t => !string.IsNullOrWhiteSpace(t) && t.Length <= 160)
            && new[] { e.BodyRu, e.BodyEn }.All(t => !string.IsNullOrWhiteSpace(t) && t.Length <= 12000))
        && guide.Entries.Select(e => e.Id).Distinct(StringComparer.Ordinal).Count() == guide.Entries.Count;
}
