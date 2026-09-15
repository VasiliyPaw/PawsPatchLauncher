"""Inventory original, mod and patch text for the local CS/UK translation review."""
import argparse, json, re
from pathlib import Path
from PrepareEuropeanLanguages import decode
from PrepareEuropeanModLanguages import source, table, ROOT
from PrepareSplitLanguages import read, write, dec

BLOCK = re.compile(r'(?ms)^\s*\[Text\s+language\s*=[^\]]*\]\s*\{.*?^\s*\}')
ROW = re.compile(r'(?m)^(\s*)([\w.]+)(\s*=\s*)"((?:\\.|[^"\\])*)"')
LITERAL = r'"((?:\\.|[^"\\])*)"'

def unquote(value):
    return re.sub(r'\\([nrt"\\])',lambda m: {'n':'\n','r':'\r','t':'\t','"':'"','\\':'\\'}[m[1]],value)

def main():
    p=argparse.ArgumentParser()
    for name in ('assets','game','feed','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); packages={p['id']:p for p in read(a.feed)['packages']}
    ru=source(packages['vanilla-localization-ru'],a.cache)
    references={}
    for path,b in ru.items():
        if path.lower().endswith('.tgi'):
            for block in BLOCK.findall(dec(b)):
                for _,k,_,v in ROW.findall(block):
                    relative=path.split('/',1)[1].lower()
                    if k!='name' or relative.startswith('maps/'):references[(relative,k)]=unquote(v)
    phrases={}; tables={}
    def add(en,key,rus=None):
        if not en:return
        row=phrases.setdefault(en,dict(en=en,keys=[],ru=[]))
        if key not in row['keys']:row['keys'].append(key)
        if rus and rus not in row['ru']:row['ru'].append(rus)
    raw=(a.game/'Data.rwd').read_bytes()
    for path,i in read(a.assets/'en-rwd-files.json').items():
        if not path.lower().endswith('.tgi'):continue
        content=decode(raw[i['offset']:i['offset']+i['size']])
        blocks=BLOCK.findall(content)
        if not blocks:continue
        tables[path]=content
        for block in blocks:
            for _,key,_,v in ROW.findall(block):
                if key!='name' or path.lower().startswith('maps/'):add(unquote(v),path+':'+key,references.get((path.lower(),key)))
    for key,e in read(ROOT/'game/localization/mod-de-fr.json')['entries'].items():
        add(e['en'],'mod:'+key,e.get('ru'))
    native={}
    for path in (ROOT/'game').rglob('*.cs'):
        if path.name.endswith('Tests.cs'):continue
        content=path.read_text('utf-8-sig')
        for r,e in re.findall(r'\bT\(\s*'+LITERAL+r'\s*,\s*'+LITERAL+r'\s*\)',content):
            e,r=unquote(e),unquote(r);native[e]=r;add(e,'native:'+path.name,r)
    for e,r in zip(['Gold','Stone','Wood','Iron','Mana','Resource income is unchanged.'],['Золото','Камень','Дерево','Железо','Мана','Доход ресурсов не изменится.']):
        native[e]=r;add(e,'native:resource',r)
    colors={}
    for block in (ROOT/'game/beta7/paws_player_colors.ini').read_text('utf-8-sig').split('[paws_')[1:]:
        en=re.search(r'(?m)^name_en=(.+)',block)[1].strip();rus=re.search(r'(?m)^name_ru=(.+)',block)[1].strip()
        colors[en]=rus;add(en,'palette:'+block.split(']')[0],rus)
    write(a.out/'source.json',dict(schemaVersion=1,phrases=phrases,native=native,colors=colors))
    write(a.out/'english-tables.json',tables)
    print('Tables',len(tables),'unique phrases',len(phrases),'characters',sum(len(t) for t in phrases),'native',len(native))

if __name__=='__main__':main()
