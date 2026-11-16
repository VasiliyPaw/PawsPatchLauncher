from context import *
import control as c,match,time,ctypes as C,struct,shutil
from checksums import compare

def hook(role):
 r=c.folder(role);ident=read(r/'qa-process.json');h=c.k.OpenProcess(0x410,False,ident['pid']);assert h
 try:
  c.k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
  addr=c.state(role)['base']+0x228b6c;b=C.create_string_buffer(5);n=C.c_size_t();assert c.k.ReadProcessMemory(h,addr,b,5,C.byref(n))and n.value==5;raw=b.raw;assert raw[0]==0xe9
  target=addr+5+struct.unpack('<i',raw[1:])[0]
  ps=C.WinDLL('psapi');ps.EnumProcessModulesEx.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_void_p,C.c_uint];ps.GetModuleFileNameExW.argtypes=[C.c_void_p,C.c_void_p,C.c_wchar_p,C.c_uint];modules=(C.c_void_p*512)();done=C.c_uint();assert ps.EnumProcessModulesEx(h,modules,C.sizeof(modules),C.byref(done),3)
  for module in modules[:done.value//C.sizeof(C.c_void_p)]:
   path=C.create_unicode_buffer(32768);ps.GetModuleFileNameExW(h,module,path,len(path))
   if Path(path.value).name=='PawsPurePresentation1372.dll':
    assert module<=target<module+0x100000;assert sha(path.value)==read(O/'native/build-report.json')['sha256'];return dict(passed=True,branchTarget=hex(target),module=path.value,sha256=sha(path.value))
  raise AssertionError('Capture hook does not belong to exact installed Pure payload')
 finally:c.k.CloseHandle(h)

def run_match():
 match.launch();evidence={role:hook(role)for role in c.ROLES};c.command('host','GameSpeed 3');c.command('host','GamePause 0');end=time.monotonic()+110
 while compare()['commonSamples']<65:
  assert time.monotonic()<end,compare();time.sleep(.4)
 c.command('host','GamePause 1');result=compare();assert result['mismatchCount']==0 and not result['errors'],result
 archive=O/('network-'+c.MODE);archive.mkdir(exist_ok=True)
 for role in c.ROLES:
  c.command(role,'!capture-view');dest=archive/role;dest.mkdir(exist_ok=True)
  for n in ['network-state.json','network-sync.jsonl','capture-view.json','plugins.log']:shutil.copy2(c.folder(role)/'game/Mods'/n,dest/n)
  c.command(role,'ReallyQuit')
 c.wait(lambda:not c.own(),30,'owned three-peer exit');write(O/(c.MODE+'-network-result.json'),dict(passed=True,mode=c.MODE,peers=3,checksums=result,hook=evidence,stockFailureHandlerEnabled=True,qaHelperOnlyProcessScopeChanged=True,networkCaptureClaimed=False));print('PURE_NETWORK_PASS',c.MODE,result,flush=True)
if __name__=='__main__':run_match()
