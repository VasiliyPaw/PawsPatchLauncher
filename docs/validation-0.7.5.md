# Launcher 0.7.5 validation — 2026-09-14

Server deployed; launcher 0.7.5 published. This revision updates all four signed
launcher catalogs and the shared change history.

## Changes

- Arcane Wars optional components are remembered while Paw's Patch is off, across
  apply/save/restart; reenabling the patch restores the selection.
- Simplified Paw's Team tooltip.
- Optional read-only game activity: phase, time, map size and participant details.
  The roster groups players by team with native colors and a separate bot icon.
- Pending Paw palette choices are read separately from the map template; Random
  is neutral until assigned. Live match colors/teams use actual kingdoms.
- Backend keeps one current bounded activity, uses existing visibility/session
  checks, and omits roster data from ordinary friend polling. No match history.

## Verification

- Full application tests: **16,182 PASS**, including 132 native/parser checks,
  31 activity transport checks and 3,080 component dependency checks.
- Database migrations and isolated PostgreSQL/WASM tests: **5,206 PASS**,
  including 57 activity cases. No real user records used as fixtures.
- WPF activity scenarios: **22 RU + 22 EN PASS**. Group order, player placement,
  exact RGB, unknown teams, 64-player scrolling, 1050 × 680 layout, loading,
  cache reuse, stale completion, retries, nested dismissal and saved opt-out.
- Prior component/footer/tooltip/toast candidate checks: **63 RU + 63 EN PASS**.
- WPF build: zero warnings/errors. RU/EN renders inspected, including bot icon.

## Production backend

`20260914000000_game_activity.sql` deployed in one transaction in the existing
Supabase project on 2026-09-14. Before commit, both previous function bodies and
all five resulting function bodies were matched against the isolated tested
schema. Six read-only post-deployment checks passed: authenticated-only RPC,
private implementations, roster index, valid team/color and invalid-value rejection.
Existing accounts, friendships and messages were not test targets.

## Manual validation boundary

Native offsets and transitions are covered by disassembly and relocated-memory
fixtures. A fresh two-client Steam lobby/match has **not** been live-tested;
automated checks do not substitute for that test. Unknown native layouts keep the
generic Playing status. See `game-activity-1372.md` for the exact native evidence.

The user's running launcher was not stopped, restarted or replaced.

## Publication

- Release: https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v0.7.5
- Source/tag: `77dba1980c28a0a96bb6407f6c1fe62d4c5786d2`.
- GitHub build/test `34792798774` and publication `34792798801`: success.
- Public EXE verified as 0.7.5.0, 72,458,732 bytes, SHA-256
  `15C31C625FF7B281D56C58F3AC46826B418AF5C714B3263D94B5A34E8E8B6887`.
- Downloaded ZIP/EXE/metadata sizes and GitHub digests match. The ZIP contains the
  identical EXE and the signed-v2-feed configuration. Authenticode remains unsigned.
- Four signed catalogs advertise this exact EXE; game packages remain unchanged
  (15 legacy / 37 v2), on both stable and beta channels.
- Full tests with the promoted catalogs: **16,182 PASS**.

## Prior cleanup

117 verified obsolete test/build/package targets removed: 178,640 files,
21,465,657,946 logical bytes; immediate free-space increase about 20.38 GiB.
The real game, running launcher, source and required mod inputs were preserved.
