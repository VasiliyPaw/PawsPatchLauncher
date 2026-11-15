LANGS=['en','ru','de','fr','cs','uk']
LABELS=[
 ['Select engineers','Build road','Stop road'],
 ['Выбери инженеров','Строить дорогу','Остановить дорогу'],
 ['Ingenieure wählen','Straße bauen','Straßenbau beenden'],
 ['Choisir ingénieurs','Construire route','Arrêter la route'],
 ['Vyber ženisty','Stavět cestu','Ukončit stavbu'],
 ['Вибери інженерів','Будувати дорогу','Зупинити дорогу'],
]
for row,extra in zip(LABELS,[['Drag road','Route blocked'],['Протяни дорогу','Путь перекрыт'],['Straße ziehen','Weg blockiert'],['Tracer la route','Trajet bloqué'],['Táhni cestu','Cesta blokována'],['Протягни дорогу','Шлях перекрито']]):row.extend(extra)
TIPS=[
 'Select engineers and drag with the left mouse button to plan a straight road. Release to build. Right click or Esc cancels the plan. Roads add 20% of base speed. No construction over water.',
 'Выдели инженеров и протяни дорогу левой кнопкой мыши. Отпусти кнопку, чтобы начать строительство. ПКМ или Esc отменяет план. Дорога даёт +20% базовой скорости. Через воду строить нельзя.',
 'Ingenieure wählen und mit der linken Maustaste eine Straße ziehen. Loslassen startet den Bau. Rechtsklick oder Esc bricht den Plan ab. Straße: +20% Grundgeschwindigkeit. Kein Bau auf Wasser.',
 'Choisissez les ingénieurs et tracez la route avec le bouton gauche. Relâchez pour construire. Clic droit ou Échap annule le tracé. Route : +20% de vitesse de base. Pas sur l’eau.',
 'Vyber ženisty a táhni cestu levým tlačítkem myši. Uvolněním začne stavba. Pravé tlačítko nebo Esc zruší plán. Cesta: +20% základní rychlosti. Nelze stavět přes vodu.',
 'Вибери інженерів і протягни дорогу лівою кнопкою миші. Відпусти кнопку для початку будівництва. ПКМ або Esc скасовує план. Дорога дає +20% базової швидкості. Через воду будувати не можна.',
]

def header():
 def w(s):return 'L"'+''.join('\\x%04x'%ord(c) for c in s)+'"'
 return 'static const wchar_t* road_labels[6][5]={\n'+',\n'.join('{'+','.join(map(w,row))+'}' for row in LABELS)+'\n};\nstatic const wchar_t* road_tips[6]={'+','.join(map(w,TIPS))+'};\n'
