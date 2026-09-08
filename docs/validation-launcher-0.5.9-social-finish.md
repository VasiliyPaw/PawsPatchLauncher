# Chat and floating-card polish — 2026-09-08

## Candidate

- Host: release_workspace_059/social-finish/launcher/win-x64/PawsPatchLauncher.exe
- VM: \\VBOXSVR\KohanShare\PawsPatch-Social-Finish\PawsPatchLauncher.exe
- Share: D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Social-Finish
- 72,207,185 bytes. Host/share SHA-256: **7F2C3D08112B6150A162664139E8523A59A1EB8B498D23293084384DEBFCEEE1**.
- Previous candidates retained. Copied only EXE and the previous per-device launcher.config.json. No account credentials, settings, or saves copied.
- VirtualBox confirms Kohan II Test running with KohanShare mapped to the above shared root. The guest executable and game were not launched.
- No server migrations, Edge deployments, public launcher/patch feed releases or game-package changes in this turn.

## Changes

- Profile, help and confirmation overlays consume clicks outside their card within the launcher. Inside clicks (including padding and text) stay open. Outside confirmation means cancellation only; its underlying player profile remains open. No click-through to underlying controls.
- The friend/chat list no longer has a separate ellipsis button. Right-clicking a friend row opens the existing themed menu. Request-row controls and composer offer menu remain.
- Player profile has red Remove friend and Block actions with existing confirmation/authenticated flow. Cancellation preserves the profile; confirmed successful actions close it. Identity/friendship rechecked after confirmation.
- Ordinary chat backgrounds, text and message avatars no longer open the player menu. Left-clicking the friend's avatar still opens their profile. Right-clicking a loaded image/GIF opens only Copy link.
- Media links disappear from message text only once the image/GIF has an actual decoded source. Captions and failed/not-loaded URLs remain. Lost preview restores the fallback link, retries update only their own URI, original signed URL is copied unchanged. Timeout returns to a retry state.
- Existing bounded, unauthenticated external-image client, DNS/IP restrictions, cancellation, no-disk-cache behavior and GIF stream disposal preserved.
- Small friend-list status dots increased from 12 to 16 px; profile dots remain 20 px.
- Open-chat header puts display name and muted @username inline, separated by a dot.
- Message timestamps include seconds. Config/save offers show their own sent time, including seconds, plus full date on hover.
- Configuration confirmation now renders a scrollable table of changed options with Current/New chips and count. Uses the same structured diff as the plain/accessibility representation. Localization remains opt-in; toggling it updates rows and identical-configuration gating. Other confirmation types reset to their plain details.
- Copy-username icon beside the own-profile identifier uses the existing retry-safe clipboard/toast flow and copies lowercase username without the decorative @.

## Validation

- Build and self-contained publish succeeded. Build: zero warnings/errors. Normal git diff --check passed (existing line-ending notices only).
- .NET suite: **8600** assertions. Offers subset 89, identity/media 74. New tests cover structured/plain diff agreement, unchanged-option exclusion and selective exact-URL removal.
- RU/EN WPF suites pass: Account 95, Social 49, Refresh/toast 23, Session/menu 20, Chat 43, Friend settings 249, Offers 112, Identity/media 16, Social refinement 35, new Social finish **37**, Feedback 27, Window 30.
- New UI tests exercise actual routed outside/inside clicks, top-layer-only cancellation, no friend mutation on cancellation, red actions, row-only menus, mocked username/link clipboard writes, exact signed URI copying, GIF and PNG success/failure/retry, fallback URL restoration, source cleanup, timestamps and compact diff layout.
- Media decoding used generated/mocked bytes and a hidden native WPF render surface; popup creation and clipboard writes were intercepted. No real account messages, remote images, clipboard contents or game saves used.
- Inspected 1440x900 compact chat, RU copy-preview table, and 1050x680 EN copy preview, RU player profile and own profile.

## Manual gate

Close older candidates and open this version on the PC and VM with different accounts. Check native outside-click behavior, row versus picture right-click, live image/GIF loading/link copy, profile action cancellation, compact chat timing and the visual configuration comparison.

Automated WPF fixtures and rendered screenshots do not replace native mouse feel or live two-account acceptance. Existing save-transfer/server access behavior was not changed by this UI turn.
