# Paw's Patch 0.3.0-beta.2

## Русский

Обновление игрового патча только для канала «Бета». Релиз остаётся 0.2.0, лаунчер — 0.6.4.

- Расширенное автоулучшение городов встроено в бету. В F1 под галочками находятся четыре порога **дохода** ресурсов с игровыми иконками. Резерв золота задаётся отдельно.
- Enter применяет значение, Esc и нажатие вне поля отменяют незавершённый ввод, не открывая чат.
- Автоулучшение не снижает доход ресурса ниже заданного порога и не усугубляет уже существующий дефицит. Если безопасно устранить нехватку сейчас нельзя, разрешён рост золота в других городах.
- Города строятся параллельно; учитываются начатые и ручные постройки. Осада одного города не блокирует остальные. Рынки выбирают выгодную золотую ветку при достаточном доходе ресурсов.
- Пороги и учёт стройки работают с обоими наборами ресурсов: с Powers/Shards и без них.
- Отдельное окно содержит правила строительства, выбор веток улучшений и исключения городов. Пороги перенесены из него в F1.
- Ускорена штатная передача сохранений при выборе сейва хостом в сетевом лобби. Используется проверенный вариант R2: в тесте ПК → виртуалка файл 1,6 МБ передался примерно за 9 секунд. Это результат конкретного теста, не гарантированная скорость.
- Новые функции доступны при всех сочетаниях компонентов, без отдельных переключателей в лаунчере. Галочка автоулучшения в самой игре по-прежнему позволяет остановить автоматические приказы.

Добавлять игроков в друзья или вручную принимать сейв в лаунчере не нужно. Используется штатная система игры; формат сейва и сетевых блоков не меняется. Обновите бету у всех участников и используйте совместимые настройки.

Новая партия и загрузка сохранения начинают с включённым автоулучшением и резервом 2000. Общие правила и пороги ресурсов сохраняются на компьютере, исключения городов сбрасываются. Справка «О патче» обновлена одинаково для обоих каналов; игровые пакеты Релиза не меняются.

## English

Beta gameplay update only. Release remains 0.2.0 and the launcher remains 0.6.4.

- Advanced city upgrades are built into Beta. F1 has four resource **income** targets with native icons beneath the checkboxes, plus a separate gold reserve.
- Enter applies a value; Esc or clicking outside cancels unfinished editing without opening chat.
- Automation never reduces resource income below its target or worsens an existing deficit. When no safe remedy is available, other cities may still grow gold income.
- Cities build in parallel, accounting for active and manual construction. A siege only excludes its own city. Markets use profitable gold conversion branches when resource income permits.
- Resource targets and construction accounting handle both resource layouts, with Powers/Shards enabled or disabled.
- The separate settings window contains construction rules, upgrade paths and city exceptions. Resource targets have moved to F1.
- Faster native lobby save transfer uses the tested R2 tuning. A PC-to-VM test transferred a 1.6 MB save in about 9 seconds; actual speed depends on the network.
- Both features are built in with every component combination, without separate launcher toggles. The in-game automation checkbox still stops automatic orders.

No friendship or manual launcher acceptance is required. Native save format and network block format are unchanged. Update all multiplayer participants and use compatible gameplay settings.

New matches and loaded saves start with automation on and a 2000 reserve. General rules and resource targets persist locally; city exceptions reset. About documentation is shared between both channels; Release gameplay packages are unchanged.
