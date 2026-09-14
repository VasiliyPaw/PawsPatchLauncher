# Paw's Launcher 0.8.0

- Архив диагностики собирает пять последних доступных комплектов журналов игры и пять дампов, а также отдельные дампы и отчёты Windows. Добавлен поиск в VirtualStore, сбор журнала графической защиты и отчёт о найденных файлах, недоступных папках и ошибках чтения. Если файлов меньше пяти, сохраняются все доступные. Сбор и упаковка выполняются в фоне.
- Добавлены чешский, немецкий и французский языки интерфейса. Выбор языка стал компактнее и получил значок перевода; названия языков интерфейса всегда написаны на своём языке. Названия языков текста и озвучки игры следуют языку лаунчера, а английский отмечен как оригинал.
- Свою карточку игрока можно открыть нажатием на аватар в чате, имя в профиле или свою строку в подробностях матча. Из карточки доступен просмотр своего аватара.
- Карточки участников матча имеют одинаковую высоту; игровой ник отображается рядом с именем. Таймер матча обновляется локально между ответами сервера; без свежих данных отсчёт останавливается через 40 секунд.
- Если применённые настройки и версия патча уже совпадают с конфигурацией друга, повторное копирование недоступно. При необходимости установки или обновления соответствующее действие остаётся доступным.

Некоторые описания модов и история обновлений в прежнем формате RU/EN показываются на английском при выборе новых языков интерфейса.

Для разбора вылета обновите лаунчер и создайте новый архив в «Настройки → Архив диагностики». Уже существующие журналы и дампы можно собрать без повторного запуска игры. Лаунчер не создаёт задним числом отсутствующие дампы и не включает их запись в Windows: архив помогает установить причину, но сам по себе не исправляет вылет. Изменения игрового патча Arcane Wars 0.3.0-beta.5 распространяются отдельно.

---

# English

- Diagnostic archives collect the five newest available game log sets and five game dumps, plus separate Windows dumps and reports. Collection now checks VirtualStore and includes the graphics-guard log and a report of found files, inaccessible folders and read failures. If fewer than five files exist, all available files are included. Collection and compression run in the background.
- Added Czech, German and French interface languages. The compact language selector has a translation icon, and interface language names always use their own language. Game text and speech language names follow the launcher language; English is marked as original.
- Open your own player card from your chat avatar, profile name or entry in match details, and preview your avatar from that card.
- Match participant cards have a consistent height, with the in-game nickname beside the profile name. Match time advances locally between server responses and stops after 40 seconds without fresh data.
- Copying a friend's configuration is disabled when the applied settings and patch version already match. Required installation or updates remain available.

Some mod descriptions and update history in the older RU/EN format use English for the new interface languages.

To investigate a crash, update the launcher and create a new archive under Settings → Diagnostic archive. Existing logs and dumps can be collected without starting the game again. The launcher cannot recreate missing dumps and does not enable Windows dump recording: the archive helps investigate crashes but is not a crash fix. Arcane Wars game patch 0.3.0-beta.5 is distributed separately.
