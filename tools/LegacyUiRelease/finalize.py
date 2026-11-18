from context import *
from publish import unchanged
def main():
 for name in ['readback.json','public-client-check/result.json','public-launcher-result.json']:assert read(O/name)['passed']
 assert read(O/'source-ci.json')['conclusion']=='success'and read(O/'catalog-ci.json')['conclusion']=='success';assert read(O/'launcher-ci.json')['release']['conclusion']=='success';unchanged()
 urls={g:read(O/g/'public-assets.json')['url']for g in ['arcane','pure']};urls['launcher']=read(O/'public-launcher-result.json')['url']
 complete=dict(passed=True,versions=dict(arcane=ARC,pure=PURE,launcher='1.0.22'),urls=urls,publication=read(O/'publication.json'),sourceCi=read(O/'source-ci.json'),catalogCi=read(O/'catalog-ci.json'),launcherCi=read(O/'launcher-ci.json'),publicClient=read(O/'public-client-check/result.json'),verification=read(O/'verification.json'),publicAssets={g:read(O/g/'public-assets.json')for g in ['arcane','pure']},sharedCheckoutPreserved=True)
 write(O/'COMPLETE.json',complete)
 (O/'FINAL-RU.md').write_text(f'''# Прежние иконки и интерфейс возвращены

Arcane Wars {ARC}: {urls['arcane']}

Vanilla / Immortals {PURE}: {urls['pure']}

Лаунчер 1.0.22: {urls['launcher']}

Все 63 части рамок представляют собой точные вырезки из 21 оригинального атласа; 477 уменьшенных копий новых иконок удалены. Шесть расовых RWD восстановлены из проверенного оригинала. Удаляются 1132 зарезервированных пути прежних HD-файлов; архив HD больше не подключается. Пакеты интерфейса: 21 157 996 байт Arcane, 15 921 609 байт Pure. Исходные художественные материалы и исторические опубликованные выпуски сохранены.

Новый лаунчер после успешного обновления удаляет из подготовленного кэша и загрузок только четыре известных официальных HD-пакета. Проверяются хеши манифеста и ZIP, отсутствие ссылок и посторонних файлов. Пакеты установленных/закреплённых/неактивных версий сохраняются. Оригиналы и резервные снимки не удаляются. В тесте настоящих компактных ZIP освобождено 420 696 478 и 381 008 310 байт; после удаления кэша откат восстановил HD-файлы из снимка.

Объединённый пакет земли остаётся прежним: версия, SHA-256, размер и содержимое без изменений. Повторная загрузка его 900 МБ для уже подготовленной копии не нужна. Игровые исправления, геометрия интерфейса и игровые native-входы сохранены; в помощниках изменились только обозначения версий.

Проверены 18 сценариев установщика на трёх модах, ещё три перехода с первого полноразмерного HD-выпуска, 28 944 сочетания каталога и все 12 помощников. Общие тесты лаунчера: PASS 40019; отдельные проверки очистки: 128 утверждений и 16 проверок настоящих архивов/отката. Новые нативные игровые или сетевые сеансы не запускались. QA соблюдает требование тишины до запуска.

Девять публичных ZIP патчей и файлы выпуска лаунчера полностью скачаны и сверены. Подписанные каталоги прочитаны по неизменяемым и обычным адресам. Обновления доступны всем трём модам, проверки GitHub прошли. Игровые пакеты стабильного канала не изменены; лаунчер 1.0.22 обновлён во всех шести каталогах. Пользовательская установленная игра, HEAD и индекс общей рабочей копии не изменялись.

Для применения: обновить лаунчер, выбрать Beta нужного мода и нажать «Обновить и применить».
''',encoding='utf-8')
 print('LEGACY_UI_BETAS_COMPLETE',json.dumps(urls),flush=True)
if __name__=='__main__':main()
