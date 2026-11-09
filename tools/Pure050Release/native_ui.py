"""Fallback UI driver confined to one path/time-verified owned game window.

The supplied Computer Use runtime cannot initialize on this machine. This QA
driver targets only the marked disposable game, never an arbitrary app/window.
"""
import argparse,ctypes as C,re,time,struct
from context import *
from PIL import ImageGrab
K=C.WinDLL('kernel32',use_last_error=True);U=C.WinDLL('user32',use_last_error=True)
K.OpenProcess.restype=C.c_void_p;K.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];K.GetProcessTimes.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p];K.CloseHandle.argtypes=[C.c_void_p]
U.GetWindowThreadProcessId.argtypes=[C.c_void_p,C.c_void_p];U.GetWindow.argtypes=[C.c_void_p,C.c_uint];U.GetWindow.restype=C.c_void_p;U.IsWindowVisible.argtypes=[C.c_void_p];U.SetForegroundWindow.argtypes=[C.c_void_p];U.GetClientRect.argtypes=[C.c_void_p,C.c_void_p];U.ClientToScreen.argtypes=[C.c_void_p,C.c_void_p];U.SendMessageW.argtypes=[C.c_void_p,C.c_uint,C.c_size_t,C.c_ssize_t];U.SendMessageW.restype=C.c_ssize_t
class Point(C.Structure):_fields_=[('x',C.c_long),('y',C.c_long)]
class Rect(C.Structure):_fields_=[('l',C.c_long),('t',C.c_long),('r',C.c_long),('b',C.c_long)]

def main():
 p=argparse.ArgumentParser();p.add_argument('peer',type=Path);p.add_argument('action',choices=['capture','click','wheel','key']);p.add_argument('--x',type=int);p.add_argument('--y',type=int);p.add_argument('--value',type=int,default=120);p.add_argument('--name',required=True);a=p.parse_args();peer=a.peer.resolve();assert(peer/'game/reconnect-test.marker').is_file();log=(peer/'harness-0.log').read_text();pid=int(re.search(r'OWNED_GAME (\d+)',log)[1]);h=K.OpenProcess(0x1000,False,pid);assert h
 try:
  size=C.c_uint(32768);path=C.create_unicode_buffer(size.value);assert K.QueryFullProcessImageNameW(h,0,path,C.byref(size));assert Path(path.value).resolve()==peer/'game/k2.exe';times=[C.c_ulonglong()for _ in range(4)];assert K.GetProcessTimes(h,*[C.byref(t)for t in times]);identity=dict(pid=pid,path=path.value,created=times[0].value);saved=peer/'native-ui-identity.json'
  if saved.exists():assert read(saved)==identity
  else:write(saved,identity)
 finally:K.CloseHandle(h)
 windows=[];callback=C.WINFUNCTYPE(C.c_int,C.c_void_p,C.c_ssize_t)
 def collect(hwnd,arg):
  found=C.c_uint();U.GetWindowThreadProcessId(hwnd,C.byref(found))
  if found.value==pid and U.IsWindowVisible(hwnd)and not U.GetWindow(hwnd,4):windows.append(hwnd)
  return 1
 cb=callback(collect);U.EnumWindows(cb,0);assert len(windows)==1,windows;hwnd=windows[0];U.SetForegroundWindow(hwnd);U.SendMessageW(hwnd,0x1c,1,0);U.SendMessageW(hwnd,0x6,1,0);rect=Rect();assert U.GetClientRect(hwnd,C.byref(rect));origin=Point(0,0);assert U.ClientToScreen(hwnd,C.byref(origin));time.sleep(.3)
 if a.action in ['click','wheel']:
  assert a.x is not None and a.y is not None and 0<=a.x<rect.r and 0<=a.y<rect.b;assert U.SetCursorPos(origin.x+a.x,origin.y+a.y);U.SendMessageW(hwnd,0x200,0,(a.y<<16)|a.x);time.sleep(.1)
  if a.action=='click':U.SendMessageW(hwnd,0x201,1,(a.y<<16)|a.x);time.sleep(.1);U.SendMessageW(hwnd,0x202,0,(a.y<<16)|a.x)
  else:U.SendMessageW(hwnd,0x20a,(a.value&0xffff)<<16,((origin.y+a.y)&0xffff)<<16|((origin.x+a.x)&0xffff))
 if a.action=='key':
  assert a.value in [27,37,38,39,40];U.SendMessageW(hwnd,0x100,a.value,1);time.sleep(1);U.SendMessageW(hwnd,0x101,a.value,0xc0000001)
 # Native PrintScreen binding captures Direct3D without relying on desktop composition.
 previous=set((peer/'docs/Kohan2/data/Screenshots').glob('*.png'));U.SendMessageW(hwnd,0x100,0x2c,0x00370001);U.SendMessageW(hwnd,0x101,0x2c,0xc0370001);time.sleep(1)
 fresh=set((peer/'docs/Kohan2/data/Screenshots').glob('*.png'))-previous;assert len(fresh)==1,('Native PrintScreen did not capture',fresh)
 folder=peer/'ui-captures';folder.mkdir(exist_ok=True);target=folder/(a.name+'.png');assert not target.exists();target.write_bytes(fresh.pop().read_bytes());print('OWNED_NATIVE_UI',a.action,str(target))
if __name__=='__main__':main()
