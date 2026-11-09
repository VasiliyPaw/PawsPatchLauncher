"""Adapt the accepted owned Pure QA driver; production helper bytes stay exact."""
from context import *
sys.path.append(str(REPO/'tools/Pure050Release'))
ANCHOR="exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source),'STOCK_AVARS':STOCK_AVARS,'re':re,'QA_MEMORY_PATH':QA_MEMORY_PATH})"
def adapt_outer(s):
 s=once(s,"OUT/'stable-fixtures/vanilla/game/Data.rwd'","PREVIOUS/'stable-fixtures/vanilla/game/Data.rwd'")
 s=s.replace('0.5.0-beta.1',PATCH)
 insertion=r'''
needle="  wait(lambda:any('connect end MainMenuInterface'in text(f)for f in(d/'game/Logs').glob('log-*.log')),120,'Actual native menu interface connected '+d.name);stay(2)"
replacement=r"""  menu_poll=[0.]
  def menu_ready():
   if any('connect end MainMenuInterface'in text(f)for f in(d/'game/Logs').glob('log-*.log')):return True
   if time.monotonic()-menu_poll[0]>=3:
    menu_poll[0]=time.monotonic();mods=i['dir']/'game/Mods';i['seq']=max(i['seq'],int(text(mods/'rig-command.txt').strip()or'0'))+1;n=i['seq'];(mods/('rig-request-'+str(n)+'.txt')).write_text(('Echo Pure native menu log flush '+('x'*400)+'\n')*24);temp=mods/'rig-command.tmp';temp.write_text(str(n));os.replace(temp,mods/'rig-command.txt')
   return False
  wait(menu_ready,120,'Actual native menu interface connected '+d.name);stay(2)"""
assert code.count(needle)==1;code=code.replace(needle,replacement)
probe=r""" def optimization_snapshot(i):
  handle=K.OpenProcess(0x1410,False,i['pid']);assert handle
  try:
   identity(handle,i)
   def data(at,n):
    b=C.create_string_buffer(n);got=C.c_size_t();assert K.ReadProcessMemory(handle,at,b,n,C.byref(got))and got.value==n;return b.raw
   def u(at):return struct.unpack('<I',data(at,4))[0]
   b=i['base'];match=re.search(r'RESOURCE_CACHE r1;[^\n]*state=0x([A-Fa-f0-9]+)',text(i['dir']/'game/harness-status.log'));assert match
   state=int(match[1],16);fields=struct.unpack('<28I',data(state,112));uv=u(b+0x5f9480);percent=u(u(uv+0x100));hook=data(b+0x18e3c8,5);assert hook[0]==0xe9
   modules=(C.c_void_p*1024)();needed=C.c_uint();assert K.K32EnumProcessModulesEx(handle,modules,C.sizeof(modules),C.byref(needed),3)
   K.K32GetModuleFileNameExW.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint];graphics=0
   for module in modules[:needed.value//C.sizeof(C.c_void_p)]:
    path=C.create_unicode_buffer(32768)
    if K.K32GetModuleFileNameExW(handle,module,path,32768)and Path(path.value).resolve()==i['dir']/'game/d3d9.dll':graphics=module;break
   assert graphics;meta=json.loads(Path('GRAPHICS_COUNTER_PATH').read_text());pool=dict(zip(meta['names'],[u(graphics+rva)for rva in meta['rvas']]))
   return dict(resource=dict(weightCalls=fields[4],frames=fields[5],prepared=fields[10],models=fields[11],animations=fields[12],failures=fields[13],pressureSkips=fields[14],maxAssetMs=fields[17],callback=fields[26],animationPolicy=fields[27]),animationPercent=percent,findHookTarget=(b+0x18e3cd+struct.unpack('<i',hook[1:])[0])&0xffffffff,buffers=pool,graphicsSha256=meta['dllSha256'])
  finally:K.CloseHandle(handle)
 def check_optimizations(i,label):
  snapshot_opt=optimization_snapshot(i);(root/(label+'-optimization.json')).write_text(json.dumps(snapshot_opt,indent=2));rc=snapshot_opt['resource'];pool=snapshot_opt['buffers'];checked(label+'-resource-cache-active',rc['weightCalls']>0 and rc['frames']>1 and rc['callback']!=0);checked(label+'-animation-policy-active',rc['animationPolicy']==1 and snapshot_opt['animationPercent']==80);checked(label+'-buffer-policy-active',pool['mode']==1 and pool['frame']>5 and pool['bytes']<=32*1024*1024 and pool['held']<=512);checked(label+'-find-hook-active',snapshot_opt['findHookTarget']!=0)
""".replace('GRAPHICS_COUNTER_PATH',str(OUT/'qa-rig/graphics-counters.json').replace('\\','/'))
assert code.count(' def errors():')==1;code=code.replace(' def errors():',probe+' def errors():')
needle="  command(h,'ReallyQuit');h['required']=False;h['process'].wait(timeout=30);checked('normal-exit'"
assert code.count(needle)==1;code=code.replace(needle,"  check_optimizations(h,'host')\n"+needle)
'''+ANCHOR
 assert s.count(ANCHOR)==1;return s.replace(ANCHOR,insertion)
