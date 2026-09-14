"""Reproduce beta.6 animations from hash-bound original KFs. Requires PyFFI 2.2.3.

Input directory mirrors validation.json paths, with stock Prophet KFs extracted
from Data.rwd and Conjuror KFs from clean Arcane Wars. Writes only --out.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import time

time.clock = time.perf_counter  # Compatibility with PyFFI 2.2.3.
from pyffi.formats.nif import NifFormat

def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()

def read(raw):
    stream = io.BytesIO(raw)
    data = NifFormat.Data()
    data.read(stream)
    assert stream.tell() == len(raw)
    return data

def serialized(obj, data):
    stream = io.BytesIO()
    obj.write(stream, data)
    return stream.getvalue()

def track(link, data):
    ctl = link.controller
    assert isinstance(ctl, NifFormat.NiKeyframeController)
    assert ctl.target is None and ctl.next_controller is None
    return (bytes(link.target_name), type(ctl).__name__, int(ctl.flags), float(ctl.frequency),
            float(ctl.phase), float(ctl.start_time), float(ctl.stop_time), serialized(ctl.data, data))

def main(args):
    repo = Path(__file__).resolve().parents[1]
    bound = json.loads((repo / 'game/prophet-animation/validation.json').read_text('utf-8-sig'))
    assert not args.out.exists(), 'Use a new output directory'
    movements = events = 0
    for entry in bound['files']:
        relative = Path(entry['path'])
        assert not relative.is_absolute() and '..' not in relative.parts and relative.suffix.lower() == '.kf'
        raw = (args.originals / relative).read_bytes()
        assert digest(raw) == entry['beforeSha256']
        data = read(raw)
        assert len(data.roots) == 1
        seq = data.roots[0]
        assert isinstance(seq, NifFormat.NiControllerSequence) and seq.num_controlled_blocks == 27
        assert [i for i, link in enumerate(seq.controlled_blocks) if link.target_name == b'Plane01'] == [9]
        kept = [(bytes(link.target_name), link.controller) for i, link in enumerate(seq.controlled_blocks) if i != 9]
        before = [track(link, data) for i, link in enumerate(seq.controlled_blocks) if i != 9]
        before_events = serialized(seq.text_keys, data)
        names = bytes(seq.name), bytes(seq.text_keys_name)
        seq.num_controlled_blocks = len(kept)
        seq.controlled_blocks.update_size()
        for link, (name, ctl) in zip(seq.controlled_blocks, kept):
            link.target_name, link.controller = name, ctl
        output = io.BytesIO()
        data.write(output)
        candidate = output.getvalue()
        checked = read(candidate)
        after = checked.roots[0]
        assert after.num_controlled_blocks == 26
        assert before == [track(link, checked) for link in after.controlled_blocks]
        assert before_events == serialized(after.text_keys, checked)
        assert names == (bytes(after.name), bytes(after.text_keys_name))
        assert digest(candidate) == entry['afterSha256']
        assert candidate == (repo / 'game/prophet-animation/assets' / relative).read_bytes()
        target = args.out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(candidate)
        movements += len(before)
        events += 1
    assert movements == 572 and events == 22
    print(json.dumps(dict(reproducedFiles=events, preservedMovementTracks=movements, preservedEventTracks=events)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--originals', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args())
