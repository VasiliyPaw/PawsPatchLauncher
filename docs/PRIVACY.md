# Privacy policy / Конфиденциальность

Updated: 2026-09-10. Applies to Paw's Patch Launcher, maintained by
[VasiliyPaw](https://github.com/VasiliyPaw), not to Kohan II or third-party mods.

## What the launcher sends

| Feature | Data and destination | User control |
| --- | --- | --- |
| Update checks and downloads | Requests to the configured GitHub/feed/package hosts. As with any HTTPS service, the host receives connection information such as your IP address and the requested resource. | Checks happen automatically while the launcher is open; close the launcher to stop its requests. |
| Optional account | Email, authentication requests, username, display name and session identifiers go to the project's Supabase authentication/backend service. The password is sent to authentication endpoints during the relevant account actions. Confirmation/recovery email uses the configured email provider. | Registration and sign-in are optional. The patch and game work in guest mode. |
| Signed-in presence | Online/playing status, applied patch channel, component settings and configuration code go to the backend for friend/profile views. Background requests continue while signed in, including after restoring a remembered login. | Sign out to stop social requests. Disable “Remember me” to avoid restoring a session on the next launch. |
| Friends and chat | Friend relationships, messages, delivery/read acknowledgements and configuration offers go to the backend and intended users. Authorized administrators can manage accounts and moderation. | Use these optional features after signing in; do not send information you do not want stored or shared. |
| Avatar and save sharing | Selected avatars and saves are uploaded to the project's Supabase backend/storage for the requested profile/transfer functions. | Uploads require the corresponding user action; game saves are not uploaded as general telemetry. |
| Chat images | Supported image/GIF hosts may be contacted directly when a conversation displays media. Other supported images require the load action. The remote host receives the media request and connection information. | Avoid loading external media; sign out to disable chat. |
| Diagnostics | Requested diagnostic archives contain local logs, crash dumps, installation/module information and hashes. Creating an archive saves it locally and does not automatically send it to the maintainer. | Review before sharing: crash dumps can contain process memory fragments. |

Settings, installation records, backups, caches and logs are stored locally.
Remembered session tokens are protected for the current Windows user;
account-session files are excluded from launcher diagnostic archives. This does
not make manually shared crash dumps safe to publish without review.

## Storage and deletion

Account and social data remain on the service for the relevant features and their
maintenance/moderation rules. Signing out or uninstalling does not by itself delete
server data. Account deletion is a separate action in the profile. Do not assume
recipients' copies of messages/saves, or provider logs/backups, disappear immediately.

Providers apply their own policies:
[GitHub](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement),
[Supabase](https://supabase.com/privacy),
[Cloudflare](https://www.cloudflare.com/privacypolicy/) for applicable download hosting,
and [Resend](https://resend.com/legal/privacy-policy) for configured email delivery.
External media is also subject to the selected host's policy.

No account credentials, chat history, saves or diagnostic files need to be sent to
SignPath for code signing. It receives the build artifact and source/build
provenance. For privacy questions contact the maintainer through the launcher or
repository. Do not post passwords, verification codes, private saves or crash dumps
in a public GitHub issue.

## Кратко по-русски

Лаунчер автоматически проверяет обновления и обращается к серверам загрузки.
Патч и игру можно использовать без аккаунта. При входе сервер получает данные
аккаунта, а во время работы — статус «в сети/в игре», канал патча и применённые
настройки для функций друзей. Выход отключает социальные функции; снятая галочка
«Запомнить меня» предотвращает автоматический вход в следующий раз.

Сообщения, аватарки и выбранные для передачи сохранения поступают в сервисы
проекта и соответствующим получателям. Картинки в чате могут загружаться прямо
с внешних сайтов. Диагностический архив создаётся локально и не отправляется
автоматически. Проверь его перед передачей: дампы могут содержать части памяти.

Удаление лаунчера не удаляет аккаунт на сервере. Для этого есть отдельное действие
в профиле; уже полученные другими людьми копии данных от этого не исчезают.
Полное описание данных и сервисов приведено выше.
