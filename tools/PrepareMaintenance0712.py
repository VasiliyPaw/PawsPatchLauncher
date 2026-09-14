"""Stage the reviewed Arcane Wars maintenance packages; no publish or game I/O.

Reuses strict archive/signature validators. Only seven new archives are made;
all other packages, pure-mode guides and game requirements remain identical.
"""
import argparse, copy, json, re, shutil
from pathlib import Path
import PreparePatchChannels078 as base

VERSIONS = {'stable': {'pawpatch-core':'0.2.1','player-colors':'0.2.1','common-ui':'1.3.72-ui.5'},
            'beta': {'pawpatch-core':'0.3.0-beta.4','player-colors':'0.3.0-beta.4','common-ui':'1.3.72-ui.5-beta.4'}}
ROAM_ID, ROAM_VERSION = 'aw-roaming-x4-new', '0.82.1.8-clean.3'
RIFT = 'data/buildings/lairsmonster/dark_rift.tgi'
EXCEPTION_RU = 'Исключение: на ×4 Тёмный лорд из Тёмного разлома (Врат теней) появляется с частотой ×2 — попытка каждые 6 игровых минут с шансом 30%. Требуется включить «Новые блуждающие роты».'
EXCEPTION_EN = 'Exception: at ×4, the Shadow Lord from the Dark Rift uses ×2 frequency: one attempt every 6 game minutes with a 30% chance. Additional roaming companies must be enabled.'

def text_encoding(data):
    return 'utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'latin-1'

def rift(data):
    encoding=text_encoding(data);text=data.decode(encoding);before=text
    for name,old,new in [('event_time','240','360'),('event_chance','0.4','0.3')]:
        pattern=r'(?m)^(\s*'+name+r'\s*=\s*)'+re.escape(old)+r'(?=\s*(?:[;\r\n]|$))'
        text,count=re.subn(pattern,lambda m:m[1]+new,text)
        assert count==1,(name,count)
    assert re.search(r'marauder_chance\s*=\s*1\b',text)
    assert 'paws_roaming_shadow_lord' in text
    assert text!=before
    return text.encode(encoding)

class Preparation(base.Preparation):
    def load_sources(self):
        for schema in base.SCHEMAS:
            for channel in base.CHANNELS:
                path=self.source_path(schema,channel);feed=self.verify_signed(path)
                assert feed['launcher']['version']=='0.7.11' and feed['channel']==channel
                key=schema+'/'+channel;self.baselines[key]=feed;self.before_hashes[key]=base.sha(path)
                assert len({p['id'] for p in feed['packages']})==len(feed['packages'])

    def helpers(self,channel):
        root=(self.args.beta_helpers if channel=='beta' else self.args.stable_helpers).resolve()
        ready=base.read(root/'release-ready.json')
        assert ready['ready'] and ready['channel']==channel
        variants=base.read(base.REPO/'game/beta7/variants.json')
        for name,defines in variants.items():
            assert base.sha(root/name)==ready['files'][name]
            f=json.loads(base.command([root/name,'--features']))
            assert f['commonFixes'] and f['quiet']
            assert f['cityPolicyRevision']==(15 if channel=='beta' else 0)
            for feature in ('cityAssistant','advancedCityPolicy','fastSaveTransfer','newCityMilitia','startingCityMilitia'):
                assert f[feature]==(channel=='beta')
            for feature,define in [('colors','PAW_COLORS'),('bypass','SYNC_CONTINUE'),('hostility','HERD_RELATIONS_ONLY')]:
                assert f[feature]==(define in defines)
            build=('beta.0.3.0-beta.4-1372-city-policy15-transfer-r2-quiet' if channel=='beta'
                   else 'release.0.2.1-1372-terrain-randommap-colors20-independent-quiet')
            assert build.encode('utf-16le') in (root/name).read_bytes()
        return root,ready,variants

    def pack(self,old,version,tag,files,allowed):
        original=self.payload(old)
        assert set(files)==set(original)
        changed={p for p in files if files[p]!=original[p]}
        assert changed and changed<=allowed,(old['id'],changed-allowed)
        manifest=copy.deepcopy(self.audited[old['sha256'].upper()]['manifest'])
        assert not manifest.get('remove')
        manifest['version']=version
        manifest['files']=[dict(path=p,size=len(b),sha256=base.sha_bytes(b)) for p,b in sorted(files.items(),key=lambda item:item[0].lower())]
        blob=base.zip_bytes(manifest,files);assert blob==base.zip_bytes(manifest,files)
        path=self.out/'releases'/tag/'assets'/(old['id']+'-'+version+'.zip')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
        package=copy.deepcopy(old);package.update(version=version,size=len(blob),sha256=base.sha_bytes(blob),urls=[base.DOWNLOADS+tag+'/'+path.name])
        self.register_asset(package,tag,path);self.audit_archive(package)
        assert self.payload(package)==files
        self.scope.append(dict(package=old['id'],version=version,sourceSha256=old['sha256'],fileCount=len(files),
                               changed={p:dict(before=base.sha_bytes(original[p]),after=base.sha_bytes(files[p])) for p in sorted(changed)}))
        return package

    def prepare_packages(self):
        self.scope=[];result={}
        for channel,versions in VERSIONS.items():
            helpers,ready,variants=self.helpers(channel)
            source={p['id']:p for p in self.baselines['v2/'+channel]['packages']}
            result[channel]={};copies=[]
            for id,version in versions.items():
                old=source[id];files=self.payload(old);names={base.normalize(p):p for p in files};allowed=set()
                for name in variants:
                    if name.lower() in names:
                        path=names[name.lower()];files[path]=(helpers/name).read_bytes();allowed.add(path);copies.append(name)
                if id=='pawpatch-core':
                    path=names[RIFT];files[path]=rift(files[path]);allowed.add(path)
                if id=='common-ui':
                    path=names['paws_patch_versions.ini'];data=files[path]
                    patch=VERSIONS[channel]['pawpatch-core']
                    old_patch=next(p['version'] for p in source.values() if p['id']=='pawpatch-core')
                    assert data.count(('PawPatch='+old_patch).encode())==1
                    files[path]=data.replace(('PawPatch='+old_patch).encode(),('PawPatch='+patch).encode());allowed.add(path)
                    if channel=='beta':
                        for relative in base.CITY_DATA:
                            path=names[base.normalize(relative)];data=(helpers/relative).read_bytes()
                            assert base.sha_bytes(data)==ready['files'][relative]
                            files[path]=data;allowed.add(path)
                result[channel][id]=self.pack(old,version,'patch-'+versions['pawpatch-core'],files,allowed)
            assert len(copies)==9 and set(copies)==set(variants)
        old=next(p for p in self.baselines['v2/stable']['packages'] if p['id']==ROAM_ID)
        files=self.payload(old);path=next(p for p in files if base.normalize(p)==RIFT);files[path]=rift(files[path])
        shared=self.pack(old,ROAM_VERSION,'patch-0.2.1',files,{path})
        for channel in base.CHANNELS:
            source=next(p for p in self.baselines['v2/'+channel]['packages'] if p['id']==ROAM_ID)
            assert source['sha256']==old['sha256']
            result[channel][ROAM_ID]=shared
        base.write(self.out/'scope.json',self.scope)
        return result

    def guide(self,source):
        guide=copy.deepcopy(source);guide['version']='0.3.0-beta.4'
        frequency=next(e for e in guide['entries'] if e['id']=='frequency')
        frequency['bodyRu']+='\n\n'+EXCEPTION_RU;frequency['bodyEn']+='\n\n'+EXCEPTION_EN
        entry=next(e for e in guide['entries'] if e['id']=='city-assistant')
        old='Применяется к новым построенным и захваченным городам; уже существующие на момент начала партии или загрузки города не изменяются.'
        new='Применяется к стартовому городу новой партии, а также новым построенным и захваченным городам. При загрузке продолжающегося матча существующие города не открываются повторно; ручное закрытие ополчения сохраняется.'
        assert old in entry['bodyRu'];entry['bodyRu']=entry['bodyRu'].replace(old,new)
        old='It applies to newly built and captured cities; cities already present at match start or save load are unchanged.'
        new='It applies to the starting city of a new match, as well as newly built and captured cities. Loading an ongoing match does not reopen existing cities; later manual militia closure is respected.'
        assert old in entry['bodyEn'];entry['bodyEn']=entry['bodyEn'].replace(old,new)
        assert [e for e in guide['entries'] if e['id'] not in ('frequency','city-assistant')]==[e for e in source['entries'] if e['id'] not in ('frequency','city-assistant')]
        return guide

    def compose(self,replacements):
        feeds={}
        for key,before in self.baselines.items():
            schema,channel=key.split('/');feed=copy.deepcopy(before)
            actual=set()
            for p in feed['packages']:
                if p['id'] in replacements[channel]:
                    actual.add(p['id']);update=replacements[channel][p['id']]
                    for field in ('version','size','sha256','urls'):p[field]=copy.deepcopy(update[field])
            assert set(VERSIONS[channel])<=actual
            if schema=='v2':assert ROAM_ID in actual
            feed['patchGuide']=self.guide(before['patchGuide'])
            version=VERSIONS[channel]['pawpatch-core']
            entry=base.release_entry('release-patch-'+version+'.md',version,self.args.published_at[:10],'arcane-wars',channel)
            assert not any(e.get('category')=='patch' and e.get('version')==version for e in before['changelog'])
            feed['changelog']=[entry]+feed['changelog'];feed['publishedAt']=self.args.published_at
            for prop in ('launcher','game','modGames','modGuides','previousReleases'):
                assert feed.get(prop)==before.get(prop)
            assert [p for p in feed['packages'] if p['id'] not in actual]==[p for p in before['packages'] if p['id'] not in actual]
            self.sign(feed,schema,channel,'production')
            previous=self.out/'previous'/schema/(channel+'.signed.json');previous.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(self.source_path(schema,channel),previous);feeds[key]=feed
        assert feeds['v2/stable']['patchGuide']==feeds['v2/beta']['patchGuide']
        base.write(self.out/'changelog.history.json',{c:feeds['v2/'+c]['changelog'] for c in base.CHANNELS})
        base.write(self.out/'patch-guide.json',feeds['v2/beta']['patchGuide'])
        plan=[]
        for tag,assets in self.assets.items():
            notes=base.REPO/'docs'/('release-'+tag+'.md')
            plan.append(dict(tag=tag,version=tag.removeprefix('patch-'),prerelease='beta' in tag,makeLatest=False,assets=assets,notes=str(notes),notesSha256=base.sha(notes)))
        base.write(self.out/'release-plan.json',dict(published=False,launcherIncluded=False,releases=plan))
        assert len(plan)==2 and sum(len(r['assets']) for r in plan)==7
        assert all(base.sha(self.source_path(*key.split('/')))==value for key,value in self.before_hashes.items())
        base.write(self.out/'preparation.json',dict(published=False,signedCandidates=4,patchArchives=7,before=self.before_hashes,scope=self.scope,
            unchanged=['Vanilla','Immortals','all other roaming companies/profiles','localizations','game requirements','launcher metadata'],sourceScriptSha256=base.sha(Path(__file__))))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('out','dotnet','signing-dir','stable-helpers','beta-helpers'):p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--cache',type=Path,action='append',default=[]);p.add_argument('--published-at',required=True)
    args=p.parse_args();assert not args.out.exists();args.out.mkdir(parents=True)
    task=Preparation(args);task.load_sources();task.compose(task.prepare_packages())
    print('MAINTENANCE PREPARED: 2 releases, 7 archives, 4 signed candidates; no publication or game changes.')

if __name__=='__main__':main()
