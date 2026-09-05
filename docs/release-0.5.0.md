## Reliability update / Надёжность

- Automatic launcher rollback if the new version fails to open its window.
- Restore the previous patch installation, including replaced and deleted files.
- Import a friend's configuration code.
- Multiplayer readiness page with actual file hashes and peer fingerprint comparison.
- Restore the last settings that successfully opened a game window.
- Crash/unclean-exit notifications with diagnostic archive creation.
- Quick critical-file checks before launching the game.
- Download progress, speed, remaining time, pause and resume.
- Unread changelog markers for Patch and Launcher.
- Select Latest or a previous signed Beta release.

Русский и английский интерфейсы сохранены. Новые функции находятся в «Настройках», «Компонентах» и на отдельной странице «Мультиплеер».

Игра и модули патча в этом выпуске не изменены. Крупные архивы заново скачивать не нужно, если они уже есть в проверенном кэше.

### Important

Automatic launcher rollback protects updates **initiated by 0.5.0 or later**. The update from an older launcher still uses its previous updater. Manual patch rollback becomes available once an installation snapshot has been recorded. A successful game-window startup or matching file fingerprint does not guarantee an absence of simulation desyncs.

Validated: 122 automated assertions; real updater success/crash/timeout scenarios; real Beta → Stable → rollback with file-hash verification; packaged and standalone EXE startup. A real multiplayer match still needs manual testing.
