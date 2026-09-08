# Launcher 0.5.9 combined candidate

Locally built and verified on 2026-09-07. Not published. Public feeds and the live
game are unchanged. Only disposable test processes were started/closed, including
a failed-update rollback fixture. User launcher/game were not stopped or replaced.

## Changes

- Channel-independent launcher discovery from the first phase is retained.
- Ignore desyncs is a toggle, second after the required core; severity warning
  retained. Frequency is last, with Standard/x2/x4.
- Two x2 profiles: 33 files/33 active sources with new companies; 48 files/14
  active sources without. Derived from verified Standard archives. Only
  event_time/event_chance values change (interval x0.75, chance x1.5). No source
  hits the chance cap. Marauder chances and translation bytes are unchanged.
  All thirteen existing package hashes remain unchanged, including seven badge
  models and seven textures. Game EXEs unchanged.
- Apply compares installed modules plus native hostility/desync choices, ignoring
  channel labels and launcher-only preferences. Reverting choices disables it.
  State persists; Launch still applies pending changes. SP2 is supported in
  import/export and detailed comparison. Old feeds without x2 explain its absence.
- Matching installed files require no update, even without a cache copy.
  Cached different profiles/channels require Apply, not a false update. Enabling
  an uncached optional profile is Apply. New required/active packages not in cache
  remain updates. Latest archived packages for both channels stay protected by
  the existing cleanup policy.
- Apply appears for pending changes on any page, remains available across tabs,
  and fades after successful direct/launch application or reverting the choices.
  Below 1250px it moves above Launch.
  Open saves folder resolves the Windows Documents known folder plus
  Kohan2/data/Save; a missing folder shows a notice and is not created.
- Running-game Apply/update/launch attempts show a notice without diagnostics.
  Reconciliation checks again after preparation; launch checks before creation.
  The detector disposes process handles and never terminates the game.

## Evidence

- General suite: 5579 passed, including 4103 new policy checks covering 768
  configurations and 44 earlier signed launcher-update checks.
- WPF: 37 component checks per RU/EN, using real disposable miniature package
  installation, apply/revert, native changes, x2 transitions, old-feed handling,
  running and late-running guards, saves navigation and footer bounds.
- WPF regressions: 13 common-update checks and 16 channel checks per language;
  54 About checks per language; 16 independent native-toggle combinations.
- Real archive audit: 384 combinations per channel, 768 for this candidate.
  No unresolved overlapping files or lost translation keys.
- Seven non-monotonic real installation transitions across the six roaming
  profiles passed full file hashes, applied-state and all fourteen badge checks.
  Fixture: release_workspace_059/components-v2/install-test/d838c7006b5445a18eef026de0cb5249.
- RU/EN 1440x900 and RU 1050x680 previews inspected. Compact footer clipping found
  during visual QA was fixed and covered by bounds tests.
- Real isolated 0.5.8 -> 0.5.9 update passed with the revised helper, executable
  replacement, previous EXE retained and window ACK. Healthy/crash/timeout
  helper fixtures passed.

## Additional self-update regression

The initial deep fixture rolled back despite a successful window. Its ACK path
was 263 characters. Windows PowerShell/.NET Framework File.Exists returned false;
the same path with an extended prefix returned true and read the correct token.
The helper now uses extended paths for file operations, normal paths for process
startup. A deeper self-update-fixed fixture passes.

This cannot retrofit helpers inside already installed old versions. An old
launcher affected by a very long path may need one manual EXE replacement.

## Candidate and acceptance

Current EXE: release_workspace_059/pending-action/launcher/win-x64/PawsPatchLauncher.exe

SHA-256: 82727540B66F4F76141D32C4B2A8939E93CCC8EB5FF1C5582754FD0AB6911878

The previous components-v2 and credits EXEs are retained unchanged. The current
candidate includes the credit panel plus the pending-action visibility change
below. Its test configuration still uses the signed components-v2 feeds/packages.

The adjacent test-only launcher.config.json points to signed local candidate
feeds. Do not publish this local configuration; embedded production sources are
unchanged. The first-phase binary under release_workspace_059/launcher is superseded.

Archive audit: release_workspace_059/components-v2/audit/combinations.json.
Scalar evidence: release_workspace_059/components-v2/roaming-x2-audit.json.
Guide text was refreshed after archive auditing; package bytes did not change.

No live match was launched. x2 is an analytic event-rate target, not a guarantee
under population/occupation/gameplay constraints. Manual feel/multiplayer
acceptance and publication require the user. Friend/chat/save-server integration
is only a proposal; no service/account/hosting purchase was created.

## Arcane Wars help attribution, 2026-09-07

- Core help, opened with the question mark, now credits Arcane Wars author
  Darquan Mortis and shows the exact user-supplied invite https://discord.gg/krCK7DDwyz.
  Other component help remains unchanged. The hover tooltip also includes the
  author and invite as text; the clickable link is in the persistent help panel.
- A click dispatches only this HTTPS invite to the default browser. Duplicate
  pending requests are suppressed. Failure stays visible inside help and permits
  retry. No remote help text is interpreted as a URL or markup.
- WPF routed-navigation tests: 19 checks per RU/EN, including exact attribution,
  scope, link event wiring, bad/relative URI rejection, retry/duplicate behavior
  and layout at 1050x680 and 1440x900. Browser dispatch was injected; no real
  browser was opened and the Discord server/invite was not independently verified.
- General regression suite rerun: 5579 passed. PreviewRenderer build and local
  self-contained 0.5.9.0 build succeeded without warnings or errors.
- RU/EN 1440x900 and RU 1050x680 help previews inspected under
  release_workspace_059/credits/. No user application was closed or restarted;
  no game files or public release/feed was changed.

## Pending Apply action across pages, 2026-09-07

- Visibility follows actual unapplied installation/settings differences instead
  of the active page. Apply stays usable on all five pages, hides after successful
  application or reverting choices, and disables temporarily during a feed check.
- Status refreshes do not restart the transition. A new change during an active
  fade safely reverses it. Unapplied changes survive a running-game rejection.
- Launch keeps the same implementation, extracted into an awaitable method behind
  the existing click handler. Its normal preparation/reconciliation refresh hides
  Apply after settings are committed, including native settings and package changes.
- WPF component checks: 61 passed per RU/EN (previously 37), including all pages,
  direct application from Home, reverting, rapid fades, running-game rejection,
  feed-check locking, actual launch-path reconciliation and compact/wide bounds.
  The launch fixture uses inert local files and stops at the final running-game
  guard before Process.Start. No real game was launched.
- WPF update discovery (13), patch channel (16), and help credits (19) passed per
  language. General suite rerun: 5579 passed. Build, local single-file publish,
  and git diff whitespace check passed. User launcher/game and public feeds were
  not touched. Visual/real-game acceptance remains with the user.
