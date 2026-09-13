# Banned account deletion

Prepared locally on 2026-09-12. No hosted SQL or Edge Function deployment was performed, and no real account was banned, deleted or registered for testing.

While a profile has an active temporary or permanent platform ban:

- The launcher's account deletion button is disabled, with an explanation available on hover.
- A ban arriving while the deletion editor is open closes that editor and clears its password field. Direct editor invocation and submission are also guarded.
- `AccountService.DeleteAccountAsync` rejects a cached ban and preserves the login. The server remains the authority when local state is stale.
- The account-actions preflight and launcher action reservation deny deletion. The final SQL mutation rechecks the ban while holding the profile lock; the private soft-delete function also denies self-deletion.
- Administrative deletion and retention cleanup remain available. Unbanned retries of incomplete deletion remain supported.

Email bans already have independent storage in `paw_private.email_bans`, with no cascading foreign key to Auth or profiles. The production ban action stores the normalized email and original expiry at ban time. Registration preflight and the Auth INSERT trigger consult those records after profile/Auth deletion. Expired or explicitly revoked bans allow signup again; permanent bans do not expire. Case and surrounding spaces are normalized; unrelated provider aliases are not rewritten.

## Server rollout required

The ordinary local test EXE contains the client changes. To enforce the new deletion rule for all clients, apply only `supabase/migrations/20260912000000_banned_account_deletion.sql`, then deploy the updated `account-actions` function. Do not implicitly deploy other pending local migrations or publish the launcher release. The SQL change is compatible with the existing moderation foundation and does not require the unpublished Paw's Team migration.

The existing Edge Function already enforces the SQL preflight result. Its new change additionally reports an accurate ban error if a ban is detected at the final mutation instead of returning a generic account-busy message.

## Verification

- Main .NET suite: PASS 10423, including client ban, permanent/expired ban, retained session on rejection, late server rejection and ordinary deletion.
- `node supabase/tests/banned_deletion.mjs`: PASS 44, executing the production functions and migration in isolated PGlite/PostgreSQL. Includes ban/deletion lease serialization, late ban rejection, admin deletion, Auth/profile purge, email expiry/revocation, direct signup denial, permanent bans and execute grants. Auth/session transport is a local fixture.
- Account-actions HTTP tests: 36 passed, 1 unrelated avatar-fixture test skipped.
- WPF admin/account checks: 156 passed in Russian and 156 in English, including disabled deletion, explanation, stale editor protection, password clearing, expiry, unban and preserved logout/local launcher access.
