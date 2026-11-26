"""Compiled river/AI regressions. Synthetic ABI fixtures, no game execution.
The common test fixture is loaded without running its separate baseline suite.
"""
from pathlib import Path
scope={'__file__':str(Path(__file__).with_name('test_ai.py')),'__name__':'bridge_ai_fixture'}
exec(compile(Path(scope['__file__']).read_text().split('\nfor image,cave in ')[0],scope['__file__'],'exec'),scope)
Fixture=scope['Fixture'];BASE=scope['BASE'];fb=scope['fb'];checks=[]
def check(name,value):
 assert value,name
 checks.append(name)
def points(f,y=48,x0=42,x1=55):
 p=0x20780000;values=[x|(y<<16) for x in range(x0,x1+1)]
 for i,v in enumerate(values):f.w(p+i*4,v)
 return p,len(values)
def valid(f,policy=False,y=48):
 p,n=points(f,y)
 return f.call('bridge_ai_river_check' if policy else 'bridge_check',[f.state,f.kingdom,p,n,100] if policy else [f.state,p,n])
def set_bed(f,value):
 hm=f.r(f.world+0x34);data=f.r(hm+0x40)
 for y in range(97):
  for x in range(46,51):f.f(data+(y*97+x)*4,value)
def shorten(f,lo,hi):
 for y in range(96):
  if lo<=y<=hi:continue
  for x in range(46,51):f.w(f.cell(x,y),f.grass);f.w(f.cell(x,y)+32,0x200)
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 suffix=hex(image)
 f=Fixture(image,cave);check('native river '+suffix,valid(f)==1 and valid(f,True)==1)
 for y in range(96):
  for x in range(46,51):f.w(f.cell(x,y),f.definition('arctic_lake01'))
 check('lake-named generated river '+suffix,valid(f)==1 and valid(f,True)==1)
 for y in range(96):
  for x in range(46,51):f.w(f.cell(x,y)+32,0x20)
 check('walkable stale water class '+suffix,valid(f)==0)
 f=Fixture(image,cave);set_bed(f,1)
 check('obstructing water flags on flat land '+suffix,valid(f)==0)
 f=Fixture(image,cave);shorten(f,42,54)
 check('short pond rejected by AI '+suffix,valid(f)==1 and valid(f,True)==0)
 f=Fixture(image,cave);shorten(f,40,95)
 check('too close to river end '+suffix,valid(f,True)==0)
 f=Fixture(image,cave);shorten(f,36,95)
 check('24-unit river-end margin '+suffix,valid(f,True)==1)
 f=Fixture(image,cave)
 for y in range(48,49):
  for x in range(46,51):f.w(f.cell(x,y),f.definition('temperate_swamp01'))
 check('wetland is not a river '+suffix,valid(f)==0)
 f=Fixture(image,cave);f.intent()
 check('allied pending crossing spacing '+suffix,valid(f,True)==0)
 f=Fixture(image,cave);site=f.danger;f.make_actor(site,300,f.enemy,97,145)
 f.w(site+4,f.definition('paws_bridge_wood_y_12'));f.f(site+0x2c,1)
 f.w(f.state+f.call('bridge_field',[1]),1);f.w(f.state+f.call('bridge_field',[2]),300)
 check('existing crossing spacing '+suffix,valid(f,True)==0)
 f.visible=False;check('new enemy bridge hidden by fog is not observed '+suffix,valid(f,True)==1);f.visible=True
 f.f(site+0x24,193)
 check('96-unit crossing spacing boundary '+suffix,valid(f,True)==1)
 f=Fixture(image,cave);coords=[]
 for i in range(1681):
  v=f.call('bridge_ai_sample_check',[i]);coords.append(((v&65535)-32,(v>>16)-32))
 check('spiral covers bounded square once '+suffix,len(set(coords))==1681 and max(max(abs(x),abs(y)) for x,y in coords)==20 and coords[0]==(0,0))
 check('spiral range guard '+suffix,f.call('bridge_ai_sample_check',[1681])==0xffffffff)
 f=Fixture(image,cave);f.w(f.army+0x820,0);f.run(30)
 check('idle engineer plans without army order '+suffix,f.count(2)==1)
 job=f.state+f.jobLayout[0];p0=f.r(job+44);pn=f.r(job+44+(f.r(job+32)-1)*4)
 check('normal native job spans opposite banks '+suffix,(p0&65535)<46 and (pn&65535)>50)
 f.w(f.builder+0xe8,f.enemy);f.tick(31)
 check('ownership change aborts intention '+suffix,f.count(4)==1 and f.r(job)==0)
 f=Fixture(image,cave);f.w(f.army+0x820,0);set_bed(f,1);f.run(30)
 check('idle engineer cannot build over flat flagged land '+suffix,f.count(2)==0)
 f=Fixture(image,cave);f.w(f.army+0x820,0);f.known=False;f.run(30)
 check('undiscovered rivers are not selected '+suffix,f.count(2)==0)
 f=Fixture(image,cave);f.w(f.army+0x820,0);f.f(f.r(f.kingdom+0x1cc),200);f.run(30)
 check('infrastructure still needs normal budget '+suffix,f.count(2)==0)
print('BRIDGE_AI_RIVERS_PASS',len(checks),'compiled checks at two relocations')
(scope['args'].out/'ai-rivers-result.json').write_text(scope['json'].dumps({'passed':True,'checks':checks,'liveGame':False,'networkPeers':False},indent=2))
