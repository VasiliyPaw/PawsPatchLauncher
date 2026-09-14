# Local 0.7.5 candidate — 2026-09-14

Status: client built locally; **not published**. Production backend is unchanged.

## Completed

- Persistent suspension/restoration of all seven Arcane Wars component choices.
  Applying the disabled configuration exports only disabled effective settings;
  the local remembered choice survives repeated saves and restarts.
- Paw's Team tooltip text simplified.
- Read-only native activity sampler, profile summary, nested details dialog,
  sharing preference, bounded server schema/RPC, legacy-server fallback/backoff.
- Latest-profile settings continue to come from the backend; received profile
  settings/details are only cached in launcher memory. Own preferences stay local.

## Verification

- Full application test executable: **16,136 PASS**, including 86 native/parser
  activity checks, 31 activity transport checks and 3,080 patch dependency checks.
- All database migrations and tests in isolated PostgreSQL/WASM: **5,191 PASS**,
  including 42 activity checks. No real account records modified.
- WPF activity scenarios: **19 RU + 19 EN PASS**. Rendered/inspected cards at
  1050 × 680; 64 participants scroll inside the bounded dialog. Loading, cache
  reuse, stale completion, transient failure, nested outside-click consumption,
  parent close, timer stop and saved opt-out covered.
- Existing dependency/footer/tooltip/toast UI checks: **63 RU + 63 EN PASS**.
- Self-contained win-x64 executable published to a local output folder; no
  launcher restart or replacement performed. User launcher PID 28616 retained.

## Remaining gates

- Deploy `supabase/migrations/20260914000000_game_activity.sql` in one transaction
  to the existing Supabase project, then verify definitions and grants read-only.
  Browser automation stopped because the automatic safety review could not
  establish the current browser URL. No production SQL was submitted.
- Fresh live native menu/lobby/match verification, including a two-client Steam
  session for participant/account matching. Synthetic memory and server tests do
  not count as that acceptance. See `game-activity-1372.md` for native provenance.
- After those gates, update the release note's rollout status, run the normal
  signed-catalog release workflow and verify the public artifacts/feeds. No tag,
  release, catalog promotion or remote commit was made in this task.

## Local cleanup

Removed 117 explicitly verified obsolete test/build/package targets within the
task workspace (178,640 files; 21,465,657,946 logical bytes). Disk free-space
increase immediately after deletion: 21,880,918,016 bytes, approximately 20.38 GiB.
The real game and the user's running launcher were not cleanup targets. One current
0.7.5 preview is retained; source, reports and required mod/localization inputs remain.
