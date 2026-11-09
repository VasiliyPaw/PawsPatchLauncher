# Paw’s Patch 0.5.0 beta 2 — Vanilla / Immortals

- Исправлено распределение кэша между моделями, анимациями и текстурами.
- Добавлена подготовка ранее запрошенных моделей и анимаций при загрузке и на паузе.
- Добавлено удержание анимаций в кэше с проверкой доступной памяти.
- Добавлено переиспользование графических буферов и ускорен поиск групп при отрисовке объектов.

Динамические сутки, смешанные биомы, карты до 2048, часы, зум миникарты и исправления окон из первой беты сохранены. Автоматическое восстановление сетевого матча остаётся выключенным.

Перенесён действующий набор оптимизаций Arcane Wars. Эксперименты с предварительной загрузкой на GPU, повторным использованием подготовленного вида и кэшем состояний графики остаются выключенными. Отдельный прирост FPS для Vanilla и Immortals не заявляется.

---

# Paw’s Patch 0.5.0 beta 2 — Vanilla / Immortals

- Fixed cache allocation across models, animations and textures.
- Added preparation of previously requested models and animations during loading and pause.
- Added animation retention with available-memory checks.
- Added graphics-buffer reuse and faster group lookup while rendering objects.

Dynamic day and night, mixed biomes, maps up to 2048, the clock, minimap zoom and dialog fixes from beta 1 remain available. Automatic network-match recovery remains disabled.

This ports the current Arcane Wars optimization set. GPU preloading, prepared-view reuse and graphics-state cache experiments remain disabled. No separate FPS improvement is claimed for Vanilla or Immortals.
