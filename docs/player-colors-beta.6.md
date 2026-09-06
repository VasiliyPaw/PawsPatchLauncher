# Player colors 0.1.0-beta.6 - r16

## Русский

- Исправлена причина рассинхрона при смене цвета в сетевом лобби: хост теперь записывает границы команды цвета в штатную контрольную сумму, как и клиент.
- Штатная проверка рассинхрона не отключена и не сбрасывается. RNG и игровая симуляция не изменены.
- Удалён тёмно-розовый; остальные 49 цветов, их порядок и затенение значков сохранены.
- Перед сетевой игрой обновить Beta на всех компьютерах. Смешанные старые и новые версии не поддерживаются.
- Только обновление модуля цветов. Stable, лаунчер 0.5.5 и остальные пакеты не изменены.

По запросу пользователя сборка опубликована в Beta для живого теста с виртуалкой. Проверки кода пройдены, но живой Steam-мультиплеер, сохранения и повторы для r16 ещё не проверены.

## English

- Fixed the lobby color-change desync cause: the host now feeds color-command boundaries into the native synchronizer, matching client processing.
- Native desync checks remain enabled and are not reset. No RNG or gameplay simulation changes.
- Removed dark pink; the remaining 49 colors, their order and badge shading are unchanged.
- All multiplayer peers must update Beta. Mixed old and new builds are unsupported.
- Color-module update only. Stable, launcher 0.5.5 and all other packages remain unchanged.

Published to Beta at the user's request for live VM testing. Code checks passed; live Steam multiplayer, save/load and replay validation for r16 remain pending.

## Validation

- Original r15 regression reproduced with different native host/client checksums.
- 98 host/client x86 synchronization cases, including different relocation bases, all colors, Random, invalid requests and legacy tags.
- 138,915 other native x86 assertions; helper payload and common-UI self-tests passed.
- Package: 10 files, no removals, exactly two changed files (EXE and palette INI) from beta.5.
- Archive SHA-256: `C45EF0EE397DEC4242CCCA7884E4579049997DBF3E835FD095F8FB0C8251ECEE` (69,009 bytes).
