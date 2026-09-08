# Account page and public email confirmation, 2026-09-08

Supersedes the UI candidate in validation-launcher-0.5.9-account-profile.md. Earlier stage results remain historical. The user has since received a confirmation email and signed in; do not interpret the earlier zero-user/SMTP notes as current state.

## Scope

- Independent Account page, reachable through the narrower 72px header button; not a sidebar entry. Guest Friends buttons navigate to Account login/register. Signed-in Friends link opens profile.
- Show password checkboxes for login/registration, profile password fields and recovery password fields. Masked and visible inputs are synchronized. Revealed copies are cleared on hiding, navigation, success and close. Visible controls disable undo history. Recovery proof stays masked.
- Failed login keeps entered email and password, including an explicitly revealed password. Successful login and successful registration clear password controls. No password persistence, diagnostics or logging was added.
- Account errors appear directly below the Account introduction, above the form, with icon, readable text and animated highlight. Email-not-confirmed uses a gold warning and retains resend action. Success uses green; other failures use red.
- Existing 6-128 password validation, remember-me persistence and profile server cooldown remain unchanged.
- Signup, resend and change-email requests now specify the fixed hosted confirmation redirect; no callback from untrusted input. Only the public publishable key is in the clients.
- Avatar uploads were discussed only; not implemented. Friends/chat/save transfer are still explicitly marked as next-stage features.

## Local candidate

`release_workspace_059/account-page/launcher/win-x64/PawsPatchLauncher.exe`

Size: 72,030,259 bytes.
SHA-256: `BFBA756EEAA7DCD9DA872DE0DA23F7B4289C1E31248079EB0742EC110A620718`.

Adjacent config uses the existing local signed components-v2 feeds for testing. Not a public launcher release. No game/VM/real launcher process was started, stopped or modified. No real account data, passwords or email flows were exercised by automated checks.

## Verification

- Main suite: 5807 assertions passed, including signup/resend callback checks. Mock Auth requests only, actual Windows DPAPI fixture storage.
- WPF: 69 RU + 69 EN account UI checks. Separate page navigation, password rendering and reveal/edit/hide, failed local validation and server rejection, unconfirmed-email gold treatment/resend, async guards, clearing when leaving, profile/recovery controls, diagnostic exclusion.
- Existing Motion: 35 checks passed. Renderer layout, typography, native input, scrollbar, caption and navigation checks passed at 1440x900 and compact 1050x680.
- Headless WPF preview images inspected: register-ru.png, confirmation-error-ru.png, profile-ru.png, login-compact-en.png. Additional friends and motion previews generated. User desktop was not controlled.
- Renderer build: no warnings/errors. Self-contained single-file candidate publish passed. Whitespace check passed (existing CRLF conversion warnings only).

## Confirmation Site

Separate project: `../PawsPatchEmailConfirmation`; Sites registration `appgprj_6a9f39d4bca48191b4fbc87c8f7234b2`.
URL: https://paws-patch-email-confirmation.vasiliypaw.chatgpt.site/
Deployment: `appgdep_6a9f3c14e9fc8191bafeaf2b845b05d0`, succeeded. The provider's final hostname differs from the pre-deploy expected_url; client and setup instructions use the final returned hostname.
Source commit: `2a56192884480f04140ab215bbdb98a917e17c05`.

The user explicitly approved public visitor access. Only this separate Site repository was committed/pushed, not the dirty launcher repository. Windows has no usable Bash executable; packaging used the skill's unchanged prepare-site-build.cjs plus equivalent PowerShell copy/tar staging, validated Worker entrypoint and hosting metadata. No secret in source, remote URL, Git config or archive.

- Navy/gold confirmation result UI matching launcher, no additional sign-in system or database.
- Removes URL fragment/query from current browser history; keeps only the required access token in tab memory, drops refresh token. No local/sessionStorage, analytics or external fonts added.
- Shows success only after fixed Supabase GET /auth/v1/user returns a confirmed email. Direct visit, expired/used links, network error, pending email change and recovery have distinct honest messages. Fake success query parameters do not grant success.
- Recovery remains the existing native-code/unopened-original-email-link flow. The Site does not reset passwords or claim that a consumed link can be reused.
- 10 protocol unit tests passed, TypeScript passed, lint on authored files + used button primitive passed, production build passed. Full scaffold lint reports pre-existing warnings/errors in unused generated shadcn primitives; not presented as a full-lint success.
- Local HTTP 200 and generated content verified. No interactive browser acceptance or real mailbox callback was performed.
- Published URL returned HTTP 200 anonymously, with expected account page content and no ChatGPT sign-in gate. Provider did not preserve configured CSP/Referrer-Policy response headers, so no deployed-header enforcement claim is made. The page still clears fragments and all Auth fetches explicitly use no-referrer, fixed origin and redirect:error. An optional local production-server check was blocked from writing Wrangler's user-profile registry; no access bypass was used.

## Remaining manual gate

The connected Supabase MCP has database/storage access, not Auth configuration write authority. No credential extraction or alternate management route used.

In the project's Authentication > URL Configuration, add the exact above URL (including trailing slash) to Redirect URLs and save. Site URL may also be set to it for the dedicated launcher project. Do not disable email confirmation. Old emails keep their old localhost links; request a new email from this candidate to test the new redirect.

Latest user screenshot shows the final vasiliypaw hostname saved as Site URL (success toast), and present in Redirect URLs. The preliminary sage-globe address remains as an extra entry; advised removing that entry only. Row checkboxes select entries, not activation. This is user-provided dashboard evidence, not a live mailbox end-to-end test.

Check real confirmation success/expired link and ordinary account login/restart on the user's test account before releasing the launcher. Changing redirect allowlist and live confirmation have not been verified by automated fixtures.

Official references: https://supabase.com/docs/guides/auth/redirect-urls ; https://github.com/supabase/auth-js/blob/master/src/GoTrueClient.ts
