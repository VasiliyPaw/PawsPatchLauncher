"""Read-only, exact-private-process bridge AI observation."""
from pathlib import Path
import argparse,ctypes as C,json,re,struct
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--save',type=Path);p.add_argument('--brief',action='store_true');a=p.parse_args();r=a.out.resolve()
identity=json.loads((r/'qa-process.json').read_text());log=(r/'sandbox/Mods/plugins.log').read_text();base=int(re.findall(r'k2.exe at ([0-9A-F]+)',log)[-1],16);cave=int(re.findall(r'bridges: READY \d+ hooks, code ([0-9A-F]+)',log)[-1],16)
m=json.loads((r/'native/prototype.json').read_text());k=C.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[C.c_uint,C.c_int,C.c_uint];k.OpenProcess.restype=C.c_void_p;k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p];k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];k.CloseHandle.argtypes=[C.c_void_p]
h=k.OpenProcess(0x410,False,identity['pid']);assert h;name=C.create_unicode_buffer(32768);length=C.c_uint(32768);assert k.QueryFullProcessImageNameW(h,0,name,C.byref(length))and Path(name.value).resolve()==(r/'sandbox/k2.exe').resolve()
def read(at,n):
 data=C.create_string_buffer(n);done=C.c_size_t();assert k.ReadProcessMemory(h,at,data,n,C.byref(done))and done.value==n,hex(at);return data.raw
def u(at):return struct.unpack('<I',read(at,4))[0]
def f(at):return struct.unpack('<f',read(at,4))[0]
def text(definition):return read(u(definition+8),160).decode('utf-16le',errors='replace').split('\0')[0]if definition and u(definition+8)else ''
def position(actor):return struct.unpack('<3f',read(actor+0x20,12))
try:
 world=u(base+0x5f3fb8);state=cave+m['roadState'];layout=struct.unpack('<5I',read(cave+m['exports']['bridge_ai_layout'],20));ai=state+layout[0]
 result={'pid':identity['pid'],'time':f(world+0xe8)if world else None,'planning':u(ai+8),'plannerCompany':u(ai+12),'plannerSource':u(ai+16),'plannerTarget':u(ai+20),'sample':u(ai+36),'samples':u(ai+40),'bestCount':u(ai+44),'sourceXY':struct.unpack('<2f',read(ai+192,8)),'goalXY':struct.unpack('<2f',read(ai+200,8)),'baseline':f(ai+208),'counts':dict(zip(['scans','candidates','accepted','finished','aborted','duplicates','budgetRejected','dangerRejected','unknownPaths','guardedCommands','resumed'],struct.unpack('<11I',read(ai+layout[4],44)))),'projects':[],'players':[],'actors':[],'nearbyNonOwned':[]}
 diag=struct.unpack('<3I',read(cave+m['exports']['bridge_ai_diagnostics'],12));result['lastSAICommand']=text(u(ai+diag[2]));result['abortReason']=u(ai+diag[2]+4);result['refusals']=struct.unpack('<8I',read(ai+diag[0],32));result['lastCandidate']=struct.unpack('<4f',read(ai+diag[1],16))
 for i in range(96):
  q=ai+layout[2]+i*layout[3]
  if u(q):result['projects'].append({'record':i,'kingdom':u(q),'worker':u(q+4),'site':u(q+8),'slot':u(q+12),'xy':struct.unpack('<2f',read(q+36,8)),'next':f(q+44),'cooldown':f(q+48),'started':f(q+52),'progress':f(q+56),'health':f(q+60)})
 sai=u(base+0x5f3fc8);n=u(sai+0x70)if sai else 0;assert n<=96;owners=set()
 for i in range(n):
  pl=u(u(sai+0x6c)+i*4)
  if not pl:continue
  kingdom=u(pl+8);engine=u(pl+0xc)
  if not kingdom:continue
  owners.add(kingdom);nr=u(kingdom+0x1d0);assert nr<=32;row={'pl':pl,'kingdom':kingdom,'id':u(kingdom+0x14),'engine':engine,'stock':struct.unpack('<%df'%nr,read(u(kingdom+0x1cc),nr*4)),'production':struct.unpack('<%df'%nr,read(u(kingdom+0x1a8),nr*4)),'upkeep':struct.unpack('<%df'%nr,read(u(kingdom+0x1c0),nr*4)),'goals':[],'owned':[]}
  node=u(pl+0x2c);j=0
  while node and j<4096:
   sa=u(node);row['owned'].append({'id':u(sa+8),'goal':u(sa+0x10)});node=u(node+4);j+=1
  table=u(engine+8)if engine else 0
  if table:
   for typ in range(23):
    lists=u(table+typ*4)
    if not lists:continue
    for status in range(3):
     node=u(lists+status*8);j=0
     while node and j<4096:
      goal=u(node)
      if goal and u(goal+4)==engine and f(goal+0x38)>0:row['goals'].append({'type':hex(u(goal)-base),'state':u(goal+8),'priority':f(goal+0x38),'target':u(goal+0x4c),'xy':struct.unpack('<2f',read(goal+0x48,8))})
      node=u(node+4);j+=1
  result['players'].append(row)
 reg=u(base+0x5ef72c);slots=struct.unpack('<65536I',read(reg+0x20004,0x40000))if reg else []
 for actor in slots:
  if not actor or u(actor)!=base+0x4e5c58 or u(actor+8)&3:continue
  definition=u(actor+4);org=u(actor+0x7c);nm=text(definition)
  if u(actor+0xe8) not in owners and 80<position(actor)[0]<210 and 110<position(actor)[1]<310 and (org or u(actor+0x6c) or u(actor+0x94)):
   result['nearbyNonOwned'].append({'id':u(actor+0x14),'name':nm,'owner':u(actor+0xe8),'position':position(actor),'company':bool(org),'structure':bool(u(actor+0x94))})
  if not(org and u(actor+0xe8)in owners)and not nm.startswith('paws_bridge_'):continue
  mind=u(actor+0x70);cmd=u(mind+0x20)if mind else 0;s=u(mind+0x14)if mind else 0;s=u(s)if s else 0
  row={'id':u(actor+0x14),'ptr':actor,'name':nm,'owner':u(actor+0xe8),'position':position(actor),'flags':u(actor+0x100),'state':hex(u(s)-base)if s else None,'command':text(u(cmd+8))if cmd else None,'commandTarget':u(cmd+0x10)if cmd else None,'commandXY':struct.unpack('<2f',read(cmd+0x18,8))if cmd else None,'members':[]}
  if org:
   count=u(org+0x2c);assert count<=64
   for j in range(count):
    member=u(u(org+0x28)+j*4)
    if member:row['members'].append({'id':u(member+0x14),'name':text(u(member+4)),'build':bool(u(member+0xa8))})
  if nm.startswith('paws_bridge_'):
   size=u(definition+0x334);assert size<=32
   row['definedUpkeep']=struct.unpack('<%df'%size,read(u(definition+0x330),size*4))if size else []
   size=u(definition+0x328);row['definedCost']=struct.unpack('<%df'%size,read(u(definition+0x324),size*4))if size else []
   meta=u(actor+0x18);row['paymentPrefix']=read(meta,40).decode('utf-16le',errors='replace')if meta else ''
  body=u(actor+0x60)
  if body:row['hp']=f(body+0x10);row['maxhp']=f(body+0x14)
  result['actors'].append(row)
 if a.save:a.save.parent.mkdir(parents=True,exist_ok=True);a.save.write_text(json.dumps(result,indent=2))
 print(json.dumps({key:result[key]for key in ['time','planning','plannerCompany','plannerSource','plannerTarget','sample','samples','bestCount','sourceXY','goalXY','baseline','counts','projects','refusals','lastCandidate','lastSAICommand','abortReason']}if a.brief else result,ensure_ascii=False))
finally:k.CloseHandle(h)
