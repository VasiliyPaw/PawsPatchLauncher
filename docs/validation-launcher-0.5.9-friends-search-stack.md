# Launcher 0.5.9 — friend search, stacked toasts and limits

Date: 2026-09-08.

## Implemented

- Search icon in the Friends heading reveals a compact input. Name and username matching is immediate, partial and case-insensitive, accepts an optional @, and filters the loaded list only. No network call is made per keystroke. Clear/Escape/toggle restore the list; account changes discard the query. Filtering preserves the active conversation/draft and normal unread counts. Identical background polls retain existing row controls.
- Compact add-friend form: small username label, one-line input, send icon and close icon; localized tooltips/accessibility names, Enter submits and Escape closes. Username validation/server authorization unchanged.
- New toasts appear below older ones; every retained card has its original deadline, localized message callback, type, progress animation and independent dismiss button. Layout changes animate; entrance comes from below, and the user's follow-up changes exit to a **48-DIP rightward slide with fade over 220 ms**, not downward. Rapid reversal preserves current visual values. All notification state is cleared on account replacement/window closure.
- Toast host stays centered above the footer and all in-window overlays. The bounded-height host scrolls during bursts. Defensive maximum: 50 cards, retiring the oldest beyond that limit to prevent an unbounded visual tree. Existing 3/8-second success/error durations and hover/focus retention remain.
- Save broadcasts allow ten recipients; configurations remain five. Partial retry, membership checks, account/cancellation guards and per-recipient durable offer IDs remain unchanged.
- Username cooldown is one day after the last successful username change. Client availability and hour/minute/second countdown updated; display name, email and password remain separate five-minute restrictions.
- Sidebar/logo unchanged. No admin roles, privileged user directory, bans or deletion capabilities enabled: see `admin-console-proposal.ru.md` for the proposed next stage.

## Server migration

Applied through the configured Supabase migration tool: `save_rate_and_username_day`, remote version **20260908120112**. Local source is `supabase/migrations/20260909000800_save_rate_and_username_day.sql` (following the existing local migration ordering).

The migration checks the existing function text before narrowly replacing the offer rate predicate and the two username cooldown intervals. It fails if the expected definition has drifted. Save/config minute counts are now independent: **10 saves/minute; 5 configuration offers/minute**. Ten concurrent active offers, 20 MiB per save, 50 MiB retained sender storage and message quotas are unchanged and may constrain a batch before its minute allowance is exhausted.

Read-only post-apply contracts passed for all three relevant functions: active-launcher wrapper/username normalization, participant locking, duplicate-offer handling, limits, SECURITY DEFINER, empty search_path and original grants. The private nickname implementation still has no authenticated/public execute grant. No account rows/messages/files were altered for verification. No synthetic user records or destructive production test were created.

## Verification

- Full unit suite: **8671 assertions passed**, including 27 Social Hub policy checks and independent snapshot deadlines/localization. Existing profile tests verify the one-day username availability separately from five-minute email/password availability.
- New Friends Polish WPF suite: **23 checks each RU/EN**: search, empty results, row identity, retained chat/draft, compact form, ten-save/five-config batch limits, independent toast lifetimes/order/dismissal/burst cleanup, account privacy and 23-hour countdown rendering.
- Feedback **39**, Motion **35**, Smooth Experience **33**, RU/EN, passed after the rightward-exit change, including actual off-screen WPF intermediate frames and exit reversal. Windows animations were enabled during these runs; the user's Windows settings were not changed.
- Social Hub **47**, account **113**, social **49**, refresh/toast **23**, session/menu **20**, chat **43**, friend settings **249**, offers **112**, identity/media **16**, social refinement **35**, social finish **54**, media layout **26**, update refresh **25**, arrival polish **75**, RU/EN, passed in the complete regression run before the final direction-only adjustment. Motion/feedback/new feature suites were rerun after that adjustment.
- Mock transports/synthetic media/clipboard only in tests. No real email, social sends, game launch or save install. Real end-to-end ten-recipient delivery remains a manual gate, not established by the mocked batch checks.
- Rendered and inspected compact search/add and three stacked notifications at 1050x680: `artifacts/friends-search-stack-right-ru.png`; EN 1440x900 render: `artifacts/friends-search-stack-right-en.png`. Corrected the search icon position to avoid another toolbar row at minimum width. Updated an obsolete width assertion specifically for the new 32-DIP send-request icon; geometric bounds remain checked.
- Release build/publish: no warnings/errors. Git whitespace check passed. Existing unrelated changes preserved; no commit/push/public feed release.

## Test candidates

Host: `release_workspace_059/friends-search-stack/launcher/win-x64/PawsPatchLauncher.exe`.

VM host share: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Friends-Search-Stack\PawsPatchLauncher.exe`.

Guest through existing share: `\\VBOXSVR\KohanShare\PawsPatch-Friends-Search-Stack\PawsPatchLauncher.exe`.

Both EXEs: **72,232,631 bytes**, SHA-256 **1E08BB6468E33683472EEA621D0CBF48F9DC318C81945C84B2F77CEA83F0E6D9**.

Each device's launcher.config.json was preserved from its own Social-Hub-Motion candidate and hash-verified. The VM folder contains only the new EXE and its own configuration, not the host's session or saves. Running Social-Hub-Motion (observed PID 19772) was left untouched. The new VM EXE was not launched.

## Manual acceptance

Close the old launcher before opening this candidate. Check real-screen search/form hit targets, notification order/rightward exit and existing chat/draft retention. Use different accounts on the host and VM for social delivery; the single-launcher account rule remains active. Visual smoothness on the real display/VM and real network batch outcomes still need user acceptance.
