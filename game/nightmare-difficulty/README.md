# Nightmare economic difficulty

Optional local Arcane helper flag: `-NightmareDifficulty`. `prepare.py` creates
additive `Handicap` and `SharedProperty` definitions with stable IDs
`handicap_paws_nightmare` / `property_handicap_paws_nightmare`. Existing five
economic levels are untouched. Only STRUCTURE_COST and RECRUIT_COST get +0.90.
The definition file must be `data/Game/handicaps_paws_nightmare.tgi`:
the real `index_k2.lst` loads `Game/handicaps*.tgi`, not `Game/*.tgi`.
Revision 1 used an unmatched filename; revision 2 fixes loading and the startup
guard. Runtime verification on 2026-09-21 confirmed all six definitions in order,
including the new entry after impossible. The original misplaced file is removed
by the guarded local migration after backup. Properties use the separate
`Properties/*.tgi` loader rule.
Native parsing negates those attributes (RVA 252D4A / 253155), resulting in
10% cost before other modifiers; the native 5% floor still applies.

No upkeep, time, strength or capacity modifier is added. AI behavior profiles
are separate: the default native selector (RVA 1E185B, called at 1E01F1) filters
compatible enabled profiles with difficulty >= HARD (1), and receives nation
and faction, not the economic-handicap index. Existing explicit profiles are
retained. No new AI profile or native selection patch is required.

The existing native lobby command resolves definitions by IDS and sends a
bounded definition index. All participants need matching definitions and
order; do not distribute data alone to old clients. The full helper compatibility
handshake changes with the binary. Saves store the handicap IDS rather than a
five-value enum. Offline codec tests are not a real two-machine network test.

Revision 3 makes this difficulty part of the AI improvements option. The two
gameplay definitions belong only to the optional ai-improvements package; turning
the option off removes them through the ordinary transactional installer. Startup
checks the applied AI state and rejects missing or leftover gameplay definitions.

All six locales are generated and installed by common UI/language packages.
Without the gameplay definitions these strings expose no difficulty. Startup
validates the selected translation without writing or recreating files. DataTests.cs
exercises all six languages, both option states, partial removal, repeat
validation, English fallback and missing/modified-file rejection.
