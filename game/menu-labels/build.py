"""Build and sign local menu-label review packages. No publication or game installation."""
import argparse, base64, copy, importlib.util, json, mmap, os, re, struct, subprocess
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('purebuild',ROOT/'game/pure-fixes/build.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def main():
    p=argparse.ArgumentParser()
    for name in ('out','dotnet','base-feeds','rwd','key'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    sdk=base.run([args.dotnet,'--list-sdks']).strip().splitlines()[-1].split(' [',1)
    compiler=[args.dotnet,Path(sdk[1].rstrip(']'))/sdk[0]/'Roslyn/bincore/csc.dll']
    common=['/nologo','/nostdlib+','/langversion:7.3','/deterministic+','/optimize+','/platform:x86','/pathmap:'+str(ROOT)+'=/src']
    common+=['/r:'+str(base.FRAMEWORK/(n+'.dll')) for n in ('mscorlib','System','System.Core')]
    presentation=ROOT/'game/beta7/GamePresentation1372.cs'
    resources=['/resource:'+str(ROOT/'game/beta7'/(n+'.bin'))+','+n for n in ('PawCommonUiPayload','PawCommonUiFixups')]
    sources=[ROOT/'game/pure-fixes'/n for n in ('Program.cs','NativeMemory.cs','PurePatch.cs')]+[presentation]
    for filename,flags in [('k2_paws_menu_1372.exe','PAW_MENU_PRESENTATION;PAW_MENU_ONLY'),('k2_paws_pure_fixes_1372.exe','PAW_MENU_PRESENTATION')]:
        options=common+resources+['/target:winexe','/define:'+flags]
        base.run(compiler+options+['/out:'+str(out/filename)]+sources)
        repro=out/'repro';repro.mkdir(exist_ok=True)
        base.run(compiler+options+['/out:'+str(repro/filename)]+sources)
        assert (out/filename).read_bytes()==(repro/filename).read_bytes(),'Non-deterministic helper'
        base.writejson(out/(filename+'.features.json'),json.loads(base.run([out/filename,'--features'])))
    tests=out/'Menu.Tests.exe';checks=out/'checks'
    base.run(compiler+common+resources+['/target:exe','/out:'+str(tests),presentation,Path(__file__).parent/'Tests.cs'])
    print(base.run([tests,checks]).strip())
    with args.rwd.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as rwd:
        needle='UI/Menus/main.tgi'.encode('utf-16le');index=rwd.find(needle)
        assert index>=0 and rwd.find(needle,index+1)<0,'Stock main menu record not unique'
        start,length=struct.unpack_from('<QQ',rwd,index+len(needle));start+=30
        assert 30<=start<index and 0<length<100000 and start+length<index
        original=rwd[start:start+length]
    text=original.decode('utf-16') if original[:2] in (b'\xff\xfe',b'\xfe\xff') else original.decode('utf-8-sig')
    text,count=re.subn(r'(\[MainMenuLabelVersion[^\]]*\][\s\S]*?\bT\s*=\s*)\d+b',r'\g<1>80b',text,count=1)
    assert count==1
    layout=text.encode('utf-8')
    base.writejson(out/'layout-audit.json',dict(originalSha256=base.sha(original),resultSha256=base.sha(layout),change='MainMenuLabelVersion top offset only',source=str(args.rwd)))
    package=base.package(out,'menu-runtime','1.3.72-menu.3',{'k2_paws_menu_1372.exe':(out/'k2_paws_menu_1372.exe').read_bytes(),'data/UI/Menus/main.tgi':layout},False,920,
        {'ru':'Версия мода в меню','en':'Mod version in the menu'},{'ru':'Отображает название мода и версию. Игровые правила не меняются.','en':'Displays the mod name and version. Game rules are unchanged.'})
    package['mods']=['vanilla','immortals','arcane-wars']
    pure=base.package(out,'pure-fixes-runtime','1.3.72-pure.5',{'k2_paws_pure_fixes_1372.exe':(out/'k2_paws_pure_fixes_1372.exe').read_bytes()},False,910,
        {'ru':"Paw's Patch: исправления движка",'en':"Paw's Patch: engine fixes"},{'ru':'Исправления отображения чисел и рельефа, информация о патче в меню.','en':'Number-display and terrain fixes, with patch information in the menu.'})
    pure['dependsOn']=['menu-runtime']
    helpers=out/'aw-helpers'
    base.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',ROOT/'tools/BuildStandaloneArcaneRuntime.ps1','-OutputDirectory',helpers])
    aw=base.package(out,'aw-runtime','1.3.72-options.menu.3',{f.name:f.read_bytes() for f in helpers.glob('*.exe')},False,300,
        {'ru':'Компоненты движка Arcane Wars','en':'Arcane Wars engine components'},{'ru':'Выбранные компоненты и подпись мода в меню.','en':'Selected components and the mod label in the menu.'})
    aw['mods']=['arcane-wars'];aw['dependsOn']=['menu-runtime']
    key=serialization.load_pem_private_key(args.key.read_bytes(),password=None)
    replacements={x['id']:x for x in (package,pure,aw)}
    for branch in ('stable','beta'):
        env=json.loads((args.base_feeds/(branch+'.json')).read_text('utf-8-sig'))
        raw=base64.b64decode(env['payload']);signature=base64.b64decode(env['signature'])
        key.public_key().verify(utils.encode_dss_signature(int.from_bytes(signature[:32],'big'),int.from_bytes(signature[32:],'big')),raw,ec.ECDSA(hashes.SHA256()))
        feed=json.loads(raw)
        for old in feed['packages']:
            if old['id'] in replacements:
                new=replacements[old['id']]
                if old['id']=='aw-runtime':new['priority']=old['priority']
        feed['packages']=[copy.deepcopy(replacements.get(x['id'],x)) for x in feed['packages']]
        if not any(x['id']=='menu-runtime' for x in feed['packages']):
            feed['packages'].append(copy.deepcopy(package))
        for mod in feed['modGuides']:
            if mod['id'] in ('vanilla','immortals') and mod.get('patchGuide'):
                mod['patchGuide']['version']='0.1.0'
        feed['publishedAt']='2026-09-12T12:00:00Z'
        payload=base.encoded(feed);der=key.sign(payload,ec.ECDSA(hashes.SHA256()));r,s=utils.decode_dss_signature(der)
        signed={'keyId':env.get('keyId','local-review'),'payload':base64.b64encode(payload).decode(),'signature':base64.b64encode(r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode()}
        base.writejson(out/(branch+'.payload.json'),feed);base.writejson(out/(branch+'.json'),signed)
    for package in replacements.values():base.writejson(out/(package['id']+'-package.json'),package)
    base.writejson(out/'packages.json',list(replacements.values()))
    print('Prepared 3 local packages and 2 signed review feeds; nothing published.')

if __name__=='__main__':main()
