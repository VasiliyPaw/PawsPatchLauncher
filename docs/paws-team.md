# Paw's Team and temporary Arcane Wars access

Arcane Wars downloads require a signed-in, unrestricted administrator or a
server-confirmed Paw's Team member. An offline account with previously verified
membership may select, apply and launch an already retained release with cached
components. This never authorizes a new installation or update. Vanilla and
Immortals remain public. Known revocation, sign-out and bans close access without
deleting stored files. Permission is rechecked after asynchronous preparation and
immediately before launch.

The component page explains that general availability awaits confirmation from
Darquan Mortis. Disabled controls retain a readable tooltip. The footer Discord
button uses the existing shared mod community invite, https://discord.gg/krCK7DDwyz.

## Roles and server rollout

Apply `supabase/migrations/20260910001000_paws_team.sql` before assigning the new
role on the hosted service. It was applied for the authorized 0.7.0 publication on
2026-09-13; no accounts were assigned roles during deployment. It adds the protected `paws_team` profile field, updates the existing
role RPC, and exposes the badge in authorized profile/social/admin responses.

Only a senior administrator may change roles. The existing RPC accepts `level=-1`
for Paw's Team; the stored `admin_level` remains zero. Choosing another role clears
team membership atomically. Team members receive no moderation privileges. Existing
ban, deletion, protected-account, account-lock, self-moderation and audit rules remain.
No real account is assigned a role by this migration.

Old servers without the new column remain usable: the client retries the legacy
profile query and preserves administrator access, with no inferred team membership.
Registration metadata cannot grant a role. Signed-out accounts do not receive
access; offline use requires trusted saved membership and an installed release.
This is an application access gate, not a claim that
previously public package URLs or old launcher versions are access controlled.

## Validation

`AccountTeamTests` covers trusted profile data, forged registration metadata, role
revocation, sign-out, bans/deletion, offline state, persistence and legacy servers.
PreviewRenderer `--team-checks --smoke-test` checks both UI languages with disposable
mock accounts; `--admin-checks` retains the existing moderation coverage.

For a standalone PostgreSQL role test:

```text
cd supabase/tests
npm ci --ignore-scripts
npm run test:team
```

`paws_team.mjs` runs the actual migration in an isolated PGlite database and checks
grants, revocation, atomic transitions, direct-write denial, RLS, JSON badges and
audit records. Its auth/session transport is a local fixture. It does not claim to
test hosted Supabase Auth and does not contact production.
