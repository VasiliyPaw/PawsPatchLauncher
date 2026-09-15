"""Preserve the engine's inline escapes when producing translated TGI text."""
import re
from collections import Counter

ENTITIES=re.compile(r'&[A-Za-z0-9#]+;|&')

def validate_engine_text(source,translated):
    # Kohan interprets '&' as an escape introducer, not a Windows menu mnemonic.
    # An added '& Delete' label aborts the whole string-table load (log-272).
    if Counter(ENTITIES.findall(source))!=Counter(ENTITIES.findall(translated)):
        raise ValueError('Translation changes engine escape sequences: '+repr(source)+' -> '+repr(translated))
    if '\x00' in translated:
        raise ValueError('NUL in translated game text: '+repr(source))
