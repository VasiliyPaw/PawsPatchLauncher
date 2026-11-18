from context import *
from publish import unchanged
def main():
 for name in['readback.json','public-client-check/result.json']:assert read(O/name)['passed']
 assert read(O/'source-ci.json')['conclusion']=='success'and read(O/'catalog-ci.json')['conclusion']=='success';unchanged();urls={g:read(O/g/'public-assets.json')['url']for g in['arcane','pure']}
 complete=dict(passed=True,versions=dict(arcane=ARC,pure=PURE),urls=urls,publication=read(O/'publication.json'),sourceCi=read(O/'source-ci.json'),catalogCi=read(O/'catalog-ci.json'),publicClient=read(O/'public-client-check/result.json'),verification=read(O/'verification.json'),publicAssets={g:read(O/g/'public-assets.json')for g in['arcane','pure']},sharedCheckoutPreserved=True);write(O/'COMPLETE.json',complete)
 (O/'FINAL-RU.md').write_text(f'''# Компактный HD-интерфейс и единый пакет земли опубликованы

Arcane Wars {ARC}: {urls['arcane']}

Vanilla / Immortals {PURE}: {urls['pure']}

Иконки ограничены 512 пикселями по большей стороне с сохранением пропорций. Половины расовых рамок — 2048×1024, центр — 512×1024. Все исходные HD-мастера сохранены. Экспорт сверяется пиксель в пиксель с соответствующим уменьшением Lanczos. Повторы хранятся один раз в штатных RWD: 708 путей изображений, семь архивов, 1026 проверенных записей с учётом штатных расовых ресурсов. Шесть расовых архивов сохраняют все 53 исходные записи каждый. Временные QA DLL и помощник в релиз не входят.

Пакет интерфейса Arcane: 124 032 632 байта вместо 1 454 124 155. Pure: 118 125 767 вместо 1 448 217 357. Разница с оценкой 115/109 МБ обусловлена сохранением штатных расовых ресурсов внутри новых архивов.

Четыре пакета местности объединены в один ZIP 900 055 601 байт. Внутри четыре прежних RWD: их имена, размеры, хеши, stamps и все пиксели полностью совпадают. Новое имя модуля arcane-biome-textures заменяет четыре старых зависимости. Уже установленным копиям при переходе потребуется одна загрузка объединённого пакета. Последующие изменения UI не требуют менять его. Основная первая загрузка Arcane — 1 190 355 480 байт, без дополнительных языков/озвучек/опций.

Публичный установщик лаунчера 1.0.19 прошёл по шесть шагов на каждой из трёх игр: обновление с beta.4/beta.8, четыре варианта помощников, отключение и повторное применение. Отключение восстанавливает штатные расовые RWD. Все 708 изображений извлечены и сверены после установки. Каталог проверен на 28 944 сочетаниях и 513 637 проверках, все 12 помощников. Производственный RwdTool.dll прочитал все 1026 записей новых архивов.

В отдельной Arcane-копии загружено прежнее сохранение при 2560×1440; фактические текстуры Direct3D: иконки 512×512, половины рамок 2048×1024, центр 512×1024. Сохранён настоящий снимок игры. Тестовая копия закрыта, QA файлы и профиль восстановлены. Остальные расы проверены по содержимому архивов; новый сетевой матч не заявляется. Все native-входы и игровые TGI совпадают с предыдущими бетами; в помощниках изменились только константы версий.

Десять публичных файлов целиком скачаны и сверены. Проверки GitHub исходников и каталога успешны, публичный лаунчер предлагает новые версии всем трём играм. Стабильные каналы, версия лаунчера, установленная пользовательская игра, HEAD и индекс общей рабочей копии сохранены.

В лаунчере: Beta → нужная игра → Применить.
''',encoding='utf-8')
 write(WS/'outputs/ui-size-estimate-20261117/implementation.json',dict(completed=True,actualUiBytes=read(O/'verification.json')['uiPackageBytes'],firstArcaneCoreBytes=1190355480,terrainPackageBytes=900055601,urls=urls,report=str(O/'FINAL-RU.md')));print('COMPACT_BETAS_COMPLETE',json.dumps(urls),flush=True)
if __name__=='__main__':main()
