"""Translate long dialogue one complete sentence at a time to prevent omissions."""
import argparse,json,re,time
from pathlib import Path
from DraftSlavicTranslation import read,save

def main():
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);p.add_argument('--model',type=Path,required=True);a=p.parse_args()
    import torch
    from transformers import AutoTokenizer,T5ForConditionalGeneration
    torch.set_num_threads(4)
    tokenizer=AutoTokenizer.from_pretrained(str(a.model),use_fast=True)
    model=T5ForConditionalGeneration.from_pretrained(str(a.model),torch_dtype=torch.bfloat16).to('cuda').eval()
    source=read(a.review/'source.json')['phrases'];sentences={}
    for en in source:
        if len(en)<=160 or '\n' in en or re.search(r'\s{3,}Cost:',en):continue
        parts=re.split(r'(?<=[.!?])\s+(?=[A-Z])',en.strip())
        if len(parts)>1:sentences[en]=parts
    unique=list(dict.fromkeys(s for parts in sentences.values() for s in parts))
    for code in ('cs','uk'):
        path=a.review/(code+'-sentences.json');out=read(path) if path.exists() else {}
        pending=[s for s in unique if s not in out];start=time.monotonic()
        for i in range(0,len(pending),8):
            batch=pending[i:i+8];inputs=tokenizer(['<2'+code+'> '+s for s in batch],return_tensors='pt',padding=True).to('cuda')
            with torch.inference_mode():result=model.generate(**inputs,num_beams=2,max_new_tokens=min(512,inputs.input_ids.shape[1]*3+20))
            out.update(zip(batch,tokenizer.batch_decode(result,skip_special_tokens=True)))
            if i%40==0 or i+8>=len(pending):save(path,out);print(code,min(i+8,len(pending)),'/',len(pending),round(time.monotonic()-start),'s',flush=True)
        final={en:' '.join(out[s].strip() for s in parts) for en,parts in sentences.items()}
        save(a.review/(code+'-long.json'),final)
    save(a.review/'long-text-audit.json',dict(paragraphs=len(sentences),sentences=len(unique),method='All source sentences translated separately; editorial overrides applied afterwards.'))

if __name__=='__main__':main()
