# Launcher 0.5.9 single-session candidate — 2026-09-08

## Build and placement

- Host: `release_workspace_059/single-session/launcher/win-x64/PawsPatchLauncher.exe`.
- EXE size: **72,070,348 bytes**.
- EXE SHA-256: `6A18D2D9E6109B62C5C10F6BD7BFB09FEC21F1BC5AEE4A83916A9ADA5E8DC057`.
- VM shared copy: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Single-Session\PawsPatchLauncher.exe`.
- Guest launch path: `\\VBOXSVR\KohanShare\PawsPatch-Single-Session\PawsPatchLauncher.exe`.
- Host retains the signed local components-v2 test feeds. The VM config uses signed public GitHub feeds and the same public verification key. Only the EXE and public config are copied: no account/session/outbox files. This is a portable shared-folder deployment, not a guest C: installation; guest execution remains manual.
- Previous candidates and public release/update feeds are unchanged.

## Behavior

- Latest successful password login owns the account. A private server registry binds the Auth session to a random launcher-instance ID, sent with every authenticated application request. It does not rely on waiting for JWT expiry (see [Supabase sessions documentation](https://supabase.com/docs/guides/auth/sessions)).
- A remembered restart rotates the instance proof using compare-and-swap. Background checks cannot reclaim a displaced session. Delayed older sign-in responses cannot override newer Auth sessions. Claim retries with the same instance are idempotent after a lost response.
- Profile RLS, player lookup, nickname change, all social RPCs/direct social reads, and profile Edge actions check current ownership. Mutations/takeover use the same profile-row lock. A reserved account action temporarily returns account_busy to a takeover; password rotation transfers ownership to its replacement Auth session before releasing the reservation.
- No Auth schema rows are edited in production. Old Auth JWTs may still be cryptographically valid until expiry, but cannot access protected launcher data. Password recovery retains its existing Auth revocation behavior.
- Launcher checks every 10 seconds while connected (also before authenticated actions). A displaced window becomes Guest and shows “В аккаунт вошли в другом лаунчере. Здесь сеанс завершён.” Cached private UI/input/avatar state is cleared. Without a connection, immediate visual detection is impossible; protected server actions remain denied.
- Process ownership is never adopted from another running window's rewritten session file. A stale process cannot clear the winner's saved login or revoke its shared Auth session during logout. Remember me remains DPAPI-protected and honored on/off.
- Sign out is red with a dedicated exit icon, asks confirmation, and defaults to Cancel. Closing/cancelling preserves sign-in. Game and saves are untouched.
- Friend/request ⋯ uses a separate rounded ContextMenu with action icons, danger coloring, hover/reveal motion and native menu dismissal/navigation; rows no longer expand. Menus close on page/identity/list changes. Stale menu actions are rejected if owner/relation changed.

## Applied server changes

- Explicit user approval obtained separately for the migration and production account-actions deployment after the initial safety reviews rejected them. No alternate credential route was used.
- `20260908150000_single_launcher.sql` applied through apply_migration, name `single_launcher`.
- `account-actions` Edge Function deployed as **version 3**, ACTIVE, bundle hash `9e98a7d2a3cc1980121895eaed54ac967f985e61718fd7e885afb22307bffc7f`.
- Existing `verify_jwt=false` retained. The handler explicitly validates the bearer token with Auth /user, then verifies live session + launcher ownership through service-only RPCs. Service credentials remain in the existing Edge runtime only.
- Real data counts before/after fixtures: profiles **2**, friendships **1**, messages **0**. Launcher registry **0** before any real new-client login. All SQL test accounts/sessions/data rolled back.

## Validation

- .NET suite: **6089 PASS**, including **31** new stateful mocked session checks (two separate stores, shared-store restart, takeover, stale logout, lost response, delayed login, refresh, remember off, revocation).
- Edge mocked tests: **29/29 PASS**, including the actual WPF-normalized avatar fixture, missing/forged launcher context, takeover during reservation, successful and failed password-session transfer.
- Live SQL rollback suites: `single_launcher.sql`, `social_access.sql`, `social_unread.sql` PASS. `account_actions_avatars.sql` assertions completed successfully. Fixtures include participants and outsider, stale JWT reads/writes/RLS, grants, nickname/lookup, receipts, friendship/block/dedup, password rotation and session revocation.
- Detached WPF checks RU and EN: account **95**, social **49**, refresh/toast **23**, new session/menu **19**, feedback **27**, window/confirmation **30** each. Motion **35**. Popup template snapshots and profile/logout previews inspected at 1440x900 / 1050x680; actual user desktop was not automated.
- Build/publish: zero warnings/errors; diff --check PASS. Host/VM EXE hashes match.
- Security advisor reviewed: private launcher_sessions has RLS enabled and no client policies intentionally (deny all), like the existing private tables. Guarded authenticated SECURITY DEFINER RPC advisories are expected. Existing public nickname availability/rls_auto_enable and leaked-password-protection warnings remain; this is not a claim of a globally clean security audit.

## Manual acceptance gate

Close older test launchers on host and VM and use the new candidate in both. Sign into the same account on host, then explicitly sign into it in VM: host should become Guest with the new notification after its next successful check, while VM stays signed in. Confirm a third opening of the shared saved session does not allow two active instances, old-window logout does not eject the winner, and restarting the winning client preserves sign-in. Then use two different accounts to check normal friend/chat behavior. Verify ⋯ positioning, outside-click/Escape dismissal and logout cancel/accept visually. Automated fixtures do not replace this live two-device/manual visual gate.
