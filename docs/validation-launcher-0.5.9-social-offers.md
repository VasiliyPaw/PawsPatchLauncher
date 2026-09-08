# Social offers, saves and notification sound — 2026-09-08

## Test candidate

- Host: release_workspace_059/social-offers/launcher/win-x64/PawsPatchLauncher.exe
- VM share: D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Social-Offers\PawsPatchLauncher.exe
- Guest path: \\VBOXSVR\KohanShare\PawsPatch-Social-Offers\PawsPatchLauncher.exe
- EXE: 72,144,164 bytes; host and VM SHA-256 **55079BD7DC05452DFB1F23FC4E6AC869012A46BDCDF60C6A91C986E6289FBD9C**.
- New folder only; previous candidates retained. VM running and share mapping verified. Only EXE and existing public-feed configuration copied to VM share. Guest executable/game were not launched. No account sessions or user saves copied.
- Host retains the existing signed local components-v2 feeds; VM retains signed public feeds. Public Beta payload checked during this task still has no roaming-profile-x2 packages. Test cross-device copying with x1/x4, not x2, until those packages are published. Unsupported configurations fail before changes. This task did not publish patch packages or public launcher feeds.

## Behavior

- Attached WAV is embedded byte-for-byte as the default notification sound: SHA-256 98EE0414CFF91D0549689377021E4A485C3FF983CD9DA16DD5046B807D2725D8. Settings provides enable, choose WAV, preview and reset. Custom PCM WAV is copied into launcher data, bounded to 2 MiB / 15 seconds; source path is not retained. First friend snapshot establishes a baseline; new incoming requests and increases in unread messages trigger sound, unchanged snapshots/read acknowledgements/outgoing requests do not.
- Clicking the current chat does nothing: no busy toggle or message/button recreation. Offer-status polling uses stable IDs/order; busy action availability updates without rebuilding cards.
- Presence dot is 16px; online blue, playing green, offline gray. Details status text uses matching online/playing colors.
- Friend copying is called configuration copying. Confirmation shows changed channel/gameplay values, old to new. Localization is preserved by default; opt-in checkbox appears only when it differs. Underlying Details stays visible and disabled; cancel removes only the upper confirmation. A start toast appears after confirmation.
- Composer More contains Offer configuration and Send save. Offers appear as distinct inline cards with sender, state and recipient-only actions.
- Configuration offers store an immutable applied configuration snapshot. Accept opens ordinary copy confirmation; cancel leaves the offer pending. Confirm transitions to applying, successful file installation and preference commit to accepted; interruption/failure is shared with sender. Server expiry is ten minutes after the offer becomes available. Existing local paths, launcher language, sound preferences and saves are not copied.
- Save picker starts at the existing Kohan saves directory. Only bounded .rsg files, 16 bytes to 20 MiB, are accepted. Sender, Edge and receiver validate size, filename, TGCK signature and SHA-256. This is integrity/format screening, not an antivirus or full game-parser guarantee.
- Same-name save requires explicit overwrite confirmation. Receiver verifies the existing file has not changed since confirmation and uses the existing atomic install path with a backup in Save/.paw-backups. Symlink/path traversal, Windows reserved names and an active game are rejected. Files are never executed or extracted.
- Stable protected send IDs survive retry/restart to avoid duplicate proposals and immutable save-object overwrite. Protected result receipts record interrupted fallback before local mutation and success after commit. Completion is retried after reconnect without repeating local application. Server accepts a matching late completion after lease timeout, but cannot promote an explicit failure.
- During application ordinary logout and close remain guarded by the existing busy policy. Forced session loss is checked again before local mutation. Already applied configuration is not undone on logout.

## Backend

- Applied social_offers and offer_late_receipts migrations through the Supabase migration tool.
- New private RLS-denied offer table; authenticated RPCs validate live Auth/active launcher, accepted unblocked friendship, recipient role, immutable payload, attempt and server timestamps.
- Ordered profile locks serialize actions and sender quotas. Limits: five offers/minute, ten active offers, 50 MiB outstanding save reservations per sender, existing 10,000-message sender cap.
- Private paw-social-saves bucket, 20 MiB object cap and no client Storage policies. New social-transfers Edge function v1 is ACTIVE; existing account-actions unchanged.
- Gateway verify_jwt=false is intentional: handler verifies bearer token against Supabase Auth, obtains the verified user ID, then enforces the active launcher and friend/offer authorization before and after storage work. Server credentials remain environment-only. Paths are server-derived UUID paths, never client URLs.
- Expired/terminal saves and deleted-account orphan objects are cleaned during later authenticated save activity. This is bounded on-demand cleanup, not a scheduled deletion guarantee. Pending 10-minute expiry does not require the sender to remain online.
- Advisor reviewed: deny-all private-table INFO and authenticated guarded SECURITY DEFINER warnings are expected. Existing public nickname/rls_auto_enable warnings and disabled leaked-password protection remain outside this change; no claim of a clean global audit.
  Relevant advisor explanations: https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy and https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable ; password protection: https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection .

## Verification

- Build/self-contained single-file publish: zero warnings/errors. Git diff --check passed.
- .NET: **8519 PASS**, including 83 new offer/audio/diff/receipt/transport assertions and existing save hash/backup/safe-overwrite tests.
- Node Edge tests: **21/21**, including Auth outage/anonymous/stale launcher, outsider/block denial during upload/download, immutable object retry and corrupt object rejection, filename/size/hash/signature bounds. No real credentials or messages.
- Live deployed unauthenticated POST returns HTTP 401 with only unauthorized status, proving the deployed route runs and rejects anonymous access.
- RU and EN WPF tests: Offer UI **61**, Friend configuration **249**, Social **49**, Refresh/toast **23**, Session/menu **20**, Chat presentation **43** each. Account **95**, Feedback **27**, Window **30**, Motion **35** also passed during this turn.
- Inspected rendered offers (1440x900 RU and 1050x680 EN), layered configuration confirmation (1050x680) and sound Settings screenshots. Fixtures use fake profiles/game state and do not contact real accounts or run a game.
- Live SQL suites social_offers, friend_configuration, social_access, social_unread and single_launcher passed with disposable identities in BEGIN/ROLLBACK. Tests cover recipient/outsider, active session, immutable retry/conflict, pending expiry, attempts/late completion, explicit failure, save publication gate, quotas, private/service-only grants, block and takeover. No fixture identities/data persisted.

## Manual acceptance gate

Close older candidates and open this version on host and VM with different accounts. Check the audible notification and custom sound persistence; current-chat clicks; incoming and outgoing configuration cards; cancel/confirm and localization opt-in; decline and ten-minute expiry; successful/failed application status visible to both sides.

Send a real .rsg save from host to VM. Accept it, repeat with an existing filename, verify overwrite confirmation and backup. Try interruption/reconnect and sender status. Use supported x1/x4 configurations with the current public VM feeds. Real authenticated Edge upload/download, native mouse feel, actual game/save loading and host-to-VM application remain this manual gate; they were not represented as automated successes.
