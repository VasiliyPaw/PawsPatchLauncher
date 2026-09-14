"""Local diagnostic candidate; remove the verified dangling bow material track.

No simulation, actor definitions, base archive or executable changes.
"""
from pathlib import Path
import sys,time,io,hashlib,json,argparse
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('original',type=Path)
parser.add_argument('output',type=Path)
parser.add_argument('--pyffi-path',type=Path)
args=parser.parse_args()
if args.pyffi_path:sys.path.insert(0,str(args.pyffi_path))
time.clock=time.perf_counter  # PyFFI 2.2.3 compatibility with current Python.
from pyffi.formats.nif import NifFormat

def read(raw):
    stream=io.BytesIO(raw); data=NifFormat.Data(); data.read(stream)
    assert stream.tell()==len(raw), 'Unexpected trailing or missing bytes'
    return data
def serialized(block,data):
    out=io.BytesIO();block.write(out,data);return out.getvalue()
def track(link,data):
    c=link.controller
    return (bytes(link.target_name),type(c).__name__,int(c.flags),float(c.frequency),float(c.phase),
            float(c.start_time),float(c.stop_time),serialized(c.data,data))

original=args.original.read_bytes()
assert hashlib.sha256(original).hexdigest()=='1bdbebfaf0d6272eae094c1dce75f5dc3b6530a18e0661f43a5c549f8d4bc493'
data=read(original);seq=data.roots[0]
assert seq.name==b'RangerDie1' and seq.num_controlled_blocks==27
bad=[i for i,c in enumerate(seq.controlled_blocks) if isinstance(c.controller,NifFormat.NiMaterialColorController)]
assert bad==[9]
removed=seq.controlled_blocks[9]
assert removed.target_name==b'bow\nPROP\nNiMaterialProperty'
assert removed.controller.target_color==3  # Emissive/self-illumination only.
before=[track(c,data) for i,c in enumerate(seq.controlled_blocks) if i!=9]
before_keys=serialized(seq.text_keys,data)
links=[(bytes(c.target_name),c.controller) for i,c in enumerate(seq.controlled_blocks) if i!=9]
seq.num_controlled_blocks=len(links);seq.controlled_blocks.update_size()
for link,(name,controller) in zip(seq.controlled_blocks,links):
    link.target_name=name;link.controller=controller
out=io.BytesIO();data.write(out);candidate=out.getvalue()
verified=read(candidate);vseq=verified.roots[0]
assert vseq.num_controlled_blocks==26
assert all(isinstance(c.controller,NifFormat.NiKeyframeController) for c in vseq.controlled_blocks)
assert before==[track(c,verified) for c in vseq.controlled_blocks], 'Movement track changed'
assert before_keys==serialized(vseq.text_keys,verified), 'Animation events changed'
assert vseq.name==seq.name and vseq.text_keys_name==seq.text_keys_name
path=args.output
path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(candidate)
report={'status':'validated_asset',
        'source':'stock Data.rwd: Units/Human/Ranger/RangerDie1.KF',
        'originalSha256':hashlib.sha256(original).hexdigest(),
        'candidateSha256':hashlib.sha256(candidate).hexdigest(),
        'originalBytes':len(original),'candidateBytes':len(candidate),
        'removedTrack':'bow / PROP / NiMaterialProperty; emissive color',
        'movementTracksExactlyPreserved':len(before),'animationEventsExactlyPreserved':True,
        'graphicsDriverCrashesAddressed':False}
path.with_suffix('.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
