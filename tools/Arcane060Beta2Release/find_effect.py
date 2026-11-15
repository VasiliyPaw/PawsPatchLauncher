from context import *
games=[FIX/'game',Path('G:/PawsWork/QA/Arcane060Beta2Net-20261115/client/game')];out=[]
for game in games:
 rows=[]
 for folder in ['data/Effects','rivers-data/Effects','local_ru/Effects','local_base_ru/Effects']:
  for f in(game/folder).rglob('*.tgi'):
   raw=f.read_bytes()
   try:s=raw.decode('utf-16')if raw[:2]in[b'\xff\xfe',b'\xfe\xff']else raw.decode('utf-8-sig')
   except UnicodeError:s=raw.decode('cp1252',errors='replace')
   if'blast_effect'in s.lower():
    lines=[line.strip()for line in s.splitlines()if'blast_effect'in line.lower()];rows.append(dict(path=f.relative_to(game).as_posix(),sha256=sha(f),lines=lines[:8]))
 out.append(dict(game=str(game),matches=rows));print(json.dumps(out[-1]),flush=True)
write(O/'blast-effect-investigation.json',out)
