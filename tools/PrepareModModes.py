"""Offline standalone Arcane Wars layers. Verified inputs; never uploads or edits live game files.

The old release uses inverse overlays over the combined core. This builder applies
only those reviewed feature deltas to Arcane Wars, preserving its other values.
"""
import argparse, base64, copy, difflib, hashlib, json, re, zipfile, mmap, struct
from pathlib import Path
from GameplayPresentationData import MAELSTROM, maelstrom_cost

def norm(p): return p.replace('\\', '/').lower()
def sha(b): return hashlib.sha256(b).hexdigest().upper()
def decode(b):
    if b.startswith((b'\xff\xfe', b'\xfe\xff')): return b.decode('utf-16')
    try: return b.decode('utf-8-sig')
    except UnicodeDecodeError: return b.decode('cp1251')
def lines(b): return decode(b).replace('\r\n', '\n').splitlines()

def feature_delta(before, after, original, path):
    """Apply exact, unambiguous line edits, allowing only surrounding whitespace drift."""
    a, b, result = ([s for s in lines(data) if s.strip()] for data in (before, after, original))
    aa, bb = [s.strip() for s in a], [s.strip() for s in b]
    edits = [op for op in difflib.SequenceMatcher(None, aa, bb, autojunk=False).get_opcodes() if op[0] != 'equal']
    mapped = []
    current = [s.strip() for s in result]
    for tag, i, j, k, l in edits:
        matches = []
        # Resolve duplicates with adjacent unchanged context. Refuse guesses.
        for context in (64,32,16,8,4,3,2,1):
            left, right = max(0, i-context), min(len(a), j+context)
            needle = aa[left:right]
            matches = [pos+i-left for pos in range(len(current)-len(needle)+1) if current[pos:pos+len(needle)] == needle]
            if len(matches) == 1: break
        if len(matches) != 1 and i != j:
            needle = aa[i:j]
            matches = [pos for pos in range(len(current)-len(needle)+1) if current[pos:pos+len(needle)] == needle]
        if len(matches) != 1: raise ValueError(f'Ambiguous feature delta: {path}: {tag} {a[i:j]!r} -> {b[k:l]!r}')
        pos = matches[0]
        mapped.append((pos,pos+j-i,b[k:l]))
    assert all(a[1]<=b[0] for a,b in zip(mapped,mapped[1:])),path
    for start,end,replacement in reversed(mapped):result[start:end]=replacement
    return ('\r\n'.join(result)+'\r\n').encode('utf-8') if edits else original

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repository',type=Path,required=True,help='Existing verified release archive cache')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--helpers',type=Path,required=True)
    ap.add_argument('--base-game',type=Path,required=True,help='Read-only Data.rwd for stock settlement camps')
    args=ap.parse_args(); repo=args.repository.resolve(); out=args.output.resolve()
    assert not out.is_relative_to(repo/'feed'), 'Never overwrite public feeds'
    out.mkdir(parents=True,exist_ok=True)
    stable=json.loads(base64.b64decode(json.loads((repo/'feed/stable.json').read_bytes())['payload']))
    roots=[repo/'packages']+list(repo.glob('release_workspace_*/packages'))+[repo/'release_workspace_056/combination-fix/packages',repo/'release_workspace_056/powers-shards/packages',repo/'release_workspace_059/components-v2/packages']
    archive_paths={}; modules={}
    def read(p):
        name=p['urls'][0].split('/')[-1]
        archive=next((r/name for r in roots if (r/name).is_file() and (r/name).stat().st_size==p['size'] and sha((r/name).read_bytes())==p['sha256'].upper()),None)
        if archive is None: raise ValueError('Missing verified archive: '+name)
        archive_paths[p['id']]=str(archive)
        with zipfile.ZipFile(archive) as z:
            manifest=json.loads(z.read('module.json')); names={norm(n):n for n in z.namelist()}
            assert manifest['id']==p['id'] and manifest['version']==p['version'] and not manifest.get('remove')
            data={norm(f['path']):z.read(names['payload/'+norm(f['path'])]) for f in manifest['files']}
            assert all(len(data[norm(f['path'])])==f['size'] and sha(data[norm(f['path'])])==f['sha256'].upper() for f in manifest['files'])
            return data
    for p in stable['packages']: modules[p['id']]=read(p)
    aw=modules['arcane-wars']; core=modules['pawpatch-core']
    # Remove localization indirection from both sides of feature diffs. This
    # prevents an English standalone option from accidentally depending on core strings.
    english=dict(re.findall(r'^\s*(awloc_[A-Za-z0-9_]+)\s*=\s*"([^"\r\n]*)"',decode(core['data/localization/strings_data_k2.tgi']),re.M))
    def plain(data):
        s=decode(data)
        return re.sub(r'"#(awloc_[A-Za-z0-9_]+)"',lambda m:'"'+english[m[1]]+'"',s).encode('utf-8')
    base_rwd={norm('data/'+p.relative_to(repo/'release_workspace_20260905/baseline_rwd').as_posix()):p.read_bytes() for p in (repo/'release_workspace_20260905/baseline_rwd').rglob('*') if p.is_file()}
    with args.base_game.open('rb') as source,mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ) as data:
        assert data[:4]==b'TGCK'
        def stock_file(relative):
            needle=relative.encode('utf-16-le');index=data.find(needle)
            assert index>=0 and data.find(needle,index+1)<0,relative
            start,length=struct.unpack_from('<QQ',data,index+len(needle))
            start+=30 # TGCK offsets are relative to the payload following the 30-byte archive header.
            assert 30<=start<index and 0<length<100000 and start+length<index,relative
            return data[start:start+length]
        # Validate the RWD record interpretation against all previously extracted stock lairs.
        for path,expected in base_rwd.items():
            relative='Buildings/LairsMonster/'+path.split('/')[-1]
            assert stock_file(relative)==expected,relative
        for name in ('bandit','barbarian','rhaksha','slaan'):
            relative=f'Buildings/Camps/{name}_settlementcamp.tgi'
            base_rwd[norm('data/'+relative)]=stock_file(relative)
    def baseline(path):
        if path in aw:return aw[path]
        if path in base_rwd:return base_rwd[path]
        raise ValueError('No original game baseline for '+path)
    standalone={}; priorities={}; evidence=[]
    def delta_module(id,before,after,priority):
        result={}
        for path,a in before.items():
            b=after.get(path,a)
            if lines(plain(a)) == lines(plain(b)):continue
            original=baseline(path)
            result[path]=feature_delta(plain(a),plain(b),plain(original),path)
            evidence.append({'module':id,'path':path,'baseSha256':sha(original),'resultSha256':sha(result[path])})
        standalone[id]=result; priorities[id]=priority
    delta_module('aw-siege-balance',modules['siege-balance-standard'],core,600)
    # The fifth engine remains an optional siege-balance change, never base AW.
    standalone['aw-siege-balance'][MAELSTROM]=maelstrom_cost(baseline(MAELSTROM))
    delta_module('aw-powers-disabled',modules['powers-shards-original'],core,450)
    # Shard-free artwork belongs to the Powers/Shards switch, not the base patch.
    standalone['aw-powers-disabled'].update({p:b for p,b in core.items() if p.startswith('skins/') and p.endswith('economybar.png')})
    off=modules['roaming-profile-standard-no-new']
    for spawn,new,overlay in [('standard',True,'roaming-profile-standard-with-new'),('x2',True,'roaming-profile-x2-with-new'),('x2',False,'roaming-profile-x2-no-new'),('x4',True,None),('x4',False,'roaming-profile-x4-no-new')]:
        enabled={**core,**(modules[overlay] if overlay else {})}
        delta_module(f'aw-roaming-{spawn}-'+('new' if new else 'original'),off,enabled,500)
    # Families need dedicated minor kingdoms. Keep the original random-map
    # rules/spawners; copy only the kingdom declarations used by the runtime.
    path='data/templates/template_rmc_k2.tgi'
    def kingdoms(text):
        spans=[]
        for m in re.finditer(r'(?m)^\s*\[Kingdom Template=RMCKingdomMinor\]',text):
            brace=text.index('{',m.end());depth=1;end=brace+1
            while depth:
                depth+=(text[end]=='{')-(text[end]=='}');end+=1
            spans.append((m.start(),end))
        return spans
    original=decode(aw[path]); patched=decode(core[path]); old=kingdoms(original); new=kingdoms(patched)
    assert old and new and len(new)>len(old)
    result=original
    for start,end in reversed(old):result=result[:start]+result[end:]
    result=result[:old[0][0]]+'\n'.join(patched[a:b] for a,b in new)+result[old[0][0]:]
    assert 'string sun' not in result and 'paws_war_barbarian' in result
    assert result.count('[Kingdom Template=RMCKingdomMajor]')==original.count('[Kingdom Template=RMCKingdomMajor]')==8
    standalone['aw-hostility']={path:result.encode('utf-8'),'data/localization/strings_data_k2.tgi':core['data/localization/strings_data_k2.tgi']}
    priorities['aw-hostility']=100
    standalone['aw-runtime']={p.name:p.read_bytes() for p in args.helpers.glob('k2_aw_*.exe')};assert len(standalone['aw-runtime'])==8
    priorities['aw-runtime']=300
    standalone['aw-player-colors']={p:b for p,b in modules['player-colors'].items() if not p.endswith('.exe')}
    priorities['aw-player-colors']=400
    # Build a translation-only layer from original AW. Its inverse must be byte
    # identical. Apply the same string mapping to standalone option data, so
    # selected options cannot undo translation at their higher priority.
    def localize(path,data):
        if not path.endswith('.tgi'):return data
        s=decode(data); before=s
        for key in set(re.findall(r'#(awloc_[A-Za-z0-9_]+)',decode(core.get(path,b'')))):
            literal='"'+english[key]+'"';s=s.replace(literal,'"#'+key+'"')
        return s.encode('utf-8') if s!=before else data
    translation=dict(modules['localization-ru'])
    translation['data/localization/strings_data_k2.tgi']=core['data/localization/strings_data_k2.tgi']
    for path,b in aw.items():
        changed=localize(path,b)
        if changed!=b:translation[path]=changed
    standalone['aw-localization-ru']=translation;priorities['aw-localization-ru']=200
    for id,files in standalone.items():
        if id.startswith('aw-roaming-') or id in ('aw-siege-balance','aw-powers-disabled'):
            for path,b in list(files.items()):files[path]=localize(path,b)
            files['data/localization/strings_data_k2.tgi']=core['data/localization/strings_data_k2.tgi']
    # No cross-feature gameplay collisions (the common English dictionary is identical).
    groups=[('aw-siege-balance','aw-powers-disabled'),('aw-hostility','aw-powers-disabled'),('aw-hostility','aw-siege-balance')]
    groups += [(r,o) for r in standalone if r.startswith('aw-roaming-') for o in ('aw-siege-balance','aw-powers-disabled','aw-hostility')]
    for x,y in groups:
        assert all(standalone[x][p]==standalone[y][p] for p in standalone[x].keys()&standalone[y].keys()),(x,y)
    releases=[];(out/'packages').mkdir(exist_ok=True)
    for id,files in standalone.items():
        version='1.0.0-local.1';archive=out/'packages'/f'{id}-{version}.zip'
        manifest={'id':id,'version':version,'files':[{'path':p,'size':len(b),'sha256':sha(b)} for p,b in sorted(files.items())],'remove':[]}
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('module.json',json.dumps(manifest))
            for p,b in sorted(files.items()):z.writestr('payload/'+p,b)
        releases.append({'id':id,'version':version,'priority':priorities[id],'required':False,'experimental':False,'size':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'urls':[str(archive)],'dependsOn':['arcane-wars'],'name':{'ru':id,'en':id},'description':{'ru':'Отдельный компонент Arcane Wars','en':'Standalone Arcane Wars component'}})
    for channel in ('stable','beta'):
        feed=json.loads(base64.b64decode(json.loads((repo/f'feed/{channel}.json').read_bytes())['payload']))
        for p in feed['packages']:
            read(p);p['urls']=[archive_paths[p['id']]]
        feed['packages']+=releases
        feed['launcher']={'version':'0.0.0','size':0,'sha256':'','urls':[]}
        feed['previousReleases']=[]
        (out/f'{channel}.payload.json').write_text(json.dumps(feed,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'composition-audit.json').write_text(json.dumps({'published':False,'arcaneBase':next(p['sha256'] for p in stable['packages'] if p['id']=='arcane-wars'),'layers':{id:len(files) for id,files in standalone.items()},'edits':evidence},indent=2))
    print('Prepared standalone layers:',{id:len(files) for id,files in standalone.items()})

if __name__=='__main__':main()
