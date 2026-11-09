# Paw’s Patch 0.5.0 beta 1 — Vanilla / Immortals

Добавлены возможности создания карт и интерфейса для Vanilla и Immortals:

- **Динамические сутки.** В параметре «Время суток» выберите «Динамически». Полный цикл занимает 10 игровых минут и начинается со случайной фазы. Освещение и часы следуют игровому времени: учитывают паузу, скорость игры и замедления симуляции. Начальная фаза сохраняется в сейве.
- **Смешанные биомы.** Новый тип карты объединяет крупные области лета, зимы и пустыни с родными объектами выбранного режима. «Все» использует три биома; «Случайно» с равной вероятностью выбирает один, два или три. У логов и технологических построек общие настройки количества.
- **Карты до 2048×2048.** Расширена вместимость объектов и исправлены связанные ограничения сохранения и отображения миникарты. Лимиты рот и очков королевства сохраняются.
- **Часы суток сверху по центру** в формате ЧЧ:ММ. При статическом освещении время фиксировано. Устранено повторное создание часов между партиями.
- **Масштаб миникарты от ×1 до ×4 с шагом 0,1.** Наведите курсор на миникарту и вращайте колёсико. Увеличенная карта следует за камерой; движение камеры сохраняет изображение миникарты.
- **Центрирование окон.** Дополнены исправления окна выхода, игрового меню, сохранения и загрузки, в том числе для широкого экрана.

Автоматическое восстановление сетевого матча выключено. Сетевые автосохранения и локальные копии сохранений клиентов сохранены. Продолжение партии выполняется обычной загрузкой сейва в лобби.

Это бета для поддерживаемого EXE Kohan II 1.3.72. Новые возможности требуют включённого Paw’s Patch; режим «Только игровые файлы» их не устанавливает. Для сетевой игры участникам нужна одинаковая версия и совместимые компоненты. Сохранения новых партий с расширенным реестром объектов требуют версии патча, которая его поддерживает.

Авторазвитие городов, дополнительные строительные места, фундаменты и дробные очки королевства в этот перенос не входят.

---

# Paw’s Patch 0.5.0 beta 1 — Vanilla / Immortals

New map-generation and interface features for Vanilla and Immortals:

- **Dynamic day and night.** Choose Dynamic under Time of day. A full cycle takes 10 game minutes and starts at a random phase. Lighting and the clock follow simulation time, including pause, game speed and slowdowns. The initial phase is saved with the match.
- **Mixed biomes.** A new map type combines broad temperate, arctic and desert regions with the native objects of the selected mode. All uses three biomes; Random selects one, two or three with equal probability. Lairs and technology sites share density controls.
- **Maps up to 2048×2048.** Expanded object capacity and related save/minimap fixes. Company and kingdom-point limits retain their native values.
- **A day clock at the top center**, in HH:MM format. Static lighting displays a fixed time. The clock is reused across match/menu transitions.
- **Minimap zoom from ×1 to ×4 in 0.1 steps.** Hover over the minimap and turn the mouse wheel. The enlarged minimap follows the camera and remains visible while it moves.
- **Centered dialogs.** Additional fixes for surrender, game menu, save and load windows, including widescreen layouts.

Automatic network-match recovery is disabled. Multiplayer autosaves and local client save copies remain available. Resume a match by loading its save through the normal lobby flow.

This beta requires the supported Kohan II 1.3.72 executable and enabled Paw’s Patch. File-only mode does not install these features. Network participants need the same version and compatible components. New matches using the expanded object registry require a patch version that supports that save format.

Automatic city development, extra building slots, foundations and fractional kingdom points are excluded from this port.
