"""Add diagnostic readback to the unchanged safety stop; never relax limits."""
import sys
from context import *
source=(HERE/'live_single.py').read_text();target="exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})"
assert target in source
instrument='''
trace = r"""class Perf(C.Structure):
 _fields_=[('cb',C.c_ulong)]+[(n,C.c_size_t) for n in ['commit','limit','peak','physical','available','cache','kernel','paged','nonpaged','pageSize']]+[(n,C.c_ulong)for n in ['handles','processes','threads']]
p=Perf();p.cb=C.sizeof(p);C.WinDLL('psapi').GetPerformanceInfo(C.byref(p),C.sizeof(p))
job=C.create_string_buffer(144);need=C.c_uint();K.QueryInformationJobObject(None,9,job,144,C.byref(need))
with open('G:/PawPure041QA-20261109/memory-readback.jsonl','a')as f:f.write(json.dumps(dict(utc=time.time(),pointerBytes=C.sizeof(C.c_void_p),statusSize=C.sizeof(status),memory={n:getattr(status,n)for n,_ in status._fields_},systemCommitFree=(p.limit-p.commit)*p.pageSize,job=job.raw.hex()))+'\\n')
"""
anchor="  raise RuntimeError('Low available memory:"
assert code.count(anchor)==1
lines='\\n'.join('  '+line for line in trace.rstrip().splitlines())+'\\n'
code=code.replace(anchor,lines+anchor)
exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
'''
source=source.replace(target,instrument);exec(compile(source,str(HERE/'live_single.py'),'exec'),{'__name__':'__main__','__file__':str(HERE/'live_single.py')})
