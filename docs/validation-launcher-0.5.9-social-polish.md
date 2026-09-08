# Launcher 0.5.9: notifications, stable refresh and request rows

2026-09-08. Local test candidate only; no public release, feed publication, server/schema changes, game launch or account/credential copying.

## Artifact and VM placement

- Host candidate: `release_workspace_059/social-polish/launcher/win-x64/PawsPatchLauncher.exe`.
- Shared VM copy: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Social-Polish\PawsPatchLauncher.exe`.
- Guest path: `\\VBOXSVR\KohanShare\PawsPatch-Social-Polish\PawsPatchLauncher.exe`.
- Both EXEs: **72,066,950 bytes**, SHA-256 `C8BC563924D149685A9BEA506482ED8608E3D200AF5978C0546CED92A48E0BC6`.
- VirtualBox VM `Kohan II Test` (71c0eae1-1046-4b89-94c6-9b617b0dc485) was already running; Guest Additions 7.2.16 active. Existing KohanShare mapping was inspected and left unchanged.
- Only EXE and public configuration were deployed to a new shared subdirectory. Windows required an approved elevated copy into this existing protected share. No unrelated files were replaced.
- VM configuration uses the repository's signed public stable/beta feed URLs, not host-only G: paths. The host candidate retains its previous signed local components-v2 feed configuration.
- This is portable shared-folder placement, not a guest C: installation. No guest launcher was started and no guest filesystem credentials were obtained. User should launch it from the UNC path and sign into a different account.
- Session storage remains per-Windows-user LocalApplicationData inside each OS; no sessions, passwords, avatar cache or outbox data were copied.

## Diagnosis and changes

The attached 7.27-second 60 fps MP4 was decoded read-only and sampled into `reported-flicker.png`. The request/add buttons visibly change to their disabled grey style during activation/navigation refresh. In the source, both the Friends navigation and Activated handlers invoke a refresh wrapped in the same busy state used for mutations.

- Read-only/background social and account refreshes now keep buttons enabled. Async gates serialize reads and explicit actions without dropping the click that arrives during a read. Repeated user submissions remain blocked, and an owner change discards a queued old-owner action.
- Unchanged navigation brushes and friend/conversation/outbox rows are retained instead of rebuilding/resetting their visuals. Only real user mutations disable their related controls. Pending request/message input is cleared only if it still matches the submitted snapshot.
- Avatar success feedback restored: “Аватарка успешно изменена.” / “Avatar updated successfully.”; removal uses a short neutral description. No server-replacement wording.
- Consistent bottom-right rounded toast styling: green success, red failure, dismiss button, existing fade motion. Success expiry 3 seconds; error expiry 8 seconds. The independent toast explicitly opts into failure expiry; actionable operation failures still persist in their status/details area.
- General operation results and friendly errors, account actions, friendship actions and social interaction errors use the common toast. Ordinary errors no longer force-open a modal details window; the explicit details action remains available. Background polls do not repeatedly toast social failures.
- Successful account actions no longer leave a large permanent success card. Confirmation/validation/recovery instructions remain beside the form when needed, alongside the transient notification.
- Requests now has Incoming/Outgoing sub-tabs. Incoming count remains visible; each player is in a compact bordered row with nickname left and Accept/Cancel/Unblock right. Incoming decline/block is behind the actions menu. Long nicknames ellipsize and retain a tooltip.

## Validation

- .NET **6064 PASS**, including four new controlled-clock tests for transient-error/success expiry and unchanged persistent-failure semantics.
- UI, each language RU/EN: account **95**, social **49**, refresh/toast **23**, feedback **27**, window/confirmation **30**. Motion **35**.
- New async UI checks observe **zero enabled-state transitions during 20 background polls** and delayed account refresh; only the explicit queued action disables/restores controls. Checks cover one execution on a double click, identity change while waiting, stable row/bubble/queue/button brush references, avatar wording/color/expiry, persistent actionable errors and unrelated operation-status isolation.
- Detached WPF previews inspected at 1440x900 and 1050x680: incoming/outgoing requests, long nickname, avatar success and error toast.
- Build/publish: zero warnings/errors. `git diff --check` passed. Host/VM-copy EXE SHA-256 equality verified.
- Prior test candidates preserved. No real auth/social requests, account deletion, mail, game/save mutation, clipboard or live main-window automation were used in these checks.

## Manual gate

Close the older launcher and start this candidate on the host and via the shared UNC path in the VM. Use two distinct accounts. Confirm Alt+Tab and page switches no longer flash grey buttons, request rows/actions behave correctly, avatar toast expires, and unread counts update after exchanging messages. Live two-account/VM rendering acceptance remains for the user; static and automated UI checks do not replace it.
