# Paw's Patch 0.3.0-beta.5 — Arcane Wars

## Русский

- Добавлена защита от некорректных команд отрисовки, которые могли вызывать растянутые графические эффекты и вылеты во время матча. Защита пропускает команды, требующие больше индексов, чем находится в графическом буфере.
- Исправлена анимация смерти рейнджера: убрана дорожка свечения лука, обращавшаяся к уже уничтоженному материалу. Движения и события анимации сохранены.
- Исправления встроены в Paw's Patch в бета-канале Arcane Wars и работают при любых сочетаниях остальных компонентов. Баланс, автопостройка, сетевой протокол и формат сохранений не изменены.

Это бета-проверка защиты: она помогла завершить ранее падавшую партию, но не гарантирует устранение всех причин вылетов. Она рассчитана на штатный Direct3D 9; совместная работа со сторонними графическими обёртками, например DXVK, не поддерживается. Ранее существовавший d3d9.dll сохраняется установщиком и восстанавливается при отключении патча. При неподдерживаемой системной реализации проверка отрисовки не подключается. Состояние защиты записывается в paws_graphics_guard.log в папке игры.

Сохранения совместимы.

## English

- Added a guard against invalid indexed draw calls that could cause stretched visual effects and crashes during matches. Calls requiring more indices than the bound graphics buffer contains are skipped.
- Fixed the Ranger death animation by removing the bow emissive-color track that could access a destroyed material. Movement tracks and animation events are preserved.
- Both fixes are built into Paw's Patch in Arcane Wars Beta with every combination of the other components. Balance, city automation, network protocol and save format are unchanged.

This is a beta workaround: it helped complete a previously crashing match, but does not guarantee that every crash cause is fixed. It targets stock Direct3D 9; third-party graphics wrappers such as DXVK are not supported alongside it. The installer backs up a pre-existing d3d9.dll and restores it when the patch is disabled. The draw guard stays inactive on unsupported system implementations. Its status is recorded in paws_graphics_guard.log in the game folder.

Existing saves are compatible.
