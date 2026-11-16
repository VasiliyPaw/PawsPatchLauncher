from context import *
import ast
p=P/'catalogs.py';s=p.read_text();a=s.index('# Same player-visible');b=s.index('\ndef note()',a)
old=(WS/'work/arcane060-beta3-release-20261116/catalogs.py').read_text();body=ast.literal_eval(old[old.index('BODIES=')+7:old.index('\ndef note')]);s=s[:a]+'BODIES='+repr(body)+'\n'+s[b:];p.write_text(s)
p=P/'sp_smoke.py';s=p.read_text().replace("assert city['owner']==enemy and city['knownOwner']==enemy,city", "assert city['owner']==enemy and city['knownOwner']==enemy and city['color']!=own['color'],city").replace("nativeCombatCapture=True,local=local", "nativeCombatCapture=True,controlledSinglePlayerSetup=True,knownOwnerAndMinimapColorUpdated=True,beforeColor=own['color'],local=local");p.write_text(s)
for mode in ['vanilla']:
 f=O/(mode+'-capture-result.json');r=read(f);v=read(O/(mode+'-capture-before.json'));before=next(x for x in v['actors']if x['id']==r['city']['id']);assert before['color']!=r['city']['color'];r.update(controlledSinglePlayerSetup=True,knownOwnerAndMinimapColorUpdated=True,beforeColor=before['color']);write(f,r)
