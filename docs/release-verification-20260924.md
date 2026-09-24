# Arcane Wars 0.4.0-beta.3 verification

This release packages the current local AI revision 35, lobby fixes, concise
localized tooltips, 100-pixel sound button with overlapping playback, and the
Gauri kingdom prerequisite for the 0.75-KP Maelstrom definition.

## Scope

Only Arcane Wars beta packages and their signed beta catalog are promoted.
Stable 0.3.3, launcher 0.8.6, legacy catalogs and other mods remain unchanged.
The build uses the explicit 0.4.0-beta.3 identity for all eight runtime helpers.
AI behavior and the default Nightmare difficulty remain gated by AI improvements.

The native AI payload was compared with the installed, observed r35 build:
157,262 bytes, with differences confined to the PE timestamp. This establishes
that publication does not introduce a different AI implementation.

## Validation

The canonical full helper build runs compiled x86 fixtures at relocated image
bases, managed transaction/rollback tests and each helper's offline modes.
The release also runs 601 sound-button and tooltip checks and the launcher suite.
The full build passed, including 58,568 AI transaction checks, 151,560 saved-owner
checks, 4,929 builder-fleet checks, 1,053 replacement-completion checks, 516
city-sharing checks and all 40 helper offline modes. The launcher suite passed
26,970 checks; the six-language packaged-data audit passed 93 checks.

Detailed build output and machine-readable reports are retained under
`outputs/release-20260924` in the release workspace.

The installation matrix resolves package precedence across languages, optional
modules, AI on/off, data-only and master-off modes. It also checks the Gauri
kingdom prerequisite wherever the 0.75-KP definition wins, the separate sound
resource, all helper variants, channel rollback and uninstall. Tests use an
isolated installation, preserve a save sentinel and the original executable,
and do not launch or alter the user's ongoing match.

The data audit checks all six localized menu overlays, native client list
height, removed bulk-panel hints, cost percentages, 100-by-100 geometry at
2560-by-1440, original button art and overlapping gold-mine audio definitions.

The first installation run caught localized overlays replacing the guarded
English family catalog. Publication stopped before any upload. The package
assembler now keeps that English table common to every language and modifies
only localized depots. A new package assertion rejects the incorrect override;
all eight helpers passed the reproduced Russian preflight without relaxing
any runtime hash guard. The corrected packages passed a fresh installation
matrix: 73,728 selections, 15,024 unique plans, 69 verified archives, all eight
helper variants, 18 frame checks, 30 preflights and 45 transitions. Save-sentinel
and stock-executable preservation, stable rollback and uninstall passed.
Stable packages are unchanged: the final run focuses actual install transitions
on beta while retaining the full selection matrix and stable installation/rollback.

The source commit `abaa43cfaaf74756dd7f07cba77d322e02f33414` also passed
[GitHub CI](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/36031020095).

## Observed match and limitations

Before release preparation, the ongoing r35 match supplied 77,261 diagnostic
events from 1:20:20 to 1:49:04 and 99 state snapshots. Two replacements completed:
combat value 208.63 to 319.89, and 179.43 to 319.89. Their new companies were hired
one game second after native disbanding. A third candidate was not confirmed as
a completed replacement. Four bots (Humans, Haroun and two Drauga) recruited up
to the company cap and each owned a kingdom.

That match did not exercise every race, the allied-city gift threshold, or all
new builder rules. The native regression fixtures stub some engine services;
they are not two-machine multiplayer acceptance. Browser room labels have not
received a new two-machine join test for this release.

A Drauga crafter delayed constructing a gold mine for at least eight game
minutes. The mine existed at the subsequent 1:56:40 observation, so this was not
a permanent stall. Its cause is unresolved and is disclosed in the release notes.
No claim is made that all large Goal-engine timing warnings are fixed.

The user's game was not restarted during release preparation. Lobby room name
and player count were not edited. All ten published assets passed anonymous
download, size, SHA-256 and GitHub digest checks before promotion of the signed
beta catalog. The prerelease tag resolves to the source commit recorded above.
