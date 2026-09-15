"""Second pass: resolve untranslated titles using the established Russian terms."""
import argparse, re, time
from pathlib import Path
from DraftSlavicTranslation import read,save,terms,invariant

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--full-reference',action='store_true');a=p.parse_args()
    import torch
    from transformers import AutoTokenizer,T5ForConditionalGeneration
    torch.set_num_threads(4)
    tokenizer=AutoTokenizer.from_pretrained(str(a.model),use_fast=True)
    model=T5ForConditionalGeneration.from_pretrained(str(a.model),torch_dtype=torch.bfloat16).to('cuda').eval()
    source=read(a.review/'source.json')['phrases'];glossary=terms()
    for code in ('cs','uk'):
        draft=read(a.review/(code+'-draft.json'));path=a.review/(code+'-refined.json');out=read(path) if path.exists() else dict(draft)
        progress=a.review/(code+('-reference-done.json' if a.full_reference else '-refined-done.json'));done=set(read(progress) if progress.exists() else [])
        pending=[]
        for en,e in source.items():
            if en in done or invariant(en) or en.strip().casefold() in glossary:continue
            # A title in Title Case is often mistaken for a brand by general MT.
            if a.full_reference:
                if len(en)>160 or '\n' in en:continue
            elif draft[en].strip().casefold()!=en.strip().casefold():continue
            ru=next((r for r in e['ru'] if re.search('[А-Яа-яЁё]',r)),None)
            if ru is not None:pending.append((en,ru))
        pending.sort(key=lambda p:len(p[1]));start=time.monotonic();print(code,'Russian reference titles',len(pending),flush=True)
        for i in range(0,len(pending),16):
            batch=pending[i:i+16];inputs=tokenizer(['<2'+code+'> '+r for e,r in batch],return_tensors='pt',padding=True).to('cuda')
            with torch.inference_mode():generated=model.generate(**inputs,num_beams=2,max_new_tokens=min(256,inputs.input_ids.shape[1]*3+15))
            for (en,ru),t in zip(batch,tokenizer.batch_decode(generated,skip_special_tokens=True)):
                out[en]=en[:len(en)-len(en.lstrip())]+t.strip()+en[len(en.rstrip()):];done.add(en)
            if i%80==0 or i+len(batch)==len(pending):save(path,out);save(progress,sorted(done));print(code,i+len(batch),'/',len(pending),round(time.monotonic()-start),'s',flush=True)
        save(path,out);save(progress,sorted(done))

if __name__=='__main__':main()
