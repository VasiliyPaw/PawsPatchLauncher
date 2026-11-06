from pathlib import Path
import ctypes as C,collections,json,hashlib,time,subprocess
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];OUT=WS/'outputs/mixed-biomes-r2-20261106'
# Host build only executes pure geometry exports; engine pointers stay x86-only.
compiler=WS/'work/crash-20260914-continue/tools/tinycc/tcc/x86_64-win32-tcc.exe'
subprocess.run([str(compiler),'-shared','-w','-I'+str(OUT/'native'),str(HERE/'biomes.c'),'-o',str(OUT/'production_geometry_host.dll')],check=True)
dll=C.CDLL(str(OUT/'production_geometry_host.dll'));dll.prepare_regions.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint];state=C.create_string_buffer(6295552)
palette=[(81,143,73),(222,236,246),(211,159,79),(100,69,123)]
rows=[];minimum=1.;minor=[];center=collections.Counter();sites=collections.Counter();start=time.time()
montage=Image.new('RGB',(960,1040),(21,29,38));draw=ImageDraw.Draw(montage);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
for seed in range(512):
 w=h=96;dll.prepare_regions(state,w,h,seed);n=int.from_bytes(state.raw[76:80],'little');data=state.raw[164:164+w*h];counts=collections.Counter(data);minimum=min(minimum,min(counts.values())/len(data));center[data[(h//2)*w+w//2]]+=1;sites[n]+=1
 sizes=[];seen=bytearray(len(data))
 for i in range(len(data)):
  if seen[i]:continue
  b=data[i];q=[i];seen[i]=1;count=0
  while q:
   p=q.pop();count+=1;x=p%w;y=p//w
   for j in (p-1 if x else -1,p+1 if x+1<w else -1,p-w if y else -1,p+w if y+1<h else -1):
    if j>=0 and not seen[j] and data[j]==b:seen[j]=1;q.append(j)
  sizes.append((b,count))
 small=[(b,c) for b,c in sizes if c<len(data)*.01]
 if small:minor.append(dict(seed=seed,small=small))
 assert set(counts)=={0,1,2,3}
 assert min(counts.values())>len(data)*.08,(seed,counts)
 assert all(max(c for bb,c in sizes if bb==b)>len(data)*.05 for b in range(4))
 rows.append(dict(seed=seed,sites=n,counts=dict(counts),components=sizes,sha256=hashlib.sha256(data).hexdigest()))
 if seed<16:
  tile=Image.new('RGB',(w,h));tile.putdata([palette[v] for v in data]);tile=tile.resize((220,220),Image.Resampling.NEAREST);x=10+240*(seed%4);y=10+260*(seed//4);montage.paste(tile,(x,y));draw.text((x,y+226),f'Зерно {seed} · областей {n}',font=font,fill='white')
assert not minor,minor
print('GEOMETRY',len(rows),'min fraction',minimum,'small components',len(minor),'center',center,'sites',sites,'seconds',round(time.time()-start,1));print('SMALL',minor[:12]);montage.save(OUT/'geometry-16-seeds.png')
(OUT/'geometry-tests.json').write_text(json.dumps(dict(seeds=len(rows),minimumBiomeFraction=minimum,smallComponents=minor,centerBiomes=dict(center),sites=dict(sites),rows=rows),indent=2))

references={}
for seed in range(24):
 dll.prepare_regions(state,32,32,seed);references[str(seed)]=hashlib.sha256(state.raw[164:164+1024]).hexdigest()
(OUT/'geometry-x86-references.json').write_text(json.dumps(references,indent=2))
for side in (192,384,640,1024):
 for seed in (0,1,1372,0xffffffff,2854222040):
  dll.prepare_regions(state,side,side,seed);assert set(state.raw[164:164+side*side])=={0,1,2,3}
(OUT/'geometry-sizes.json').write_text(json.dumps(dict(passed=True,seeds=[0,1,1372,4294967295,2854222040],physicalSizes=[384,768,1280,2048]),indent=2))
print('PHYSICAL_SIZES_GEOMETRY_PASS 20 maps; 384..2048')
