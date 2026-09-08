# Launcher 0.5.9 — social hub and profile

Date: 2026-09-08.

## Changes

- Friend profile uses the actual nine Components-tab labels and visual order, never server JSON property order. Localization now updates those labels before refreshing an open friend profile.
- Clicking the selected friend row deselects the chat, clears its draft/display and returns the empty right pane; sending is disabled. Durable outgoing messages/offers are not deleted.
- Installed core version and applied channel appear below the launcher version. Settings show the installed version and local verified archive download time, including seconds.
- New verified package downloads receive a separate local completion-date sidecar; this becomes module state metadata and survives state serialization/rollback. Cache hits do not reset dates. Old caches/installations without metadata say the date is unavailable; release/file timestamps are not misrepresented as download dates.
- Multiplayer navigation removed. Existing manual configuration copy/import moved to Settings. Other sidebar entries, 228-DIP sidebar width and 108-DIP logo preserved.
- Friends has an accessible send-icon button next to Add friend: a recipient-selection dialog for configuration/save offers. One chosen, validated save is reused for the selected recipients; the existing per-recipient authenticated create/upload protocol remains unchanged.
- Up to five recipients per batch, matching the existing five-new-offers/minute server rate limit. The server also retains its ten-active-offers cap. A previous individual/batch send can consume that allowance: partial results are shown and successful recipients are disabled; retry sends only selected remaining recipients.
- Configurations that match, unknown recipient configurations and missing installed local configurations cannot be offered. Membership/configuration rechecked before sending; existing server checks remain authoritative. Receiver acceptance and sender cancellation remain individual chat cards.
- Each delivery reuses the existing durable owner/recipient/content identity after an uncertain response. A cancel/close stops remaining work, retaining already-sent offers; account changes clear the dialog and private file bytes, cancel pending work and prevent stale delivery.
- Own profile redesigned with identity banner and separate profile/security actions. Large clickable avatar shows a translucent camera affordance on hover and a styled upload/remove menu. Standalone avatar buttons removed; existing avatar validation, account permissions and success toasts retained.
- Success/error toasts are centered above the main footer, with slide-up entrance and a filling expiry bar, on the root layer above profile/help/confirmation/broadcast overlays. Existing success/error lifetimes retained (3/8 seconds), with hover/focus retaining the message for reading. Progress ticks do not recreate brushes or rebuild chat controls. Entrance honors Windows animation settings.

## Verification

- Full unit suite: **8660 assertions passed**, including 16 new notification/date/cache/legacy metadata checks.
- New WPF Social Hub suite: **41 checks each in RU and EN**: exact labels/order including language change while open, avatar menu, removed controls/navigation, selected-chat toggle, center/root-layer toast geometry, non-zero modal/control heights and bounds, timestamps, recipient limits, partial retry without re-sending successes, cancellation, removed membership, rate limit and account replacement during pending preflight.
- Existing RU/EN account, social, clipboard/feedback, background-update no-flicker and arrival suites passed. Additional EN motion, appearance, component-settings and typography checks passed. No real clipboard contents, media, Auth or social network traffic were used; mock send transport exercised batch outcomes.
- Final release build/publish: no warnings/errors. Diff whitespace check passed.
- Visually inspected rendered profile, batch dialog and toast-over-dialog at 1050×680 and/or 1440×900. Fixed a zero-height off-screen dialog binding found in the first render; tests now explicitly require non-zero control heights.
- Relevant previews: artifacts/social-hub-profile-final-ru.png, artifacts/social-hub-final-ru.png, artifacts/social-hub-final-en.png, artifacts/social-hub-settings-en.png.
- Database migrations, edge functions, SMTP/templates, real accounts, game installations and save files were not modified by this task. No public feed release or commit/push.

## Test candidates

Host: release_workspace_059/social-hub/launcher/win-x64/PawsPatchLauncher.exe.

VM shared host folder: D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Social-Hub.

Existing guest share route: \\VBOXSVR\KohanShare\PawsPatch-Social-Hub\PawsPatchLauncher.exe.

Both EXEs: **72,226,202 bytes**; SHA-256 **F41E5790FD6FB843D95E7F4799B0D5C6E14AF8D85C2BD40E4EAAF8618EFD4F13**.

Each device's launcher.config.json was copied from its own Recovery-Code candidate and hash-checked. VM share contains only EXE and configuration; no sessions, credentials or saves copied. Running Recovery-Code launcher left untouched. Guest EXE not launched.

## Manual acceptance

Close the old launcher and open the Social-Hub candidate on each device with different accounts. Verify selecting/deselecting a chat, avatar hover/upload/remove, friend component order and settings date (old install may legitimately have no date).

Select configuration or one real save using Send to friends, verify receipt/accept/reject in the recipient's chat and cancellation in the sender card. Real end-to-end batch delivery, save installation and VM rendering remain manual gates; mocked transport/layout checks are not proof of those external outcomes. More than one selected recipient is needed to manually accept the full batch flow. Keep existing server limits enabled.
