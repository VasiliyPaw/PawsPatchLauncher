"""Normalize bridge depth state without reserializing art or geometry."""
import hashlib,io,struct,sys,time
from pathlib import Path

def repair(path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'outputs/bridge-model-ee2-20261109/deps'))
    time.clock=time.perf_counter
    from pyffi.formats.nif import NifFormat as N
    raw=path.read_bytes();model=N.Data();model.read(io.BytesIO(raw))
    assert model.version==0x0A010000
    changed=[];offset=0
    for block in model.blocks:
        if not isinstance(block,N.NiZBufferProperty):continue
        assert int(block.flags)&3==3
        if int(block.function)==3:continue
        # Serialize only this property and match its exact block bytes. In
        # 10.1.0.0 its comparison function is the final uint32 field. Never
        # regenerate vertices/materials/links just to change render state.
        stream=io.BytesIO();block.write(stream,model);old=stream.getvalue()
        assert old[-4:]==struct.pack('<I',int(block.function))
        new=old[:-4]+struct.pack('<I',3)
        at=raw.find(old,offset);assert at>=0,(path,offset)
        # Identical default properties can occur several times. Advance
        # monotonically through blocks to patch each serialized occurrence.
        raw=raw[:at]+new+raw[at+len(old):];offset=at+len(old);changed.append(at+len(old)-4)
    checked=model
    if changed:checked=N.Data();checked.read(io.BytesIO(raw))
    depths=[b for b in checked.blocks if isinstance(b,N.NiZBufferProperty)]
    assert depths and all(int(b.flags)&3==3 and int(b.function)==3 for b in depths)
    if changed:path.write_bytes(raw)
    return {'properties':len(depths),'corrected':len(changed),'comparisonOffsets':changed,
            'sha256':hashlib.sha256(raw).hexdigest(),'comparison':'LESS_EQUAL','depthTest':True,'depthWrite':True}
