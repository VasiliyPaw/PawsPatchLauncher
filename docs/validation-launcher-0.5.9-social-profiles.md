# Social profiles, username sign-in and inline media — 2026-09-08

## Candidate

- Host: release_workspace_059/social-profiles/launcher/win-x64/PawsPatchLauncher.exe
- Guest: \\VBOXSVR\KohanShare\PawsPatch-Social-Profiles\PawsPatchLauncher.exe
- Share: D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Social-Profiles
- EXE: 72,198,907 bytes. Host/share SHA-256 AC52EEE3BA42A62BB4BF9522B38A6A19D5D83160D6EEDFB482496E9D06FC64D9.
- Separate new candidate; previous candidates preserved. Only executable and existing public-feed config copied to VM, no credentials, settings or saves.
- VM "Kohan II Test" is running; KohanShare mapping verified. Guest launcher and game were not launched by this task.
- Host retains signed components-v2 local feeds; VM retains signed public feeds. Public Beta checked again: no roaming-profile-x2 package. Cross-device configuration acceptance should use x1/x4 until patch packages are published. No public launcher/patch feed release was performed.

## Implemented

- Unique username reuses the existing nickname column/key; stable account UUIDs, relationships and messages are untouched. Existing nickname initializes display name. Display names may repeat, are bounded to 32 Unicode characters and reject blank/control/format names. Username retains 3–24 character grammar and case-insensitive unique key.
- Registration supplies both names. Account supports separate display/username editing with independent five-minute server cooldowns. UI shows display name plus smaller @username in friend/request rows, chat header and profile. Friend adding remains exact unique username, with optional @ prefix.
- Email/password sign-in remains native Auth. Username/password uses new username-login Edge function: service-only private username lookup followed by actual Supabase password authentication. Email is never returned before successful password authentication; unknown users use a dummy Auth target. No passwords or emails are logged.
- Username lookup is service-only. Global, client-hash and canonical-username rate limits protect the route. Errors are sanitized; malformed/oversized input and unexpected origin are rejected. Existing active-launcher claim/refresh/DPAPI storage remain in place.
- Profile replaces Details in friend menu. Friend avatar opens profile; right-clicking friend rows, avatars or chat messages opens the existing themed action popup.
- Composer menu gets explicit light text and icon colors. Row status dots 12px; profile dots 20px. Online blue, playing green.
- Sender sees a dim inline offer immediately during sending/uploading, with progress/failure text. Protected immutable send IDs continue to deduplicate retries. Lost responses reconcile to the server card on refresh.
- Sender cancellation is allowed for uploading/pending offers; both sides see cancelled. Recipient/outsider cancellation denied. Applying/terminal offers cannot be cancelled by sender.
- Configuration sending is allowed during the game; applying still requires closed game. Identical applied configuration disables copy/accept and confirmation action. Diff and localization default use actual applied settings when available. Personal notification volume/sound and local paths are not copied.
- Save receive can run during the game. Same-name receive still requires confirmation and backup. A deny-write handle through atomic replacement rejects an actively written target; changed hashes fail safely. This is not a guarantee that arbitrary received save data is valid for every in-game context.
- Notification volume 0–100 scales only PCM samples in a copy of the WAV, not global Windows volume. Original sound asset remains untouched. Visual unread badges are suppressed for the active visible chat; background chats still notify. Read receipts remain conservative and separate from presentation.
- HTTPS PNG/JPEG/GIF links with query strings render inline, without uploading images to our hosting. Known media CDNs load automatically; other public hosts require a click. External hosts see recipient network traffic.
- Media uses a separate unauthenticated/cookieless client: no proxy/credential forwarding, redirects revalidated, actual connection DNS/IP rejects local/private/transition addresses, bounded download/time/concurrency/dimensions/frame count. Max 8 MiB per image, 4 million pixels, 300 GIF frames, 24 MiB byte cache per account. Up to 16 inline previews per rendered conversation. No disk media cache. Cancellation/disposal clears streams on rerender/account exit.
- GIF playback uses pinned XamlAnimatedGif 2.3.2 with bounded MemoryStream, not its URL-to-temporary-file mode. Expired/inaccessible CDN links remain text with a retry placeholder.

## Backend deployment

Applied migrations: usernames_display_names, sender_offer_cancel, offer_legacy_label. The latter preserves the renamed PL/pgSQL function's qualified attempt parameter. Legacy entry points are not client-executable; guarded public wrappers preserve existing access checks.

Deployed username-login v1 ACTIVE, verify_jwt=false because this pre-login endpoint performs custom password authentication through Supabase Auth. Its privileged lookup remains server-only. Existing account-actions and social-transfers deployments were not replaced.

## Validation

- Build and self-contained publish: zero warnings/errors. Normal repository git diff --check passed; pre-existing unrelated changes preserved.
- .NET suite: 8585 assertions; new identity/media suite 66, covering username routing and private metadata, display name change/signup, PCM 8/16/24/32-bit scaling, URL/IP/redirect/cache boundaries, running-game file lock and exact backup.
- Node: username-login 7/7; existing social-transfers 21/21.
- Deployed username-login smoke: anonymous malformed POST returned HTTP 400 with only invalid_credentials; no Auth request or user lookup was needed.
- Live disposable BEGIN/ROLLBACK SQL: social_names_cancel, social_offers, friend_configuration, social_access, social_unread, single_launcher passed. No test accounts/data persisted.
- SQL tests verify duplicate display names and legacy signup fallback, own-name cooldown, forbidden public email resolution and legacy RPC access, friend-only names, sender cancellation/idempotency, recipient/outsider denial, cancelled-offer acceptance denial and applying-offer cancellation denial.
- RU/EN WPF suites: Account 95, Social 49, Refresh/toast 23, Session/menu 20, Chat 43, Friend configuration 249, Offers 112, Identity/media 16, Feedback 27, Window 30; Motion 35 (RU). New UI test verifies distinct identity lines, avatar-click profile, volume, a decoded GIF first frame, repeat setting and disposal, using mocked HTTP and a hidden render surface.
- Inspected compact 1050x680 registration/settings and 1440x900 offers renders; themed volume slider, smaller username text and light menu styling.
- Supabase advisor is not warning-free: private RLS-denied tables intentionally have no direct policies; guarded SECURITY DEFINER RPCs are intentional and tested. Existing rls_auto_enable advisory and disabled leaked-password protection were not changed by this feature task. See [function advisor](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable) and [password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Manual gate

Close older candidates; use different real accounts on host and VM. Test username and email login, duplicate display names, avatar/right-click Profile, live image/GIF URLs, quiet active-chat badges, audible volume, sending/cancelling offers from both sides, identical configuration and game-running restrictions. Receive a real save during the game, including overwrite confirmation and backup, and check that the game loads it.

Automated tests do not replace real authenticated host-to-VM Edge upload/download, audible playback, native mouse feel or actual game acceptance. Existing public Beta x2 limitation remains. No real user password/email/message/save was used for validation.

References: [Supabase password authentication](https://supabase.com/docs/guides/auth/passwords), [XamlAnimatedGif stream playback](https://github.com/XamlAnimatedGif/XamlAnimatedGif/wiki/Documentation).
