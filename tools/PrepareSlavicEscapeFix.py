"""Repackage the local Ukrainian text depot after the log-272 startup failure."""
import argparse,json
from pathlib import Path
from CollectSlavicCatalog import ROW,unquote
from PrepareEuropeanModLanguages import source,ROOT
from PrepareSplitLanguages import read,write,build,dec
from GameTextValidation import validate_engine_text

def main():
    p=argparse.ArgumentParser()
    for key in ('base','out','reference','cache'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve()
    feeds={c:read(a.base/(c+'.payload.json')) for c in ('stable','beta')}
    old=next(p for p in feeds['stable']['packages'] if p['id']=='game-localization-uk')
    assert old['version']=='1.0.0-preview.1',old['version']
    tables=read(a.reference);catalog=read(ROOT/'game/localization/text-cs-uk.json')['entries']
    original=source(old,a.cache);files=dict(original);changed=[];audited=0
    for path,data in original.items():
        if not path.endswith('.tgi') or '/Fonts/' in path:continue
        relative=path.split('/',1)[1]
        if relative not in tables:continue
        reference={k:unquote(v) for _,k,_,v in ROW.findall(tables[relative])}
        content=dec(data)
        def row(m):
            nonlocal audited
            key=m[2];value=unquote(m[4])
            if key not in reference:return m[0]
            english=reference[key];audited+=1
            try:validate_engine_text(english,value);return m[0]
            except ValueError:
                corrected=catalog[english]['uk'];validate_engine_text(english,corrected)
                assert value.startswith('& ') and english in ('Delete','Add','Remove','DELETE','RENAME','KICK','BAN')
                changed.append(dict(path=path,key=key,source=english,before=value,after=corrected))
                return m[1]+key+m[3]+json.dumps(corrected,ensure_ascii=False)
        updated=ROW.sub(row,content)
        if updated!=content:files[path]=updated.encode('utf-16')
        for _,key,_,value in ROW.findall(updated):
            if key in reference:validate_engine_text(reference[key],unquote(value))
    assert len(changed)==21,changed
    paths=sorted(set(r['path'] for r in changed));assert len(paths)==3,paths
    assert all(files[p]==raw for p,raw in original.items() if p not in paths)
    corrected=build(a.out,old,'1.0.0-preview.2',files)
    for channel,feed in feeds.items():
        previous=list(feed['packages']);feed['packages']=[corrected if p['id']==old['id'] else p for p in previous]
        assert sum(p!=n for p,n in zip(previous,feed['packages']))==1
        write(a.out/'feeds'/(channel+'.payload.json'),feed)
    write(a.out/'escape-fix-audit.json',dict(cause='log-272: extra ampersand mnemonic aborts strings_rtse.tgi loading',auditedRows=audited,changedRows=changed,changedFiles=paths,otherFilesUnchanged=len(files)-len(paths),version=corrected['version']))
    print('ESCAPE_FIX_PACKAGE_PASS',len(changed),'labels in',len(paths),'files;',audited,'rows checked')

if __name__=='__main__':main()
