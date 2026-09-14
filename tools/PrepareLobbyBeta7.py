"""Prepare immutable Arcane Wars beta.7 assets and signed candidates; no upload."""
import argparse,copy,shutil,urllib.request,urllib.parse
from pathlib import Path
import PreparePatchChannels078 as base
VERSION='0.3.0-beta.7'
TAG='patch-'+VERSION
VERSIONS={'pawpatch-core':VERSION,'common-ui':'1.3.72-ui.6-beta.7','player-colors':VERSION}
GUIDE=dict(id='lobby-compatibility',category='always',titleRu='Проверка совместимости перед входом в лобби',titleEn='Lobby compatibility check',
    bodyRu="При запуске через лаунчер игра проверяет версию игры, Arcane Wars, Paw's Patch, используемые EXE и применённые игровые компоненты до входа в лобби. При несовпадении окно показывает вашу конфигурацию и версии хозяина лобби. Все участники должны использовать одинаковую бету и игровые настройки. Язык интерфейса, текста и озвучки на эту дополнительную проверку не влияет. Обычные проверки файлов и Steam сохранены.",
    bodyEn="When launched through the launcher, the game checks game, Arcane Wars and Paw's Patch versions, active EXEs and applied gameplay components before lobby admission. On mismatch, the dialog shows your configuration and the host's versions. All players need matching Beta versions and gameplay settings. Interface, text and speech languages do not affect this additional check. Native game-file and Steam checks remain enabled.")
class Preparation(base.Preparation):
    def local(self,package):
        try:return super().local(package)
        except FileNotFoundError:
            url=package['urls'][0];parsed=urllib.parse.urlparse(url)
            assert parsed.scheme=='https' and parsed.hostname in ('github.com','raw.githubusercontent.com')
            path=self.out/'verified-source-cache'/(package['sha256']+'.zip');path.parent.mkdir(parents=True,exist_ok=True)
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PawsPatchBetaPreparation'}),timeout=60) as response:
                data=response.read(package['size']+1)
            assert len(data)==package['size'] and base.sha_bytes(data)==package['sha256'].upper()
            path.write_bytes(data);self.paths[package['sha256'].upper()]=path.resolve();return path.resolve()
    def prepare(self):
        for schema in base.SCHEMAS:
            for channel in base.CHANNELS:
                path=self.source_path(schema,channel);key=schema+'/'+channel
                self.baselines[key]=self.verify_signed(path);self.before_hashes[key]=base.sha(path)
                assert self.baselines[key]['launcher']['version']=='0.8.0'
                previous=self.out/'previous'/schema/(channel+'.signed.json');previous.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,previous)
        source={p['id']:p for p in self.baselines['v2/beta']['packages']}
        assert source['pawpatch-core']['version']=='0.3.0-beta.6'
        variants=base.read(base.REPO/'game/beta7/variants.json');helper_bytes={};features={}
        for name,defines in variants.items():
            path=self.args.helpers/name;helper_bytes[name]=path.read_bytes()
            feature=__import__('json').loads(base.command([path,'--features']))
            assert feature['lobbyCompatibility'] and feature['lobbyCompatibilityProtocol']==1 and feature['patchVersion']==VERSION
            assert all(feature[k] for k in ('cityAssistant','advancedCityPolicy','fastSaveTransfer','commonFixes','quiet','nativeCityQueue','automaticMines','startingCityMilitia'))
            assert feature['cityPolicyRevision']==15
            for key,flag in (('colors','PAW_COLORS'),('bypass','SYNC_CONTINUE'),('hostility','HERD_RELATIONS_ONLY')):assert feature[key]==(flag in defines),name
            features[name]=dict(sha256=base.sha(path),features=feature)
        updates,scope,replaced={},{},[]
        for id,version in VERSIONS.items():
            old=source[id];original=self.payload(old);files=dict(original);names={base.normalize(p):p for p in files};allowed=set()
            for name,blob in helper_bytes.items():
                if name.lower() in names:
                    target=names[name.lower()];files[target]=blob;allowed.add(target);replaced.append(name)
            if id=='common-ui':
                target=names['paws_patch_versions.ini'];assert files[target].count(b'PawPatch=0.3.0-beta.6')==1
                files[target]=files[target].replace(b'PawPatch=0.3.0-beta.6',b'PawPatch='+VERSION.encode());allowed.add(target)
            assert set(files)==set(original)
            changed={p for p in files if files[p]!=original[p]};assert changed==allowed
            manifest=copy.deepcopy(self.audited[old['sha256'].upper()]['manifest']);assert not manifest.get('remove')
            manifest['version']=version;manifest['files']=[dict(path=p,size=len(b),sha256=base.sha_bytes(b)) for p,b in sorted(files.items(),key=lambda x:x[0].lower())]
            blob=base.zip_bytes(manifest,files);assert blob==base.zip_bytes(manifest,files)
            path=self.out/'assets'/(id+'-'+version+'.zip');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
            package=copy.deepcopy(old);package.update(version=version,size=len(blob),sha256=base.sha_bytes(blob),urls=[base.DOWNLOADS+TAG+'/'+path.name])
            self.register_asset(package,TAG,path);self.audit_archive(package);assert self.payload(package)==files;updates[id]=package
            scope[id]=dict(changed={p:dict(before=base.sha_bytes(original[p]),after=base.sha_bytes(files[p])) for p in sorted(changed)},preservedPayloadFiles=len(files)-len(changed))
        assert set(replaced)==set(variants) and len(replaced)==9
        entry=base.release_entry('release-'+TAG+'.md',VERSION,self.args.published_at[:10],'arcane-wars','beta')
        feeds={}
        for schema in base.SCHEMAS:
            before=self.baselines[schema+'/beta'];feed=copy.deepcopy(before)
            for p in feed['packages']:
                if p['id'] in updates:
                    assert p['sha256']==source[p['id']]['sha256']
                    for key in ('version','size','sha256','urls'):p[key]=updates[p['id']][key]
            feed['changelog']=[entry]+before['changelog'];feed['publishedAt']=self.args.published_at
            guide=feed['patchGuide'];guide['version']=VERSION;assert not any(e['id']==GUIDE['id'] for e in guide['entries']);guide['entries'].insert(0,GUIDE)
            self.sign(feed,schema,'beta','production')
            local=copy.deepcopy(feed)
            for p in local['packages']:p['urls']=[str(self.local(p))]
            self.sign(local,schema,'beta','local')
            assert [p for p in feed['packages'] if p['id'] not in updates]==[p for p in before['packages'] if p['id'] not in updates]
            assert {k:v for k,v in feed.items() if k not in ('packages','changelog','publishedAt','patchGuide')}=={k:v for k,v in before.items() if k not in ('packages','changelog','publishedAt','patchGuide')}
            feeds[schema]=feed
        history=base.read(base.REPO/'feed/changelog.history.json');assert history['beta']==self.baselines['v2/beta']['changelog'];history['beta']=feeds['v2']['changelog']
        base.write(self.out/'changelog.history.json',history);base.write(self.out/'patch-guide-beta.json',feeds['v2']['patchGuide'])
        notes=base.REPO/'docs'/('release-'+TAG+'.md')
        base.write(self.out/'release-plan.json',dict(tag=TAG,version=VERSION,prerelease=True,launcherIncluded=False,assets=self.assets[TAG],notes=str(notes),notesSha256=base.sha(notes)))
        base.write(self.out/'scope.json',scope);base.write(self.out/'features.json',features)
        base.write(self.out/'preparation.json',dict(before=self.before_hashes,historyBefore=base.sha(base.REPO/'feed/changelog.history.json'),guideBefore=base.sha(base.REPO/'feed/patch-guide-beta.json'),scope=scope,published=False,
            unchanged=['stable feeds','launcher','Vanilla','Immortals','combat balance','all game assets except version label and nine helper copies'],sourceScriptSha256=base.sha(Path(__file__))))
        assert all(base.sha(self.source_path(*key.split('/')))==v for key,v in self.before_hashes.items())
        print('BETA 7 PREPARED: three packages, eight helpers, signed local/production beta candidates.',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('out','dotnet','signing-dir','helpers'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cache',type=Path,action='append',default=[]);p.add_argument('--published-at',required=True)
    args=p.parse_args();assert not args.out.exists();args.out.mkdir(parents=True);Preparation(args).prepare()
