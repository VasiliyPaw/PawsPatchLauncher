"""Copy reviewed bridge art into a marked candidate, preserving its sources."""
from pathlib import Path
import hashlib,json,shutil
from depth import repair

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def apply_art(out, target):
    config=out/'bridge-art-inputs.json'
    if not config.exists():return {}
    inputs=json.loads(config.read_text(encoding='utf-8'))
    previous=json.loads((out/'bridge-art.json').read_text()) if (out/'bridge-art.json').exists() else {}
    bridge_root=target/'Paws/Bridges';bridge_root.mkdir(parents=True,exist_ok=True)
    report={'core':{},'styles':{},'sources':{}}
    core=Path(inputs['core']);selection=json.loads((core/'selection-manifest.json').read_text())
    assert selection['passed'] and len(selection['variants'])==112
    original=json.loads((out/'bridge-model-manifest.json').read_text())
    for name,row in selection['variants'].items():
        assert row['visibleGeometryUnchanged'] and row['sourceSha256'].lower()==original[name]['sha256'].lower()
        assert sha(core/name)==row['sha256']
        shutil.copy2(core/name,bridge_root/name)
    report['core']=selection
    for style in ('undead','shadow','human','gauri','drauga','haroun'):
        if style not in inputs:continue
        source=Path(inputs[style]);manifest=json.loads((source/'manifest.json').read_text())
        tests=json.loads((source/'model-tests.json').read_text())
        assert tests['passed'] and tests['variants']==112 and not tests['partialPrototype']
        assert len(manifest['variants'])==112
        source_models=source/'Paws/Bridges'/style.title()
        overlay=Path(inputs[style+'Selection']) if style+'Selection' in inputs else None
        selection=json.loads((overlay/'selection-manifest.json').read_text()) if overlay else None
        if selection:assert selection['passed'] and len(selection['variants'])==112
        destination=bridge_root/style.title();destination.mkdir(exist_ok=True)
        variants={}
        for name,row in manifest['variants'].items():
            assert sha(source_models/name)==row['sha256']
            selected=selection['variants'][name] if selection else row
            if selection:assert selected['sourceSha256']==row['sha256'] and selected['visibleGeometryUnchanged']
            path=(overlay if overlay else source_models)/name
            assert sha(path)==selected['sha256']
            prior=previous.get('styles',{}).get(style,{}).get(name,{})
            cached=prior.get('depthState',{})
            if (prior.get('sourceArtSha256')==selected['sha256'] and cached.get('comparison')=='LESS_EQUAL'
                and cached.get('depthTest') and cached.get('depthWrite') and (destination/name).exists()
                and sha(destination/name)==prior.get('sha256')):
                depth=cached
            else:
                shutil.copy2(path,destination/name)
                depth=repair(destination/name)
            variants[name]={**row,'sourceArtSha256':selected['sha256'],'sha256':depth['sha256'],'depthState':depth}
        for name,row in manifest['textures'].items():
            assert sha(source_models/name)==row['sha256']
            shutil.copy2(source_models/name,destination/name)
        report['styles'][style]=variants
        report['sources'][style]={'path':str(source.resolve()),'manifestSha256':sha(source/'manifest.json'),'tests':tests,'textures':manifest['textures'],'selection':selection}
        print('BRIDGE_ART_STYLE_READY',style,len(variants),flush=True)
    (out/'bridge-art.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report['styles']
