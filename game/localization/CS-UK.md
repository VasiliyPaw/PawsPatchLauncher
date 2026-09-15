# Czech and Ukrainian text — local 0.8.1 candidate

This candidate adds game **text**, independently of the four existing speech
languages. It is not a public release and does not add Czech or Ukrainian audio.

The catalogs cover 8,947 distinct source phrases: all 60 original text tables
(including campaign map titles and dialogue), 1,939 mod/patch keys reused from
the reviewed Russian/German/French catalog, and 54 managed patch UI strings.
Names, map data identifiers, costs, gameplay values and substitution tokens are
not localization-dependent network settings.

The initial draft was generated locally with `google/madlad400-3b-mt`, pinned to
revision `fa184c675da0b5c9e1c8694fccd4e12e2d422094`. Russian translations provide
a semantic reference. The TSV glossaries, spell costs, mission titles, tutorial
paragraphs and JSON corrections are authored editorial overrides. Long dialogue
was also translated sentence by sentence to avoid dropped endings. This is a
first complete text candidate, not a claim that every line has been reviewed by
a native-speaking editor. Player feedback is still needed for idiom and fit.

`CompileSlavicCatalog.py` verifies coverage, literal numbers, substitution tokens,
markup, empty text, repetition and unrelated translation boilerplate. The final
`text-cs-uk.json` and `mod-cs-uk.json` are the package inputs; the model is not
included in the launcher or language downloads.

`PrepareSlavicLanguages.py` prepares and audits local packages. Text depots use
only the selected language. Existing speech packages remain unchanged. Startup
mounts preserve separate speech selection. Signed local feeds identify modified
runtime archives by SHA-256; published release files are untouched.

Patch colors read the applied `paws_game_text.ini` once at helper startup. The
same 49 color IDs, ordering and RGB values are preserved for all six languages.
The color selector has its own `paws_color_random` label, separate from Random Map.
The beta lobby warning supports the six text languages without changing its
protocol or including language packages in the compatibility identity.

The extended private fonts retain the original glyphs and metrics, add missing
Czech/Ukrainian glyphs, and use distinct family names to avoid installed-font
collisions. Added outlines come from DejaVu Serif; its license is shipped with
each new text depot. The font audit and a GDI glyph coverage test are included.
