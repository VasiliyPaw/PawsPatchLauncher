# Launcher 1.0.11 publication — 2026-11-09

Source/tag: `749b0533377667051b6557e7da7660a1d0216692`, `v1.0.11`.

## Production profiles

The user authorized publication after reviewing the UI. Migration
`20261108020000_unblocked_player_profiles.sql` was applied transactionally and
registered in `supabase_migrations.schema_migrations`. Preconditions matched the
deployed friend presence, activity and avatar definitions before mutation.
All eight resulting normalized function source checksums and execution grants
match the isolated local migration result:

| Function | Source MD5 | Anonymous execution | Authenticated execution |
| --- | --- | --- | --- |
| `paw_friend_avatar_allowed(uuid,uuid,uuid,uuid)` | `3be885efd85b22303d80d9f30ae663a9` | false | false |
| `paw_game_activity(uuid)` | `54f67b137a6ad665439655c63bf5314d` | false | true |
| `paw_private.friend_presence(uuid,uuid)` | `1901a0c08043ea7da830f4e5eb72014f` | false | false |
| `paw_private.profile_activity_details(uuid)` | `3e789f41262d1d4f03a9af98b940c358` | false | false |
| `paw_private.profile_presence(uuid,uuid)` | `5cea1d37e267f367a41d7452a70acdcb` | false | false |
| `paw_private.profile_view_allowed(uuid,uuid)` | `1fa06a31707495af8503b3d23037fe04` | false | false |
| `paw_profile_activity(uuid)` | `110fd63e801dbb66d49f5179ac949084` | false | true |
| `paw_profile_card(uuid)` | `404746b7c8af8f3f530e4a9629b7827c` | false | true |

The original friend presence and activity functions retain their exact source.
New full-profile endpoints require authenticated execution; private helpers and
the avatar authorization callback are not directly executable by clients.
HTTPS readback returned 401/42501 for anonymous calls to both new endpoints,
rather than a missing-function/schema error. The existing public online directory
still returns 200/ok. No production fixture users, friendships or presence rows
were created or modified. Full two-account interaction remains covered locally.

## Verification

- Local C# suite after version bump: 38,418 assertions passed.
- Local isolated PostgreSQL/WASM suite: 12,547 passed.
- Prior targeted UI checks and reviewed screenshots are recorded in
  `verification-friend-downloads-profiles-20261108.md`.
- Source CI `42541917298`: success.
- Release workflow `42541932222`: success.
- Public release: https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v1.0.11
- Source and public assets identify the exact tagged commit above.
- Public EXE: 74,368,040 bytes, SHA-256
  `120B5777E2D3B40A2B6EB6A3A88AD84272AE56A74DC0E1B4D75AF1BF2A0F68DF`.
- Public EXE and ZIP were downloaded and verified against the tagged CI artifact
  manifest, including every file in the ZIP.
- All six signed catalogs advertise 1.0.11 with the verified EXE hash. Their
  signatures passed verification; every game catalog/package field is unchanged
  relative to its own 1.0.10 baseline. Changelog history preserves both branches.
- Staging and publication evidence: top-level
  `outputs/release1011-catalogs-20261109/`, including the signed catalogs, baseline,
  artifact manifest and downloaded EXE/ZIP.
- This is a normal production build, without a community test flag/profile marker.
