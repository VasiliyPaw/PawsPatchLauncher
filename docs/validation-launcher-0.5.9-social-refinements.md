# Save retries, lowercase usernames and offer confirmation — 2026-09-08

## Candidate

- Host: release_workspace_059/social-refinements/launcher/win-x64/PawsPatchLauncher.exe
- VM: \\VBOXSVR\KohanShare\PawsPatch-Social-Refinements\PawsPatchLauncher.exe
- Host share: D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Social-Refinements
- EXE: 72,201,446 bytes; host/share SHA-256 **2C91934C1356AD6E25D4B8CFEFF4038154A60AF234D4237AF2F8F909641CD5E5**.
- Previous candidate preserved. VM share contains only EXE and launcher.config.json; no passwords, account storage, preferences or saves copied.
- Host retains its previous signed local-feed configuration; VM retains its previous signed public-feed configuration. No launcher/patch feed or game packages published.
- VirtualBox confirms Kohan II Test running and KohanShare mapped to the above host share. The guest launcher and game were not launched.

## Save retry fix

The social-transfers cleanup route successfully deletes completed/declined transfer objects and calls the SQL void function paw_transfer_cleaned. The function commits successfully, but PostgREST may return an empty HTTP 204 or 200 body. Calling response.json() on it throws AFTER cleanup succeeds; the handler maps that exception to service_unavailable, and the launcher presents it as a connection failure. On the next attempt no cleanup candidates remain, so it succeeds. This reproducibly explains the reported alternating behavior.

Only this known void RPC consumes no JSON now; failure HTTP statuses still fail. The upload/download access checks, launcher lease, friendship, immutable payload, maximum size and hash validation are unchanged.

- Regression demonstrated red on old handler: two new assertions failed with 503 instead of 200 (22/24).
- Corrected handler: 24/24 Node tests. Includes cleanup/upload/cleanup/upload, empty HTTP 200, and real failed cleanup RPC.
- Deployed social-transfers v2 ACTIVE. verify_jwt=false is unchanged; custom verified Auth/session/launcher checks remain. Deployment SHA-256 94ee26acfe35a46d43bb1a38d38fcbad6597fb2fc79b46ed61eb76684eea4dad.
- Production log access returned Insufficient scope. No alternate credentials or log route used; the reproduction is not a correlation with the user's exact production failures and does not rule out other network faults.

## Interface and identity

- Registration and profile edit actions put display name before username. Registration focuses the display-name field.
- Usernames accept uppercase entry but are normalized on signup, login, availability checks, renames, friend requests, profile loading and friend-list parsing. Cached identifiers are presented lowercase too. Display names retain their case.
- Database trigger and check enforce lowercase identifiers for all clients. Existing profile usernames were backfilled without changing UUIDs, display names or rename cooldown timestamps.
- Before/after: 2 profiles, mixed-case username count 1 -> 0; digest of UUID/display-name/nickname_changed_at unchanged (a4bd174c328276ea4fcb573ebfb7ef81).
- Case-only rename requests are unchanged, including during the five-minute cooldown; real renames still enforce uniqueness and cooldown.
- Volume track click now captures one continuous mouse gesture until release/lost capture. Drag clamps at boundaries, snaps to integer percent and calculates from absolute geometry to avoid stale thumb-layout jumps. Native thumb and keyboard behavior retained.

## Sending configurations

- Reads the actual installed/applied configuration and refreshes the recipient's configuration before showing confirmation.
- Confirmation identifies recipient and lists changes for them. Cancel does not create an offer or optimistic card. Confirm starts the existing dim inline send workflow.
- Matching configurations show a clear explanation with disabled Send. Unknown recipient configuration is also disabled rather than guessed.
- New server check prevents sending a fresh identical offer through an old/tampered client or after a recipient-side change while the confirmation was open.
- Legacy omitted PS suffix equals PS1, NOT PS0. Both client and server account for that.
- Server check runs under existing participant/session locks and after immutable idempotency lookup, so retrying an already-created offer remains safe even if the recipient has since applied it.
- Sending while a game is running remains allowed; applying a configuration still requires a closed game. Save transfer behavior is unchanged apart from the cleanup correction.

## Validation

- Build and self-contained publish succeeded; build: zero warnings/errors. Normal git diff --check passed (line-ending notices only).
- .NET: **8587** assertions; identity/media subset 67.
- Node: social-transfers **24/24**, username-login **7/7**.
- Live disposable BEGIN/ROLLBACK suites passed: social_refinements, social_names_cancel, social_offers, friend_configuration, social_access, social_unread, single_launcher.
- New SQL suite checks signup/rename lowercase, preserved display case, duplicate denial, case-only/no-cooldown behavior, uppercase friend lookup, matching/PS1/PS0 configurations, immutable retries, save independence, stale-launcher denial and outsider denial. No test identities persisted.
- RU/EN WPF checks: Account 95, Social 49, Refresh/toast 23, Session/menu 20, Chat 43, Friend configuration 249, Offers 112, Identity/media 16, new Social refinement **35**, Feedback 27, Window 30.
- New WPF checks cover field/button order, confirmation match/diff/unknown/cancel/accept and programmatic disabled-action bypass, no premature cards, actual mouse capture on a hidden WPF surface, continuous value changes before layout, bounds/release/lost capture.
- Visually inspected RU send-difference dialog, EN matching dialog, and compact 1050x680 registration. The compact form scrolls; display name is first.
- Existing Supabase advisor warnings were inspected; no access policies or unrelated security settings weakened.

## Manual gate

Close older candidates, open this candidate on host and VM with two different accounts, then send/accept or decline several saves in succession. Check drag feel, lowercase identifiers, configuration match/difference confirmation and cancellation.

Automated fixtures do not replace real authenticated host-to-VM transfers, native mouse feel or game acceptance. The unfinished user phrase about clicking outside boundaries is awaiting clarification; no guessed outside-click behavior was added.
