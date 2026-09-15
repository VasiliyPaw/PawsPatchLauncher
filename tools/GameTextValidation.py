"""Preserve the engine's inline escapes when producing translated TGI text."""
import re
from collections import Counter

ENTITIES=re.compile(r'&[A-Za-z0-9#]+;|&')
FORMAT_TOKENS=re.compile(r'%%|%[-+#0]*(?:\d+)?(?:\.\d*)?(?:hh|ll|[hlLwI])?[diuoxXfFeEgGaAcCsSpn]|%\d+|\{\d+(?::[^}]+)?\}')

def validate_engine_text(source,translated):
    # Kohan interprets '&' as an escape introducer, not a Windows menu mnemonic.
    # An added '& Delete' label aborts the whole string-table load (log-272).
    if Counter(ENTITIES.findall(source))!=Counter(ENTITIES.findall(translated)):
        raise ValueError('Translation changes engine escape sequences: '+repr(source)+' -> '+repr(translated))
    if '\x00' in translated:
        raise ValueError('NUL in translated game text: '+repr(source))
    # The TGI loader and the string-table loader each process escapes. A JSON
    # escaped ASCII quote is therefore not a safe in-game quotation mark
    # (log-274: \\P in the Czech alliance tooltip). Use typographic quotes.
    if translated.count('"') > source.count('"'):
        raise ValueError('Added ASCII quotation mark in game text: '+repr(source))
    if translated.count('\\') > source.count('\\'):
        raise ValueError('Added backslash in game text: '+repr(source))
    if re.search(r'\.\s*kgm\b|City in |prefectures|weather condition|weather forecast|star name|object name \(optional\)',translated,re.I) and not re.search(r'\.\s*kgm\b|City in |prefectures|weather condition|weather forecast|star name|object name \(optional\)',source,re.I):
        raise ValueError('Unrelated translation annotation: '+repr(source)+' -> '+repr(translated))

def validate_format_tokens(source,translated):
    if FORMAT_TOKENS.findall(source)!=FORMAT_TOKENS.findall(translated):
        raise ValueError('Translation changes ordered format arguments: '+repr(source)+' -> '+repr(translated))
