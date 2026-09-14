# Paw's Patch 0.3.0-beta.3 — Arcane Wars

## Русский

- Автоматизация учитывает полную принятую очередь ручных и автоматических построек: активные и ожидающие заказы. Будущий положительный доход уменьшает оставшуюся потребность в ресурсе, а отрицательные эффекты учитываются заранее при защите дохода. Незавершённая положительная прибавка не считается уже полученным доходом. Оплата проверяется по текущим ресурсам. Пока отправленные игроком приказы на строительство или улучшение ещё не обработаны игрой, автоматика ждёт; после обработки пересчитывает доступное золото и сохраняемый резерв.
- Рынки всех шести рас доступны, когда до заказа доход каждого из четырёх ресурсов строго выше его порога с учётом ожидаемых отрицательных эффектов. Заказ рынка может опустить доход ниже порога; затем автоматика возвращается к восполнению ресурсов. Для остальных построек защита порогов сохраняется.
- Когда нет доступной полезной постройки для ресурсов, золота или подготовки золотой ветки и доходы позволяют, автоматика продолжает случайно выбирать доступные варианты. Выбор повторяется постоянно после завершения экономических приоритетов; отдельная настройка «Другие здания» больше не требуется.
- Независимые рудники всех рас участвуют в улучшениях по ресурсам, золоту и случайному выбору. Разные рудники получают отдельные приказы; занятый рудник не получает повторный приказ на тот же объект. Обычная очередь игры и её проверки законности сохраняются.
- Открытое ополчение для новых собственных городов включено по умолчанию. Настройка доступна в F1 и сохраняется на компьютере. Она применяется к новым построенным и захваченным городам. Уже существующие на момент начала партии или загрузки города не изменяются.
- Эти изменения и прежняя передача сохранений R2 встроены во все восемь вариантов Beta при любых сочетаниях цветов, вражды независимых и контроля рассинхрона. Общие городские правила сохраняются локально, исключения городов сбрасываются при новой партии или загрузке.

## English

- Automation accounts for the full accepted manual and automatic construction queue, including active and waiting orders. Future positive income reduces outstanding resource goals, while adverse effects protect income in advance. An unfinished positive gain is not treated as income already received. Payment uses current resources. Automation waits while the player's sent building or upgrade orders await game processing, then recomputes available gold and the protected reserve.
- Markets of all six races are available when each of the four resource incomes is strictly above its target before the order, accounting for pending adverse effects. A market order may cross below a target; resource recovery then takes priority. Other buildings retain target protection.
- When no useful resource, gold or gold-branch preparation choice is available and income permits, automation continues to select random eligible options. This fallback remains active after economic priorities are exhausted; it no longer requires a separate Other buildings setting.
- Independent mines of every race can receive resource, gold and random upgrades. Different mines receive separate orders; a busy mine does not receive a duplicate order for the same object. The normal game queue and its legality checks remain in control.
- Open militia for new owned cities is enabled by default. Its F1 setting persists on this PC and applies to newly built and captured cities. Cities already present at match start or save load are unchanged.
- These changes and the existing R2 save transfer are built into all eight Beta variants, with every combination of colors, independent hostility and desync handling. General city rules persist locally; city exceptions reset on new matches or loads.
