"""Build Vanilla/Immortals stable 0.2.0 and optional beta 0.3.0. No install or publication."""
import argparse, importlib.util, json, mmap, re, shutil, sys
from pathlib import Path
import build as b
from build_channels import stock_file, decode, read_archive, ANALYSIS_HASH

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'game/lobby-colors'))
from PrepareRelease081 import key, verify, read, fetch
from compact_menu import span
VERSIONS={'stable':('0.2.0','1.3.72-pure.8'),'beta':('0.3.0-beta.1','1.3.72-pure.9-beta.1')}
VARIANTS={'k2_paws_pure_fixes_1372.exe':'', 'k2_paws_pure_colors_1372.exe':'PAW_PURE_COLORS',
 'k2_paws_pure_sync_1372.exe':'PAW_PURE_SYNC','k2_paws_pure_colors_sync_1372.exe':'PAW_PURE_COLORS;PAW_PURE_SYNC'}

def main():
    p=argparse.ArgumentParser()
    for n in ('out','dotnet','analysis-work','rwd'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    assert b.sha((a.analysis_work/'k2_runtime_1372_20260904.bin').read_bytes())==ANALYSIS_HASH
    assert b.sha((a.rwd.parent/'k2.exe').read_bytes())==b.GAME_HASH
    feed=verify(read(ROOT/'feed/v2/beta.json'),key());packages={p['id']:p for p in feed['packages']}
    inputs=out/'inputs';inputs.mkdir()
    def source(id):
        p=packages[id];path=inputs/Path(p['urls'][0]).name;path.write_bytes(fetch(p['urls'][0]));return read_archive(inputs,p)
    data=source('pure-fixes-data');assert len(data)==16
    aw=source('player-colors');palette=aw['paws_player_colors.ini']
    assert palette== (ROOT/'game/beta7/paws_player_colors.ini').read_bytes()
    assert len(re.findall(rb'^\[paws_',palette,re.M))==48
    old=decode(aw['data/ui/menus/pcolors.tgi']);control=old[slice(*span(old,'PawColor'))]
    with a.rwd.open('rb') as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as m:
        stock=decode(stock_file(m,'UI/Menus/staging.tgi'))
    menu=stock
    for name in ('PlayerSlot','ObserverSlot'):
        start,end=span(menu,name);block=menu[start:end]
        assert 'PawColor' not in block
        for child in ('Name','AddAI'):
            c,d=span(block,child);change=block[c:d].replace('L = 33','L = 46').replace('R = +148','R = +135')
            assert change!=block[c:d];block=block[:c]+change+block[d:]
        block=block[:-1]+'\n'+control+'\n}'
        menu=menu[:start]+block+menu[end:]
    # Do not carry Arcane Wars staging, extra kingdoms, map options or faction labels.
    colors={'Data/UI/Menus/pcolors.tgi':menu.encode('utf-16'),'paws_player_colors.ini':palette}
    guards=out/'guards';print(b.run([sys.executable,ROOT/'game/fast-transfer/prepare_guards.py','--work',a.analysis_work,'--out',guards]))
    sdk=b.run([a.dotnet,'--list-sdks']).strip().splitlines()[-1].split(' [',1)
    compiler=[a.dotnet,Path(sdk[1].rstrip(']'))/sdk[0]/'Roslyn/bincore/csc.dll']
    common=['/nologo','/nostdlib+','/langversion:7.3','/deterministic+','/optimize+','/platform:x86','/pathmap:'+str(ROOT)+'=/src']
    common+=['/r:'+str(b.FRAMEWORK/(n+'.dll')) for n in ('mscorlib','System','System.Core')]
    sources=[b.SOURCE/n for n in ('Program.cs','NativeMemory.cs','PurePatch.cs','PureChannel.cs')]+[ROOT/'game/beta7/GamePresentation1372.cs',ROOT/'game/fast-transfer/FastTransfer.cs']
    resources=['/resource:'+str(ROOT/'game/beta7'/(n+'.bin'))+','+n for n in ('PawCommonUiPayload','PawCommonUiFixups')]
    resources+=['/resource:'+str(guards/'FastTransferGuards.bin')+',FastTransferGuards']
    result={};report={}
    for channel,(patch,version) in VERSIONS.items():
        target=out/channel;target.mkdir();report[channel]={};files={}
        variants=VARIANTS if channel=='beta' else {b.EXE:''}
        for name,flags in variants.items():
            flags='PAW_MENU_PRESENTATION;PAW_PURE_CHANNEL;PAW_PURE_FAST_TRANSFER'+(';'+'PAW_PURE_BETA' if channel=='beta' else '')+(';' + flags if flags else '')
            src=list(sources);res=list(resources)
            if 'PAW_PURE_COLORS' in flags:
                src += [ROOT/'game/beta7/LobbyColorsNative.cs',ROOT/'game/beta7/GameText.cs']
                res += ['/resource:'+str(ROOT/'game/beta7'/(n+'.bin'))+','+n for n in ('PawLobbyColorsPayload','PawLobbyColorsFixups')]
            if 'PAW_PURE_SYNC' in flags:src+=[b.SOURCE/'PureSync.cs']
            options=common+['/define:'+flags]+res
            exe=target/name;b.run(compiler+options+['/target:winexe','/out:'+str(exe)]+src)
            repro=target/'repro';repro.mkdir(exist_ok=True);b.run(compiler+options+['/target:winexe','/out:'+str(repro/name)]+src)
            assert exe.read_bytes()==(repro/name).read_bytes()
            feature=json.loads(b.run([exe,'--features']))
            assert feature['patchVersion']==patch and feature['version']==version and feature['fastSaveTransfer']
            assert feature['colors']==('PAW_PURE_COLORS' in flags) and feature['bypass']==('PAW_PURE_SYNC' in flags)
            assert all(not feature[k] for k in ('hostility','cityAssistant','randomMap','randomTime','changesGameFiles'))
            assert b.run([exe,'--preflight',a.rwd.parent]).strip()=='PURE_PREFLIGHT_PASS 1.3.72'
            files[name]=exe.read_bytes();report[channel][name]={'sha256':b.sha(files[name]),'features':feature}
            if name==b.EXE:
                for test,main,extras in [('Pure','Tests',['Tests.cs']),('Channel','ChannelTests',['ChannelTests.cs'])]:
                    testexe=target/(test+'.Tests.exe');check=target/('checks-'+test)
                    more=[b.SOURCE/n for n in extras]+([ROOT/'game/fast-transfer/FastTransferTests.cs'] if test=='Channel' else [])
                    b.run(compiler+options+['/target:exe','/main:PawPureFixes.'+main,'/out:'+str(testexe)]+src+more)
                    log=b.run([testexe,check]);(target/(test+'-checks.txt')).write_text(log);print(channel,log[-180:].strip(),flush=True)
                log=b.run([sys.executable,b.SOURCE/'test_native.py','--out',target/'checks-Pure','--deps',a.analysis_work/'lobby_colors_1372/pydeps_r3','--original-ui-payload',ROOT/'game/beta7/PawCommonUiPayload.bin'])
                (target/'pure-native.txt').write_text(log)
                shutil.copyfile(guards/'guards.json',target/'checks-Channel/guards.json')
                log=b.run([sys.executable,ROOT/'game/fast-transfer/test_native.py','--work',a.analysis_work,'--out',target/'checks-Channel'])
                (target/'transfer-native.txt').write_text(log)
        d=b.package(target,'pure-fixes-data',patch,data,True,900,{'ru':"Paw's Patch: значки и управление",'en':"Paw's Patch: badges and controls"},packages['pure-fixes-data']['description'])
        r=b.package(target,'pure-fixes-runtime',version,files,False,910,packages['pure-fixes-runtime']['name'],{'ru':'Исправления рельефа и отображения чисел; быстрая передача сохранений.','en':'Terrain and number-display fixes; fast saved-game transfers.'})
        r.update(dependsOn=['menu-runtime'],experimental=channel=='beta');result[channel]=[d,r]
        if channel=='beta':
            c=b.package(target,'pure-player-colors',patch,colors,False,920,{'ru':'Расширенные цвета игроков','en':'Extended player colors'}, {'ru':'48 цветов и компактный выбор возле значка игрока.','en':'48 colors and a compact picker beside the player badge.'})
            c.update(dependsOn=['pure-fixes-runtime'],experimental=True);result[channel].append(c)
        b.writejson(target/'packages.json',result[channel])
    # Exercise the actual optional suppression implementation independently of launch.
    testexe=out/'Sync.Tests.exe';args=common+['/define:PAW_MENU_PRESENTATION;PAW_PURE_CHANNEL;PAW_PURE_FAST_TRANSFER']+resources
    b.run(compiler+args+['/target:exe','/main:PawPureFixes.SyncTests','/out:'+str(testexe)]+sources+[b.SOURCE/n for n in ('PureSync.cs','SyncTests.cs','ChannelTests.cs')]+[ROOT/'game/fast-transfer/FastTransferTests.cs'])
    print(b.run([testexe,out/'sync-checks']),flush=True)
    log=b.run([sys.executable,b.SOURCE/'test_sync_native.py','--stub',out/'sync-checks/sync-stub.bin','--deps',a.analysis_work/'lobby_colors_1372/pydeps_r3'])
    (out/'sync-native.txt').write_text(log);print(log,flush=True)
    b.writejson(out/'packages.json',result);b.writejson(out/'features.json',report)
    b.writejson(out/'scope.json',dict(sourceData=packages['pure-fixes-data'],sourceColors=packages['player-colors'],stockStagingOnly=True,colorPayloadSha256=b.sha((ROOT/'game/beta7/PawLobbyColorsPayload.bin').read_bytes()),versions=VERSIONS,gameLaunched=False,published=False))

if __name__=='__main__':main()
