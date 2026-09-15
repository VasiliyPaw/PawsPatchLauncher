"""Resumable local model draft. Authored glossary wins; output still needs review."""
import argparse, csv, json, re, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(p,obj):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n','utf-8');tmp.replace(p)
def terms():
    with (ROOT/'game/localization/slavic-terms.tsv').open(encoding='utf-8') as f:
        return {r['English'].casefold():r for r in csv.DictReader(f,delimiter='\t')}
def invariant(s):
    return not re.search('[A-Za-z]',s) or bool(re.fullmatch(r'[\w./\\:\-\s]*_[\w./\\:\-\s]*',s)) or bool(re.fullmatch(r'(?:\d+|[^A-Za-z])*',s)) or s in ('Paw’s Patch','Paw\'s Patch','Arcane Wars','Immortals','Vanilla')
def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--batch',type=int,default=32);a=p.parse_args()
    assert (a.model/'verified.sha256').read_text().strip()=='66ff5f8fcaf92291da486fdfbd4d5233cec90e1359348a56e3172c978b3a76d4'
    import torch
    from transformers import AutoTokenizer,T5ForConditionalGeneration
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=True
    tokenizer=AutoTokenizer.from_pretrained(str(a.model),use_fast=True)
    model=T5ForConditionalGeneration.from_pretrained(str(a.model),torch_dtype=torch.bfloat16).to('cuda').eval()
    source=read(a.review/'source.json')['phrases'];glossary=terms()
    for code in ('cs','uk'):
        path=a.review/(code+'-draft.json');output=read(path) if path.exists() else {}
        for s in source:
            if invariant(s):output[s]=s
            elif s.strip().casefold() in glossary:
                value=glossary[s.strip().casefold()][code]
                output[s]=s[:len(s)-len(s.lstrip())]+value+s[len(s.rstrip()):]
        pending=sorted((s for s in source if s not in output),key=lambda s:len(s))
        start=time.monotonic();print(code,'remaining',len(pending),'total',len(source),flush=True)
        i=0;batch_number=0
        while i<len(pending):
            size=min(a.batch,8 if len(pending[i])>80 else a.batch)
            texts=pending[i:i+size]
            inputs=tokenizer(['<2'+code+'> '+s.strip() for s in texts],return_tensors='pt',padding=True).to('cuda')
            length=min(512,max(32,int(inputs.input_ids.shape[1]*3)+15))
            with torch.inference_mode():
                generated=model.generate(**inputs,num_beams=2 if inputs.input_ids.shape[1]<64 else 1,max_new_tokens=length)
            for s,t in zip(texts,tokenizer.batch_decode(generated,skip_special_tokens=True)):
                output[s]=s[:len(s)-len(s.lstrip())]+t.strip()+s[len(s.rstrip()):]
            if batch_number%5==0 or i+len(texts)==len(pending):
                save(path,output);print(code,'translated',i+len(texts),'/',len(pending),'seconds',round(time.monotonic()-start),flush=True)
            i+=len(texts);batch_number+=1
        save(path,output)
    print('Drafts complete; review required.',flush=True)

if __name__=='__main__':main()
