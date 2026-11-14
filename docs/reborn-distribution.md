# Kohan Reborn distribution

## Access and installation

Reborn is available to confirmed, unrestricted Paw’s Team members **or administrators**, with an active launcher session. Public Arcane Wars access is unrelated. Navigation sits directly above administration. Installation, update checking and Play share the standard footer. The folder picker opens at first installation. One root contains independent `Release` and `Beta` directories with atomic per-build activation; Kohan II files are untouched.

Private release history includes both channels and up to 200 published builds. Notes support RU/EN/UK/CS/DE/FR with English/Russian fallback. Account/role changes cancel pending operations. Self-update/closing is deferred during installation; social controls remain independent.

## Backend and protocol

Apply the three migrations `20261114000000_reborn_builds.sql`, `20261114010000_reborn_history.sql` and `20261114020000_reborn_github.sql`, then deploy `supabase/functions/reborn-builds`. JWT gateway verification is disabled because the handler validates the token with Auth itself, then checks confirmed email, current role and active session through service-only RPCs. Anonymous/authenticated database roles cannot read build rows or impersonate RPC callers. The Storage bucket remains private.

The edge accepts authenticated POSTs with the launcher session header:

- `?action=catalog&protocol=2`: latest enabled, already-published build per channel.
- `?action=history&protocol=2`: published history, limited to 200.
- `?action=download&protocol=2&channel=stable&build_id=<UUID>`: ticket for that exact build.

Protocol 2 supports `supabase` and `github`. Legacy requests omit the protocol, receive only Storage builds and cannot request GitHub tickets. Only the explicit gateway `404 NOT_FOUND` for undeployed catalog/history is empty; other errors and failed downloads remain errors.

## Private GitHub provider

Configure server environment variables:

| Name | Value |
| --- | --- |
| `REBORN_GITHUB_TOKEN` | Server-only repository credential, Contents: read for the selected private repository |
| `REBORN_GITHUB_REPOSITORY` | Canonical `OWNER/REPO` |
| `REBORN_GITHUB_REPOSITORY_ID` | Positive numeric repository ID |

Manage production secrets in the [Supabase dashboard or CLI](https://supabase.com/docs/guides/functions/secrets). Never commit the token, include it in the launcher or reuse a broad publishing credential as the integration credential. A [fine-grained token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) restricts repository and permissions. Monitor and rotate it before expiry.

Build rows add `download_provider='github'`, `github_repository`, `github_repository_id` and `github_asset_id` to UUID/channel/version/size/SHA-256/root EXE/notes/publication date. Constraints reject incomplete identities. Storage rows default to `supabase` with null GitHub fields. Credentials and signed URLs are never persisted in rows or installation markers.

For each ticket the server verifies the configured repository is private with the expected numeric ID. The exact asset must be uploaded, a ZIP, and match the catalog size and GitHub SHA-256 digest. The [GitHub asset API](https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28) is called with manual redirects; only API requests receive the GitHub credential. Binary 200 responses are refused instead of proxied through Supabase. A 302/307 Location is accepted only for HTTPS `release-assets.githubusercontent.com`, default port, no userinfo/fragment, repository-bound release-asset path and non-expired signature. The server never fetches the archive/CDN.

The ticket contains `ticket_version=2`, exact build, `url`, `expires_at` and `url_expires_at`. `expires_at` is the deadline to **start** a download (at most 120 seconds). `url_expires_at` is GitHub's actual signed URL expiry, read from `se`. These are different lifetimes: role withdrawal or ticket expiry cannot instantly revoke an already-issued CDN URL. Responses have `Cache-Control: no-store`. Membership and exact archive identity are checked again before issuing the ticket.

## Publishing

1. ZIP an accepted standalone Windows export with the actual EXE at the root and every required runtime/data file. Choose a fresh UUID and record exact size/SHA-256. Do not reuse UUIDs or replace assets.
2. Upload to a private GitHub Release, download back and verify. Record canonical repo, numeric repo/asset IDs and localized notes.
3. Insert metadata with `enabled=false` through the trusted database administration route.
4. Verify server credential access and download behavior; release a compatible launcher. Only then enable the row. Disabled/future rows do not appear in history/catalogs. Beta may remain empty.
5. Later compatible builds require new UUIDs/assets and metadata, without updating the launcher.

Existing Storage distribution signs only `paw-reborn-builds/<channel>/<UUID>.zip` for 120 seconds and remains subject to project Storage limits. No paid plan is required or activated.

## Client verification

Tickets bind every archive identity field, including provider/repository/asset IDs. The client restricts HTTPS host/path/port/userinfo/fragment, validates both expiries and refuses redirects. A fresh download client sends no account, Supabase or GitHub credentials to the CDN. Size and SHA-256 are checked before extraction.

Extraction uses fresh owned staging. Absolute/traversal paths, Windows streams/device names, case-insensitive collisions, symlinks and oversized archives are rejected. Authorization is repeated before atomic activation. Unknown files, unrelated markers and existing installations survive failed/cancelled updates. Matching completed builds can be retried. Already downloaded files are not remotely deleted on role withdrawal.

Tests use mocked providers, a loopback HTTP fixture and tiny text EXEs that are never executed. Real desktop game/launcher acceptance is separate.
