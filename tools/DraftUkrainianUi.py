"""Local Ukrainian UI draft from authored Russian references, with intact line breaks."""
import argparse,json,re,time
from pathlib import Path

def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--languages',nargs='+',default=['uk']);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];pairs=read(a.review/'authored-pairs.json')['pairs'];base=read(root/'src/PawsPatchLauncher/Assets/Languages/cs.json')
    pairs.update(read(a.review/'feed-guide-pairs.json'))
    all_sources={en:pairs.get(en,en) for en in sorted(set(base)|set(pairs))}
    import torch
    from transformers import AutoTokenizer,T5ForConditionalGeneration
    torch.set_num_threads(4);tokenizer=AutoTokenizer.from_pretrained(str(a.model),use_fast=True)
    model=T5ForConditionalGeneration.from_pretrained(str(a.model),torch_dtype=torch.bfloat16).to('cuda').eval()
    for code in a.languages:
        existing={} if code=='uk' else read(root/('src/PawsPatchLauncher/Assets/Languages/'+code+'.json'))
        sources={k:v for k,v in all_sources.items() if k not in existing}
        parts={en:re.split(r'(\n+)',value) for en,value in sources.items()}
        segments=sorted(set(s.strip() for rows in parts.values() for s in rows if s.strip()),key=len)
        outpath=a.review/(code+'-segments.json');out=read(outpath) if outpath.exists() else {}
        pending=[s for s in segments if s not in out];start=time.monotonic()
        for i in range(0,len(pending),8):
            batch=pending[i:i+8];inputs=tokenizer(['<2'+code+'> '+s for s in batch],return_tensors='pt',padding=True).to('cuda')
            with torch.inference_mode():generated=model.generate(**inputs,num_beams=2,max_new_tokens=min(768,inputs.input_ids.shape[1]*3+20))
            out.update(zip(batch,tokenizer.batch_decode(generated,skip_special_tokens=True)))
            if i%40==0 or i+8>=len(pending):save(outpath,out);print(code,min(i+8,len(pending)),'/',len(pending),round(time.monotonic()-start),'s',flush=True)
        values={en:''.join(s if not s.strip() else s[:len(s)-len(s.lstrip())]+out[s.strip()].strip()+s[len(s.rstrip()):] for s in rows) for en,rows in parts.items()}
        save(a.review/(code+'-draft.json'),dict(existing,**values))
    save(a.review/'source-keys.json',all_sources)

if __name__=='__main__':main()
