"""Generate bounded, relocated startup guards from the existing offline image.
No game process is opened. Output is generated build data, not a game patch.
"""
import argparse, hashlib, json, pathlib, struct, sys

parser = argparse.ArgumentParser()
parser.add_argument('--work', type=pathlib.Path, required=True)
parser.add_argument('--out', type=pathlib.Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.work / 'pydeps_readable'))
import capstone

base = 0x460000
image_path = args.work / 'k2_runtime_1372_20260904.bin'
image = image_path.read_bytes()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
cs.detail = True
ranges = [
    ('packet_type_and_lobby_gate', 0x5b0009, 0x5b01df),
    ('normal_host_serializer', 0x5b189f, 0x5b196e),
    ('file_serializer', 0x5b27e8, 0x5b2817),
    ('sender_layout_and_progress', 0x5b91e8, 0x5b9275),
    ('sender_reset', 0x5b930a, 0x5b9323),
    ('sender_block_generation', 0x5b9496, 0x5b9584),
    ('transfer_status', 0x5b04f0, 0x5b052d),
    ('packet_timestamp', 0x5bc4b7, 0x5bc542),
    ('packet_buffer_capacity', 0x5bc16e, 0x5bc178),
    ('steam_receiver_capacity', 0x4e05a5, 0x4e05b1),
    ('sender_unsent_query', 0x5b8857, 0x5b887f),
    ('sender_metadata_index', 0x5b8c74, 0x5b8ca0),
    ('send_pass_reset_and_bandwidth', 0x5bbded, 0x5bbe8f),
    ('receive_contiguous_progress', 0x5b96f0, 0x5b975c),
    ('receive_timestamp', 0x5bc931, 0x5bc9a0),
]
blob = bytearray(struct.pack('<II', 0x31544650, len(ranges)))
manifest = []
for name, lo, hi in ranges:
    code = image[lo-base:hi-base]
    fixups = set()
    instructions = list(cs.disasm(code, lo))
    assert sum(i.size for i in instructions) == len(code), name
    for i in instructions:
        for op in i.operands:
            if op.type == capstone.x86.X86_OP_MEM and base <= (op.mem.disp & 0xffffffff) < base+len(image):
                assert i.disp_size == 4
                fixups.add(i.address-lo+i.disp_offset)
            elif op.type == capstone.x86.X86_OP_IMM and not (i.group(capstone.CS_GRP_CALL) or i.group(capstone.CS_GRP_JUMP)) and base <= (op.imm & 0xffffffff) < base+len(image):
                assert i.imm_size == 4
                fixups.add(i.address-lo+i.imm_offset)
    blob += struct.pack('<II', lo-base, len(code)) + code + struct.pack('<I', len(fixups))
    for offset in sorted(fixups):
        blob += struct.pack('<I', offset)
    manifest.append(dict(name=name, rva=lo-base, size=len(code), fixups=sorted(fixups), sha256=hashlib.sha256(code).hexdigest()))
args.out.mkdir(parents=True, exist_ok=True)
(args.out/'FastTransferGuards.bin').write_bytes(blob)
(args.out/'guards.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(image).hexdigest(), ranges=manifest), indent=2))
print(f'Prepared {len(ranges)} guarded regions, {sum(r["size"] for r in manifest)} bytes. No game launched.')
