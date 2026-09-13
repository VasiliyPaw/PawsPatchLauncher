"""Build reviewed, executable-independent Paw layers from verified local archives.

Run after PrepareModModes.py. Writes only local payloads/packages; never publishes.
"""
import argparse, json, re, zipfile
from pathlib import Path
from PrepareModModes import decode, norm, sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('candidate',type=Path);args=ap.parse_args()
    root=args.candidate.resolve(); feeds={c:json.loads((root/f'{c}.payload.json').read_text('utf-8')) for c in ('stable','beta')}
    cache={}
    def read(p):
        key=p['sha256'];archive=Path(p['urls'][0]);assert archive.is_file()
        if key in cache:return cache[key]
        assert sha(archive.read_bytes())==key.upper()
        with zipfile.ZipFile(archive) as z:
            manifest=json.loads(z.read('module.json'));assert manifest['id']==p['id'] and manifest['version']==p['version']
            names={norm(n):n for n in z.namelist()}
            data={norm(f['path']):z.read(names['payload/'+norm(f['path'])]) for f in manifest['files']}
            assert all(sha(data[norm(f['path'])])==f['sha256'].upper() and len(data[norm(f['path'])])==f['size'] for f in manifest['files'])
            cache[key]=(data,manifest);return data,manifest
    packages={p['id']:p for p in feeds['stable']['packages']}
    aw=read(packages['arcane-wars'])[0];core=read(packages['pawpatch-core'])[0]
    common=read(packages['common-ui'])[0];ru=read(packages['aw-localization-ru'])[0]
    text=lambda b:decode(b).replace('\r','')
    template='data/templates/template_rmc_k2.tgi';patched=text(core[template])
    major=r'\[Kingdom[^\]]*RMCKingdomMajor\][^{]*\{[^}]*\}'
    teams=r'\[Team\]\s*IDS[^\n]+\s*name[^\n]+'
    maps=r'\[MapSize\]\s*width[^\n]+\s*height[^\n]+\s*recommended_kingdoms_min[^\n]+\s*recommended_kingdoms_max[^\n]+'
    def transform(data):
        result=text(data)
        for pattern,old_count,new_count in [(major,8,16),(teams,4,8),(maps,10,12)]:
            before=list(re.finditer(pattern,result,re.I));after=list(re.finditer(pattern,patched,re.I))
            assert len(before)==old_count and len(after)==new_count,(pattern,len(before),len(after))
            # Existing kingdom names retain the language of the source. Only map limits change.
            replacement=[m.group() for m in after] if pattern==maps else [m.group() for m in before]+[m.group() for m in after[old_count:]]
            for index in reversed(range(old_count)):
                b=before[index];r=replacement[index]
                if index==old_count-1:r+='\n\n\t'+'\n\n\t'.join(replacement[old_count:])
                result=result[:b.start()]+r+result[b.end():]
        assert 'paws_war_' not in result and 'string sun' not in result
        return result.encode('utf-8')
    base={p:b for p,b in common.items() if p.startswith('data/organizations/banners/')}
    assert len(base)==14
    for path,key,old,new in [('data/game/svars.tgi','KingdomsMax',8,16),('data/avars.tgi','MultiplayerMaxNumPlayers',12,16)]:
        original=text(aw[path]);wanted,n=re.subn(rf'({key}\s*=\s*){old}\b',rf'\g<1>{new}',original)
        assert n==1
        base[path]=wanted.encode('utf-8')
    hotkey='data/localization/hotkeys/actions/hotkeys_visual_dvorak_k2.txt'
    base[hotkey]=core[hotkey]
    # The default string table includes names for kingdoms 9–16 and teams 5–8.
    # Russian has its own table supplied by aw-localization-ru.
    base['data/localization/strings_data_k2.tgi']=core['data/localization/strings_data_k2.tgi']
    releases=[]
    for id,source in [('pawpatch-data',aw),('pawpatch-data-ru',{**aw,**ru})]:
        files={**base,template:transform(source[template])};version='1.3.72-data.1'
        archive=root/'packages'/f'{id}-{version}.zip'
        manifest={'id':id,'version':version,'files':[{'path':p,'size':len(b),'sha256':sha(b)} for p,b in sorted(files.items())],'remove':[]}
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('module.json',json.dumps(manifest))
            for p,b in sorted(files.items()):z.writestr('payload/'+p,b)
        releases.append({'id':id,'version':version,'priority':900,'executableIndependent':True,'required':False,'size':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'urls':[str(archive)],'dependsOn':['arcane-wars'],'name':{'ru':"Paw's Patch · файловые изменения",'en':"Paw's Patch · file changes"}})
    safe={'arcane-wars','startup-base','aw-localization-ru','aw-siege-balance','aw-powers-disabled','pawpatch-data','pawpatch-data-ru'}
    safe.update(p for p in packages if p.startswith('aw-roaming-'))
    evidence=[]
    for channel,feed in feeds.items():
        feed['packages']=[p for p in feed['packages'] if p['id'] not in ('pawpatch-data','pawpatch-data-ru')]+releases
        for p in feed['packages']:
            p['executableIndependent']=p['id'] in safe
            if p['executableIndependent']:
                data,manifest=read(p)
                assert not any(Path(n).suffix.lower() in ('.exe','.dll','.asi','.com','.cmd','.bat','.ps1') for n in list(data)+manifest.get('remove',[]))
                evidence.append({'channel':channel,'id':p['id'],'files':len(data),'sha256':p['sha256']})
        (root/f'{channel}.payload.json').write_text(json.dumps(feed,ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'data-only-audit.json').write_text(json.dumps(evidence,indent=2))
    print('DATA-ONLY PACKAGES VERIFIED:',len(evidence),'entries; base layers:',[(p['id'],len(read(p)[0])) for p in releases])

if __name__=='__main__':main()
