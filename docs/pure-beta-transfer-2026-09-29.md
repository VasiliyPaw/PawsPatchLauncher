# Vanilla / Immortals beta transfer

Requested scope: all applicable entries from `pure-transfer-audit-2026-09-27.md`,
except player city development, automatic militia deployment, camp/foundation
distribution, additional building slots and fractional kingdom points.

Stable Pure 0.3.0 and the Arcane Wars channels are outside this change.
Native code is shared where the engine ABI is identical. Data must come from
the selected mode; Arcane Wars city plans, unit costs and royal recipes are not
inputs to either pure package.

## Implemented scope

The separate `PAW_PURE_EXTENDED` composition imports the reviewed native fixes
from Arcane Wars beta.10: allied economy, camera, company position, exhaustion,
bot lobby, engine crash guards, AI policy r39 and the existing input/sound UI.
AI and wounded lair recovery are optional. The AI uses each mode's own unit
definitions, recipes and economic plans. Existing first-desync diagnostics and
fast saved-game transfer remain available.

Maps retain their native actors, camp counts and placement. Selectable limits
are extended to 16 kingdoms, 8 teams and 1152-square maps. Random map selection
uses the same synchronized seed permutation, reduced to the three native biomes.
It makes no additional simulation RNG calls. Time-of-day names and bot controls
are localized in all six languages. New localization files are present in the
base depot as well as its language overlay, as required by native enumeration.

Optional roaming profiles contain **13 exact authored `paws_roaming_*` company
definitions per mode**, with references checked against native units/templates.
The source is the existing authored company blocks, not newly invented groups
or militia substitutes. Additional companies, frequency and family hostility
have independent settings. No Arcane Wars unit-stat or SAI data files are copied.

The launcher stores choices independently for Vanilla, Immortals and Arcane Wars.
The `PB1` configuration extension is accepted only with the beta patch enabled,
and cannot be combined with file-only mode. Server projections derive its flags
from that explicit code. Existing configurations remain accepted.

## Verification

Evidence directory: `outputs/pure-beta-transfer-20260929` in the workspace root.
Final data are `data-11`; final native helpers are `helpers-11`; combined packages
are `candidate-7`; publication staging is `publication-3`.

| Check | Result |
| --- | --- |
| Launcher Release suite | 34,048 passed, including 6,149 Pure beta checks |
| Isolated database suite | 7,138 passed |
| Mode-native data and authored-company validation | 2,510 passed |
| Native composition | 804 guarded installs across 12 combinations / 3 image bases |
| Random-map transaction failure/rollback tests | 477 passed |
| Launcher UI | 352 passed, both modes/channels and six languages |
| Installed native main-menu launches | 16/16; final 12 beta cases plus four unchanged stable/disabled cases |
| Stable source regression | Four helpers rebuilt reproducibly; Pure, transfer and desync tests passed |
| Production configuration migration | Applied; nine independent readback checks passed |

The native tests reject overlapping hooks and verify original bytes before
mutation. All four new helpers have reproducible builds and explicitly report
excluded features as false. Stable source regression includes 36,571 Pure x86,
8,421 transfer x86 and 21,312 desync x86 checks, plus managed/hardware checks.

Interactive single-player 1024-square random maps loaded in Immortals and
Vanilla. Both AIs recruited companies and built city structures during the
smoke tests (130 seconds in Immortals and 261 seconds in Vanilla). The title,
localized bot panel, title-only tooltip and 100-pixel sound button were
visually checked. This is a startup/early-match check, not a full multiplayer
soak or exhaustive acceptance of every AI situation. The installed Steam game
is not the fixture; tests use a separate copy and restore shared user preferences.

## Publication gates

`tools/PreparePureBetaRelease.py` prepares only the Pure beta payload and launcher
metadata. Before catalog promotion it requires successful installation evidence,
server readback, immutable release asset hashes and exact release-tag commits.
It then verifies all four signed feeds and checks that stable Pure and Arcane
Wars game packages remain unchanged. Public readback is recorded separately in
`publication-3/readback.json` after the catalog commit is pushed.
