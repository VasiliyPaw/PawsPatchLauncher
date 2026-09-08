# Launcher 0.5.9: channel-independent update checks

Historical first-phase report. Superseded by [the combined candidate](validation-launcher-0.5.9-combined.md).

Status: locally built and verified; not published. Game packages and public feeds
remain unchanged. User's running launcher/game were not stopped or replaced.

## Implementation

- `FeedClient.GetLauncherUpdateAsync` reads both configured signed channel sources
  and mirrors in parallel, selecting the highest valid launcher version. It neither
  installs nor archives gameplay packages and does not consult a patch pin.
- `LauncherUpdateState` retains a detached latest release for the session. Channel
  switches, null/old responses and errors cannot erase it. Equal-version assets are
  immutable. Failed self-update hashes are still blocked by existing UI policy.
- The shared check runs alongside the selected patch check. It completes even when
  the selected patch endpoint or pinned manifest fails, before startup auto-update.
  Existing startup/manual/minute checks and manual update button are preserved.
- Manifest HTTP requests ask caches to revalidate (`no-cache`, `max-age=0`). This
  does not claim that an unavailable or delayed server can be made fresh instantly.

## Verification

- General tests: 1476 passed, including 44 new signed-source/state checks.
- New checks cover Release newer/Beta older and vice versa, 404, tampered signatures,
  wrong channels, malformed metadata, stale first mirror, preserved URL query,
  partial timeout, full cancellation/failure, Beta-only/empty configurations,
  no patch writes, mutable-feed aliasing and monotonic update retention.
- WPF: 13 shared-update assertions in both RU and EN runs. Beta startup discovers a
  newer launcher advertised by Release; button stays visible across four switches,
  both stale feeds, both failed feeds, missing pinned patch and broken active channel.
- Existing patch-channel checks: 16 passed per language. Independent settings and
  About regression checks passed. 1440x900 preview inspected; update button fits.
- Real isolated self-update 0.5.8 -> 0.5.9 passed with a Unicode/ampersand/bracket
  path, executable replacement, previous EXE retained and window acknowledgement.

Built EXE: `release_workspace_059/launcher/win-x64/PawsPatchLauncher.exe`

SHA-256: `A9F321E0D11EB455AB496A10100964B7264071DE9949FA917E4BC7E7FDBC6F47`

No live network/game test is claimed for these fixtures: HTTP sources were mocked,
WPF feeds were disposable local files, and real EXE update ran in smoke isolation.
Publication and user acceptance are separate steps.
