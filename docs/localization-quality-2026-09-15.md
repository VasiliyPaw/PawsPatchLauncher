# Local 0.8.1: Czech startup and Slavic text corrections

Status: local test feed only. No public release. The launcher executable is unchanged.

## Evidence and causes

- Installed Immortals, Czech text, Russian speech, Paw's Patch disabled failed during startup in `log-274-error.log`. The exception was `Unrecognized single char escape sequence 'P'` while loading `Localization/strings_K2.tgi`. A generated ASCII quotation mark in the alliance tooltip had passed through TGI escaping and became an invalid inline escape. Authored text avoids that quoting and the validator rejects added ASCII quotes/backslashes.
- The original inventory regex omitted typed string identifiers (`|s`, `|dd`, `|*`, etc.). Thus 362 distinct formatted phrases remained in English. Both the inventory and mod-table readers now preserve the entire key. The 362 phrases are authored in Czech and Ukrainian with ordered formatting arguments checked.
- Unreviewed draft translations of fictional names included geographic annotations (`City in ...`, `.kgm`, etc.) and incorrect dictionary senses. Corrections use the original English context and the official Russian, German and French tables. Example: `drauga_barracks_name` is Russian `Полигон`, German `Ausbildungsstätte`, French `Salle d'épreuves`; it is a military training facility, not a geometric polygon. Corrections also cover buildings, units, spells, UI labels and original name-list references.
- Separate key corrections distinguish the spell `Fury` from the creature and the spell `Host` from a network host. English phrase identity alone is insufficient for those meanings.
- Immortals' 15 additional AI profiles originally exposed versioned names such as `Sledge_v106`. The shared `immortals-text-fixes` package now replaces only their top-level display names with stable string keys. The matching fallback and five localized tables provide friendly names. AI identifiers, behavior, costs and priorities remain byte-identical; the same AI files are used for every language.

## Validation

- Eight Python regression tests pass, including both startup escape failures, typed-key coverage, ordered printf arguments, context-sensitive labels, and rejected geographic annotations. Existing game and mod dictionaries pass 30,252 escape/annotation checks.
- Both local feeds contain 59 unique modules. Fourteen modules per channel change. Package verification checks 36,392 base-table rows, including 1,660 typed rows, across both languages and channels. Text-block stripping produces identical non-text source content. Runtime executables, voices and fonts are unchanged.
- The test runner builds with zero warnings/errors. Its existing isolated installer staging command now optionally accepts the mod, so the reported Immortals combination can be staged without modifying a user's installed game.
- Before the user's request to stop game launches: the isolated game loaded the string tables and main-menu UI for Vanilla/Czech, Immortals/Czech and Immortals/Ukrainian and remained alive for 24 seconds each without a startup exception. Each test process was then deliberately terminated; these are not completed matches or visual acceptance. Hashes of the user's personal game settings were unchanged. The final additional short UI-label/context corrections were validated statically after game launches were prohibited.
- No game was started after the user said they were playing. Do not resume game testing until they authorize it.

## Later manual acceptance

After the current game has closed, use the existing local 0.8.1 launcher to check for updates and apply. For each of Vanilla, Immortals and Arcane Wars, try Czech and Ukrainian text (six combinations); keep any existing speech language. Open the lobby AI list and tooltips, start a small match, select a settlement and inspect construction/unit requirements and notifications. With Paw's Patch enabled, also open F1. Public distribution remains out of scope.

Evidence: workspace `work/crash-20260915-czech-and-text-quality/`, candidate packages and signed feeds under `outputs/launcher-0.8.1-uk-ui/languages-quality-fix/`.
