# Kohan Reborn launcher integration

Local feature candidate. No archive, production migration, edge deployment or launcher release has been published by this work.

## Access and channels

- Eligible accounts: a verified, unrestricted Paw’s Team member **or an administrator**. Arcane Wars' public-access switch is unrelated and is not reused.
- Release (`stable`) and Beta (`beta`) start empty. No example build is inserted by the migration. The page honestly shows that no build has been published, with Download disabled.
- The navigation entry sits directly above the admin menu and uses a dedicated circled K icon. Installation, update checking and Play use the same footer positions as Kohan II. The folder picker opens only when the first available build is installed; it is absent from the page.
- Channel choice and the shared installation folder are local launcher preferences. The root contains `Release` and `Beta` subfolders with fixed names independent of UI language. The two channels keep separate active builds and version directories; changing channel does not reinstall the other channel or alter Kohan II.
- Account identity/role changes invalidate pending page responses and cancel an active Reborn operation. Launcher self-update and closing are deferred while Reborn is installing; friendship/chat controls remain independent.

## Server contract prepared for activation

1. Apply `supabase/migrations/20261114000000_reborn_builds.sql` through the established production migration procedure.
2. Deploy `supabase/functions/reborn-builds` using the same environment/authentication configuration as the existing account edge functions. The handler validates the Auth user, confirmed email, active launcher session and current database role.
3. Verify both empty catalogs using a team account and an admin account; verify rejection of ordinary/guest/restricted accounts.

The `paw-reborn-builds` storage bucket is private. No anon/authenticated direct-storage policy is added. The authorization RPC is callable by `service_role` only, so a client cannot impersonate another player by passing an arbitrary UUID. Download authorization is repeated after the signed URL is prepared. URLs expire in 120 seconds, are returned with `no-store`, and are never saved in installation metadata.

Private-bucket and expiring-link behavior follows the [Supabase storage documentation](https://supabase.com/docs/guides/storage/buckets/fundamentals); the REST signing request/response matches the [official storage client implementation](https://github.com/supabase/storage-js/blob/main/src/packages/StorageFileApi.ts).

The local SQL/WASM and edge tests exercise the authorization contract without touching production.

## Adding the first accepted build later

- Choose an accepted standalone Windows export. Package the EXE at the ZIP root alongside every required runtime/data file. Supply its actual root EXE filename in metadata, e.g. `KohanReborn.exe`; do not package the unrelated old Recoil prototype or a developing working directory automatically.
- Generate a new UUID for each build. Compute the ZIP's exact byte length and SHA-256. Upload it to private storage as `stable/<UUID>.zip` or `beta/<UUID>.zip` without upsert.
- Insert a row in `paw_private.reborn_builds` using a trusted server/SQL administrator: `id`, `channel`, `version`, `size`, `sha256`, `executable`, `published_at`, `notes` and `enabled=false`. Notes are a JSON object with RU/EN/UK/CS/DE/FR text as available. The launcher falls back to English/Russian when a translation is absent.
- Verify the uploaded immutable archive, then enable that row. Do not replace an existing archive or reuse a UUID. Catalogs select the latest enabled, already-published row per channel.
- Disabling a row prevents issuance of a new ticket. A previously issued short-lived URL may remain usable until expiry; already downloaded files are not deleted from a player's disk.

## Client installation

The client accepts tickets only for the configured Supabase HTTPS host and exact private object path, checks selected build identity/hash/size/EXE/expiry, refuses redirects, verifies archive size and SHA-256, and extracts into a fresh owned staging folder. Absolute paths, traversal, Windows streams/device names, duplicate case-insensitive paths and archive symlinks are rejected. Server authorization is repeated before activation. A complete directory is activated atomically; an interrupted activation can retry only when all existing build paths/bytes match. Unknown files and unrelated installation markers are preserved.

Tests use tiny text EXEs that are never executed. Real Reborn archives will be provided separately, as requested.
