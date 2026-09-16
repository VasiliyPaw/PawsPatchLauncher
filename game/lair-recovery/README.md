# Lair survivor r3 (Kohan II 1.3.72, Arcane Wars beta.9)

Promoted from the manually accepted beta.8 standalone test to beta.9. Build
the eight release helpers with `-CityAssistant -LobbyCompatibility -LairRecovery`.
`-LairWoundedTest` additionally enables the standalone-only data-root checks.
The native r3 payload is identical to the accepted test; the package version
and release helper identities are advanced together. Uses the complete startup
helper with guarded native hooks.
The stock game EXE, save format, kingdom owners and native healing rates
are unchanged. The helper only patches the fresh game process it launches.

## Behavior

- A defender that returned alive can redeploy with its remaining HP.
- Deployment carries the stored HP fraction into the created actor instead of
  granting a free heal. Native maximum-HP modifiers are respected.
- A dead defender must regenerate to full HP. Partial regeneration is not a
  surviving wounded defender, even if another survivor is ready in that lair.
- UI counts, organization selection, individual count and individual chooser
  use the same readiness rule for actual KKC_LairComponent buildings.
- Ordinary city militia retains native readiness and deployment behavior.
- This is component-based, not restricted to fire dragons or a kingdom ID.

## State and save compatibility

The two unused padding bytes at Denizen group +0x0e hold a survivor marker.
Both native allocation paths initialize them. Actual return paths set the
marker; deployment, death and regeneration starting from zero clear it. Native
group transfer carries the marker. Category/role bytes +0x0c/+0x0d are preserved.

Native saves contain group actor ID and HP ratio, but no death/return provenance.
The save format is deliberately unchanged. On **every load**, partially healed
defenders already inside are conservatively treated as unknown and wait for
full recovery; a surviving deployed actor can still return and acquire the
marker. The marker is not persisted across save/reload, including newly made
saves. Fully healed defenders work immediately. No inferred resurrection and
no rewriting of saved ownership.

## Evidence and validation

The live 2026-09-16 read-only capture is documented in
`../diagnostics/lairs/README.md`. It proved that a first wounded youngling
monopolized its native resupply category, leaving two almost-healthy returned
dragons waiting behind it. The old deployment threshold required full HP.
The capture does not prove a kingdom migration caused the behavior.

`build_native.py` verifies the stock runtime SHA-256 and hook bytes, builds a
4096-byte payload and verifies relocation at three image/cave layouts. Fifteen
guarded hooks include initialization and lifecycle metadata. Unknown runtime
bytes reject installation. Partial installation is rolled back and verified;
an allocation is retained if rollback cannot be verified.

`test_native.py`: 2664 native checks, including actual ID-matched return,
death and resupply functions; dead vs wounded choice; both HP carry-over paths;
UI agreement; both group allocators; conservative load; group transfer; city
isolation; three ASLR layouts. Container/owner lookup fixtures are explicitly
bounded. No game is launched by these tests.

`LairRecoveryTests.cs`: 3981 transaction checks with faults at every operation,
including partial writes, failed rollback and mismatched executable bytes.

The full beta build's city, saved-owner, lobby and transfer regressions passed.
All eight helper variants compiled and passed their normal offline self-tests.
Live fire-dragon combat with r3 passed the user's wounded-return and
dead-replacement checks; the capture evidence is recorded below. Separate
storm-creature combat and a full dead-to-fully-regenerated live cycle are not
claimed by that session (the full regeneration threshold passed native tests).

## Manual acceptance

Run the local `PawsLairSurvivorTest.exe`, which locates the installed Steam game.
Use a lair that has fully recovered, or a save made before its first fight.
Wound a defender, kill another, retreat, and re-attack after the survivor returns.
The wounded survivor should emerge with its retained health; the killed slot
must stay inside until full regeneration. Repeat for a storm-creature lair.
An already-wounded home group from a loaded save is subject to the conservative
load rule above. Do not use that initial state as a return-event test.

The helper's exact name and SHA-256 are included in lobby compatibility, so this
local test cannot silently join a normal beta.8 lobby as the same executable.

## External EXE startup correction

The first r3 user launch (2026-09-16 17:29) installed all lair hooks, then the
common UI loader failed because it looked for `paws_patch_versions.ini` beside
the external test EXE. The incomplete fresh process was stopped by the existing
startup cleanup. No save had been loaded. The same location assumption also
affected the menu-layout check, player palette and text catalog.

The corrected local build uses the verified installation root consistently for
those readers and validates them before starting the game, including preflight.
The installed language is loaded only after selecting the data directory. The
published helper path behavior is unchanged (the correction is compiled under
`LAIR_RECOVERY_TEST`). The lair native payload remains r3, byte-for-byte.

`test_local_launch_data.ps1` verifies the actual standalone EXE from a directory
with no adjacent INI/layout files: installed root, a separate Ukrainian catalog,
missing versions/main layout/palette/color layout, invalid catalog, and complete
installation preflight. Eight checks passed; no game launched. The full native
and managed beta regression suite also passed for the rebuilt helpers.

## Live acceptance of corrected standalone EXE (2026-09-16)

Game PID 30660 reached `QUIET_READY` at 17:44:55, with the r3 lair hooks active
at image 0x00E40000, cave 0x00D40000. User reported both checks successful:
wounded survivors redeployed, and killed defenders did not redeploy early.

Read-only session `20260916-174930-27604` contains 616 frames over game times
3033.0--3339.0625. Target fire-dragon lair ID 92 at (18, 227) had 508 complete
target samples. The unrelated global frame remained incomplete; no whole-world
completeness claim is made. Native survivor markers were visible in group
padding and cleared on deployment/death.

Observed examples: a young dragon redeployed with exactly 2744.1/3600 HP, an
adult with 5859.6/6000 HP, and another wounded sortie retained 2120.589/3600 HP.
After the final fight all five slots were observed reset to zero. None was
observed redeployed before the lair reached zero HP; the recovering first
youngling reached 228/600 HP and remained inside. Other two dragon lairs showed
no deployment changes in this observation window.

The collector was stopped and archived after the completed test without
stopping or changing the running game. ZIP:
`D:\SteamLibrary\steamapps\common\Kohan II\Logs\PawsLairDiagnostics\20260916-174930-27604.zip`
(1,210,193 bytes). This archive describes the accepted local test; the beta.9
publication contains the normal eight helper variants, without the collector.
