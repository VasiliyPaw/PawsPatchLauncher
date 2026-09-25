# Launcher 0.8.7 verification

## Scope

Changelog Markdown headings and bullets use distinct WPF formatting. Native
observer slots are transmitted with an explicit `observer` flag and displayed
in a separate localized group in lobby and match details. Unknown team or color
alone never implies an observer. Observer rows retain profile access and omit
inapplicable race and color fields.

The optional field was appended to the participant constructor to preserve
existing positional callers. Native snapshots reject role changes during a
read; lobby detection requires a readable empty kingdom identifier, while
match detection follows the native `ObserverGlyphInfo` null-kingdom branch.

## Local validation

- Full Release console suite: `PASS 27010`, plus `AI_OPTIONS_PASS 307`.
  Run with `dotnet run --project tests/PawsPatchLauncher.Tests/PawsPatchLauncher.Tests.csproj -c Release`.
- PreviewRenderer Release build: zero warnings and errors.
- WPF activity checks: 44 checks in each of Russian and English, including
  explicit observers in both lobby and match, legacy unknown participants,
  grouping, linked profiles, layout, scrolling, refresh and cancellation.
- WPF changelog checks: 24 checks in each language, including heading styling,
  marker removal, bullets, expansion/collapse and filter transitions.
- Isolated account database: 6,522 checks with the standard migration runner
  and 6,522 checks using the guarded deployment SQL.
  Checks cover explicit roles, invalid/conflicting roles, legacy activity,
  authenticated presence-to-friend-detail round trips and profile access.

These are native-memory, transport and database fixtures plus rendered WPF
windows. They do not establish a live two-client game acceptance test. No game
installation, save, lobby name or player-count preference was changed.
Local UI captures are under `outputs/launcher-087-release/ui-ru` and `ui-en`
in the enclosing task workspace.

## Production Supabase

On 2026-09-25 the guarded transaction in
`supabase/tests/deploy_game_activity_observers.sql` was applied to the configured
production project `trdzsdclscuwwmxnepyt` through its authenticated SQL editor.
It changes only `paw_private.valid_game_activity(jsonb)`; RPC signatures,
profile resolution, permissions and stored user rows are preserved.

The transaction checks the existing function source before applying the change
and verifies the result before commit. MD5 here fingerprints normalized PostgreSQL
function source (`replace(prosrc, E'\r', '')`), not an artifact security signature:

- Before: `b01105abadb6bdb525395136b46be7b9`.
- After: `c3d0db57bc183dac69c62f6988d337ec`.

A separate post-commit query confirmed the new source fingerprint, acceptance
of an explicit observer and an old client participant, rejection of an observer
with a team, and no direct execute grant to `anon` or `authenticated`.
No production test accounts or presence rows were inserted. The SQL migration
file produces the same validated function as the guarded deployment script.

## Publication procedure

The existing tag-triggered workflow builds the autonomous win-x64 release and
publishes its manifest, EXE and ZIP. The current repository configuration, also
used for 0.8.6, does not enable Authenticode signing of the EXE. Catalog signing
is independent: all four legacy/v2 stable/beta catalogs use the production
ECDSA P1363 key.

`tools/PrepareLauncher087.py` verifies public tag identity and asset digests,
downloads and verifies EXE/ZIP contents, stages the signed catalogs, and checks
that every field outside launcher metadata/news/history remains identical.
Promotion rejects a changed local or public baseline. Its `readback` action
verifies the published four catalogs and history against the final main commit.

## Published artifacts

- Source/tag: `522e25a972250314c072ceff8b3af8ec55f6c39f`, `v0.8.7`.
- [Release](https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v0.8.7).
- [Release workflow](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/36092548636): success.
- [Independent build/test workflow](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/36092546254): success.
- Downloaded EXE: 73,119,334 bytes, file version `0.8.7.0`, product version `0.8.7`.
  SHA-256: `92F640947C5679BF9CC236F2E38E8665B40F2B453C4B9E4E09C54196AC5A1D62`.
- Downloaded ZIP: 67,712,612 bytes.
  SHA-256: `B80E112E2FFF10A52F9770C35A24E6ED11AE81949D2F0E8D5071219AC9A584E7`.
- Both hashes match the published manifest and GitHub asset digests. Every file
  inside the ZIP matches its manifest record. Windows independently reports
  `NotSigned`, matching the existing workflow policy and artifact manifest.
- Four staged production catalogs passed ECDSA verification and preserve all
  prior game data and notes. The separate history JSON receives only the new
  launcher entry in each channel; older entries are left as they were.
