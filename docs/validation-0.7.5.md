# Launcher 0.7.5 validation — 2026-09-14

Server deployment completed. Client release publication is in progress.

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

## Prior cleanup

117 verified obsolete test/build/package targets removed: 178,640 files,
21,465,657,946 logical bytes; immediate free-space increase about 20.38 GiB.
The real game, running launcher, source and required mod inputs were preserved.
