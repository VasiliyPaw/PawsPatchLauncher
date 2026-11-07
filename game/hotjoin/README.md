# Active-match return — Arcane Wars beta

Arcane Wars Paw’s Patch 0.5.0-beta.2 embeds this runtime in all eight managed
game helpers. It is part of the main patch, with no additional launcher option.
The existing component selections still select their corresponding helpers.
Vanilla/Immortals and the stable channel are outside this release.

Join the running game's current host through the normal multiplayer connection
flow. A returning participant reclaims their original kingdom from its implicit
AI; a newcomer becomes an observer. Nicknames do not establish ownership. A
private random credential is stored in the local Kohan2 profile; only its public
SHA-256 verifier is replicated to support native host migration. Do not share
the local `User/HotJoinTicket.bin` file. Reinstalling/deleting that profile may
remove the right to reclaim the kingdom.

A departure requests a shared native pause before AI simulation can proceed.
Players may resume without the absent participant. Admission temporarily pauses
an active match and restores the pause state from before admission. Returning
does not clear a pause retained after a departure. Native chat announces the
successful return/observer admission in en/ru/de/fr/cs/uk.

Admission uses a native checkpoint, accelerated native transfer and a shared
load barrier inside the existing network session. Native authentication,
version, password and CRC validation remain in place. Everyone must update to
the same beta and use matching gameplay components. The old integrated
save-and-return-to-lobby recovery is deliberately excluded from every Arcane
helper; the separate Pure recovery implementation is unchanged.

If the current host disappears while admission is pending, the survivors retain
the match and pause; uncommitted arrivals return to the multiplayer lobby and
must retry with the elected host. Native resign requests are deferred until the
admission transaction settles. These are intentional ongoing policies.

## Build and installation

`release_runtime.c` builds as an x86 TinyCC DLL. It shares the reviewed native
implementation in `../hotjoin-test`, compiled with `PAWS_HOTJOIN_RELEASE`.
That mode excludes the lab marker, test hold files, command-file loop, actor
traces and periodic QA dumps. It exposes only the helper's queued installation
handshake/status exports. Its fixed production wire revision is R; laboratory
environment switches cannot alter it.

`PawHotJoin.cs` is included in the managed helper and embeds that DLL as
`PawHotJoinNative`. The helper extracts it into a hash-addressed private cache,
verifies it, validates the fresh process and native hook sites, suspends the
process while its dedicated worker installs the runtime, checks completion,
then resumes. Failure aborts the incomplete game launch. Runtime logging is
`Logs/paws_hotjoin.log`; personal credentials are omitted.

The normal builder supports `game/beta7/build.ps1 -HotJoin` with the full Arcane
helper prerequisites. For this release, `build_beta.py` replays the archived
0.5.0-beta.1 build report, first verifying every source/resource digest. It
retains the accepted mixed-biome, interface and other gameplay payloads while
adding this runtime and changing the version. Example, from the checkout:

```powershell
python game/hotjoin/build_beta.py --baseline ../../outputs/release-042-050-20261106/beta/build-report.json --out ../../outputs/hotjoin-beta-20261107/rebuild --version 0.5.0-beta.2 --compiler ../../work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe
```

The archived build report and its pinned local inputs are required; the
repository does not contain the original game or all generated binary payloads.
The accepted final build is `../../outputs/hotjoin-beta-20261107/helpers-r5`.
It retains `build-report.json`, `native-inputs.json`, exact generated C# inputs,
compiler arguments, resource hashes and the 40 helper self-test results.
`tools/PrepareHotJoinBeta.py` stages/signs Arcane-only packages/catalogs using an
external signing key. It does not install or publish anything by itself.

## Verification boundary

See `docs/verification-hotjoin-release-20261107.md` for the final packaged
runtime tests, actual installation/rollback matrix and publication provenance.
The separate laboratory README retains earlier accepted and failed attempts;
their long soak and complete scenario matrix are not reruns of this final
packaged binary. Local multiple-process LAN acceptance does not establish
Steam Internet behavior across separate computers/NATs.
