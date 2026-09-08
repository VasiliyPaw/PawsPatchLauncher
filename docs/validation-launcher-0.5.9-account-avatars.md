# Launcher 0.5.9: avatars and account actions

Date: 2026-09-08. Local test candidate only; no launcher release, tag, push or public source publication.

## Candidate

- EXE: `release_workspace_059/account-avatar/launcher/win-x64/PawsPatchLauncher.exe`
- Size: 72,038,388 bytes.
- SHA-256: `217E83364E730BF49F72DAC2EA6FF2A118AA5772C33CF9105473A5CC05DD47A6`.
- Adjacent launcher.config.json retains the signed local components-v2 feeds from the previous account-page candidate.
- No game, launcher, VM or real desktop was started/stopped/controlled. Previews render detached WPF content.

## Implemented

- Direct login/register tabs in the separate Account page; Friends guest links select the appropriate tab.
- Selected Account header uses the same blue/gold selection as sidebar navigation.
- Signed-in Friends page has a truthful empty/preparation state, with no Account navigation button. Friends/chat/transfers are still not implemented.
- Release/Beta tooltips explicitly describe one shared launcher version and update stream.
- Select/remove own avatar. PNG/JPEG up to 10 MiB; dimensions <=8192 per side and <=32 MP.
- Bounded decode, center square crop, resize to 256x256, re-encode JPEG without original metadata.
- Private Storage bucket paw-avatars; one fixed path per account, max 200 KiB, JPEG only. Replacement does not accumulate old avatar files.
- Own avatar shown in header/profile and reloaded after sign-in/restart. No anonymous public URL, remote URL input, or executable image formats.
- Avatar cache is memory-only and identity/revision scoped. Leaving/signing out cannot show a different account's image.
- Delete account requires current password plus launcher-style modal with dimmed background. Cancel sends no network request.
- Server clears only the caller's avatar through Storage API, then deletes that caller through Auth Admin API. Profile rows cascade. Local game/patch/saves are untouched.
- Independent server-stored five-minute email/password cooldowns. Protected timestamps survive restart. Wrong-password/definitively rejected requests release their reservation.
- Uncertain transport outcomes are not reported as success; action lease and cooldown reservation prevent immediate conflicting retries.
- Deletion-in-progress marker blocks new mutations, allowing deletion retries after partial failure.
- Password changes preserve the newly retained Auth session with the original Remember me choice. Other-session revocation is Auth's behavior.
- Password-recovery flow remains available and separate from ordinary change cooldowns.
- Success, errors, cooldown notices and avatar updates use existing motion/feedback styling.

## Backend

Project remains scoped to `trdzsdclscuwwmxnepyt`.
User approved extra `edge_functions:read` and `edge_functions:write`; browser OAuth confirmed and MCP connection refreshed.

Applied migration: `20260908020000_account_actions_avatars.sql`.
Deployed function: `account-actions`, version 2, ACTIVE.
Bundle SHA-256: `9fa5c158cf2c585a22607c91265a7bc43ca46c68c4269379fc8d31637f74a6cd`.

Function gateway verify_jwt=false is intentional: the handler authenticates each caller using Auth GET /user, then checks the live auth.sessions row through a service-only RPC. Merely decoding a JWT is not accepted.
Every sensitive mutation additionally verifies the current password where appropriate; caller identity cannot be supplied by the body.
Service credentials exist only in the Edge runtime. Desktop code/config contain only the publishable key.
No real account was deleted, renamed, emailed, or given an avatar by these tests.
After transactional fixtures: 2 existing profiles, 0 temporary action rows, 0 avatar objects.

Cooldown scope: enforced for this launcher's account-actions endpoint, including concurrent clients. It is not an Auth-schema trigger and does not replace Supabase's independent Auth API policies/rate limits. Direct calls to the underlying Auth update API and password recovery are not a global five-minute blockade. Avoid fragile triggers on managed encrypted-password fields (login may rehash them).

Storage has no client write policies; avatar access currently goes through authenticated owner-only Edge actions. Friends avatar visibility must be added with the friendship access rules, not by making the bucket public.

Deletion does not promise immediate cryptographic expiry of an issued JWT. Sensitive account-actions explicitly checks the live session/user; lookup also requires an existing non-deleting caller profile.

## Verified

- .NET test runner: PASS 5937, including Account Profile 159 and Account Actions 103.
- WPF Account UI: 89 RU + 89 EN.
- Motion suite: 35.
- Edge handler mocked suite: 24/24, including actual WPF-normalized JPEG compatibility; no skipped fixture check in the recorded run.
- SQL account-action assertions passed in BEGIN/ROLLBACK: independent timers, wrong/rejected rollback, crash reservation, expired leases, stale completion isolation, deletion pending, privilege restrictions, bounded private bucket.
- Existing nickname cooldown/RLS/lookup regression SQL passed; all fixture changes rolled back.
- Hosted Edge function returned HTTP 401 with sanitized unauthorized JSON for no token and a forged token.
- Build: 0 warnings, 0 errors. Self-contained x64 single-file publish succeeded.
- git diff --check: no whitespace errors (existing CRLF normalization notices only).
- Detached previews inspected: RU avatar profile, EN registration at 1050x680, RU deletion modal.

Security advisor is not warning-free: expected public nickname-availability and authenticated profile RPC warnings, pre-existing rls_auto_enable warnings, leaked-password protection disabled. New private action table's no-policy INFO is intentional deny-by-default. New privileged action RPCs are service_role-only. No unrelated Auth settings or paid options were changed.

## Manual acceptance still required

Use a disposable account for deletion, not an account you want to keep.

1. Upload your PNG/JPEG, replace it, restart launcher, verify header/profile; remove it and restart again.
2. Check login/register switching and failed-login field retention.
3. Change email and confirm the mail flow; retry before five minutes and after. Password change invalidates earlier email-change/recovery links per Auth, so complete or re-request those flows.
4. Change password, verify you remain signed in; restart with Remember me on and off. Old password must fail.
5. Verify the independent timers are retained after restart and do not block one another's form.
6. Deletion: wrong password, Cancel, then confirm on a disposable account. Verify guest state, failed subsequent login and no avatar object. Check local saves unchanged.
7. Two-account isolation with authenticated real clients remains a manual end-to-end gate; mocks and SQL fixtures are not represented as real email/storage/Auth acceptance.

## Relevant primary sources

- Auth user update implementation: https://github.com/supabase/auth/blob/master/internal/api/user.go
- Password session revocation: https://github.com/supabase/auth/blob/master/internal/models/user.go
- User deletion and Storage ownership: https://supabase.com/docs/guides/auth/managing-user-data
- Storage operations must use the API: https://supabase.com/docs/guides/storage/schema/design
