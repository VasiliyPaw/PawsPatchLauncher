# September 20 release verification

Source: `1d78bc47064a94de56243f8169656260573d66fe`.

- Launcher: 0.8.6, built by [the successful release workflow](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/35516211769). The independent [build and test workflow](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/35516210373) also passed.
- Arcane Wars stable: 0.3.3 promotes the previously published 0.3.2-beta.2 payload. Native feature equality was checked for all eight helpers. New AI, economy and presentation experiments are confined to the new beta.
- Arcane Wars beta: 0.4.0-beta.1 includes the accepted local changes. AI data and native behavior share one enabled-by-default setting. Bulk host bot controls belong to the Paw's Patch master option and remain available with AI improvements disabled.

## Checks

- Standard launcher suite: `PASS 26970`; additional AI settings and translation suite: `AI_OPTIONS_PASS 307`.
- Isolated account database: 6,514 checks. The bounded AI configuration migration was deployed transactionally and independently read back; no test accounts or rows were added to production.
- Final package matrix: 73,728 selections, 15,024 distinct package/helper plans and 73 verified archives, including all six text languages and four voice languages.
- Real installation fixture: 71 installation, setting, channel, fallback and uninstall transitions; 44 helper preflight invocations; 270 installed minimap-frame checks.
- The final matrix checks both native and file-based AI activation, the Maelstrom cost with siege balance enabled/disabled, presentation overlays, the eight helper variants, master-off cleanup, file-only fallback and rollback to the previous stable release.
- All six localized normal/expanded-color lobby layouts and new translated guide entries: 118 checks. Native compatibility identities: 48 checks against the eight built beta helpers; language overlays do not change compatibility, while AI settings do.
- Accepted AI data were preserved byte-for-byte in Git and verified against all 13 manifest digests.

No game was launched during release validation. Only the separate fixture was installed or rolled back; the user's game and saves were not modified. These checks do not replace live visual review or a new multiplayer match.

Detailed local evidence is under `outputs/release-20260920` in the task workspace. Public assets are verified by downloading them and comparing their hashes before signed catalogs are promoted. Vanilla and Immortals game packages remain unchanged.
