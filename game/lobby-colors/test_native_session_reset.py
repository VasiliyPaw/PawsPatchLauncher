"""Execute stock Session::Reset then candidate color code, without a live game.

OS GUID/timer, logging, container cleanup and unrelated subsystems are stubbed.
The native Session writes, argument construction and lifetime transition execute
unaltered. Use an empty departing roster so no player destructor is simulated.
"""
import argparse,json,struct,sys
from pathlib import Path
p=argparse.ArgumentParser()
for key in ['legacy','candidate']:p.add_argument('--'+key,type=Path,required=True)
p.add_argument('--expect-fixed',type=int,choices=[0,1],required=True);p.add_argument('--palette',type=Path);a=p.parse_args()
sys.argv=[sys.argv[0],'--legacy',str(a.legacy),'--candidate',str(a.candidate)]
source=Path(__file__).with_name('test_participant_colors.py');scope={'__file__':str(source)}
exec(compile(source.read_text().split('\nfor game,cave in ')[0],str(source),'exec'),scope)
if a.palette:
 import configparser
 palette=configparser.ConfigParser();palette.read(a.palette,encoding='utf-8-sig')
 count=len(palette.sections());assert count in [39,48]
 scope['palette']=palette;scope['RANDOM']=scope['scope']['RANDOM']=count
 scope['env']['RANDOM']=scope['env']['PALETTE_COUNT']=count
Peer,MAN,ENGINE,RANDOM=scope['Peer'],scope['MAN'],scope['env']['ENGINE'],scope['RANDOM']
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP

class ResetPeer(Peer):
 def __init__(self):
  self.guid_byte=0x11;self.contract_calls=[];self.reset_active=False
  super().__init__(True,0x460000,0x10000000)
  self.guid_buffer=self.intern('0'*32)
  self.write(self.session+0x170,self.guid_buffer)
  self.u.mem_write(0x5c208b,ENGINE[0x5c208b-0x460000:0x5c21f4-0x460000])
  MAN['functions']['stock_session_reset']=0x5c208b-self.cave
  self.write(0x8ad204,0x800010);self.write(0x8ad540,0x800020)
  self.write(self.session+0x180,0)

 def hook(self,u,address,size,data):
  if not self.reset_active:return super().hook(u,address,size,data)
  if address in [0x5957af,0x5c6276,0x5ad13e]:self.ret(0,0);return
  if address in [0x762374,0x5c12ac]:self.ret(0,4);return
  if address==0x480d4b:
   self.write(u.reg_read(UC_X86_REG_ECX),0);self.ret(0,0);return
  if address==0x800010:self.ret(12345,0);return
  if address==0x800020:
   arg=self.read(u.reg_read(UC_X86_REG_ESP)+4)
   u.mem_write(arg,bytes([self.guid_byte])*16);self.contract_calls.append('CoCreateGuid')
   self.ret(0,4);return
  if address==0x4810c4:
   sp=u.reg_read(UC_X86_REG_ESP);dest=self.read(sp+4)
   assert dest==self.session+0x170
   assert self.read(sp+8)==0x91eb04
   values=[self.read(sp+12+i*4) for i in range(11)]
   formatted=''.join(format(v,'X') for v in values)
   assert len(formatted)==32
   assert formatted==format(self.guid_byte,'X')*16
   # Native string formatting may reuse this exact heap allocation.
   u.mem_write(self.guid_buffer,formatted.encode('utf-16le')+b'\0\0')
   self.write(dest,self.guid_buffer);self.contract_calls.append('GUID format')
   self.ret(dest,0);return
  super().hook(u,address,size,data)

f=ResetPeer()
def native_reset():
 f.roster(set());f.reset_active=True
 try:f.call('stock_session_reset',f.session)
 finally:f.reset_active=False
 assert f.read(f.session+0xf4)==0
 assert f.read(f.session+0x170)==f.guid_buffer
 assert f.u.mem_read(f.session+0x100,1)==b'\0'
 f.u.mem_write(f.session+0x100,b'\1');f.write(f.session+0xf0,1)
 f.roster({0,1});f.write(f.session+0xf4,2)

native_reset();f.call('state_init',f.session);f.choose(0,3);f.choose(1,9)
assert (f.pref(0),f.pref(1))==(3,9)
f.guid_byte=0x22;native_reset();f.call('state_init',f.session)
f.move(0,0);f.move(1,1)
expected=(RANDOM,RANDOM) if a.expect_fixed else (3,9)
assert tuple(f.choices()[:2])==expected
assert f.contract_calls==['CoCreateGuid','GUID format']*2
result=dict(passed=True,fixed=bool(a.expect_fixed),paletteCount=RANDOM,nativeResetEntry='0x5c208b',
 nativeResetBytes=0x5c21f4-0x5c208b,sessionAddressReused=True,guidBufferAddressReused=True,
 guidCreationAndFormattingCalls=f.contract_calls,observed=f.choices()[:2],liveGameTested=False)
(a.candidate/'native-reset-tests.json').write_text(json.dumps(result,indent=2))
print('STOCK_SESSION_RESET_PASS',json.dumps(result))
