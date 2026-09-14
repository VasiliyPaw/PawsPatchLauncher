# Arcane Wars beta.7 validation — 2026-09-14

Release: Paw's Patch 0.3.0-beta.7. Launcher stays 0.8.0.

## Automated validation

- Launcher suite: 23,085 checks passed.
- Lobby identity suite: 91 checks passed, including EXE-only changes at an equal
  patch label and independence from language/settings culture and ordering.
- Native codec and installation rendezvous: 2,613 checks passed; parser/format:
  225. The bit codec executes actual 1.3.72 instructions in a separate test process.
- All eight generated native helpers built and passed their existing quiet startup,
  common UI, lobby colors, city assistant and fast transfer test modes.
- City planner/policy/resource/automation/transport and native transfer suites pass;
  accepted city policy 15, transfer R2 and previous graphics/animation fixes remain.
- Signed package selection coverage: 18,432 combinations of mod/channel, components,
  language and incompatible-game fallback. Actual installer exercises all eight
  helper selections and uninstall, preserving the save sentinel.
- Package scope audit permits only nine helper copies and the beta menu label to
  change across core/common-ui/player-colors archives. Every other payload byte is
  compared to beta.6. Stable feeds, launcher, Vanilla and Immortals are unchanged.

## Actual Steam installations

Both existing Steam game folders were updated through ModuleInstaller, with their
applied settings preserved. Both use stock k2.exe 1.3.72 SHA256
`1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.

- PC fresh launch PID 2844: LOBBY_COMPATIBILITY_READY and QUIET_READY at
  2026-09-14 23:15:02 local log time.
- VM fresh launch PID 6236: same markers at 23:15:20.
- Both generated identity digest:
  `9647F7CE16E5EB085744805B116AD5109955C0A52CBEE605628616F7229C7799`.
- An observed live Steam lobby on the PC subsequently contained both Paw and
  nekitars, with the join notification. The user performed this join during the
  Computer Use session; matching-configuration admission is confirmed.
- Earlier user acceptance: temporary native hook on beta.4 VM correctly rejects
  entry to beta.6 PC, showing the real game/mod/patch requirements. Screenshot
  VirtualBoxVM_5einnDBzAW.png supplied by the user.

Startup tests caught two issues before publication: AppData library loading failed
with Windows 126 on the PC; loading from the game control directory succeeds.
On the VM, starting the install thread while all other threads were suspended
blocked on Windows DLL notifications. The ready/go/result worker now completes
thread attachment before suspension and reports completion before thread detachment.
Both final fresh launches passed after this correction.

The displayed different-version layout and matching join are live-tested. EXE-only
and component-only differences are covered by identity/codec tests, not separately
claimed as live Steam joins. Legacy unmodified peers, wrong passwords and native
data mismatch are not newly live-tested. Their original checks remain in the code.
No long-running match or save-transfer soak was run for this lobby-only update.
The user's running launcher was not restarted.
