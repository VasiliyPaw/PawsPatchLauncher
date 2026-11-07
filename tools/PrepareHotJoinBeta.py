"""Stage the Arcane-only hot-join beta; never installs or publishes it."""
import argparse,base64,copy,hashlib,json,subprocess,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import key,sign,fetch,RAW,normalize
from PrepareRelease070 import verify,validate_package

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.5.0-beta.2'
def digest(data):return hashlib.sha256(data).hexdigest().upper()
def encode(obj):return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def envelope(path):return verify(json.loads(path.read_bytes()),key())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--helpers',type=Path,required=True)
    ap.add_argument('--baseline-assets',type=Path,required=True);ap.add_argument('--private-key',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);assert not (out/'preparation.json').exists()
    private=serialization.load_pem_private_key(a.private_key.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
    report=json.loads((a.helpers/'build-report.json').read_text());locales=json.loads((ROOT/'game/hotjoin-test/localization.json').read_text())
    baseline={};feeds={};archives={};assets=[];changed=set()
    targets=['feed/v3/beta.json','feed/v2/beta.json']
    for path in [*targets,'feed/v3/stable.json','feed/v2/stable.json','feed/beta.json','feed/stable.json']:
        raw=(ROOT/path).read_bytes();assert normalize(fetch(RAW+path+'?hotjoin=baseline'))==normalize(raw),path
        previous=out/'before'/path;previous.parent.mkdir(parents=True,exist_ok=True);previous.write_bytes(raw)
        baseline[path]=verify(json.loads(raw),key())
    for path in targets:
        before=baseline[path];feed=copy.deepcopy(before)
        for package in feed['packages']:
            pid=package['id']
            if package.get('mods')!=['arcane-wars']:continue
            if pid not in ('pawpatch-core','common-ui','player-colors','desync-continue') and not pid.startswith('pawpatch-data'):continue
            old=package['sha256'];changed.add(pid)
            if pid not in archives:
                source=a.baseline_assets/(pid+'-'+package['version']+'.zip');data=source.read_bytes();assert digest(data)==old.upper(),pid
                with zipfile.ZipFile(source) as z:
                    manifest=json.loads(z.read('module.json'));files={n:z.read(n) for n in z.namelist() if n!='module.json'}
                manifest['version']=VERSION
                for name in list(files):
                    leaf=Path(name).name
                    if leaf in report:
                        value=(a.helpers/leaf).read_bytes();assert digest(value)==report[leaf]['sha256'];files[name]=value
                    elif leaf=='paws_patch_versions.ini':files[name]=files[name].replace(b'PawPatch=0.5.0-beta.1',b'PawPatch='+VERSION.encode())
                if pid.startswith('pawpatch-data'):
                    lang='en' if pid=='pawpatch-data' else pid.rsplit('-',1)[1];entries=locales[lang]
                    text='[Text language=default]\n{\n ids = Localization/paws_hotjoin.tgi\n name = "@Localization/paws_hotjoin.tgi"\n'+''.join(' '+k+' = '+json.dumps(v,ensure_ascii=False)+'\n' for k,v in entries.items())+'}\n'
                    files['payload/data/Localization/paws_hotjoin.tgi']=text.encode('utf-16')
                manifest['files']=[dict(path=n[len('payload/'):],size=len(b),sha256=digest(b)) for n,b in sorted(files.items()) if n.startswith('payload/')]
                target=out/'assets'/(pid+'-'+VERSION+'.zip');target.parent.mkdir(exist_ok=True)
                with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                    z.writestr('module.json',encode(manifest))
                    for n,b in sorted(files.items()):z.writestr(n,b)
                archives[pid]=dict(path=str(target),sha256=digest(target.read_bytes()),size=target.stat().st_size)
                validate_package(target,dict(package,version=VERSION,sha256=archives[pid]['sha256'],size=archives[pid]['size']))
                assets.append(dict(id=pid,**archives[pid]))
            item=archives[pid];package.update(version=VERSION,sha256=item['sha256'],size=item['size'],urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-'+VERSION+'/'+Path(item['path']).name])
            package.pop('url',None) # PackageRelease consumes urls, not the legacy singular key.
        # Only Arcane patch packages change. Other games and the launcher keep
        # their exact entries and their existing channel behavior.
        assert [p for p in before['packages'] if p['id'] not in changed]==[p for p in feed['packages'] if p['id'] not in changed]
        feed['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        titles={'ru':'Возврат в идущую партию','en':'Return to a running match','de':'Rückkehr in eine laufende Partie','fr':'Retour dans une partie en cours','cs':'Návrat do probíhající hry','uk':'Повернення до поточної партії'}
        bodies={
            'ru':'Возврат за своё прежнее королевство вместо ИИ; новые участники входят наблюдателями. При отключении игрока матч остаётся на паузе. При потере хоста во время входа повторите подключение у нового хоста. Встроено в основной Paw’s Patch при любом сочетании остальных компонентов; старое восстановление через сохранение и лобби отключено.',
            'en':'Return to your original kingdom instead of its AI; new participants join as observers. A disconnect leaves the match paused. If the host is lost during admission, retry with the new host. Built into Paw’s Patch with every combination of other components; legacy save-and-lobby recovery is disabled.',
            'de':'Übernimm wieder dein ursprüngliches Königreich von der KI; neue Teilnehmer treten als Zuschauer bei. Nach einem Verbindungsabbruch bleibt die Partie pausiert. Fällt der Host beim Beitritt aus, verbinde dich erneut mit dem neuen Host. In Paw’s Patch integriert, unabhängig von anderen Komponenten; die alte Wiederherstellung über Spielstand und Lobby ist deaktiviert.',
            'fr':'Reprenez votre royaume initial à la place de son IA ; les nouveaux participants rejoignent les observateurs. Une déconnexion laisse la partie en pause. Si l’hôte disparaît pendant l’entrée, reconnectez-vous au nouvel hôte. Intégré à Paw’s Patch avec toutes les autres options ; l’ancienne récupération par sauvegarde et salon est désactivée.',
            'cs':'Vraťte se ke svému původnímu království místo jeho AI; noví účastníci se připojují jako pozorovatelé. Po odpojení zůstane hra pozastavená. Pokud během připojování vypadne hostitel, připojte se znovu k novému hostiteli. Součást Paw’s Patch při libovolné kombinaci ostatních voleb; staré obnovení přes uloženou hru a lobby je vypnuté.',
            'uk':'Повернення за своє попереднє королівство замість ШІ; нові учасники входять спостерігачами. Після відключення гравця матч залишається на паузі. Якщо під час входу втрачено хоста, повторіть підключення до нового хоста. Вбудовано в основний Paw’s Patch за будь-якого поєднання інших компонентів; старе відновлення через збереження та лобі вимкнено.'}
        entry=dict(category='patch',mods=['arcane-wars'],channel='beta',version=VERSION,publishedAt='2026-11-07',title={k:'Paw’s Patch '+VERSION+' — '+v for k,v in titles.items()},body=bodies)
        feed['changelog']=[entry]+[x for x in feed.get('changelog',[]) if x.get('version')!=VERSION]
        guide=feed.get('patchGuide')
        if isinstance(guide,dict):
            guide['version']=VERSION
            guide['entries']=[dict(id='hotjoin',category='always',titleRu=titles['ru'],titleEn=titles['en'],bodyRu=bodies['ru'],bodyEn=bodies['en'])]+[x for x in guide.get('entries',[]) if x.get('id')!='hotjoin']
        target=out/'signed'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(encode(sign(feed,private)));feeds[path]=feed
    history=json.loads((ROOT/'feed/changelog.history.json').read_text());history['beta']=[entry]+[x for x in history['beta'] if x.get('version')!=VERSION]
    for path,value in [('feed/changelog.history.json',history),('feed/patch-guide-beta.json',feeds[targets[0]]['patchGuide'])]:
        previous=out/'before'/path;previous.parent.mkdir(parents=True,exist_ok=True);previous.write_bytes((ROOT/path).read_bytes())
        assert normalize(fetch(RAW+path+'?hotjoin=baseline'))==normalize(previous.read_bytes())
        target=out/'signed'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(encode(value))
    (out/'preparation.json').write_bytes(encode(dict(version=VERSION,sourceHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),assets=assets,changedPackages=sorted(changed),feeds=targets)))
    (out/'notes.md').write_text('''Paw’s Patch 0.5.0-beta.2 — Arcane Wars

* Возврат прямо в идущую партию за своё прежнее королевство вместо ИИ.
* Новый участник входит наблюдателем; штатный чат сообщает о входе и возврате.
* При выходе или потере игрока матч остаётся на паузе до решения участников.
* При потере хоста во время входа незавершённый вход отменяется; повторите его у нового хоста.
* Работает при всех сочетаниях остальных компонентов основного Paw’s Patch, без отдельной галочки.
* Старое восстановление через сохранение и общий выход в лобби отключено в Arcane Wars.
* Переводы уведомлений: русский, английский, немецкий, французский, чешский и украинский.

Всем участникам нужны одинаковая бета и одинаковые игровые компоненты.
Локальные проверки не заменяют проверку Steam Internet на разных компьютерах.
''',encoding='utf-8')
    print(json.dumps(dict(version=VERSION,packages=len(assets),changed=sorted(changed)),ensure_ascii=False))
if __name__=='__main__':main()
