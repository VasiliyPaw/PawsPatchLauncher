# Arcane Wars 0.4.0-beta.2 verification

The release packages the accepted AI revision 31, city plans, observer backgrounds
and gold-mine sound button. Nightmare is available only with **AI improvements**
enabled. The six-language changelog separates bot changes from general changes.

## Scope and build

- Built all eight runtime helpers with the 0.4.0-beta.2 identity. Their feature
  reports require AI revision 31, Nightmare revision 3 with the AI-option gate,
  foundation distribution revision 2 and the two engine crash guards.
- The full helper build completed its native, emulated and managed regression
  suites. In particular: 56,648 AI transaction checks, 4,287 builder-fleet checks,
  14,268 recruitment-accounting checks, 7,416 large-lair checks and 6,423 expansion
  pulse checks passed. Native service stubs are explicitly identified by the
  individual suites; these counts do not represent played matches.
- Nightmare data: 39 checks across six languages, both option states, missing
  and modified files. Disabled startup does not recreate removed definitions.
- Foundation distribution: 16,104 count checks, 4,016 placement checks,
  312 transaction checks and 69 isolated Windows memory checks.
- Engine guards: 126 native cases, 217 transaction checks and 52 Windows probe
  checks. The guards cover specific animation-target and absent-client faults;
  they are not a general crash or graphics-driver fix.
- Launcher regression suite: **26,970 passed**. Sound button native suite:
  **481 passed**. The six city-plan tests passed separately.

## Packaging checks

Packages are derived from the previously signed beta catalog. Ten Arcane Wars
packages change. Stable 0.3.3, launcher 0.8.6, legacy channels, Vanilla and
Immortals payloads remain unchanged.

The final package composition checks the effective file after every overlay.
An initial isolated launch caught an old map template in common-ui overriding
the new core template. Both runtime layers now contain the same verified new
template, and the installation matrix checks all five foundation data files.
No failed candidate was published.

The completed installation matrix passed **73,728 selections**, **15,024 unique
plans**, 69 verified archives, all eight helpers, 270 installed frame checks,
**71 installation transitions** and **44 helper preflights**. The matrix includes
AI on/off, every language overlay, data-only, master-off, channel rollback and
uninstall; it preserves a save sentinel and the original game executable.

Three actual native main-menu launches passed separately: Nightmare enabled,
disabled, then enabled again. Read-only process inspection found six handicap
definitions, five stock definitions, then six definitions respectively. The
isolated test processes exited after inspection. User preferences and UVars were
byte-identical to their pre-test backups immediately after these three launches.

The generated button layout matches every non-comment definition in the accepted
in-game layout. Byte differences are limited to line endings and correction of
an outdated size comment. Observer backgrounds and the annotated button image
retain their accepted hashes.

## Interactive evidence and limits

The accepted local game loaded the saved match, advanced from 28:37 to 30:20 and
was paused. Screenshots show the 150-by-150 frame, 145-by-145 image with red arrows
and a circle, and the F1 panel covering the button. Clicking and button appearance
were checked; audible playback was not independently recorded in this pass.
The button references the native gold-mine selection sound.

Before release runtime checks, the match was saved separately and exited through
the game UI. Test launches use an isolated installation. No lobby room-name or
player-count controls are edited.

This release verification is not a new full-match progression test for all six
races or a two-machine multiplayer acceptance test. The saved match used for UI
acceptance no longer had an active major bot army and cannot establish those
claims.

## Publication

The prerelease `patch-0.4.0-beta.2` points to source commit
`85f875f46b4afa398d588515a75ba6bf62c8cdb4`. All ten public release archives were
downloaded again and matched their prepared sizes and SHA-256 digests before
the beta catalog was promoted. No stable or launcher catalog was promoted.

After inspecting the installed game's menus, its automatic preference writes
were preserved separately for diagnosis and the pre-test Preferences.rup was
restored while the game was closed. Preferences.rup and UVars.tgi were verified
byte-identical to their backups again after relaunch. The game was left at the
main menu; the separately saved match remains intact. No room-name or
player-count controls were changed.
