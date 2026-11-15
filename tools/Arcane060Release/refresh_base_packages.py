from release_context import *
import zipfile
packages=read(O/'packages.json');audit=read(O/'package-audit.json');helpers=read(O/'helpers/build-report.json');used=set();fixed=0
for q in packages:
 if q['id'].startswith('arcane-biome-'):
  q['description'].update(uk='Плавні переходи між біомами та кольорами дна.',cs='Plynulé přechody mezi biomy a barvami dna.',de='Weiche Übergänge zwischen Biomen und Gewässerböden.',fr='Transitions douces entre les biomes et les fonds aquatiques.');continue
 path=Path(audit[q['id']]['path'])
 with zipfile.ZipFile(path)as z:
  module=json.loads(z.read('module.json'));files={row['path']:z.read('payload/'+row['path'])for row in module['files']}
 for rel in files:
  leaf=Path(rel).name
  if leaf in helpers:files[rel]=(O/'helpers'/leaf).read_bytes();used.add(leaf)
  if rel.startswith('rivers-data/Paws/Bridges/RacialBuild/undead/finish_')and rel.endswith('.nif'):
   files[rel]=(R/'sandbox'/rel).read_bytes();fixed+=1
 if q['id']=='pawpatch-core':
  startup=files['startup/autoexec.txt'];files['startup-optimizations.enabled']=b'Arcane 0.6.0: memory, trim, tokens, fields; native font cache\n'
  rel='rivers-data/Localization/paws_060.tgi';text=files[rel].decode('utf-16');blocks=text.strip().split('\n\n');assert len(blocks)==6
  files[rel]=('\n\n'.join([b for b in blocks if not b.startswith('[Text language = Default]')]+[b for b in blocks if b.startswith('[Text language = Default]')])+'\n').encode('utf-16')
 if q['id']=='common-ui':
  # Text localization owns an earlier copy of autoexec (priority 200).
  # The common UI module (900) selects this complete feature mount last.
  files['startup/autoexec.txt']=startup
 module['files']=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())]
 temp=path.with_suffix('.new')
 with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in [('module.json',encode(module))]+[('payload/'+n,b)for n,b in sorted(files.items())]:
   info=zipfile.ZipInfo(n,(2026,11,15,0,0,0));info.compress_type=zipfile.ZIP_STORED if n.lower().endswith('.png')else zipfile.ZIP_DEFLATED;z.writestr(info,b)
 temp.replace(path);q.update(size=path.stat().st_size,sha256=sha(path));validate_package(path,q);audit[q['id']].update(size=q['size'],sha256=q['sha256']);print('REFRESHED',q['id'],q['sha256'],flush=True)
assert len(used)==8 and fixed==56
write(O/'packages.json',packages);write(O/'package-audit.json',audit)
