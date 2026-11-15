"""Read simulation AND independently recomputed visual heights in marked QA."""
from pathlib import Path
import argparse,json,ctypes as C,struct,re
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--save',type=Path);p.add_argument('--pid',type=int);a=p.parse_args()
r=a.out.resolve();identity={'pid':a.pid} if a.pid else json.loads((r/'qa-process.json').read_text());base=int(re.findall(r'k2.exe at ([0-9A-F]+)',(r/'sandbox/Mods/plugins.log').read_text())[-1],16)
k=C.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[C.c_uint,C.c_int,C.c_uint];k.OpenProcess.restype=C.c_void_p;k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p];k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];k.CloseHandle.argtypes=[C.c_void_p]
h=k.OpenProcess(0x410,False,identity['pid']);assert h
buf=C.create_unicode_buffer(32768);size=C.c_uint(32768)
assert k.QueryFullProcessImageNameW(h,0,buf,C.byref(size)) and Path(buf.value).resolve()==(r/'sandbox/k2.exe').resolve()
def read(at,n):
 data=C.create_string_buffer(n);done=C.c_size_t();assert k.ReadProcessMemory(h,at,data,n,C.byref(done)) and done.value==n,hex(at);return data.raw
def u(at):return struct.unpack('<I',read(at,4))[0]
def f(at):return struct.unpack('<f',read(at,4))[0]
def xyz(at):return [round(v,4) for v in struct.unpack('<3f',read(at,12))]
try:
 rows=json.loads((r/'sandbox/Mods/bridge-state.json').read_text());reg=u(base+0x5ef72c)
 if a.pid:
  ids=set();slots=struct.unpack('<65536I',read(reg+0x20004,65536*4))
  for act in slots:
   if not act or u(act)!=base+0x4e5c58:continue
   org=u(act+0x7c);de=u(act+4);name=read(u(de+8),160).decode('utf-16le',errors='replace').split('\0')[0] if de else ''
   if org or name.startswith('paws_bridge_'):
    ids.add(u(act+0x14))
    if org and u(org+0x2c)<64:
     for j in range(u(org+0x2c)):
      member=u(u(org+0x28)+j*4)
      if member:ids.add(u(member+0x14))
  rows={'actors':[{'id':ident} for ident in ids],'time':f(u(base+0x5f3fb8)+0xe8)}
 ids={v['id'] for row in rows['actors'] for v in [row,*row.get('elements',[])]}
 plugin=(r/'sandbox/Mods/plugins.log').read_text();cave=int(re.findall(r'code ([0-9A-F]+)',plugin)[-1],16);meta=json.loads((r/'native/prototype.json').read_text());state=cave+meta['roadState']
 result={'ticks':u(state+0x10),'roadWorld':hex(u(state+0xc)),'time':rows['time'],'actors':[],'commands':[]}
 # Stable prefix of Roads: jobs (8*2092), road brush, bridge job fields.
 result['bridgeCache']={'world':hex(u(state+19316)),'count':u(state+19320),'spans':[{'id':u(state+19332+i*2092),'bounds':list(struct.unpack('<5f',read(state+19336+i*2092,20))),'direction':list(struct.unpack('<3f',read(state+19332+i*2092+2080,12))),'opened':u(state+19356+i*2092)}for i in range(min(u(state+19320),128))]}
 if 'bridge_route_layout' in meta['exports']:
  off,count=struct.unpack('<2I',read(cave+meta['exports']['bridge_route_layout'],8))
  assert count==9
  result['routing']=dict(zip(['memory','cells','stamp','busy','calls','expanded','queued','fallback','restoreCursor'],struct.unpack('<9I',read(state+off,36))))
 app=u(base+0x5f92a4)
 current=u(app+0x140) if app else 0
 session=u(base+0x5f3fe4);world=u(base+0x5f3fb8);result['sessionDiagnostic']={'sessionType':u(session+0xf0),'networkFlag':read(session+0x100,1)[0],'worldMode':u(world+0xd8) if world else None}
 result['kingdomStockpiles']=[]
 for i in range(u(world+0x154)):
  kingdom=u(u(world+0x150)+i*4)
  if not kingdom:continue
  count=u(kingdom+0x1d0)
  if count<=32:result['kingdomStockpiles'].append({'id':u(kingdom+0x14),'stockpile':list(struct.unpack('<%df'%count,read(u(kingdom+0x1cc),count*4)))})
 map_=u(world+0x30);raw=read(u(map_+0x28),u(map_+0x1c)*u(map_+0x20)*0x30);result['waterBodiesByTerrain']={}
 for i in range(0,len(raw),0x30):
  flags=struct.unpack_from('<I',raw,i+0x20)[0]
  if flags&0x70!=0x20:continue
  de=struct.unpack_from('<I',raw,i)[0];name=read(u(de+8),160).decode('utf-16le',errors='replace').split('\0')[0];key=name+':'+('linked' if raw[i+0x2c] else 'MISSING');result['waterBodiesByTerrain'][key]=result['waterBodiesByTerrain'].get(key,0)+1
 result['bodyRecords']={str(i):{'words':list(struct.unpack('<8I',read(u(u(map_+0x50)+i*4),32))),'floats':list(struct.unpack('<8f',read(u(u(map_+0x50)+i*4),32)))} for i in range(1,255) if u(u(map_+0x50)+i*4) and u(u(u(map_+0x50)+i*4)+4)}
 result['wetExamples']={}
 for i in range(0,len(raw),0x30):
  if struct.unpack_from('<I',raw,i+0x20)[0]&0x70!=0x20:continue
  de=struct.unpack_from('<I',raw,i)[0];name=read(u(de+8),160).decode('utf-16le',errors='replace').split('\0')[0]
  if name not in result['wetExamples']:result['wetExamples'][name]={'xy':[i//0x30%u(map_+0x1c),i//0x30//u(map_+0x1c)],'tail':list(struct.unpack_from('<2fI',raw,i+0x24))}
 result['currentInterface']=hex(u(current)-base) if current else None
 ui=rows.get('gameInterface',0)
 if ui:
  brush=u(ui+0xf0)
  if brush:
   de=u(brush+0x18);head=u(brush+0xc);entry=u(head) if head else 0;ghost=u(entry+0xc) if entry else 0
   result['ghost']={'entry':hex(entry),'offset':xyz(entry+0x14) if entry else None,'visualTarget':xyz(ghost+0x38) if ghost else None,'visualType':hex(u(ghost)-base) if ghost else None,'actor':hex(u(ghost+0x14)) if ghost else None,'flags':hex(u(ghost+0x54)) if ghost else None,'groundOffset':f(ghost+0x64) if ghost else None}
   result['brush']={'self':hex(brush),'type':hex(u(brush)-base),'valid':read(brush+0x30,1)[0],'position':xyz(brush+0x24),'direction':xyz(brush+0x34),'definition':read(u(de+8),120).decode('utf-16le',errors='replace').split('\0')[0] if de else None}
 db=u(base+0x5f3fb4);table=u(db+0x298)
 for index in range(39):
  de=u(table+index*4)
  if de:result['commands'].append({'index':index,'id':u(de+0xc),'component':u(de+0x18),'name':read(u(de+8),100).decode('utf-16le',errors='replace').split('\0')[0]})
 for ident in sorted(ids):
  act=u(reg+0x20004+4*(ident&65535))
  if not act or u(act+0x14)!=ident:continue
  body=u(act+0x60);view=u(act+0xc);data=u(act+4);name=read(u(data+8),160).decode('utf-16le',errors='replace').split('\0')[0]
  row={'id':ident,'name':name,'flags':hex(u(act+8)),'simulation':xyz(act+0x20),'direction':xyz(act+0x2c),'health':f(body+0x10) if body else None,'maxHealth':f(body+0x14) if body else None,'construction':bool(u(act+0x100)&0x200000),'actorStates':hex(u(act+0x100)),'economy':u(act+0x84),'availableCommands':hex(u(act+0xf0)),'components':{hex(off):hex(u(act+off)) for off in range(0x60,0xd8,4)}}
  row['movementMask']=hex(u(data+0x234))
  def command_record(cmd):
   de=u(cmd+8)
   return {'id':u(de+12) if de else None,'flags':hex(u(cmd+12)),'target':u(cmd+16),'point':xyz(cmd+24)[:2],'queued':read(cmd+60,1)[0]}
  mind=u(act+0x70)
  if mind:
   row['mindVtable']=hex(u(mind)-base);row['mindTeleportMethod']=hex(u(u(mind)+0x19c)-base)
   if u(mind+0x68)==base+0x4f4df0:row['nativeMove']={'active':u(mind+0x74),'target':u(mind+0x78),'point':xyz(mind+0x7c)[:2],'originalPoint':xyz(mind+0x84)[:2]}
   active=u(mind+0x10);active=u(active) if active else 0
   row['activeAiState']=hex(u(active)-base) if active else None
   if active:row['activeAiWords']=list(struct.unpack('<16I',read(active,64)));row['activeAiFloats']=list(struct.unpack('<16f',read(active,64)))
   cmd=u(mind+0x20);row['mindCommand']=command_record(cmd) if cmd else None
   node=u(mind+0x18);pending=[]
   while node and len(pending)<70:
    cmd=u(node)
    if cmd:pending.append(command_record(cmd))
    node=u(node+4)
   row['mindQueue']=pending
  cost_n=u(data+0x328);row['definitionCost']=list(struct.unpack('<%df'%cost_n,read(u(data+0x324),cost_n*4))) if 0<cost_n<=32 else []
  row['shapes']={hex(off):list(struct.unpack('<I5f',read(data+off,24))) for off in (0x38,0x50,0x68)}
  row['targetFlags']={'definition':hex(u(data+0x1b8)),'properties':hex(u(u(act+0x78)+0xd8)) if u(act+0x78) else None}
  instance=u(act+0x18)
  if instance:
   length=u(instance-12);assert length<32768
   row['instanceName']=read(instance,length*2).decode('utf-16le',errors='replace')
  if u(act+0x78):
   props=u(act+0x78);row['liveShapes']=[round(v,4) for v in struct.unpack('<24f',read(props+0x1c,96))]
   count=u(props+0xc4);listing=u(props+0xc0)
   if count<=64 and (not count or listing):row['periodicHealingAmounts']=[f(u(listing+i*4)+0xc) for i in range(count)]
  ai=u(act+0x70)
  if ai:row['aiCommandHandler']=hex(u(u(ai)+0x24)-base);row['aiConstructHandler']=hex(u(u(ai)+0xd0)-base)
  if ai:
   stateptr=u(ai+0x14);stateptr=u(stateptr) if stateptr else 0
   row['aiState']=hex(u(stateptr)-base) if stateptr else None
  ability=u(act+0x74)
  if ability:row['ability']={'targetId':u(ability+0x28),'current':hex(u(ability+0x34)),'state':read(ability+0x20,36).hex()}
  construction=u(act+0x9c)
  if construction:
   paid_n=u(construction+0x14);row['paidConstructionCost']=list(struct.unpack('<%df'%paid_n,read(u(construction+0x10),paid_n*4))) if 0<paid_n<=32 else []
  if body:row['bodyValues']=list(struct.unpack('<8f',read(body+0x10,32)))
  if view:row['visualTarget']=xyz(view+0x38);row['visualFlags']=hex(u(view+0x54));row['viewType']=hex(u(view)-base)
  result['actors'].append(row)
 if a.save:a.save.parent.mkdir(parents=True,exist_ok=True);a.save.write_text(json.dumps(result,indent=2))
 print(json.dumps(result,ensure_ascii=False))
finally:k.CloseHandle(h)
