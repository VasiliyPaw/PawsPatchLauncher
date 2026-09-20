"""Idempotent data transforms for the next local Arcane update. No publication."""
import re

MAELSTROM='data/units/gauri/aw_maelstrom_destroyer.tgi'
SLAANRI_ENCLAVE='data/structures/slaanrienclaveaw/aw_slaanri_enclave.tgi'
AMBIENT={f'data/units/ambient/{n}.tgi' for n in
         ('eagle','snowowl','vulture','aw_duck','aw_ikaris','aw_raven','aw_spineling','lake_fish')}

def decode(blob):
    if blob.startswith((b'\xff\xfe',b'\xfe\xff')):return blob.decode('utf-16'),'utf-16'
    try:return blob.decode('utf-8-sig'),'utf-8-sig' if blob.startswith(b'\xef\xbb\xbf') else 'utf-8'
    except UnicodeDecodeError:return blob.decode('cp1251'),'cp1251'

def maelstrom_cost(blob):
    text,enc=decode(blob)
    assert re.search(r'(?im)^\s*IDS\s*=\s*maelstrom_destroyer\s*$',text)
    blocks=list(re.finditer(r'(?im)^(\s*)\[Upkeep\][^\r\n]*\r?\n(?P<body>(?:(?!\s*[\[\]}])[^\r\n]*\r?\n)*)',text))
    assert len(blocks)==1,'Unexpected Maelstrom economy layout'
    m=blocks[0];body=m['body'];nl='\r\n' if '\r\n' in text else '\n'
    if re.search(r'(?i)Kingdom_points_consumed\s*=',body):
        changed=re.sub(r'(?im)^(\s*Kingdom_points_consumed\s*=\s*)[^\r\n]+',r'\g<1>0.75',body)
    else:changed='\t\tKingdom_points_consumed = 0.75'+nl+body
    return (text[:m.start('body')]+changed+text[m.end('body'):]).encode(enc)

def hide_ambient(path,blob):
    assert path.lower().replace('\\','/') in AMBIENT
    text,enc=decode(blob);nl='\r\n' if '\r\n' in text else '\n';count=0
    matches=list(re.finditer(r'(?im)^\s*\[Thing Template=K2Ambient(?:Unit|Company)\]',text))
    assert matches,'Missing ambient definitions'
    for m in reversed(matches):
        start=text.index('{',m.end());depth=1;end=start+1
        while depth:
            depth+=(text[end]=='{')-(text[end]=='}');end+=1
        body=text[start+1:end-1]
        flags=re.search(r'(?im)^\s*\[Flags\][^\r\n]*\r?\n(?P<body>(?:(?!\s*[\[\]}])[^\r\n]*\r?\n)*)',body)
        if flags:
            segment=flags['body']
            if re.search(r'(?im)^\s*radar\s*=',segment):
                segment=re.sub(r'(?im)^(\s*radar\s*=\s*)[^\r\n]+',r'\g<1>false',segment)
            else:segment='\t\tradar = false'+nl+segment
            body=body[:flags.start('body')]+segment+body[flags.end('body'):]
        else:body=nl+'\t[Flags]'+nl+'\t\tradar = false'+nl+body
        text=text[:start+1]+body+text[end-1:];count+=1
    result=text.encode(enc)
    assert len(re.findall(r'(?im)^\s*radar\s*=\s*false\s*$',text))==count
    return result

def slaanri_guard_range(blob):
    text,enc=decode(blob)
    assert re.search(r'(?im)^\s*IDS\s*=\s*slaanri_enclave_center\s*$',text)
    # Match the existing center template (44), with a two-unit operational
    # margin. Do not change sight, supply, unit stats or offensive/defensive roles.
    for name,old,new in [('guard_range',28,44),('guard_operational_range',30,46)]:
        pattern=rf'(?im)^(\s*{name}\s*=\s*)({old}|{new})(\s*)$'
        text,count=re.subn(pattern,lambda m:m[1]+str(new)+m[3],text)
        assert count==1,'Unexpected Slaanri enclave range: '+name
    return text.encode(enc)

def apply_modules(modules,stock):
    """Mutate staged payload dictionaries only, before signing a later release.

    Keys are normalized game-relative paths. The original Arcane module is
    preserved. Old inverse and newer standalone option models both work.
    """
    arcane=modules['arcane-wars'];core=modules['pawpatch-core']
    original=arcane[MAELSTROM]
    assert not re.search(r'(?i)Kingdom_points_consumed\s*=',decode(original)[0]),'Unexpected original siege balance'
    for path in AMBIENT:
        before=core.get(path,arcane.get(path,stock.get(path)))
        assert before is not None,'Missing ambient source: '+path
        core[path]=hide_ambient(path,before)
    core[MAELSTROM]=maelstrom_cost(core.get(MAELSTROM,original))
    core[SLAANRI_ENCLAVE]=slaanri_guard_range(core.get(SLAANRI_ENCLAVE,arcane[SLAANRI_ENCLAVE]))
    # Original Maelstrom has no KP field: disabling restores the original data.
    modules.setdefault('siege-balance-standard',{})[MAELSTROM]=original
    if 'aw-siege-balance' in modules:
        modules['aw-siege-balance'][MAELSTROM]=maelstrom_cost(original)
