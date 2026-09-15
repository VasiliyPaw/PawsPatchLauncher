"""Keep original game glyphs/icons; add missing CS/UK outlines from DejaVu."""
import io
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen

LETTERS='ČčŘřĚěŤťĎďŇňŮůÁáÉéÍíÓóÚúÝýŠšŽžҐґЄєІіЇїАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЮЯабвгдежзийклмнопрстуфхцчшщьюя’–—…→'

def extend(original,fallback):
    font=TTFont(io.BytesIO(original));donor=TTFont(fallback)
    cmap=font.getBestCmap();donor_map=donor.getBestCmap();glyphs=donor.getGlyphSet()
    missing=sorted(set(map(ord,LETTERS))-set(cmap))
    assert set(missing)<=set(donor_map),('missing fallback glyphs',set(missing)-set(donor_map))
    scale=font['head'].unitsPerEm/donor['head'].unitsPerEm
    order=list(font.getGlyphOrder());original_order=list(order)
    original_cmap=dict(cmap);original_metrics=dict(font['hmtx'].metrics)
    for code in missing:
        name='paw_uni%04X'%code;source=donor_map[code]
        recording=DecomposingRecordingPen(glyphs);glyphs[source].draw(recording)
        pen=TTGlyphPen(None);recording.replay(TransformPen(pen,(scale,0,0,scale,0,0)))
        font['glyf'][name]=pen.glyph();order.append(name)
        width,lsb=donor['hmtx'][source];font['hmtx'][name]=(round(width*scale),round(lsb*scale))
        for sub in font['cmap'].tables:
            if sub.isUnicode() and sub.format in (4,12):sub.cmap[code]=name
    font.setGlyphOrder(order);font['maxp'].numGlyphs=len(order)
    # Distinguish the private extended face from an old installed copy. Otherwise
    # GDI can select that copy by family name and lose the added characters.
    old_family=font['name'].getDebugName(1) or 'GameFont'
    family='Paw Kohan '+old_family
    for record in list(font['name'].names):
        if record.nameID in (1,3,4,6,16,21):
            value=family.replace(' ','') if record.nameID==6 else family
            font['name'].setName(value,record.nameID,record.platformID,record.platEncID,record.langID)
    output=io.BytesIO();font.save(output);result=output.getvalue();check=TTFont(io.BytesIO(result))
    assert all(check.getBestCmap()[c]==g for c,g in original_cmap.items())
    assert all(check['hmtx'][g]==metric for g,metric in original_metrics.items())
    assert check.getGlyphOrder()[:len(original_order)]==original_order
    assert set(map(ord,LETTERS))<=set(check.getBestCmap())
    # Glyph slots used for resource/smiley icons, and all existing outlines, stay exact.
    for name in original_order:
        assert check['glyf'][name].compile(check['glyf'])==font['glyf'][name].compile(font['glyf']),name
    return result,dict(added=len(missing),originalGlyphs=len(original_order),originalMetricsPreserved=True)
