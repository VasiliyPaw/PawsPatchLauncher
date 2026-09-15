# Local 0.8.1 mod translations (2026-09-15)

German and French text now covers the existing translation keys of Immortals and
Arcane Wars in both channels, with Paw's Patch enabled or disabled. This is a local
candidate; no public release or remote feed was changed.

The reviewed catalog contains 1,939 keys per language:

- 1,887 added/changed Arcane Wars keys, including 8 additional kingdom labels;
- 23 Immortals labels and 4 optional text-fix aliases;
- 7 Paw's Patch settings labels and 18 city-assistant labels/tooltips/glyphs.

Four of the city-assistant values are resource glyphs, retained byte-for-byte.
Proper names are retained where appropriate. Russian corrections were used to
clarify the English source, not copied mechanically: Foundation Spot is **Bauplatz**
in German and **Emplacement de construction** in French; Apparations is translated
as apparitions, not the erroneous Russian applications wording. Spell costs and
other numbers, format placeholders, key IDs and resource glyphs are preserved.

Official base-game dictionaries remain authoritative for unchanged game keys.
The full `strings_data_K2.tgi` table is merged with the official selected language,
because locale files replace whole tables. A partial table would lose base strings.

## Package selection

`tools/PrepareEuropeanModLanguages.py` reads the review's existing DE/FR base feeds,
`game/localization/mod-de-fr.json`, and hash-verified source release packages.
It creates eight small text packages:

- `immortals-localization-de/fr`: Immortals dictionary and optional fix aliases;
- `localization-de/fr`: full Paw's Patch Arcane Wars dictionaries;
- `aw-localization-de/fr`: standalone Arcane Wars keyed display templates;
- `pawpatch-data-de/fr`: file-only Paw's Patch variant with the same keyed templates
  as its released RU counterpart.

Base dictionaries mount first, the selected mod dictionary second. Mod text mounts
have priority 225; the file-only variant preserves its existing priority 900.
Standalone reference templates are never applied over the full Paw's Patch core.
Every copied gameplay file is byte-identical to the corresponding released RU
variant; only locale dictionary contents and their mount file are new. No executable,
DLL, audio, font or RWD enters these packages. Speech remains independently selected.

The selector keeps compatibility with earlier 0.8.1 base-only language previews.
Translation updates affect only the selected mod/language. The mod library excludes
language packages from its download-all-components behavior; cached translations can
be switched offline.

## Evidence and limits

- Build: zero warnings/errors. Core suite: 23,571 checks passed.
- Language suite: 20,906 checks, 384 configurations, 40 real resource reconciliations,
  including offline reuse with zero HTTP requests. Configurations include all 3 mods,
  both channels, all 4 text/voice choices, Paw's Patch on/off and file-only on/off.
- Package compiler validates complete mod-key coverage, unchanged numbers and format
  placeholders, UTF-16 round trips, gameplay byte identity, and resolved new references.
- The final package generation additionally includes the city-assistant F1 text table;
  its four glyphs are kept unchanged. No simulation or native hook behavior was changed.
- No match was started and the user's installed game and open launcher were not modified.
  In-game layout acceptance is left to the user. The separate advanced city-rules window
  and native runtime status messages still have their existing RU/EN text; this change
  translates mod string tables, not those native controls.

To regenerate packages, pass the original base preview's `languages/feeds` directory
as `--base`, an output directory as `--out`, and a cache directory as `--source-cache`.
The script verifies source archives and their individual files against manifest hashes.
Local signed feeds must be regenerated after changing a translation. The TSV term
lists and `CompileEuropeanModCatalog.py` preserve the compilation rules; the committed
keyed JSON is the reproducible package input and requires no translation service.
