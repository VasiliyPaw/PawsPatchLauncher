from context import *
def main():
 s=(WS/'work/ui-fullres-release-20261117/publish.py').read_text();a=s.index('def gate():');b=s.index('\ndef commit_files',a)
 s=s[:a]+'''def gate():
 unchanged();assert read(O/'verification.json')['passed'];assert read(O/'catalog-qa/result.json')['passed'];assert read(O/'live-result.json')['passed']and read(O/'live-cleanup.json')['passed'];assert read(O/'reader-result.json')['passed'];assert read(O/'terrain-merge.json')['unchangedQuality']
 for mod in['arcane','vanilla','immortals']:assert read(O/(mod+'-installer-result.json'))['passed']
 for p in read(O/'packages.json'):
  f=Path(read(O/'package-audit.json')[p['id']]['path']);assert sha(f)==p['sha256']and f.stat().st_size==p['size']
 for group in['arcane','pure']:
  b=read(O/group/'bundle.json');assert sha(b['path'])==b['sha256']
 print('COMPACT_RELEASE_GATE_PASS',flush=True)
''' +s[b:]
 s=s.replace("(5 if group=='arcane'else 4)","(6 if group=='arcane'else 4)").replace("[('arcane',5),('pure',4)]","[('arcane',6),('pure',4)]")
 s=s.replace('Preserve full-resolution HD icons and faction HUD frames across all patch betas','Pack resized HD UI resources without duplicate payloads and group terrain downloads').replace('Publish full-resolution HD UI in Arcane beta.4 and Vanilla/Immortals beta.8','Publish compact HD UI in Arcane beta.5 and Vanilla/Immortals beta.9')
 (P/'publish.py').write_text(s)
 s=(WS/'work/ui-fullres-release-20261117/public_client_check.py').read_text().replace('0.6.0-beta.4',ARC).replace('0.5.0-beta.8',PURE)
 s=s.replace('if(changed.Any(p=>p.StartsWith("arcane-biome-textures-")))throw new Exception("Terrain downloads changed");','if(mod==GameMod.ArcaneWars&&(selected.Count(p=>p.Id=="arcane-biome-textures")!=1||selected.Any(p=>p.Id.StartsWith("arcane-biome-textures-"))))throw new Exception("Terrain not grouped");')
 (P/'public_client_check.py').write_text(s);print('PUBLICATION_TOOLS_READY')
if __name__=='__main__':main()
