"""Compare exact live walkable-grid routes; never send gameplay commands."""
import argparse,heapq,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--terrain',type=Path,required=True);p.add_argument('--actors',type=Path,required=True);p.add_argument('--start',nargs=2,type=float,required=True);p.add_argument('--goal',nargs=2,type=float,required=True);p.add_argument('--save',type=Path,required=True);a=p.parse_args()
j=json.loads(a.terrain.read_text())[0];actors=json.loads(a.actors.read_text())['actors'];w=j['map']['width'];h=j['map']['height'];cells=j['terrain']['cells']
bridges=[b for b in actors if b['name'].startswith('paws_bridge_')];start=int(a.start[1]/2)*w+int(a.start[0]/2);goal=int(a.goal[1]/2)*w+int(a.goal[0]/2)
def on(b,i):
 x,y=i%w*2+1,i//w*2+1;ux,uy=b['direction'][:2]
 if '_x_' in b['name']:ux,uy=uy,-ux
 length=math.hypot(ux,uy);ux/=length;uy/=length;dx=x-b['simulation'][0];dy=y-b['simulation'][1]
 return abs(dx*ux+dy*uy)<=int(b['name'].rsplit('_',1)[1])+1 and abs(dx*uy-dy*ux)<=3.001
def solve(keep):
 blocked={i for i,(name,flags) in enumerate(cells) if flags&0x100 or (name=='paws_engineer_bridge01' and any(on(b,i) for b in bridges if b['id']!=keep))}
 if start in blocked or goal in blocked:return {'reachable':False}
 dist={start:0};parent={};q=[(0,0,start)]
 while q:
  _,cost,c=heapq.heappop(q)
  if cost!=dist[c]:continue
  if c==goal:
   path=[c]
   while c!=start:c=parent[c];path.append(c)
   return {'reachable':True,'octileCost':cost,'worldDistance':cost*.2,'cells':len(path),'path':[[i%w*2+1,i//w*2+1] for i in path[::-1]]}
  x,y=c%w,c//w
  for dy in (-1,0,1):
   for dx in (-1,0,1):
    xx,yy=x+dx,y+dy;n=yy*w+xx
    if not(dx or dy) or not(0<=xx<w and 0<=yy<h) or n in blocked:continue
    if dx and dy and (y*w+xx in blocked or yy*w+x in blocked):continue
    nc=cost+(14 if dx and dy else 10)
    if nc>=dist.get(n,10**12):continue
    parent[n]=c;dist[n]=nc;gx,gy=goal%w,goal//w;hx,hy=abs(xx-gx),abs(yy-gy);heapq.heappush(q,(nc+10*(hx+hy)-6*min(hx,hy),nc,n))
 return {'reachable':False}
report={'start':a.start,'goal':a.goal,'metric':'8-neighbour live walkable grid, no diagonal corner cutting; other bridges blocked per alternative','alternatives':{str(b['id']):{'name':b['name'],**solve(b['id'])}for b in bridges}}
a.save.write_text(json.dumps(report,indent=2));print({k:{z:v[z]for z in ('name','reachable','worldDistance')if z in v}for k,v in report['alternatives'].items()})
