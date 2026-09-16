# Paw's Patch 0.3.0-beta.8 — Arcane Wars

- Компактный выбор цвета по стрелке рядом с кружком: игрок занимает одну строку. Выбранный цвет привязан к участнику, а не к месту в списке. Светло-красный убран, осталось 48 цветов.
- В управлении поселениями убрана кнопка «Правила», настройка ополчения перенесена выше автоулучшения и порогов ресурсов.
- Приоритет авторазвития: последнее доступное улучшение центра города → цели по ресурсам → доход золота → случайные допустимые постройки и улучшения. Если на приоритетное действие не хватает золота, средства копятся на него, а не тратятся на дешёвые действия меньшего приоритета.
- При достижении целей ресурсов учитывается вся ручная и автоматическая очередь, включая доход будущих зданий, центров и рудников. На этапе ресурсов прибыльный рынок может получить приоритет, если он даст больший прирост золота после расходов на дефицит. При равном результате выбираются ресурсы. Рынки допускаются даже при увеличении дефицита, если итоговый доход золота растёт.
- На всех этапах рынки улучшаются только по ветке с наибольшим положительным приростом золота. Если такой ветки нет, рынок не улучшается. Запас золота сохраняется; строительство и улучшение в осаждённых городах запрещены.
- Настройки авторазвития сохраняются локально отдельно для партии и её сейвов. Новая партия начинается со стандартных значений: автоулучшение включено, запас золота 2000, цели ресурсов 0. Передача настроек других игроков внутри сетевого сейва пока не добавлена.
- Настройка ополчения применяется к стартовым, новым и захваченным городам и новым зданиям с ополчением. Временно недоступный приказ повторно проверяется после снятия блокировки; сама осада не мешает штатному переключению ополчения. Состояние готовых зданий при загрузке сейва и последующие ручные изменения сохраняются.
- При загрузке владельцы объектов остаются такими, как записаны в сохранении: старые независимые лагеря больше не перераспределяются в королевства игроков. Правила новых партий сохранены. Уже записанная в сейв ошибочная принадлежность не меняется задним числом.
- Версии файлов патча и запуска проверяются согласованно; обновлены описания и подсказки на поддерживаемых языках.

---

# English

- Compact color selection via the arrow beside the color swatch keeps each player on one row. Colors follow participants rather than lobby slots. Light red was removed, leaving 48 colors.
- Removed the Rules button from settlement management and moved the militia option above auto-development and resource targets.
- Development priority: final available city-center upgrade → resource targets → gold income → random eligible construction or upgrades. If a priority action is legal but unaffordable, the assistant saves for it instead of spending on cheaper, lower-priority actions.
- All manual and automatic queued work is included in resource projections, including future buildings, centers and mine upgrades. During the resource stage, a profitable market can take priority when it offers a greater net gold increase after shortage costs. Ties favor resources. Markets may deepen deficits when net gold income improves.
- At every stage, markets use only the upgrade branch with the greatest positive gold increase; without one, they are never upgraded. The gold reserve remains protected. Besieged cities remain excluded from construction and upgrades.
- Auto-development preferences are stored locally per match and its saves. New matches use the defaults: auto-upgrade enabled, 2000 gold reserve and zero resource targets. Other players' preferences are not yet carried inside transferred multiplayer saves.
- The militia option applies to starting, new and captured cities and newly completed militia buildings. Temporarily blocked orders remain pending; siege alone does not prevent native militia toggling. Loading preserves completed buildings' militia state, and later manual changes are respected.
- Loading retains exact saved object owners: old independent camps are no longer reassigned to player kingdoms. Fresh-match rules remain unchanged. Ownership already saved incorrectly is not silently reversed.
- Patch-file and startup identities are checked consistently; descriptions and tooltips were updated in the supported languages.
