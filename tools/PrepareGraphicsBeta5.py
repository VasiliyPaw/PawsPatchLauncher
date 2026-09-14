"""Stage two immutable Arcane Wars Beta 5 archives and signed beta feeds only."""
import argparse, copy, json, shutil
from pathlib import Path
import PreparePatchChannels078 as base

VERSION='0.3.0-beta.5'
TAG='patch-'+VERSION
VERSIONS={'pawpatch-core':VERSION,'common-ui':'1.3.72-ui.5-beta.5'}
FIXES={'d3d9.dll':'94A0EC76C89F2122712C04D8F276E853C20670A0EEC000BC55F67DCC1E464E2E',
       'data/Units/Human/Ranger/RangerDie1.KF':'990CF3DDADD764A12126768FDEC606C8469A7C0C19AD55252F94301475A8A781'}

class Preparation(base.Preparation):
    def prepare(self):
        for schema in base.SCHEMAS:
            for channel in base.CHANNELS:
                path=self.source_path(schema,channel)
                key=schema+'/'+channel
                self.baselines[key]=self.verify_signed(path)
                self.before_hashes[key]=base.sha(path)
                assert self.baselines[key]['launcher']['version']=='0.7.12'
                previous=self.out/'previous'/schema/(channel+'.signed.json')
                previous.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,previous)
        source={p['id']:p for p in self.baselines['v2/beta']['packages']}
        assert source['pawpatch-core']['version']=='0.3.0-beta.4'
        updates={};scope=[]
        for id,version in VERSIONS.items():
            old=source[id];original=self.payload(old);files=copy.deepcopy(original)
            if id=='pawpatch-core':
                for path,digest in FIXES.items():
                    assert base.normalize(path) not in {base.normalize(p) for p in files}
                    data=(self.args.fixes/path).read_bytes()
                    assert base.sha_bytes(data)==digest
                    files[path]=data
                assert {p:b for p,b in files.items() if p not in FIXES}==original
            else:
                path=next(p for p in files if base.normalize(p)=='paws_patch_versions.ini')
                old_label=b'PawPatch=0.3.0-beta.4'
                assert files[path].count(old_label)==1
                files[path]=files[path].replace(old_label,b'PawPatch='+VERSION.encode())
                assert {p for p in files if files[p]!=original[p]}=={path}
            manifest=copy.deepcopy(self.audited[old['sha256'].upper()]['manifest'])
            assert not manifest.get('remove')
            manifest['version']=version
            manifest['files']=[dict(path=p,size=len(b),sha256=base.sha_bytes(b)) for p,b in sorted(files.items(),key=lambda item:item[0].lower())]
            blob=base.zip_bytes(manifest,files);assert blob==base.zip_bytes(manifest,files)
            archive=self.out/'assets'/(id+'-'+version+'.zip')
            archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(blob)
            package=copy.deepcopy(old)
            package.update(version=version,size=len(blob),sha256=base.sha_bytes(blob),urls=[base.DOWNLOADS+TAG+'/'+archive.name])
            self.register_asset(package,TAG,archive);self.audit_archive(package)
            assert self.payload(package)==files
            updates[id]=package
            scope.append(dict(id=id,sourceSha256=old['sha256'],sha256=package['sha256'],
                added={p:base.sha_bytes(b) for p,b in files.items() if p not in original},
                changed={p:dict(before=base.sha_bytes(original[p]),after=base.sha_bytes(b)) for p,b in files.items() if p in original and original[p]!=b}))
        entry=base.release_entry('release-'+TAG+'.md',VERSION,self.args.published_at[:10],'arcane-wars','beta')
        feeds={}
        for schema in base.SCHEMAS:
            before=self.baselines[schema+'/beta'];feed=copy.deepcopy(before)
            for p in feed['packages']:
                if p['id'] in updates:
                    assert p['sha256']==source[p['id']]['sha256']
                    for field in ('version','size','sha256','urls'):p[field]=copy.deepcopy(updates[p['id']][field])
            feed['changelog']=[entry]+before['changelog'];feed['publishedAt']=self.args.published_at
            self.sign(feed,schema,'beta','production')
            assert {k:v for k,v in feed.items() if k not in ('packages','changelog','publishedAt')}=={k:v for k,v in before.items() if k not in ('packages','changelog','publishedAt')}
            assert [p for p in feed['packages'] if p['id'] not in updates]==[p for p in before['packages'] if p['id'] not in updates]
            feeds[schema]=feed
        history=base.read(base.REPO/'feed/changelog.history.json')
        assert history['beta']==self.baselines['v2/beta']['changelog']
        history['beta']=feeds['v2']['changelog'];base.write(self.out/'changelog.history.json',history)
        notes=base.REPO/'docs'/('release-'+TAG+'.md')
        base.write(self.out/'release-plan.json',dict(tag=TAG,version=VERSION,prerelease=True,launcherIncluded=False,
            assets=self.assets[TAG],notes=str(notes),notesSha256=base.sha(notes)))
        base.write(self.out/'scope.json',scope)
        base.write(self.out/'preparation.json',dict(before=self.before_hashes,historyBefore=base.sha(base.REPO/'feed/changelog.history.json'),
            scope=scope,unchanged=['stable feeds','launcher','Vanilla','Immortals','game requirements','all other packages','all helper executables'],
            published=False,sourceScriptSha256=base.sha(Path(__file__))))
        assert all(base.sha(self.source_path(*key.split('/')))==digest for key,digest in self.before_hashes.items())
        print('BETA 5 PREPARED: two archives; two signed beta feeds; stable/launcher/other mods unchanged.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('out','dotnet','signing-dir','fixes'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cache',type=Path,action='append',default=[])
    p.add_argument('--published-at',required=True)
    args=p.parse_args();assert not args.out.exists();args.out.mkdir(parents=True)
    Preparation(args).prepare()
