# Chat activity and quick save candidate — 2026-09-09

Local launcher candidate only; no launcher release/feed/tag was published. Prior layout and registration changes remain included. Public version is not assigned (the binary still reports 0.6.3.0).

## Behavior

- Game folder / Send save opens the native save picker first, then the recipient dialog with the selected file. Canceling the picker does not open a recipient dialog or request the friends list.
- Only this quick entry point closes after successful delivery to every selected recipient. Partial failures leave the dialog open; retry excludes already sent recipients. Normal Friends / Broadcast remains open after sending and does not automatically open the picker.
- Existing save validation, size limit, ownership/cancellation guards and delivery limits are retained. No real save was sent during automated checks.
- Conversations sort by their newest incoming or outgoing message. Confirmed activity comes with the existing friends-list response, so initial/restarted launchers do not need a request per conversation. Local pending messages and offers promote their conversation immediately.
- Equal timestamps use the server ordinal; older poll responses cannot undo already observed activity. Account changes clear cached order/cards, and removed pending messages do not leave permanent phantom activity.
- Existing chat cards move as one retargetable animation batch. A new update starts from the current displayed position instead of queuing another animation. Selected chat, draft and button identities are preserved. Hidden/minimized windows, search changes and disabled Windows animations skip motion.

## Approved production migration

Applied through the configured Supabase migration tool with explicit user approval: `chat_activity`, source `supabase/migrations/20260909002000_chat_activity.sql`.

The existing `public.paw_social_list()` adds nullable `last_message_at` and `last_message_ordinal`. Its prior access/moderation/hidden-chat rules and array ordering remain intact for older clients. No new policies, grants, tables, indexes, retention rules or limits were introduced.

`supabase/tests/chat_activity.sql` passed on the live database using synthetic identities inside a rolled-back transaction: both directions, timestamp/ordinal ties, newly sent message, unrelated conversation exclusion, pending/blocked metadata absence, invalid session rejection and unchanged function grants. No real accounts/messages were modified or email sent. Read-only EXPLAIN confirms the newest-message lookup uses the existing `paw_message_dialog_history` index with LIMIT 1.

## Validation

- Core: **PASS 8801**, including 164 new order/parser checks and 150 synthetic activity bursts.
- Detached WPF chat/quick-save suite: **PASS 104 RU + 104 EN**. Includes 24 overlapping retargets, immediate position continuity, three same-poll updates, no duplicate cards, selection/draft preservation, search/reset cleanup, picker-before-friends ordering, source-specific closing, partial retry without resending successes, canceled picker and delayed picker after sign-out.
- Regressions: layout refresh 61 RU; social chain RU (49 basic, 23 refresh, 22 session/menu, 43 chat, 249 friend configuration, 112 offers, 16 identity/media, 35 refinement, 54 social finish, 26 media layout); Friends polish 24 EN; social hub 48 EN. Generic layout checks passed at 1050 × 680 and 1600 × 1000.
- Inspected actual detached WPF moving/settled frames: promoted row moves in front of shifting rows; settled cards retain consistent spacing. Previews use synthetic data, not an authenticated launcher session. Motion feel remains a manual acceptance item.
- Build and successful self-contained publish completed; final diff whitespace check passed. The first publish into the previous test directory failed because its EXE was running; that launcher was not stopped. The new build is in a separate directory.

## Local artifact and manual check

`release_workspace_064/test-chat-activity/win-x64/PawsPatchLauncher.exe`

SHA-256: `0815DCD750A3D21963C820C5717954170CA321D52902161EE41067CC01CF0DBF`

Close the previous test launcher before opening this one. Check quick save selection/cancel/send with a consenting friend, normal broadcast remaining open, and incoming/outgoing chat movement including several active conversations. Do not publish the launcher until the user accepts the real interaction and animation.
