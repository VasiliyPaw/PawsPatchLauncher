# Friend settings / launch state candidate — 2026-09-08

## Delivery

- Host: release_workspace_059/friend-settings/launcher/win-x64/PawsPatchLauncher.exe
- VM share: D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Friend-Settings\PawsPatchLauncher.exe
- Guest: \\VBOXSVR\KohanShare\PawsPatch-Friend-Settings\PawsPatchLauncher.exe
- EXE size: 72,086,123 bytes.
- Host and VM SHA-256: 8BD797820789EC7EBDD1723B9194C418148475042F71F5FE6EBEF62CC6DB7FFF.
- Only EXE and launcher.config.json copied to a new VM-share folder. Older candidates, account sessions, outbox and game files preserved. VirtualBox running/share mapping verified; guest EXE and game were not launched.
- Host uses existing signed local components-v2 feeds. VM uses existing signed public feeds. Important: public Beta payload checked today does not contain the two x2 roaming packages. Copying an x2 profile there is rejected with a localized explanation and no preference/file change. Use standard/x4 for the current public-feed VM acceptance test. No public release, signed feed or package was published by this task.

## Behavior

- Message bound unchanged: 2000 UTF-16 units (some emoji occupy two). Existing client/server validation retained.
- Launch label changes to Game running / Игра запущена and disables while a known Kohan executable is running. A one-second independent status timer, activation and ordinary refresh observe external starts as well as launcher starts; close stops timer. Existing immediate pre-launch/pre-install guards retained.
- Details is a dedicated responsive modal with a 68px avatar, presence/duration/last-seen, channel and component chips including exact x1/x2/x4. Centered font-independent profile icon replaces the text glyph. Esc/close, identity/friend removal cleanup and no chat-read acknowledgement through the modal.
- Copy settings requires explicit confirmation, signs in to the existing authenticated RPC, revalidates ownership/friendship/code before work and again just before file reconciliation, and uses the latest signed configured feed for that channel. No friend-supplied URL/path is accepted.
- The configuration snapshot preserves this device's game path, launcher language and personal preferences. Only channel/gameplay options are replaced; pinned release is cleared. Existing transactional installer/backup path performs the file change, then preferences are committed. No game auto-launch.
- Cancellation, changed friend snapshot, account replacement, missing package support or network failure before commit leave prior selection/game files unchanged (verified downloads may remain cached). A settings-file write failure after successful install is explicitly reported as partial persistence, not falsely described as rollback.
- Logout is visibly disabled while applying/checking feeds and its handler has the same guard. Ordinary logout cannot interrupt the operation. Forced session loss is handled by authenticated checks before changing files; already applied settings are not undone on logout.

## Backend

- Migration friend_configuration applied through the standard migration tool. First generated SQL attempt failed syntax and rolled back; corrected migration then succeeded.
- Nullable bounded exact-code field in existing private RLS-denied presence table; channel/finite grammar validation. Boolean display flags derive from exact code on the server, preserving x2/x4 and powers/shards state without disclosing paths or personal settings.
- New four-argument presence RPC and backward-compatible three-argument wrapper. Legacy heartbeats clear obsolete exact configuration; no ambiguous default argument overload.
- Accepted, unblocked friends only receive configuration. Existing Auth/active-launcher guards and direct-table denial remain. No Edge deployment or secret changes.
- Security advisor reviewed: expected private deny-all/no-policy INFO and authenticated guarded RPC warnings; existing public nickname/rls_auto_enable and disabled leaked-password-protection warnings remain outside this change. Not a clean-global-audit claim.

## Verification

- Build and self-contained single-file publish succeeded, zero warnings/errors.
- .NET suite: **8436 PASS**, including 2314 exact-configuration assertions across 768 combinations, personal preference preservation, malformed/channel mismatch/unsupported feed, and exact client RPC payload/response tests.
- RU and EN detached WPF suites: FriendSettings 176 each, Social 49, RefreshToast 23, SessionMenu 20, ChatPresentation 43; Account 95, Feedback 27, Window 30. Motion 35 passed. New tests cover cancel, running game, busy launch/logout, network failure, removed/changed friend, game starting during load, unsupported feed, failed apply, account replacement and exactly-once successful snapshot apply. Network and install work are mocked in these UI fixtures.
- Rendered RU 1440x900 and EN 1050x680 Details screenshots inspected; avatar, close/copy buttons and component list fit. Native interactive mouse feel remains a manual acceptance gate.
- Live SQL suites passed with disposable identities in BEGIN/ROLLBACK: friend_configuration, friend_presence, social_access, social_unread, single_launcher. Exact SP1/SP2/SP4 + PS0 roundtrips, malformed/mismatch/oversize, legacy clearing, private grants, pending/stranger/block/takeover denials tested. No real user data persisted from tests.

## Manual acceptance

Close older candidates; open the new host/VM versions with different accounts. Check Details and the menu icon, start/exit Kohan normally and observe the launch label, copy a supported friend's profile and compare the applied channel/components. Test cancellation and blocked logout during applying. Actual game execution and real host-to-VM configuration application were not performed by automated fixtures.
