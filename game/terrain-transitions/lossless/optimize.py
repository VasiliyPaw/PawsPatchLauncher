from audit import *
import subprocess,shutil
def main():
 records=json.loads((O/'original-files.json').read_text());groups=collections.defaultdict(list)
 for r in records:groups[r['sha256']].append(r)
 unique=[g[0]for g in groups.values()];exe=P/'tools/oxipng.exe';logs=O/'optimization.log';start=time.monotonic()
 with logs.open('w',encoding='utf-8')as log:
  for off in range(0,len(unique),64):
   batch=unique[off:off+64];cmd=[exe,'-q','-o','2','--nx','--interlace','keep','-t','12',*[Q/'candidate/payload'/r['path']for r in batch]]
   p=subprocess.run(list(map(str,cmd)),env=os.environ,stdout=log,stderr=log);assert p.returncode==0
   if off%512==0 or off+64>=len(unique):print('OPTIMIZED_UNIQUE',min(off+64,len(unique)),'/',len(unique),flush=True)
 # Preserve every referenced path in the loose candidate; archive packing will
 # store identical contents once while keeping all resource names.
 for group in groups.values():
  src=Q/'candidate/payload'/group[0]['path']
  for r in group[1:]:shutil.copyfile(src,Q/'candidate/payload'/r['path'])
 def verify_one(r):
  raw=(Q/'candidate/payload'/r['path']).read_bytes();after=describe(raw)
  assert all(after[k]==r[k]for k in ['width','height','rgbaSha256','ihdr','nonIdatSha256']),(r['path'],'changed image data')
  assert after['size']<=r['size'];after.update(path=r['path'],beforeBytes=r['size']);return after
 with futures.ThreadPoolExecutor(max_workers=8)as pool:after=list(pool.map(verify_one,records))
 write(O/'optimized-files.json',after);summary=dict(passed=True,files=len(after),uniqueInputImages=len(unique),beforeBytes=sum(r['size']for r in records),afterBytes=sum(r['size']for r in after),exactPixels=True,exactAlpha=True,exactDimensions=True,exactIhdr=True,exactMetadata=True,seconds=round(time.monotonic()-start,3),tool=json.loads((O/'tool.json').read_text()),options=['-o','2','--nx','--interlace','keep']);write(O/'optimization.json',summary);print('LOSSLESS_FULL_SET_PASS',json.dumps(summary),flush=True)
if __name__=='__main__':main()
