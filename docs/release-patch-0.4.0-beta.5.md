# Paw’s Patch 0.4.0-beta.5 — Arcane Wars

При включённом пропуске рассинхрона теперь сохраняется подробный журнал первой
ошибки в матче. Повторные ошибки не создают дубли; в новом матче или после загрузки
сохранения запись снова доступна. Лаунчер автоматически включает эти журналы в
архив диагностики.

Это улучшение диагностики. Продолжение игры не устраняет уже возникший рассинхрон.
Перед новым сетевым матчем обновиться нужно всем участникам.

---

Continuing after a desync now preserves a detailed log of the first error in a
match. Repeated errors do not create duplicate logs; a new match or loaded save
enables another capture. The launcher includes these logs in diagnostic archives
automatically.

This improves diagnostics; continuing play does not repair an existing desync.
All participants should update before starting a new multiplayer match.
