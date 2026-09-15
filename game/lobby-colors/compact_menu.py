"""Compact existing localized menus without replacing unrelated UI/localization."""
import re

def span(text,name):
    m=re.search(r'\['+re.escape(name)+r'\b',text);assert m,name
    start=m.start();brace=text.index('{',start);end=brace+1;depth=1
    while depth:
        if text[end]=='{':depth+=1
        elif text[end]=='}':depth-=1
        end+=1
    return start,end

def compact(raw,candidate):
    encoding='utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    text=raw.decode(encoding);new=candidate.decode('ascii')
    ca,cb=span(new,'PawColor');control=new[ca:cb].replace('#staging_WorldParamsPanel_random_option_text','#paws_color_random')
    for name in ('PlayerSlot','ObserverSlot'):
        a,b=span(text,name);block=text[a:b]
        block,count=re.subn(r'B = \+49','B = +27',block,count=1);assert count==1
        for child in ('Name','AddAI'):
            c,d=span(block,child)
            changed=block[c:d].replace('L = 33','L = 46').replace('R = +148','R = +135')
            block=block[:c]+changed+block[d:]
        c,d=span(block,'PawColor');block=block[:c]+control+block[d:]
        text=text[:a]+block+text[b:]
    return text.encode(encoding if encoding=='utf-16' else 'utf-8')
