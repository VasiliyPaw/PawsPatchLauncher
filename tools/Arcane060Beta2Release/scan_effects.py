from context import *
sys.path.insert(0,str(S/'tools/Pure050Release'));from rwd import entries
rows=[]
for name,raw in entries(FIX/'game/Data.rwd').items():
 if'blast_effect'.encode('utf-16le')in raw.lower()or b'blast_effect'in raw.lower():rows.append(dict(path=name,bytes=len(raw)));print('STOCK',name,flush=True)
for root in [FIX/'game',FIX/'Documents/Kohan2/data']:
 for folder in root.iterdir():
  if not folder.is_dir()or folder.name in ['.pawpatch','Logs']:continue
  for f in folder.rglob('*.tgi'):
   raw=f.read_bytes()
   if'blast_effect'.encode('utf-16le')in raw.lower()or b'blast_effect'in raw.lower():rows.append(dict(path=str(f),bytes=len(raw)));print('LOOSE',str(f),flush=True)
write(O/'effect-references.json',rows)
