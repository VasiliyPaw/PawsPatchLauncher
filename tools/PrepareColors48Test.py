"""Build signed local beta catalogs only. Does not install or publish."""
import argparse,base64,copy,sys
from pathlib import Path
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec,utils
from PrepareRelease081 import key,verify,read,write
from PrepareSplitLanguages import encoded
from PrepareSplitLanguages import readpkg,build

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'game/lobby-colors'))
from compact_menu import compact
VERSION='0.3.0-beta.8-test.1'
VERSIONS={'pawpatch-core':VERSION,'common-ui':'1.3.72-ui.7-beta.8-test.1','player-colors':VERSION}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('out','helpers','native','signing-dir','source-packages'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),password=None)
    def sign(feed):
        payload=encoded(feed);r,s=utils.decode_dss_signature(private.sign(payload,ec.ECDSA(hashes.SHA256())))
        envelope=dict(keyId='pawpatch-prod-2026',payload=base64.b64encode(payload).decode(),signature=base64.b64encode(r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode())
        assert verify(envelope,private.public_key())==feed
        return envelope
    before=verify(read(ROOT/'feed/v2/beta.json'),key());feed=copy.deepcopy(before)
    variants=read(ROOT/'game/beta7/variants.json');changed={}
    for package in feed['packages']:
        ident=package['id']
        if ident not in VERSIONS:continue
        source=copy.deepcopy(package);source['urls']=[str(a.source_packages/Path(source['urls'][0]).name)]
        old=readpkg(source);files=dict(old)
        for path in files:
            basename=path.replace('\\','/').rsplit('/',1)[-1]
            if basename in variants:files[path]=(a.helpers/basename).read_bytes()
            elif basename=='paws_player_colors.ini':files[path]=(a.helpers/basename).read_bytes()
            elif basename=='paws_patch_versions.ini':files[path]=(a.helpers/basename).read_bytes()
            elif basename=='pcolors.tgi':files[path]=compact(files[path],(a.native/'staging.tgi').read_bytes())
        changed[ident]=[path for path in files if files[path]!=old[path]]
        assert changed[ident]
        package.update(build(a.out,package,VERSIONS[ident],files))
        if ident=='player-colors':
            package['description']={'ru':'48 цветов игроков и компактный выбор рядом со значком. Цвет следует за участником при смене места.',
                'en':'48 player colors with a compact picker beside the badge. Colors follow participants when changing seats.'}
    feed['playerColorCount']=48
    feed['publishedAt']='2026-09-15T20:00:00Z'
    guide=feed['patchGuide'];guide['version']=VERSION
    for entry in guide['entries']:
        if entry['id']=='colors':
            entry['bodyRu']='48 цветов и вариант «Случайно». Нажмите стрелку рядом с цветным значком игрока: выбор больше не занимает дополнительную строку. Светло-красный удалён из списка, но сохранения с этим оттенком поддерживаются.\n\nВ новой игре цвет связан с участником и следует за ним при смене места или переходе в наблюдатели. Новый участник не получает цвет прежнего владельца места. Если прежний цвет уже занят, назначается «Случайно».\n\nХост может менять цвета всех участников, клиент — только свой. В сохранениях цвета принадлежат королевствам и доступны только для просмотра.'
            entry['bodyEn']='48 colors plus Random. Click the arrow next to the player color badge; the picker no longer occupies a second row. Light Red is removed from the list, while existing saves using it remain supported.\n\nIn new games, colors belong to participants and follow them between seats or when spectating. New participants do not inherit the previous occupant’s color. If a former color is occupied, Random is selected.\n\nHosts may change all participant colors; clients only their own. Saved-game colors belong to kingdoms and are read-only.'
    feed['changelog'].insert(0,dict(category='patch',mod='arcane-wars',channel='beta',version=VERSION,publishedAt='2026-09-15',title={'ru':'Компактный выбор цвета — локальный тест','en':'Compact color picker — local test'},body={'ru':'Выбор цвета перенесён к значку игрока. Исправлена привязка цвета при смене места. Удалён светло-красный: осталось 48 цветов.','en':'Moved the color picker beside the player badge. Fixed color ownership when changing seats. Removed Light Red, leaving 48 colors.'}))
    write(a.out/'beta.payload.json',feed);write(a.out/'beta.json',sign(feed))
    # Stable and other mods retain their public packages and 49-color metadata.
    stable=verify(read(ROOT/'feed/v2/stable.json'),key())
    write(a.out/'stable.json',sign(stable))
    config=read(ROOT/'src/PawsPatchLauncher/launcher.config.json')
    config.update(feedUrls=[str((a.out/'stable.json').resolve())],betaFeedUrls=[str((a.out/'beta.json').resolve())],
        publicKeyPem=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode())
    write(a.out/'launcher.config.json',config)
    assert [p for p in feed['packages'] if p['id'] not in VERSIONS]==[p for p in before['packages'] if p['id'] not in VERSIONS]
    write(a.out/'scope.json',{'localOnly':True,'published':False,'changedFiles':changed,'unchangedPackages':len(feed['packages'])-len(changed)})
    print('LOCAL beta prepared; 3 packages changed, no publication.')

if __name__=='__main__':main()
