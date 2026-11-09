"""Read-only process/kernel attribution for the owned startup memory guard."""
import ctypes as C,json,struct
from pathlib import Path
K=C.WinDLL('kernel32',use_last_error=True);PS=C.WinDLL('psapi',use_last_error=True)
class Perf(C.Structure):
 _fields_=[('cb',C.c_ulong)]+[(n,C.c_size_t) for n in ['commit','limit','peak','physTotal','physFree','sysCache','kernelTotal','kernelPaged','kernelNonPaged','pageSize']]+[(n,C.c_ulong) for n in ['handles','processes','threads']]
class Memory(C.Structure):
 _fields_=[('cb',C.c_ulong),('faults',C.c_ulong)]+[(n,C.c_size_t) for n in ['peakWorking','working','peakPaged','paged','peakNonPaged','nonPaged','pagefile','peakPagefile','private']]
PS.GetPerformanceInfo.argtypes=[C.POINTER(Perf),C.c_ulong];PS.EnumProcesses.argtypes=[C.c_void_p,C.c_ulong,C.c_void_p];PS.GetProcessMemoryInfo.argtypes=[C.c_void_p,C.POINTER(Memory),C.c_ulong]
K.OpenProcess.argtypes=[C.c_ulong,C.c_int,C.c_ulong];K.OpenProcess.restype=C.c_void_p;K.CloseHandle.argtypes=[C.c_void_p];K.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_ulong,C.c_wchar_p,C.c_void_p];K.K32EnumProcessModulesEx.argtypes=[C.c_void_p,C.c_void_p,C.c_ulong,C.c_void_p,C.c_ulong];K.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
K.OpenThread.argtypes=[C.c_ulong,C.c_int,C.c_ulong];K.OpenThread.restype=C.c_void_p;K.GetProcessIdOfThread.argtypes=[C.c_void_p];K.SuspendThread.argtypes=[C.c_void_p];K.ResumeThread.argtypes=[C.c_void_p];K.Wow64GetThreadContext.argtypes=[C.c_void_p,C.c_void_p]
K.SuspendThread.restype=C.c_ulong;K.ResumeThread.restype=C.c_ulong
PS.GetMappedFileNameW.argtypes=[C.c_void_p,C.c_void_p,C.c_wchar_p,C.c_ulong]
class Region(C.Structure):_fields_=[('base',C.c_void_p),('allocation',C.c_void_p),('initialProtect',C.c_ulong),('size',C.c_size_t),('state',C.c_ulong),('protect',C.c_ulong),('kind',C.c_ulong)]
K.VirtualQueryEx.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(Region),C.c_size_t];K.VirtualQueryEx.restype=C.c_size_t
def view_stack(process,pid,base,word):
 manager=word(base+0x5ef728);tid=word(manager+0x48);thread=K.OpenThread(0x4a,False,tid)
 if not thread:return {}
 suspended=False
 try:
  if K.GetProcessIdOfThread(thread)!=pid:return {}
  if K.SuspendThread(thread)==0xffffffff:return {}
  suspended=True;context=C.create_string_buffer(716);C.c_uint.from_buffer(context).value=0x10001
  if not K.Wow64GetThreadContext(thread,context):return {}
  pc,sp=struct.unpack_from('<I',context.raw,184)[0],struct.unpack_from('<I',context.raw,196)[0];stack=C.create_string_buffer(1024);got=C.c_size_t()
  words=[]
  if K.ReadProcessMemory(process,sp,stack,1024,C.byref(got)):words=struct.unpack('<256I',stack.raw)
 finally:
  if suspended:K.ResumeThread(thread)
  K.CloseHandle(thread)
 name=C.create_unicode_buffer(32768);PS.GetMappedFileNameW(process,pc,name,32768);region=Region();K.VirtualQueryEx(process,pc,C.byref(region),C.sizeof(region))
 callers=[]
 for p in words:
  if base+6<=p<base+0x700000:
   opcode=C.create_string_buffer(6);got=C.c_size_t()
   if K.ReadProcessMemory(process,p-6,opcode,6,C.byref(got)) and (opcode.raw[1]==0xe8 or opcode.raw[:2]==b'\xff\x15'):callers.append(hex(p-base))
 return dict(thread=tid,pc=hex(pc),module=Path(name.value).name,moduleOffset=hex(pc-(region.allocation or 0)),nativeReturnRvas=callers[:24])
def snapshot(owned,capture_stack=False):
 perf=Perf();perf.cb=C.sizeof(perf);assert PS.GetPerformanceInfo(C.byref(perf),C.sizeof(perf));pids=(C.c_ulong*4096)();done=C.c_ulong();assert PS.EnumProcesses(pids,C.sizeof(pids),C.byref(done));rows=[];games=[]
 for pid in list(pids)[:done.value//4]:
  h=K.OpenProcess(0x410,False,pid)
  if not h:continue
  try:
   m=Memory();m.cb=C.sizeof(m)
   if not PS.GetProcessMemoryInfo(h,C.byref(m),C.sizeof(m)):continue
   name=C.create_unicode_buffer(32768);size=C.c_ulong(32768)
   path=name.value if not K.QueryFullProcessImageNameW(h,0,name,C.byref(size)) else name.value
   rows.append(dict(pid=pid,name=Path(path).name,privateMiB=m.private//2**20,workingMiB=m.working//2**20))
   if Path(path).name.lower()=='k2.exe' and str(Path(path).resolve()).lower().startswith(str(Path(owned).resolve()).lower()):
    def word(p):
     buf=C.c_uint();got=C.c_size_t()
     if not K.ReadProcessMemory(h,p,C.byref(buf),4,C.byref(got)) or got.value!=4:raise OSError('Native startup field not readable')
     return buf.value
    modules=(C.c_void_p*1024)();n=C.c_ulong()
    if not K.K32EnumProcessModulesEx(h,modules,C.sizeof(modules),C.byref(n),3):continue
    base=modules[0];item=dict(pid=pid,base=base)
    try:
     meta=json.loads(Path('C:/PawsArcane051ReleaseQA-20261109/native-r6/cache-build/payload.json').read_text());site=base+meta['hooks'][0]['site'];jump=word(site)
     if jump&255==0xe9:
      target=(site+5+word(site+1))&0xffffffff;state=target-meta['hooks'][0]['entry']+meta['state'];item['resourceState']=[word(state+i*4) for i in range(28)]
     manager=word(base+0x5f3fd4);uv=word(base+0x5f9480);item.update(ramBudget=word(manager+0xd0),vramBudget=word(manager+0xdc),ramPercent=word(word(uv+0x100)))
     if capture_stack:item['viewStack']=view_stack(h,pid,base,word)
    except OSError:pass
    games.append(item)
  finally:K.CloseHandle(h)
 return dict(kernelPagedMiB=perf.kernelPaged*perf.pageSize//2**20,kernelNonPagedMiB=perf.kernelNonPaged*perf.pageSize//2**20,processPrivateSumMiB=sum(r['privateMiB'] for r in rows),topPrivate=sorted(rows,key=lambda r:r['privateMiB'],reverse=True)[:7],ownedNative=games)
