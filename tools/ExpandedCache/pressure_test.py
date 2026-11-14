"""Temporary low-VA report in the owned QA process; no real memory exhaustion.

Replaces only this candidate's memory-query callback, restores it in finally.
Both callback targets remain executable until the QA process exits, avoiding
any pointer/null/free race. No other process is opened or changed.
"""
import ctypes as C,struct,time,sys
import live
from build import OUT,write
K=live.K
K.VirtualAllocEx.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.c_ulong,C.c_ulong];K.VirtualAllocEx.restype=C.c_void_p
K.WriteProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
K.VirtualProtectEx.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.c_ulong,C.c_void_p]
K.FlushInstructionCache.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t]
def recover(low):
 until=time.monotonic()+35
 while time.monotonic()<until:
  r=live.snapshot();b=r['budget']
  # A flushed cache has smaller logical usage. Recovery must restore useful
  # quotas, not immediately force the previous warm-cache 2+ GiB estimates.
  if b['pressure']==0 and b['calls']>low['calls'] and b['ram']>low['ram']+64*1024**2 and b['vram']>low['vram']+64*1024**2:
   write(OUT/'live-pressure-recovery.json',dict(passed=True,after=r));print('LIVE_PRESSURE_SHRINK_AND_RECOVERY_PASS',b,flush=True);return
  time.sleep(2)
 raise RuntimeError('Native periodic budget did not recover within 35 seconds')
if '--recover-only' in sys.argv:
 recover(live.read(OUT/'live-pressure-injection.json')['lowMemorySamples'][-1]['budget']);raise SystemExit(0)
s=live.snapshot();assert s['phase']==4 and s['world'] and s['budget']['pressure']==0
h=K.OpenProcess(0x1438,False,s['pid']);assert h
state=s['cacheState'];events=[];original=None;stub=None
def get(at,n):
 b=C.create_string_buffer(n);got=C.c_size_t();assert K.ReadProcessMemory(h,at,b,n,C.byref(got))and got.value==n;return b.raw
def put(at,b):
 got=C.c_size_t();buf=C.create_string_buffer(b);assert K.WriteProcessMemory(h,at,buf,len(b),C.byref(got))and got.value==len(b)
try:
 # snapshot() verifies the executable path before every sample/operation.
 assert struct.unpack('<I',get(state,4))[0]==s['base'];original=struct.unpack('<I',get(state+8,4))[0];assert original
 stub=K.VirtualAllocEx(h,None,4096,0x3000,4);assert stub and stub<0x100000000
 # MEMORYSTATUSEX fields used by the candidate: load=30, availablePhysical=16GiB,
 # availableVirtual=256MiB. Returning 1 exercises the real pressure branch.
 code=b'\x8b\x44\x24\x04'
 for offset,value in [(0,64),(4,30),(16,0),(20,4),(48,256*1024*1024),(52,0)]:code+=b'\xc7\x40'+bytes([offset])+struct.pack('<I',value)
 code+=b'\xb8\x01\x00\x00\x00\xc2\x04\x00';put(stub,code);old=C.c_ulong();assert K.VirtualProtectEx(h,stub,4096,0x20,C.byref(old));assert K.FlushInstructionCache(h,stub,len(code))
 put(state+8,struct.pack('<I',stub));print('OWNED_SYNTHETIC_LOW_VA_BEGIN',flush=True)
 for _ in range(3):
  time.sleep(1.2);r=live.snapshot();events.append(r);print('PRESSURE',r['budget'],flush=True)
 assert events[-1]['budget']['pressure']&1 and events[-1]['budget']['refreshes']>s['budget']['refreshes']
 assert events[-1]['budget']['ram']<s['budget']['ram'] and events[-1]['budget']['vram']<s['budget']['vram']
finally:
 if original is not None and stub and struct.unpack('<I',get(state+8,4))[0]==stub:put(state+8,struct.pack('<I',original))
 K.CloseHandle(h)
write(OUT/'live-pressure-injection.json',dict(passed=True,before=s,lowMemorySamples=events,callbackRestored=True,realAddressSpaceExhausted=False,qaOnly=True,stubRetainedUntilProcessExit=True))
print('OWNED_MEMORY_CALLBACK_RESTORED',flush=True)
recover(events[-1]['budget'])
