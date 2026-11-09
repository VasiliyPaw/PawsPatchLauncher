# Launcher usability test — 2026-11-09

Unpublished preview on source base `08263495f58d64184bed3a86ba9a0e570a7329f5`
(launcher 1.0.11). No Git push, release, tag or signed feed changes were made.
Unrelated game research, monitor and earlier test changes were preserved.

## Changes

- File transport pause/resume, cancellation while paused, persistent speed caps,
  inactivity timeout/retries and gates before verified downloads can proceed to
  installation. Network metadata/account traffic is not throttled.
- Persisted main install/update intent records a signed archived release identity,
  configuration and game directory. A new process offers explicit continuation;
  it does not automatically write game files or resume in a different directory.
  Dismissing intent does not delete downloads or game data.
- Actionable inline error help and retry of persisted installation intent.
- Modeless read-only gameplay comparison from profiles, canonical gameplay-only
  differences, with honest independent version status and no file compatibility claim.
- Bounded progress dispatcher cadence (120 ms, latest sample retained), accurate
  speed reset after pause/rate changes, background profile-avatar decoding.
- Account-level independent configuration/activity visibility, enforced on the
  server for both current and legacy read endpoints. Hidden-data notices distinguish
  both categories from one category; hidden settings cannot be compared/copied.
- Dedicated preview profile/cache and compile-time suppression of launcher updates.
  No production credentials or fixture identities are included in the distribution.
- New player-facing strings translated for UK/CS/DE/FR as well as RU/EN.

## Validation

- Normal Release build: passed. Existing unused social test seam warning only.
- C# suite: **38,874 assertions passed**, including **24** targeted usability checks.
- Isolated PostgreSQL/WASM suite: **12,703 assertions passed**, including **156**
  privacy checks across all nine audience combinations, self/friend/stranger,
  legacy/current activity APIs, friend polling, blocks, invalid writes and RLS.
- New UI fixture: **21 checks passed in Russian and 21 in English**. Covers save
  success/failure/reload, speed preference, paused/stopped transport UI, fresh-window
  recovery, retry help, all hidden-data states and minimum launcher height.
- Existing friend/download UI: **35 passed**; community UI: **120 passed**;
  game participants UI: **18 passed**.
- Existing background installer UI: **13 passed** through isolated download,
  extraction, hashes, commit, rollback and cancellation. Dispatcher max gap in the
  final run was 45.4 ms. New UI page-switch timings are in the review output folder.
- Native self-contained test EXE: started and exited cleanly with an isolated
  `--smoke-test --smoke-exit --test-profile=...` invocation; health metadata confirms
  test identity, disabled launcher auto-update and separate profile/cache roots.
  No game was launched and no live two-account gameplay test was performed.
- Twelve Russian UI screenshots were rendered from real WPF controls with mocked
  accounts/data, visually reviewed, and bundled with a portable HTML gallery.
- ZIP decoded successfully; its EXE hash matches the published local EXE and all
  twelve screenshot entries are present. PDBs are excluded from the test ZIP.

## Server support for testing

Migration `20261109000000_profile_visibility.sql` was applied transactionally and
registered after validating all four previous projection definitions. Existing
accounts retain Everyone/Everyone without inserting or changing their preferences.
The schema includes revoked client table grants and RLS. The readback verified
all twelve expected source MD5s and grants against the local migration result,
plus RLS and migration registration (all six aggregate checks true).

Only authenticated users can call `paw_profile_visibility`; unfiltered helpers
are not directly executable by clients. Anonymous HTTPS readback returned
401/42501 for the preference endpoint, while the existing online directory
remained 200/ok. No fixture users, friendships or presence rows were added to
production. Source hashes and readback evidence are in top-level outputs:
`usability-server-expected.json`, `usability-server-readback.json`,
`usability-server-https.json`.

The public launcher/feed release remains 1.0.11. Account visibility chosen by the
user in this test build is real account data and also affects ordinary clients;
this is stated in the interface and test instructions. A player's own profile
remains visible to themselves. Cached views refresh on their normal polling cycle.

## Local distribution

- EXE: `G:\CodexData\projects\Codex\2026-09-09\paws-patch-kohan-ii-3\outputs\launcher-usability-test-20261109\PawsLauncherTest.exe`
- Size: 78,831,988 bytes.
- SHA-256: `06129ed71e4555266810a62334c2f1eb4f28edca4782f3cce86b9ee5a652d207`.
- ZIP: `G:\CodexData\projects\Codex\2026-09-09\paws-patch-kohan-ii-3\outputs\PawsLauncher-Test-20261109.zip`.
- Gallery: `G:\CodexData\projects\Codex\2026-09-09\paws-patch-kohan-ii-3\outputs\launcher-usability-review-20261109\index.html`.
- Complete player-visible notes: `G:\CodexData\projects\Codex\2026-09-09\paws-patch-kohan-ii-3\outputs\launcher-usability-review-20261109\CHANGES.md`.

## Revision 2: account-profile placement

Moved the existing visibility card from launcher settings into the signed-in
account profile, between personal profile actions and security. The card is not
shown in general Settings. Preference reads are now lazy-loaded only on the
account page. No server policy, saved selections, download behavior or published
feeds changed. The dedicated UI fixture passed 23 checks in Russian and 23 in
English, including placement, removal from Settings, save/reload/failure behavior
and access during a paused download. A contextual full-window screenshot records
the new location. Revision 2 uses separate local output names to preserve the
earlier test distribution.

Revision 2 native startup passed with isolated profile/cache and auto-update suppression.
EXE: `G:\CodexData\projects\Codex\2026-09-09\paws-patch-kohan-ii-3\outputs\launcher-usability-test-20261109-r2\PawsLauncherTest.exe`; SHA-256 `7e53e3eaf89606457271754a36a8b56a78b78e59102787f75e3cae008d5cd4dd`.
ZIP: `G:\CodexData\projects\Codex\2026-09-09\paws-patch-kohan-ii-3\outputs\PawsLauncher-Test-20261109-r2.zip`; 13 screenshot entries and EXE hash verified after packaging.
