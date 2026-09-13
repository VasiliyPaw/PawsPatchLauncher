# Paw's Launcher 0.7.3

При нажатии «Обновить лаунчер» нижняя полоса загрузки больше не появляется на мгновение перед открытием отдельного окна обновления.

В окне загрузки обновления появилась тёмная кнопка «Отменить»: она прерывает скачивание и открывает установленную версию. Перед заменой программы отмена скрывается. При обрыве соединения текущая версия сохраняется; зависшая загрузка прекращается после 30 секунд без новых данных. Скачанная часть используется при следующей попытке, если сервер поддерживает продолжение. Обновление устанавливается только после полной загрузки и проверки файла.

Исправлен сбой «Нет доступа к папке» при кратковременной блокировке файла состояния во время «Обновить и применить». Лаунчер повторяет сохранение в течение двух секунд. Если доступ остаётся закрыт, операция завершается ошибкой с откатом, а путь проблемного файла сохраняется в диагностике.

Убраны двойные сообщения об одной ошибке. Повторное одинаковое уведомление теперь продлевает время уже показанного сообщения.

Изменения окна обновления действуют начиная с установленной версии 0.7.3. Переход на неё из 0.7.2 выполняется прежним окном обновления.

---

# English

Clicking Update launcher no longer briefly displays the bottom download panel before the separate update window opens.

The update download window now has a dark Cancel button. It stops the download and opens the installed version. Cancellation is hidden before replacing the application. If the connection drops, the installed version is retained; a stalled download ends after 30 seconds without new data. Partial downloads are reused on the next attempt when the server supports resuming. Updates are installed only after the complete file has been downloaded and verified.

Fixed Folder access denied when the installation-state file is briefly locked during Update and apply. The launcher retries saving for up to two seconds. A persistent access failure still reports an error and rolls back the operation, with the affected file path included in diagnostics.

Removed duplicate reports of the same error. Repeating an identical notification now extends the existing notice instead of creating another copy.

The updated window is used by installed version 0.7.3 and later. Updating from 0.7.2 to this version still uses the previous update window.
