"""Import an explicitly supplied bridge package into one marked private copy."""
from pathlib import Path
import argparse, hashlib, json, shutil, sys
from models import definitions, construction_effect

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--package',type=Path,required=True);a=p.parse_args()
r=a.out.resolve();pkg=a.package.resolve();assert (r/'installed-rivers.marker').is_file()
root=r/'sandbox/rivers-data';manifest=json.loads((pkg/'package-manifest.json').read_text())
def sha(data):return hashlib.sha256(data).hexdigest()
payload=[f for f in (pkg/'payload/data').rglob('*') if f.is_file()]
for f in payload:
    assert sha(f.read_bytes())==manifest[f.relative_to(pkg).as_posix()]['sha256']
integration=json.loads((pkg/'integration.json').read_text())
from models import bridge_balance
for style, variants in integration['raceVariants'].items():
    for material,key in [('wood','weak'),('stone','strong')]:
        hp,gold,resource,amount=bridge_balance(style,material);v=variants[key]
        assert (hp,gold,resource,amount)==(v['hp'],v['constructionGold'],v['upkeep']['resource'],v['upkeep']['amount'])
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from PrepareSplitLanguages import rwd_files
archive=None;originals={}
enclave=json.loads((pkg/'enclave-slaanri/manifest.json').read_text())
for name,row in enclave['models'].items():
    original=next((q.read_bytes() for q in [root/name,r/'sandbox/data'/name] if q.is_file()),None)
    if original is None:
        if archive is None:archive={k.lower():v for k,v in rwd_files((r/'sandbox/Data.rwd').read_bytes()).items()}
        original=archive[name.lower()]
    # Repeating the import is allowed only for this exact reviewed revision.
    assert sha(original) in [row['sourceSha256'],row['outputSha256']],(name,sha(original))
    assert sha((pkg/'payload/data'/name).read_bytes())==row['outputSha256']
    originals[name]=sha(original)
art=json.loads((r/'bridge-art.json').read_text());before={}
for f in payload:
    rel=f.relative_to(pkg/'payload/data');target=root/rel;target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_file():before[rel.as_posix()]=sha(target.read_bytes())
    shutil.copy2(f,target)
    parts=rel.parts
    if len(parts)==4 and parts[:2]==('Paws','Bridges') and f.suffix.lower()=='.nif':
        style=parts[2].lower();row=art['styles'][style][f.name]
        row['previousSha256']=row['sha256'];row['sha256']=sha(f.read_bytes());row['damageAnchorsPackageRevision']=7
(r/'bridge-art.json').write_text(json.dumps(art,indent=2))
things=root/'Special/Things/thing_visibilityactors.tgi';s=things.read_text(encoding='utf-16');s=s.split('[Template PawsBridge ')[0];things.write_text(s+definitions('ru',art['styles']),encoding='utf-16')
effects=root/'Effects/construction.tgi';s=effects.read_text(encoding='utf-16');cut=s.rfind('[VFX',0,s.index('IDS = paws_bridge_construction_raise_vfx'));effects.write_text(s[:cut]+construction_effect(),encoding='utf-16')
report={'passed':True,'packageRevision':7,'localOnly':True,'payloadFiles':len(payload),'payloadNif':sum(f.suffix.lower()=='.nif' for f in payload),'enclaveSourceHashes':originals,'previousOverlayHashes':before}
(r/'qa-evidence/package-import.json').write_text(json.dumps(report,indent=2));print('PACKAGE_IMPORTED',len(payload),'files;',report['payloadNif'],'NIF; approved balance and icons')
