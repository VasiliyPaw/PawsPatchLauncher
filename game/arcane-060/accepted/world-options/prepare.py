"""Create only a new owned fixture from the accepted Arcane beta. No publication."""
import argparse,hashlib,json,re,shutil,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
def dec(p):
 b=Path(p).read_bytes();return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r','')
def emit(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(s.encode('utf-16'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cycle-seconds',type=int,choices=(30,600),default=600);a=ap.parse_args()
 source=a.source.resolve();out=a.out.resolve();cycle_seconds=a.cycle_seconds;game=out/'game'
 assert sha(source/'k2.exe')=='1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45'
 assert (source/'reconnect-test.marker').is_file(),'Only an owned source is allowed'
 if out.exists():assert not list(out.iterdir()),'Use a fresh output directory'
 else:out.mkdir()
 cache=Path('G:/PawHotJoinSharedArchives-20261107')
 def copy(src,dst):
  p=Path(src)
  if p.parent==source and p.name.lower() in ('data.rwd','music.rwd'):
   candidates=list(cache.glob('*-'+p.name));same=next((q for q in candidates if q.stat().st_size==p.stat().st_size and sha(q)==sha(p)),None)
   if same:
    if Path(dst).anchor.lower()==same.anchor.lower():os.link(same,dst)
    else:shutil.copy2(same,dst)
    return dst
  return shutil.copy2(src,dst)
 shutil.copytree(source,game,copy_function=copy,ignore=shutil.ignore_patterns('.pawpatch','Logs','*.log','*.dmp','*.mdmp'))
 (game/'.pawpatch').mkdir();shutil.copy2(source/'.pawpatch/state.json',game/'.pawpatch/state.json')
 (game/'reconnect-test.marker').write_text('Private world-options test only\n')
 (out/'Documents/Kohan2/data/User').mkdir(parents=True);(out/'AppData').mkdir()
 baseline={};changed={}
 def write(rel,text):
  p=game/rel
  if p.exists():baseline[rel]=sha(p)
  emit(p,text);changed[rel]=sha(p)
 rel='data/Game/world_rules_k2.tgi';t=dec(game/rel)
 assert 'paws_dynamic_sun' not in t
 # Add to the existing Sun enum, keeping every old value/index and its default.
 a=t.lower().index('ids = sun');b=t.index('\n}',a)
 block=t[a:b];block=re.sub(r'description\s*=\s*"[^"]*"','description = "#paws_day_description"',block,count=1,flags=re.I)
 t=t[:a]+block+'\n [EnumValue]\n ids = paws_dynamic_sun\n name = "#paws_day_dynamic"\n'+t[b:]
 t+='''\n[WorldRule Template=WorldRule]
{
 ids = PawsBiomes
 name = "#paws_biomes"
 description = "#paws_biomes_description"
 type = enum
 default = paws_all
 [EnumValue]
 ids = paws_all
 name = "#paws_biomes_all"
 [EnumValue]
 ids = paws_random
 name = "#paws_biomes_random"
}
[WorldRule Template=WorldRule]
{
 ids = PawsDayPhase
 name = ""
 type = int
 default = 0
 never_editable = true
}
'''
 write(rel,t)
 rel='data/Game/SVars.tgi';t=dec(game/rel);at=t.index('{')+1
 t=t[:at]+'\n int PawsBiomes = 0\n int PawsDayPhase = 0\n'+t[at:];write(rel,t)
 write('data/Sun/paws_dynamic_sun.tgi','''[Sun Template=Sun]
{
 ids = paws_dynamic_sun
 name = "#paws_day_dynamic"
 diffuse = 1,1,1
 ambient = 1,1,1
 specular = 0,0,0
}
''')
 rel='data/UI/Shared/random_map_dialog.tgi';t=dec(game/rel)
 # Three complete 30-unit rows plus viewport margins, with buttons unchanged.
 for name in ('MapPreviewPanel','ObjectsSlidersPanel'):
  at=t.index('['+name+']') if '['+name+']' in t else t.index('['+name+' ')
  end=t.index('\n\t}',at)+4;block=t[at:end]
  block,n=re.subn(r'B = \+239', 'B = +215',block,count=1);assert n==1
  t=t[:at]+block+t[end:]
 at=t.index('[WorldRulesPanel Inherit=WorldRulesPanel]');end=t.index('\n\t[SelectButton]',at);block=t[at:end]
 assert block.count('T = 572')==1 and block.count('B = +88')==1
 block=block.replace('T = 572','T = 548').replace('B = +88','B = +112')
 enum='\n\t\t[WorldRuleEnum]\n\t\t{\n\t\t\t[Dropdown]\n\t\t\t{\n\t\t\t\t[View]\n\t\t\t\tR = +150\n\t\t\t}\n\t\t}\n'
 endblock=block.rfind('\n\t}');assert endblock>=0;block=block[:endblock]+enum+block[endblock:]
 t=t[:at]+block+t[end:];write(rel,t)
 # Native WorldRules::Reset unlocks defaults; every other RMC must therefore
 # explicitly hide the mixed-only rule, including the random-map proxy.
 for path in sorted((game/'data/RandomMap').glob('*.tgi')):
  t=dec(path);starts=list(re.finditer(r'(?im)^\s*\[RMC\s',t));assert starts
  for i,m in reversed(list(enumerate(starts))):
   end=starts[i+1].start() if i+1<len(starts) else len(t)
   block=t[m.start():end];mixed=bool(re.search(r'(?im)^\s*ids\s*=\s*paws_mixed_biomes\s*$',block))
   at=block.rfind('}');assert at>=0
   rule=' [Rules]\n {\n  [Rule]\n  ids = PawsBiomes\n  default = paws_all\n  show_ui = '+('true' if mixed else 'false')+'\n }\n'
   t=t[:m.start()]+block[:at]+rule+block[at:]+t[end:]
  write(path.relative_to(game).as_posix(),t)
 languages=json.loads((HERE/'localization.json').read_text(encoding='utf-8'));tables={}
 if cycle_seconds==30:
  durations={'en':('10 game minutes','30 game seconds'),'ru':('10 игровых минут','30 игровых секунд'),'de':('10 Spielminuten','30 Spielsekunden'),'fr':('10 minutes de jeu','30 secondes de jeu'),'cs':('10 herních minut','30 herních sekund'),'uk':('10 ігрових хвилин','30 ігрових секунд')}
  for lang,(old,new) in durations.items():
   assert old in languages[lang]['paws_day_description'];languages[lang]['paws_day_description']=languages[lang]['paws_day_description'].replace(old,new)
 for lang,values in languages.items():
  assert set(values)==set(languages['en'])
  rel=('data/Localization' if lang=='en' else 'local_aw_'+lang+'/localization')+'/strings_data_K2.tgi';p=game/rel
  if not p.exists():
   # Preserve the complete accepted locale text table from the released package.
   import zipfile
   ws=HERE.parents[3];old=ws/'outputs/release-042-050-20261106/beta/assets'/('pawpatch-data-'+lang+'-0.5.0-beta.1.zip')
   with zipfile.ZipFile(old) as z:
    name=next(n for n in z.namelist() if n.lower()=='payload/'+rel.lower());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
  t=dec(p);assert not any(k+' =' in t for k in values)
  b=t.rfind('}');t=t[:b]+''.join(' '+k+' = '+json.dumps(v,ensure_ascii=False)+'\n' for k,v in values.items())+t[b:]
  write(rel,t);tables[lang]=dict(path=rel,sha256=sha(p))
  # A later Arcane locale layer replaces the entire table, rather than merging
  # individual strings. Keep its new rule labels in sync as well.
  for folder in sorted(game.glob('*')):
   if not folder.is_dir() or not folder.name.lower().startswith('local_aw_'+lang+'_'):continue
   override=folder/'Localization/strings_data_K2.tgi'
   if not override.is_file():continue
   text=dec(override);assert not any(k+' =' in text for k in values)
   at=text.rfind('}');assert at>=0
   text=text[:at]+''.join(' '+k+' = '+json.dumps(v,ensure_ascii=False)+'\n' for k,v in values.items())+text[at:]
   write(override.relative_to(game).as_posix(),text)
 (out/'preparation.json').write_text(json.dumps(dict(source=str(source),game=str(game),baseline=baseline,changed=changed,languages=tables,dynamicDayCycleSeconds=cycle_seconds),ensure_ascii=False,indent=2),encoding='utf-8')
 print('PRIVATE_WORLD_OPTIONS_DATA_READY',out,len(changed),'files')
if __name__=='__main__':main()
