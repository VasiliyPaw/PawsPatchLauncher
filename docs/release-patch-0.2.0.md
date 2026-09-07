# Paw's Patch 0.2.0, Релиз

Все нововведения беты 7 переведены в Релиз:

- Случайный тип карты и случайное время суток. Общие настройки сохраняются после перезапуска; особая местность зависит от выбранного типа карты.
- Исправление выявленной причины стартового рассинхрона после повторных матчей.
- 49 цветов игроков. Хост меняет цвет любого игрока, клиент только свой. Цвета сохраняются после возврата в лобби и повторного подключения; если прежний цвет занят, возвращающийся игрок получает «Случайно».
- В лобби сохранения отображаются цвета королевств из сейва без возможности изменить их.
- Подписи версий игры и модов, корректное отображение нуля вместо -0.
- Запуск без лишнего служебного окна.

Дополнительно в этом выпуске:

- Все переключатели компонентов независимы. Расширенные цвета работают и с выключенной враждой независимых, и с любым режимом контроля рассинхрона.
- В обязательный пакет включены все 7 моделей значков рот и соответствующие текстуры мягкого затенения. Исправление работает даже при выключенных расширенных цветах. В прежней публичной бете моделей не хватало, из-за чего локальная тестовая установка и установка друга могли выглядеть по-разному.
- Релиз и Бета сейчас содержат одинаковые игровые пакеты. Отдельных нововведений только для беты пока нет.

Нужен лаунчер 0.5.8. Обновите лаунчер и патч у всех участников матча. «Независимые переключатели» не означает, что игроки могут использовать разные игровые настройки в одном матче.

Пропуск рассинхрона не исправляет расхождения и пропускает даже серьёзные. Этот выпуск не заявляет исправление всех возможных вылетов игры. Два недавних вылета в обработке анимации остаются на диагностике; их связь с патчем пока не установлена. Самые большие карты по-прежнему повышают риск вылета из-за пределов движка.

## English

All accepted Beta 7 features graduate to Release: persistent random map type/time of day, the identified repeated-match startup desync fix, synchronized 49-color lobbies with reconnect/conflict handling and saved-game colors, common version/zero-display fixes and quiet startup.

All optional switches are independent, including colors with independent hostility disabled and with either desync mode. The required common package now includes all seven company-badge NIF models and matching soft-shading textures, even with extended colors disabled. Public Beta 7 omitted the models present in local testing.

Release and Beta currently share gameplay packages. Update launcher 0.5.8 and the patch on every multiplayer PC; gameplay settings must remain compatible. Desync bypass does not repair divergent state. This is not a universal crash fix: two recent animation-path crashes remain under investigation, and the largest maps still stress engine limits.
