# Paw's Patch Launcher 0.5.9

Локальная общая сборка. Публикация отложена до проверки и подтверждения пользователя.

- В подсказке основного компонента указан автор Arcane Wars, Darquan Mortis, и добавлена ссылка на Discord-сервер распространения мода. По нажатию на «?» ссылка открывается в браузере.
- «Игнорирование рассинхронов» стало переключателем сразу под основным компонентом. Подсказка предупреждает, что игнорируются и серьёзные расхождения, но их причина не исправляется.
- Частота блуждающих рот перенесена в конец компонентов. Добавлен режим ×2: интервал на 25% короче, шанс события на 50% выше. Подготовлены два совместных игровых пакета, с новыми ротами и без них.
- В блок папки игры добавлена кнопка открытия сейвов.
- Кнопка «Применить настройки» появляется при неприменённых изменениях и остаётся доступной на всех вкладках. После применения отдельной кнопкой или через запуск игры она плавно скрывается. Возврат к уже применённым значениям тоже скрывает кнопку. На узком окне она размещается над запуском.
- Смена Релиза и Беты не требует повторного скачивания уже сохранённых пакетов. Совпадающие установленные файлы не считаются обновлением даже при отсутствии копии в кэше. Применение другого сохранённого набора отделено от скачивания нового выпуска.
- При попытке применения, обновления или повторного запуска запущенная Kohan II вызывает понятное уведомление, а не окно ошибки с диагностикой. Перед записью файлов выполняется повторная проверка.
- Код конфигурации и подробное сравнение поддерживают SP2. Старый закреплённый выпуск без пакетов ×2 не подменяет настройку молча.
- Исправлена ложная отмена самообновления при слишком длинном пути к подтверждению запуска. Уже установленные старые лаунчеры с таким путём могут потребовать однократной ручной замены EXE.

- Проверка обновлений лаунчера больше не зависит от выбранного канала патча или закреплённой версии игры. Лаунчер проверяет подписанные источники Релиза и Беты и выбирает наиболее новую доступную версию.
- Найденное обновление не пропадает при переключении каналов, старом ответе из кеша или временной ошибке источника. Проверка одного канала может завершиться ошибкой, не скрывая обновление из другого.
- При получении описаний обновлений запрашивается повторная проверка кеша. Подписи, размеры и контрольные суммы остаются обязательными.
- Сохранены автоматическое обновление при запуске и отдельная кнопка обновления. Проверка версий лаунчера не устанавливает игровые пакеты и не меняет настройки патча.

## English

- Core component help credits Arcane Wars author Darquan Mortis and links to the mod's Discord server. Open the question-mark help to follow the link in a browser.
- Desync bypass is now an Ignore desyncs toggle below the core component, with a warning about serious divergent states.
- Roaming frequency is last in Components; ×2 has two combined data profiles, with additional companies on/off.
- Adds Open saves folder and an animated Apply settings action. Pending changes keep Apply visible across all tabs. Applying directly, through Launch, or reverting to applied choices hides it.
- Cached channel switches and identical installed files no longer masquerade as a new download. Running-game attempts show a simple notice; a second check protects reconciliation.
- Friend codes and detailed comparison support SP2. Older pinned releases lacking ×2 explain the unavailable option instead of silently changing it.

- Launcher updates are checked independently of the selected patch channel or pinned game release. Signed Release and Beta sources are checked for the newest available launcher.
- A discovered update stays available during channel switches, stale cache responses and temporary source failures. One broken channel does not hide an update from another.
- Manifest requests ask caches to revalidate. Signatures, sizes and SHA-256 checks remain required.
- Startup self-update and the manual update button remain. The launcher-only check does not install game packages or alter patch settings.
