# Local 0.8.1 language preview

German and French game text and speech are separate optional packages for Vanilla,
Immortals and Arcane Wars, in both patch channels. They are not published.
Additional mod translations are intentionally outside this preview's scope.

`GameTextLanguage` extends old profiles without changing their EN/RU meaning.
Settings changes, configuration codes, diagnostics, mod switching and peer-copy
language preservation use the resolved text/speech choices. A language update is
offered only when the selected language uses that package. The mod library does
not fetch unselected languages; verified downloaded packages remain reusable offline.

`tools/PrepareEuropeanLanguages.py` consumes the previously extracted assets and
the current signed v2 catalogs. It produces local candidate payloads and four
independent packages, without modifying the source catalogs or publishing assets.

Package details:

- DE text: 62 string tables, version `1.0.0-preview.2`.
- FR text: 62 string tables plus bundled font resources, version `1.0.0-preview.3`.
- DE speech: 1,119 audio files, version `1.0.0-preview.1`.
- FR speech: 1,106 audio files, version `1.0.0-preview.1`.
- Localized TGIs use UTF-16. Old hotkey files are excluded to preserve current
  hotkey fixes. Audio stays independent of locale depots.
- Locale `AVars_Locale.tgi` must contain the full startup variables: the engine
  replaces that file rather than merging missing fields from the base locale.
- Font paths resolve against `Fonts/`; the French Village font uses
  `TrueType/VILLAGE.TTF`. The script checks bundled font references.

Validation on 2026-09-15:

- 23,242 core checks passed; build and standalone publish had no warnings/errors.
- 8,490 language checks covered 384 combinations: 3 mods × 2 channels × 4 text
  languages × 4 speech languages × patch on/off × data-only on/off.
- Eight resource reconciliations covered text-only selection, cross-language
  speech, EN/RU compatibility, restoration, and offline reuse with zero HTTP requests.
- 125 WPF checks across RU/EN/CS/DE/FR covered all four choices, Apply/Launch
  availability, reverting choices, and retained/older catalog behavior.
- Final DE/FR text packages were opened in separate Vanilla 1.3.72 game runs;
  both reached the main menu and exit confirmation with readable localized text.
- The final standalone EXE displayed the four text choices and independent
  French text/German speech. No settings were applied to the user's installed game.

Full campaign playback and additional mod-specific translations remain untested.
The preview sidecar uses local language sources. Its ZIP is for this computer;
language packages are not bundled into every launcher update.
