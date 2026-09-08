# Launcher 0.5.9 — clipboard and chat polish (2026-09-08)

## Scope and evidence

- Friend profile has a copy-username icon. Own/friend username and configuration-code buttons become a green checkmark after successful copy and stay disabled for five seconds. Pending copies also prevent repeated clicks. Failure restores the normal button immediately. Changing profile identity or closing the window clears stale feedback. Button content/localization and external disabled states survive the cooldown.
- Account creation and friend last-seen timestamps use local date/time with seconds (RU `dd.MM.yyyy HH:mm:ss`, EN `yyyy-MM-dd HH:mm:ss`).
- Chat header has a 38 px avatar and one keyboard-accessible profile button covering the avatar/name/username. Username baseline is raised. The avatar is retained on unchanged renders.
- Loaded media hosts shrink-wrap their images; media messages align to their sender instead of filling the entire row. PNG/GIF limits, signed-link preservation, explicit loading for non-CDN links, failure fallback, and animation cleanup are unchanged.

## Clipboard diagnosis and implementation

Read-only inspection of the local launcher error log found `CLIPBRD_E_CANT_OPEN (0x800401D0)` at `System.Windows.Clipboard.Flush`, including 2026-09-08 05:00:19 and 05:00:29 UTC. The existing writer used WPF `Clipboard.SetText` on the main STA dispatcher. This establishes the failing clipboard/OLE flush path, not which other application held the clipboard or a measured duration of each freeze.

Copy now writes eager `CF_UNICODETEXT` using `OpenClipboard` / `EmptyClipboard` / `SetClipboardData` on a serialized background worker, without `OleFlushClipboard`. The full movable Unicode buffer is prepared before opening/emptying; successful ownership is transferred to Windows and only untransferred buffers are freed. The owner is a real launcher HWND. Open contention gets six attempts with 600 ms total backoff; unrelated errors are not retried. Cancellation is checked before mutation; once cleared, the short native transaction finishes before a newer writer can run. Stale completion cannot produce a success toast. Clipboard reads/paste remain on their existing STA path.

Native protocol references: [Microsoft SetClipboardData](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setclipboarddata), [Using the clipboard](https://learn.microsoft.com/en-us/windows/win32/dataxchg/using-the-clipboard).

## Validation

- Build and self-contained win-x64 publish succeeded, no warnings/errors.
- .NET suite: **8611 assertions passed**, including 11 new background clipboard checks (Unicode, contention, unexpected failure, responsiveness under simulated blocking, serialized writes, canceled queued/stale work).
- WPF RU/EN: Account 95, Social 49, Refresh/Toast 23, Session/Menu 20, Chat 43, Friend Settings 249, Offers 112, Identity/Media 16, Social Refinement 35, Social Finish **54**, new Media Layout **26**, Feedback 27, Window 30. The clipboard tests use simulated writers only and do not read or replace the user's clipboard.
- Actual decoded fixture PNGs at 1440x900 and 1050x680: wide and portrait aspect ratio, tight background/bubble width, hidden URL, sender alignment and horizontal bounds passed. Existing GIF first-frame/repeat/link fallback/teardown checks passed on hidden native render surfaces.
- Rendered and visually inspected chat, media (RU normal / EN compact), profile (EN compact), and account (RU compact) previews in `release_workspace_059/social-polish/`.
- `git diff --check` passed (existing line-ending warnings only). Existing mixed source changes preserved; no commit, push, feed publishing, Supabase change, real account mutation, game launch, or save replacement.

## Candidate

Host: `release_workspace_059/clipboard-polish/launcher/win-x64/PawsPatchLauncher.exe`.

VM host-share copy: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Clipboard-Polish\PawsPatchLauncher.exe`.

Guest: `\\VBOXSVR\KohanShare\PawsPatch-Clipboard-Polish\PawsPatchLauncher.exe`.

Both files: **72,210,690 bytes**, SHA-256 **AF5FACE4083093A0DEBCCBFD593922588A872EDE54B6432F585EECE517DCE3E8**.

Separate new candidate directories contain only the executable and device-appropriate `launcher.config.json`, copied from the preceding Social-Finish candidate. No account/session files copied. Existing VM Social-Polish folder was detected and left untouched; Social-Finish also remains. VM is running with KohanShare mapped to the expected host directory. Guest EXE was not launched.

## Manual acceptance remaining

Close the previous test launcher and open the new candidate. Check real username/configuration copying with the usual clipboard utilities running, the green five-second checkmark, profile opening from avatar/name, and a real image/GIF. Automated contention tests establish responsive scheduling and truthful feedback, not empirical timing or zero future clipboard contention on the user's desktop.
